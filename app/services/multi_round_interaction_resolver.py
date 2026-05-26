from __future__ import annotations

from typing import Dict, List, Optional, Set

from app.models.interaction import (
    AgentDrivenInteractionResult,
    AgentIntent,
    AgentPerception,
    InteractionProposal,
    InteractionResult,
    InteractionRound,
    ReactionIntent,
    ScenePresence,
    SpeechSegment,
    TurnState,
)
from app.models.state import WorldState
from app.models.world import WorldConfig
from app.services.agent_driven_orchestrator import AgentDrivenOrchestrator
from app.services.exposure_tracker import ExposureTracker
from app.services.fact_exposure_matrix import FactExposureMatrix
from app.services.interrupt_arbitrator import InterruptArbitrator
from app.services.perception_resolver import PerceptionResolver
from app.services.sandbox_guardrail_service import SandboxGuardrailService
from app.services.speech_segmenter import SpeechSegmenter


class MultiRoundInteractionResolver:
    def __init__(
        self,
        fact_matrix: FactExposureMatrix,
        perception_resolver: PerceptionResolver,
        max_rounds: int = 5,
        agent_mind=None,
        speech_segmenter: SpeechSegmenter | None = None,
        interrupt_arbitrator: InterruptArbitrator | None = None,
        exposure_tracker: ExposureTracker | None = None,
        world: WorldConfig | None = None,
    ):
        self.fact_matrix = fact_matrix
        self.perception_resolver = perception_resolver
        self.max_rounds = max_rounds
        self.agent_mind = agent_mind
        self.speech_segmenter = speech_segmenter or SpeechSegmenter()
        self.interrupt_arbitrator = interrupt_arbitrator or InterruptArbitrator()
        self.exposure_tracker = exposure_tracker or ExposureTracker()
        self.guardrail = SandboxGuardrailService()
        self.agent_driven_orchestrator: AgentDrivenOrchestrator | None = None
        self.last_agent_driven_result: AgentDrivenInteractionResult | None = None
        if world:
            self.agent_driven_orchestrator = AgentDrivenOrchestrator(world)

    def resolve(
        self,
        state: WorldState,
        scene: ScenePresence,
        proposal: InteractionProposal,
    ) -> InteractionResult:
        result = self._resolve_segment_driven(state, scene, proposal)

        self.last_agent_driven_result = None
        if self.agent_driven_orchestrator:
            agent_result = self.agent_driven_orchestrator.process_interaction(
                proposal,
                state,
            )
            self.last_agent_driven_result = agent_result
            self.agent_driven_orchestrator.apply_structured_results_to_interaction(
                agent_result,
                result,
            )
            self._append_agent_reactions_as_intents(agent_result, result)

        return result

    def _append_agent_reactions_as_intents(
        self,
        agent_result: AgentDrivenInteractionResult,
        result: InteractionResult,
    ) -> None:
        """
        将 Agent 驱动的反应转换为 InteractionResult 中的 intents/reactions。
        这样 Writer 只能消费这些结构化结果，不能自行决定冲突。
        """
        for reaction in agent_result.agent_reactions:
            if not reaction.will_express:
                continue

            reaction_intent = ReactionIntent(
                reaction_id=reaction.reaction_id,
                agent_id=reaction.agent_id,
                reaction_type=reaction.reaction_type
                if reaction.reaction_type in {
                    "interrupt", "observe", "hold", "challenge",
                    "clarify", "probe", "block_disclosure",
                    "support", "redirect", "leave", "deflect", "continue_speaking"
                }
                else "observe",
                target_speaker=reaction.target_agent,
                spoken_text=reaction.spoken_text,
                reason=reaction.reasoning,
                urgency=reaction.urgency,
                pressure_delta=reaction.pressure_delta,
                intent_source=reaction.trigger_source
                if reaction.trigger_source in {"agent_mind", "director_intervention", "system_seed"}
                else "agent_mind",
            )
            result.reaction_intents.append(reaction_intent)

    def _resolve_legacy(
        self,
        state: WorldState,
        scene: ScenePresence,
        proposal: InteractionProposal,
    ) -> InteractionResult:
        rounds: List[InteractionRound] = []
        revealed: List[str] = []
        still_hidden: List[str] = []
        suspected: Dict[str, Dict[str, float]] = {}
        relationship_changes: List[dict] = []
        state_changes: List[dict] = []
        pressure = max((intent.pressure_level for intent in proposal.intents), default=0)
        visible_to = sorted(set(proposal.participants + proposal.observers))

        for idx, intent in enumerate(proposal.intents[: self.max_rounds], start=1):
            if intent.action_type in {"ask", "challenge", "accuse"}:
                pressure += max(1, intent.pressure_level)
            elif intent.action_type in {"withhold", "lie", "refuse"}:
                pressure += 1

            stage = self._pressure_stage(pressure)
            says = self._safe_say(state, intent.agent_id, intent.will_say, pressure)
            hidden = list(intent.will_hide)
            referenced_fact_ids = set(intent.referenced_fact_ids) | set(intent.claimed_fact_ids)
            referenced_fact_ids.update(self._fact_ids_for_texts(state, intent.claimed_facts))

            if intent.action_type in {"share_info", "answer", "trade_info"}:
                revealed.extend(
                    self._revealable_facts(
                        state, intent.agent_id, referenced_fact_ids, pressure, idx, intent.action_type
                    )
                )
            elif intent.action_type in {"withhold", "lie", "refuse"}:
                still_hidden.extend(hidden)
            elif intent.action_type in {"challenge", "accuse"}:
                for target_id in intent.target_agents:
                    relationship_changes.append(
                        {
                            "from": intent.agent_id,
                            "to": target_id,
                            "trust_delta": 0,
                            "suspicion_delta": 1,
                        }
                    )

            if intent.claim_mode == "known":
                revealed.extend(
                    self._revealable_facts(
                        state, intent.agent_id, referenced_fact_ids, pressure, idx, intent.action_type
                    )
                )
            elif intent.claim_mode == "suspected":
                for fact in self._claim_labels(state, intent.claimed_facts, referenced_fact_ids):
                    suspected.setdefault(fact, {})[intent.agent_id] = max(0.4, min(0.8, intent.raw_confidence))
            elif intent.claim_mode == "misdirect":
                for fact in self._claim_labels(state, intent.claimed_facts, referenced_fact_ids):
                    state_changes.append(
                        {
                            "type": "misunderstood_fact",
                            "fact": fact,
                            "fact_id": self._fact_id_for_text(state, fact) or fact,
                            "character_id": intent.agent_id,
                            "misunderstanding": fact,
                        }
                    )

            if stage in {"guarded", "challenged"} and intent.action_type in {"withhold", "lie", "refuse"} and not says:
                says = ["gives a guarded response" if stage == "guarded" else "offers an inconsistent explanation"]
            elif stage in {"cracked", "forced"} and intent.action_type in {"withhold", "lie", "refuse"} and not says:
                says = ["hesitates under pressure"]

            observers = [cid for cid in visible_to if cid != intent.agent_id]
            notices = self.perception_resolver.resolve_notices(
                state,
                scene,
                intent,
                observers,
                proposal.interaction_id,
                pressure,
            )
            for notice in notices:
                for fact, confidence in notice.suspected_facts.items():
                    suspected.setdefault(fact, {})[notice.observer] = confidence
                for target_id, delta in notice.relationship_deltas.items():
                    relationship_changes.append(
                        {
                            "from": notice.observer,
                            "to": target_id,
                            "trust_delta": delta,
                            "suspicion_delta": abs(delta),
                        }
                    )
            rounds.append(
                InteractionRound(
                    round=idx,
                    speaker=intent.agent_id,
                    action=intent.action_type,
                    says_summary="; ".join(says),
                    hides=hidden,
                    pressure_level=pressure,
                    notices=notices,
                )
            )
            if idx >= self.max_rounds:
                break

        revealed = self._dedupe(revealed)
        still_hidden = self._dedupe(still_hidden)
        revealed = [fact for fact in revealed if fact not in still_hidden]
        agent_goal_results = self._goal_results(proposal, revealed, still_hidden, suspected)
        return InteractionResult(
            interaction_id=proposal.interaction_id,
            interaction_type=proposal.interaction_type,
            scene_id=proposal.scene_id,
            location_id=proposal.location_id,
            participants=proposal.participants,
            observers=proposal.observers,
            topic=proposal.topic,
            rounds=rounds,
            agent_goal_results=agent_goal_results,
            revealed_facts=revealed,
            still_hidden_facts=still_hidden,
            suspected_facts=suspected,
            relationship_changes=relationship_changes,
            state_changes=state_changes,
            plot_changes={
                "progress_delta": min(6, len(revealed) + len(suspected) + len(rounds)),
                "opened_threads": [],
                "primary_conflict": proposal.primary_conflict,
            },
            visible_to=visible_to,
            hidden_effects=still_hidden,
        )

    def _resolve_segment_driven(
        self,
        state: WorldState,
        scene: ScenePresence,
        proposal: InteractionProposal,
    ) -> InteractionResult:
        rounds: List[InteractionRound] = []
        speech_plans = []
        spoken_segments: List[SpeechSegment] = []
        prevented_segments: List[SpeechSegment] = []
        reaction_intents: List[ReactionIntent] = []
        interruption_results = []
        post_reactions: List[ReactionIntent] = []
        turn_states: List[TurnState] = []
        relationship_changes: List[dict] = []
        pressure = max((intent.pressure_level for intent in proposal.intents), default=0)
        visible_to = sorted(set(proposal.participants + proposal.observers + self._audible_agents(scene)))
        round_no = 0
        transfer_count = 0
        max_turn_transfers = max(1, self.max_rounds - 1)
        max_segments_per_turn = max(1, min(3, self.max_rounds))
        max_pressure = 6
        turn_queue = self._queue_initial_turns(proposal)
        repeated_speakers: Dict[str, int] = {}

        while turn_queue and round_no < self.max_rounds:
            intent = turn_queue.pop(0)
            repeated_speakers[intent.agent_id] = repeated_speakers.get(intent.agent_id, 0) + 1
            if repeated_speakers[intent.agent_id] > 2:
                continue
            interrupted = False
            plan = self.speech_segmenter.build_plan(state, intent, max_segments_per_turn)
            speech_plans.append(plan)
            if not plan.segments:
                continue
            turn_state = TurnState(
                interaction_id=proposal.interaction_id,
                current_speaker=intent.agent_id,
                speech_state="in_progress",
                pressure=pressure,
            )
            for idx, segment in enumerate(plan.segments[:max_segments_per_turn]):
                if round_no >= self.max_rounds:
                    break
                turn_state.current_segment_id = segment.segment_id
                turn_states.append(turn_state.model_copy(deep=True))
                spoken_segments.append(segment)
                round_no += 1
                rounds.append(
                    InteractionRound(
                        round=round_no,
                        speaker=segment.speaker,
                        action="say",
                        says_summary=segment.spoken_text or segment.content_summary,
                        hides=[],
                        pressure_level=pressure,
                        round_type="speech_segment",
                        segment_id=segment.segment_id,
                        intent_source=segment.intent_source,
                        turn_owner_after=intent.agent_id,
                    )
                )
                reactions = self._reaction_intents_for_segment(state, scene, proposal, intent.agent_id, segment, turn_state)
                self._ensure_withheld_fact_reaction(state, scene, proposal, intent.agent_id, segment, reactions)
                reaction_intents.extend(reactions)
                if reactions and transfer_count < max_turn_transfers:
                    interruption = self.interrupt_arbitrator.arbitrate(reactions, segment, turn_state, self._agent_scores(scene, state))
                    if interruption.result != "no_interrupt":
                        interruption.prevented_fact_ids = self._segment_fact_ids(plan.segments[idx + 1 :])
                        interruption_results.append(interruption)
                    if interruption.success:
                        prevented_segments.extend(plan.segments[idx + 1 :])
                        transfer_count += 1
                        pressure = min(max_pressure, pressure + max(1, max((reaction.pressure_delta for reaction in reactions), default=0)))
                        if round_no >= self.max_rounds:
                            interrupted = True
                            break
                        round_no += 1
                        rounds.append(
                            InteractionRound(
                                round=round_no,
                                speaker=interruption.interrupter or "",
                                action="interrupt",
                                says_summary=interruption.spoken_text,
                                pressure_level=pressure,
                                round_type="interruption",
                                segment_id=segment.segment_id,
                                intent_source=interruption.intent_source,
                                interrupted_by=interruption.interrupter,
                                turn_owner_after=interruption.turn_owner,
                            )
                        )
                        turn_state = TurnState(
                            interaction_id=proposal.interaction_id,
                            current_speaker=interruption.turn_owner,
                            previous_speaker=intent.agent_id,
                            speech_state="interrupted",
                            current_segment_id=segment.segment_id,
                            turn_shift_reason=interruption.reason,
                            pressure=pressure,
                            others_can_interrupt=True,
                        )
                        turn_states.append(turn_state)
                        profile = self.agent_mind.world.characters.get_character(intent.agent_id)
                        post = self.agent_mind.decide_post_interruption_reaction(
                            state,
                            profile,
                            interruption,
                            self._segment_fact_ids(spoken_segments),
                            interruption.prevented_fact_ids,
                            pressure,
                        )
                        post_reactions.append(post)
                        if round_no >= self.max_rounds:
                            next_turn = self._reaction_to_turn_intent(state, proposal, interruption, pressure)
                            if next_turn:
                                turn_queue.append(next_turn)
                            interrupted = True
                            break
                        round_no += 1
                        rounds.append(
                            InteractionRound(
                                round=round_no,
                                speaker=post.agent_id,
                                action=post.reaction_type,
                                says_summary=post.spoken_text,
                                pressure_level=pressure,
                                round_type="post_interruption_reaction",
                                segment_id=segment.segment_id,
                                intent_source=post.intent_source,
                                turn_owner_after=post.agent_id,
                            )
                        )
                        next_turn = self._reaction_to_turn_intent(state, proposal, interruption, pressure)
                        if next_turn:
                            turn_queue.append(next_turn)
                        if post.reaction_type in {"challenge", "continue_speaking"}:
                            turn_queue.append(self._post_reaction_to_turn_intent(state, proposal, post, pressure))
                        interrupted = True
                        break
            if not interrupted:
                turn_states.append(
                    TurnState(
                        interaction_id=proposal.interaction_id,
                        current_speaker=intent.agent_id,
                        speech_state="completed",
                        current_segment_id=plan.segments[-1].segment_id,
                        pressure=pressure,
                    )
                )

        exposure_update = self.exposure_tracker.build_update(
            state,
            scene,
            spoken_segments,
            prevented_segments,
            reaction_intents,
            interruption_results,
        )
        revealed = self._truths_for_fact_ids(state, [item.get("fact_id", "") for item in exposure_update.revealed_facts])
        suspected = self._suspicions_from_exposure(state, exposure_update.suspected_facts)
        for intent in proposal.intents:
            if intent.action_type in {"challenge", "accuse", "block", "call_out"}:
                for target_id in intent.target_agents:
                    relationship_changes.append({"from": intent.agent_id, "to": target_id, "trust_delta": 0, "suspicion_delta": 1})
        agent_goal_results = self._goal_results(proposal, revealed, [], suspected)
        return InteractionResult(
            interaction_id=proposal.interaction_id,
            interaction_type=proposal.interaction_type,
            scene_id=proposal.scene_id,
            location_id=proposal.location_id,
            participants=proposal.participants,
            observers=proposal.observers,
            topic=proposal.topic,
            rounds=rounds,
            agent_goal_results=agent_goal_results,
            revealed_facts=revealed,
            still_hidden_facts=[],
            suspected_facts=suspected,
            relationship_changes=relationship_changes,
            state_changes=[],
            plot_changes={
                "progress_delta": min(3, len(revealed)),
                "opened_threads": [],
                "primary_conflict": proposal.primary_conflict,
                "mystery_delta": len(suspected),
                "conflict_delta": len(interruption_results),
            },
            visible_to=visible_to,
            hidden_effects=[],
            speech_plans=speech_plans,
            spoken_segments=spoken_segments,
            prevented_segments=prevented_segments,
            reaction_intents=reaction_intents,
            interruption_results=interruption_results,
            post_interruption_reactions=post_reactions,
            turn_states=turn_states,
            exposure_update=exposure_update,
        )

    @staticmethod
    def _queue_initial_turns(proposal: InteractionProposal) -> List[AgentIntent]:
        return list(proposal.intents)

    def _reaction_to_turn_intent(
        self,
        state: WorldState,
        proposal: InteractionProposal,
        interruption,
        pressure: int,
    ) -> AgentIntent | None:
        if not interruption.interrupter or not interruption.spoken_text:
            return None
        return AgentIntent(
            agent_id=interruption.interrupter,
            intent_id=f"intent_{state.tick:04d}_{interruption.interrupter}_{len(proposal.intents)}_{pressure}",
            scene_id=proposal.scene_id,
            intention="claim a short follow-up after taking the turn",
            action_type="challenge",
            target_agents=[interruption.interrupted_speaker] if interruption.interrupted_speaker else [],
            topic=proposal.topic,
            will_say=[interruption.spoken_text],
            pressure_level=pressure,
        )

    def _post_reaction_to_turn_intent(
        self,
        state: WorldState,
        proposal: InteractionProposal,
        reaction: ReactionIntent,
        pressure: int,
    ) -> AgentIntent:
        return AgentIntent(
            agent_id=reaction.agent_id,
            intent_id=f"intent_{state.tick:04d}_{reaction.agent_id}_{reaction.reaction_id}",
            scene_id=proposal.scene_id,
            intention="briefly respond after losing the previous turn",
            action_type="challenge" if reaction.reaction_type == "challenge" else "answer",
            target_agents=[reaction.target_speaker] if reaction.target_speaker else [],
            topic=proposal.topic,
            will_say=[reaction.spoken_text] if reaction.spoken_text else [reaction.reason],
            pressure_level=pressure,
        )

    @staticmethod
    def _remaining_capacity(round_no: int, transfer_count: int, max_turn_transfers: int) -> bool:
        return round_no >= 0 and transfer_count <= max_turn_transfers

    def _agent_scores(self, scene: ScenePresence, state: WorldState) -> Dict[str, Dict[str, int]]:
        scores: Dict[str, Dict[str, int]] = {}
        for agent_id in self._audible_agents(scene):
            try:
                profile = self.agent_mind.world.characters.get_character(agent_id)
            except KeyError:
                continue
            skills = profile.skills or {}
            runtime = state.characters.get(agent_id)
            suspicion = max((rel.suspicion for rel in runtime.relationships.values()), default=0) if runtime else 0
            scores[agent_id] = {
                "dominance": int(skills.get("leadership", skills.get("willpower", 0))) // 25,
                "reaction_speed": int(skills.get("observation", skills.get("agility", 0))) // 30,
                "assertiveness": int(skills.get("presence", skills.get("logic", 0))) // 30 + min(2, suspicion),
            }
        return scores

    def _reaction_intents_for_segment(
        self,
        state: WorldState,
        scene: ScenePresence,
        proposal: InteractionProposal,
        current_speaker: str,
        segment: SpeechSegment,
        turn_state: TurnState,
    ) -> List[ReactionIntent]:
        reactions: List[ReactionIntent] = []
        candidates = [agent_id for agent_id in self._audible_agents(scene) if agent_id != current_speaker]
        for agent_id in candidates:
            try:
                profile = self.agent_mind.world.characters.get_character(agent_id)
            except KeyError:
                continue
            perception = AgentPerception(
                agent_id=agent_id,
                scene_id=scene.scene_id,
                location_id=scene.location_id,
                visible_agents=[cid for cid in scene.present_agents if cid != agent_id],
                audible_agents=[cid for cid in self._audible_agents(scene) if cid != agent_id],
                known_facts=self.fact_matrix.allowed_facts_for(state, agent_id),
                suspicions=list(state.characters.get(agent_id).suspicions if state.characters.get(agent_id) else []),
            )
            reactions.append(
                self.agent_mind.decide_reaction_intent(
                    state,
                    profile,
                    perception,
                    current_speaker,
                    segment,
                    turn_state,
                    {"interaction_id": proposal.interaction_id, "topic": proposal.topic},
                )
            )
        return reactions

    def _ensure_withheld_fact_reaction(
        self,
        state: WorldState,
        scene: ScenePresence,
        proposal: InteractionProposal,
        current_speaker: str,
        segment: SpeechSegment,
        reactions: List[ReactionIntent],
    ) -> None:
        if not segment.withheld_fact_ids:
            return
        if any(reaction.reaction_type in {"probe", "clarify", "observe", "challenge", "block_disclosure", "interrupt"} for reaction in reactions):
            return
        listener = next((agent_id for agent_id in self._audible_agents(scene) if agent_id != current_speaker), None)
        label = self._fact_label(state, segment.withheld_fact_ids[0])
        if listener:
            reactions.append(
                ReactionIntent(
                    reaction_id=f"react_{proposal.interaction_id}_{segment.segment_id}_withheld",
                    agent_id=listener,
                    reaction_type="probe",
                    trigger_segment_id=segment.segment_id,
                    target_speaker=current_speaker,
                    spoken_text="你刚才回避的是什么？",
                    reason="A referenced fact was withheld or blurred in speech.",
                    urgency=1,
                    pressure_delta=1,
                    focus=label,
                )
            )
            return
        reactions.append(
            ReactionIntent(
                reaction_id=f"react_{proposal.interaction_id}_{segment.segment_id}_withheld_observe",
                agent_id=current_speaker,
                reaction_type="observe",
                trigger_segment_id=segment.segment_id,
                target_speaker=current_speaker,
                reason="A referenced fact was withheld or blurred in speech.",
                focus=label,
            )
        )

    @staticmethod
    def _fact_label(state: WorldState, fact_id: str) -> str:
        entry = state.world.fact_exposure.get(fact_id)
        return (entry.public_label or fact_id) if entry else fact_id

    @staticmethod
    def _audible_agents(scene: ScenePresence) -> List[str]:
        agents = list(scene.present_agents)
        for nearby in scene.nearby_agents:
            if nearby.can_hear and nearby.character_id not in agents:
                agents.append(nearby.character_id)
        return sorted(agents)

    @staticmethod
    def _segment_fact_ids(segments: List[SpeechSegment]) -> List[str]:
        fact_ids: List[str] = []
        for segment in segments:
            for fact_id in segment.exposes_fact_ids:
                if fact_id not in fact_ids:
                    fact_ids.append(fact_id)
        return fact_ids

    @staticmethod
    def _truths_for_fact_ids(state: WorldState, fact_ids: List[str]) -> List[str]:
        truths: List[str] = []
        for fact_id in fact_ids:
            entry = state.world.fact_exposure.get(fact_id)
            truth = entry.truth if entry else fact_id
            if truth and truth not in truths:
                truths.append(truth)
        return truths

    @staticmethod
    def _suspicions_from_exposure(state: WorldState, suspected_items: List[dict]) -> Dict[str, Dict[str, float]]:
        suspected: Dict[str, Dict[str, float]] = {}
        for item in suspected_items:
            fact_id = str(item.get("fact_id") or item.get("label") or "")
            entry = state.world.fact_exposure.get(fact_id)
            label = str(item.get("label") or (entry.public_label if entry else fact_id))
            confidence = float(item.get("confidence", 0.5))
            for agent_id in item.get("suspected_by", []):
                suspected.setdefault(label, {})[agent_id] = confidence
        return suspected

    def _safe_say(self, state: WorldState, agent_id: str, facts: List[str], pressure: int = 0) -> List[str]:
        allowed = set(self.fact_matrix.allowed_facts_for(state, agent_id))
        safe = [fact for fact in facts if fact in allowed]
        return self.guardrail.sanitize_lines(safe, pressure)

    def _revealable_facts(
        self,
        state: WorldState,
        speaker_id: str,
        fact_ids: Set[str],
        pressure: int,
        round_no: int,
        action_type: str,
    ) -> List[str]:
        if action_type not in {"share_info", "answer", "trade_info"} and pressure < 4:
            return []
        revealed: List[str] = []
        for fact_id in fact_ids:
            entry = state.world.fact_exposure.get(fact_id)
            if not entry:
                continue
            if speaker_id not in entry.known_by:
                continue
            if pressure < entry.min_pressure_to_reveal:
                continue
            if round_no < entry.min_rounds_to_reveal:
                continue
            if not self.fact_matrix.can_reveal(fact_id):
                continue
            revealed.append(entry.truth)
        return revealed

    @staticmethod
    def _pressure_stage(pressure: int) -> str:
        if pressure <= 0:
            return "normal"
        if pressure == 1:
            return "guarded"
        if pressure == 2:
            return "challenged"
        if pressure == 3:
            return "cracked"
        return "forced"

    @staticmethod
    def _fact_ids_for_texts(state: WorldState, texts: List[str]) -> Set[str]:
        fact_ids: Set[str] = set()
        for text in texts:
            for fact_id, entry in state.world.fact_exposure.items():
                if text == fact_id or text == entry.truth or text == entry.public_label:
                    fact_ids.add(fact_id)
        return fact_ids

    @staticmethod
    def _fact_id_for_text(state: WorldState, text: str) -> str | None:
        for fact_id, entry in state.world.fact_exposure.items():
            if text == fact_id or text == entry.truth or text == entry.public_label:
                return fact_id
        return None

    @staticmethod
    def _claim_labels(state: WorldState, claimed_facts: List[str], fact_ids: Set[str]) -> List[str]:
        labels = list(claimed_facts)
        for fact_id in fact_ids:
            entry = state.world.fact_exposure.get(fact_id)
            if entry:
                labels.append(entry.public_label or fact_id)
        return labels

    @staticmethod
    def _dedupe(values: List[str]) -> List[str]:
        result: List[str] = []
        for value in values:
            if value and value not in result:
                result.append(value)
        return result

    @staticmethod
    def _goal_results(
        proposal: InteractionProposal,
        revealed: List[str],
        still_hidden: List[str],
        suspected: Dict[str, Dict[str, float]],
    ) -> Dict[str, Dict[str, str]]:
        results: Dict[str, Dict[str, str]] = {}
        for intent in proposal.intents:
            if intent.action_type in {"withhold", "lie", "refuse"}:
                results[intent.agent_id] = {
                    "preserve_hidden_information": "success" if still_hidden else "failed",
                    "avoid_suspicion": "failed" if suspected else "success",
                }
            elif intent.action_type in {"ask", "challenge", "accuse"}:
                results[intent.agent_id] = {
                    "increase_pressure": "success",
                    "get_confirmed_information": "success" if revealed else "failed",
                }
            else:
                results[intent.agent_id] = {"perform_intent": "success"}
        return results
