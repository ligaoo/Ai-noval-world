from __future__ import annotations

import json
from pathlib import Path
from typing import Literal, Optional

from app.llm_client import OpenAICompatibleClient
from app.models.interaction import AgentIntent, AgentPerception, IntentActionType
from app.models.state import WorldState
from app.models.world import CharacterProfile, WorldConfig
from app.services.prompt_template_service import PromptTemplateService
from app.services.trace_service import TraceService


class AgentMindService:
    def __init__(
        self,
        project_root: Path,
        world: WorldConfig,
        mode: Literal["scripted", "heuristic", "llm"],
        llm_client: Optional[OpenAICompatibleClient] = None,
        trace_service: Optional[TraceService] = None,
        temperature: float = 0.2,
    ):
        self.world = world
        self.mode = mode
        self.llm_client = llm_client
        self.trace_service = trace_service
        self.temperature = temperature
        self.templates = PromptTemplateService(project_root, world.world_id)
        self.policy = self.templates.load_policy()

    def decide_intent(
        self,
        state: WorldState,
        profile: CharacterProfile,
        perception: AgentPerception,
    ) -> AgentIntent:
        if self.mode == "llm" and self.llm_client:
            try:
                return self._llm_intent(state, profile, perception)
            except Exception:
                return self._heuristic_intent(state, profile, perception)
        return self._heuristic_intent(state, profile, perception)

    def _heuristic_intent(
        self,
        state: WorldState,
        profile: CharacterProfile,
        perception: AgentPerception,
    ) -> AgentIntent:
        runtime = state.characters[profile.id]
        target_agent = perception.visible_agents[0] if perception.visible_agents else None
        target_object = perception.visible_objects[0] if perception.visible_objects else None
        target_location = None
        action_type: IntentActionType = "wait"
        intention = "maintain current position and reassess available information"
        will_hide = []
        will_say = []
        topic = None

        disclosure_policy = profile.disclosure_policy or {}
        has_secret = bool(profile.secrets)
        low_trust_target = False
        if target_agent and target_agent in runtime.relationships:
            rel = runtime.relationships[target_agent]
            low_trust_target = rel.trust < 0 or rel.suspicion > 1

        if target_agent and has_secret and disclosure_policy.get("can_withhold", True):
            action_type = "withhold"
            intention = "avoid exposing private information while staying responsive"
            will_hide = list(profile.secrets[:3])
            public_facts = [fact for fact in perception.known_facts if fact not in profile.secrets]
            will_say = public_facts[:2]
            topic = self._first_topic(target_agent)
        elif target_agent and (runtime.suspicions or low_trust_target):
            action_type = "challenge"
            intention = "test whether the other character is reliable"
            will_say = runtime.suspicions[:2]
            topic = self._first_topic(target_agent)
        elif target_agent and perception.known_facts:
            action_type = "share_info"
            intention = "share useful known information with another present character"
            will_say = perception.known_facts[:2]
            topic = self._first_topic(target_agent)
        elif target_object:
            action_type = "inspect"
            intention = "inspect a visible object for useful information"
        else:
            next_location = self._first_connected_location(runtime.location_id)
            if next_location:
                action_type = "move"
                target_location = next_location
                intention = "move to an adjacent location to gather more information"

        intent = AgentIntent(
            agent_id=profile.id,
            intent_id=f"intent_{state.tick:04d}_{profile.id}",
            scene_id=perception.scene_id,
            intention=intention,
            action_type=action_type,
            target_agents=[target_agent] if target_agent else [],
            target_object=target_object if action_type == "inspect" else None,
            target_location=target_location,
            topic=topic,
            will_say=will_say,
            will_hide=will_hide,
            referenced_fact_ids=self._fact_ids_for_texts(state, will_say + will_hide),
            behavioral_leak_risk=self._behavioral_risk(profile, action_type),
            risk_level="medium" if action_type in {"withhold", "lie", "challenge"} else "low",
            pressure_level=1 if action_type in {"ask", "challenge", "accuse"} else 0,
        )
        runtime.current_intention = intent.intention
        runtime.last_intent_signature = f"{intent.action_type}:{intent.topic}:{intent.target_agents}:{intent.target_object}:{intent.target_location}"
        return intent

    def _llm_intent(
        self,
        state: WorldState,
        profile: CharacterProfile,
        perception: AgentPerception,
    ) -> AgentIntent:
        if not self.llm_client:
            raise RuntimeError("LLM client required")
        system_prompt = self.templates.render(
            "agent_mind_system.txt",
            {},
        )
        user_prompt = self.templates.render(
            "agent_mind_user.txt",
            {
                "character": profile.model_dump(),
                "runtime": state.characters[profile.id].model_dump(),
                "perception": perception.model_dump(),
                "policy": self.policy,
            },
        )
        response = self.llm_client.chat_json(
            system=system_prompt,
            user=user_prompt,
            temperature=self.temperature,
        )
        intent = AgentIntent.model_validate(response)
        if intent.agent_id != profile.id or intent.scene_id != perception.scene_id:
            raise ValueError("LLM intent identity mismatch")
        return intent

    def _first_topic(self, target_agent: str) -> Optional[str]:
        topics = self.world.clues.all_topics_for_target(target_agent)
        return topics[0] if topics else None

    def _first_connected_location(self, location_id: str) -> Optional[str]:
        loc = self.world.map.get_location(location_id)
        return loc.connected_to[0] if loc.connected_to else None

    @staticmethod
    def _behavioral_risk(profile: CharacterProfile, action_type: str) -> list[str]:
        if action_type not in {"withhold", "lie", "refuse"}:
            return []
        risks = []
        if profile.fears:
            risks.append("stress_response")
        if profile.secrets:
            risks.append("guarded_reaction")
        return risks

    @staticmethod
    def _fact_ids_for_texts(state: WorldState, texts: list[str]) -> list[str]:
        fact_ids = []
        for fact_id, entry in state.world.fact_exposure.items():
            if entry.truth in texts or fact_id in texts:
                fact_ids.append(fact_id)
        return fact_ids
