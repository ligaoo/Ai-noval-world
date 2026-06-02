from __future__ import annotations

from pathlib import Path
from typing import Literal, Optional

from app.llm_client import OpenAICompatibleClient
from app.models.action import ActionCommand
from app.models.event import EventLog
from app.models.interaction import SandboxTickResult
from app.models.state import WorldState
from app.models.world import WorldConfig
from app.services.action_arbitrator import ActionArbitrator
from app.services.agent_mind_service import AgentMindService
from app.services.agent_perception_service import AgentPerceptionService
from app.services.director_risk_checker import DirectorRiskChecker
from app.services.environment_engine import EnvironmentEngine
from app.services.event_log_service import EventLogService
from app.services.fact_exposure_matrix import FactExposureMatrix
from app.services.key_event_detector import KeyEventDetector
from app.services.key_event_discussion_builder import KeyEventDiscussionBuilder
from app.services.memory_service import MemoryService
from app.services.multi_round_interaction_resolver import MultiRoundInteractionResolver
from app.services.perception_resolver import PerceptionResolver
from app.services.prompt_template_service import PromptTemplateService
from app.services.sandbox_event_log_writer import SandboxEventLogWriter
from app.services.scene_conflict_builder import SceneConflictBuilder
from app.services.scene_presence_tracker import ScenePresenceTracker
from app.services.trace_service import TraceService
from app.services.world_state_updater import WorldStateUpdater


class AgentSandboxLoop:
    def __init__(
        self,
        project_root: Path,
        sim_dir: Path,
        world: WorldConfig,
        mode: Literal["scripted", "heuristic", "llm"],
        environment: EnvironmentEngine,
        event_service: EventLogService,
        memory_service: Optional[MemoryService] = None,
        llm_client: Optional[OpenAICompatibleClient] = None,
        trace_service: Optional[TraceService] = None,
        plot_arc_service=None,
        temperature: float = 0.2,
    ):
        self.project_root = project_root
        self.sim_dir = sim_dir
        self.world = world
        self.environment = environment
        self.event_service = event_service
        self.memory_service = memory_service
        self.fact_matrix = FactExposureMatrix(world)
        policy = PromptTemplateService(project_root, world.world_id).load_policy()
        visibility_policy = policy.get("default_visibility", {})
        self.presence_tracker = ScenePresenceTracker(world, visibility_policy)
        self.perception_service = AgentPerceptionService(self.presence_tracker, self.fact_matrix, memory_service)
        self.agent_mind = AgentMindService(
            project_root,
            world,
            mode,
            llm_client,
            trace_service,
            temperature,
        )
        self.arbitrator = ActionArbitrator()
        self.perception_resolver = PerceptionResolver(world)
        self.interaction_resolver = MultiRoundInteractionResolver(
            self.fact_matrix,
            self.perception_resolver,
            max_rounds=int(policy.get("max_interaction_rounds", 5)),
            agent_mind=self.agent_mind,
            world=self.world,
        )
        self.updater = WorldStateUpdater(self.fact_matrix)
        self.event_writer = SandboxEventLogWriter(world)
        self.conflict_builder = SceneConflictBuilder(world)
        self.director_checker = DirectorRiskChecker(world, self.fact_matrix, plot_arc_service)
        self.key_event_detector = KeyEventDetector()
        self.key_discussion_builder = KeyEventDiscussionBuilder(world)

    def run_tick(self, state: WorldState, recent_events: list[EventLog]) -> SandboxTickResult:
        self.fact_matrix.initialize_if_missing(state)
        scenes = self.presence_tracker.build_scenes(state)
        perceptions = {}
        intents = []
        interactions = []
        agent_driven_results = []
        event_ids = []
        key_discussions_this_tick = 0

        for scene in scenes:
            pending_event_ids, pending_interactions, pending_agent_results, pending_count = self._drain_pending_key_events(
                state,
                scene,
                max(0, 2 - key_discussions_this_tick),
            )
            event_ids.extend(pending_event_ids)
            interactions.extend(pending_interactions)
            agent_driven_results.extend(pending_agent_results)
            key_discussions_this_tick += pending_count
            active_agents = [
                cid
                for cid in scene.present_agents
                if self.world.characters.get_character(cid).active_agent
            ]
            for agent_id in active_agents:
                profile = self.world.characters.get_character(agent_id)
                perception = self.perception_service.build_perception(
                    state,
                    scene,
                    agent_id,
                    recent_events,
                )
                perceptions[agent_id] = perception
                intents.append(self.agent_mind.decide_intent(state, profile, perception))

            scene_intents = [intent for intent in intents if intent.scene_id == scene.scene_id]
            scene.goal_conflicts = self.conflict_builder.build_for_scene(state, scene, scene_intents)
            simple_intents, proposals = self.arbitrator.split_intents(scene_intents)
            for intent in simple_intents:
                new_event_ids, new_interactions, new_agent_results, discussion_count = self._apply_simple_intent(
                    state,
                    scene,
                    intent,
                    max(0, 2 - key_discussions_this_tick),
                )
                event_ids.extend(new_event_ids)
                interactions.extend(new_interactions)
                agent_driven_results.extend(new_agent_results)
                key_discussions_this_tick += discussion_count
            for proposal in proposals:
                result = self.interaction_resolver.resolve(state, scene, proposal)
                result = self.director_checker.check_and_correct(state, result)
                self.updater.apply_interaction_result(state, result)
                interactions.append(result)
                if self.interaction_resolver.last_agent_driven_result:
                    agent_driven_results.append(self.interaction_resolver.last_agent_driven_result)
                for event in self.event_writer.events_from_interaction(state, result):
                    self.event_service.append(self.sim_dir, event)
                    event_ids.append(event.event_id)
                    if self.memory_service:
                        self.memory_service.write_from_event(event, state)

        return SandboxTickResult(
            tick=state.tick,
            scenes=scenes,
            perceptions=perceptions,
            intents=intents,
            interactions=interactions,
            event_ids=event_ids,
            agent_driven_results=agent_driven_results,
        )

    def _apply_simple_intent(self, state: WorldState, scene, intent, discussion_budget: int = 0):
        action_type = intent.action_type
        if action_type not in {"observe", "inspect", "search", "move", "wait"}:
            return [], [], [], 0
        target = intent.target_location or intent.target_object or scene.location_id
        action = ActionCommand(
            agent_id=intent.agent_id,
            intent=intent.intention,
            action_type=action_type,
            target=target,
            topic=intent.topic,
            method="agent_sandbox",
            dialogue="; ".join(intent.will_say) if intent.will_say else None,
            expected_gain=intent.intention or "advance current goal",
            risk_level=intent.risk_level,
        )
        applied = self.environment.apply_action(state, action)
        event_ids = []
        interactions = []
        agent_driven_results = []
        discussion_count = 0
        visible_to = sorted(set(scene.present_agents))
        for event in applied.new_events:
            event.scene_id = scene.scene_id
            event.visible_to = visible_to
            event.perceived_by = visible_to
            if event.discovered_facts:
                event.event_level = "plot"
            self.event_service.append(self.sim_dir, event)
            event_ids.append(event.event_id)
            if self.memory_service:
                self.memory_service.write_from_event(event, state)
            for signal in self.key_event_detector.detect_from_event(state, event):
                if not self._register_key_signal(state, signal):
                    continue
                if not signal.requires_discussion or discussion_count >= discussion_budget:
                    continue
                result, discussion_event_ids, agent_result = self._resolve_key_discussion(state, scene, signal)
                interactions.append(result)
                event_ids.extend(discussion_event_ids)
                if agent_result:
                    agent_driven_results.append(agent_result)
                discussion_count += 1
        return event_ids, interactions, agent_driven_results, discussion_count

    @staticmethod
    def _register_key_signal(state: WorldState, signal) -> bool:
        existing_ids = {item.signal_id for item in state.world.pending_key_events + state.world.resolved_key_events}
        if signal.signal_id in existing_ids:
            return False
        state.world.pending_key_events.append(signal)
        return True

    def _drain_pending_key_events(self, state: WorldState, scene, discussion_budget: int):
        if discussion_budget <= 0:
            return [], [], [], 0
        event_ids = []
        interactions = []
        agent_driven_results = []
        discussion_count = 0
        pending = sorted(
            list(state.world.pending_key_events),
            key=lambda signal: signal.priority,
            reverse=True,
        )
        for signal in pending:
            if discussion_count >= discussion_budget:
                break
            if not signal.requires_discussion or signal.location_id != scene.location_id:
                continue
            result, discussion_event_ids, agent_result = self._resolve_key_discussion(state, scene, signal)
            interactions.append(result)
            event_ids.extend(discussion_event_ids)
            if agent_result:
                agent_driven_results.append(agent_result)
            discussion_count += 1
        return event_ids, interactions, agent_driven_results, discussion_count

    def _resolve_key_discussion(self, state: WorldState, scene, signal):
        proposal = self.key_discussion_builder.build(state, scene, signal)
        result = self.interaction_resolver.resolve(state, scene, proposal)
        result = self.director_checker.check_and_correct(state, result)
        self.updater.apply_interaction_result(state, result)
        discussion_event_ids = []
        for discussion_event in self.event_writer.events_from_interaction(state, result):
            self.event_service.append(self.sim_dir, discussion_event)
            discussion_event_ids.append(discussion_event.event_id)
            if self.memory_service:
                self.memory_service.write_from_event(discussion_event, state)
        signal.resolved_by_interaction_id = result.interaction_id
        if signal in state.world.pending_key_events:
            state.world.pending_key_events.remove(signal)
        state.world.resolved_key_events.append(signal)
        return result, discussion_event_ids, self.interaction_resolver.last_agent_driven_result
