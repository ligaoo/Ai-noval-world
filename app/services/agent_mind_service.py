from __future__ import annotations

import json
from pathlib import Path
from typing import Literal, Optional

from app.llm_client import OpenAICompatibleClient
from app.models.interaction import (
    AgentIntent,
    AgentPerception,
    IntentActionType,
    InterruptionResult,
    ReactionIntent,
    SpeechSegment,
    TurnState,
)
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
        high_trust_target = False
        if target_agent and target_agent in runtime.relationships:
            rel = runtime.relationships[target_agent]
            low_trust_target = rel.trust < 0 or rel.suspicion > 1 or rel.hostility > 1
            high_trust_target = rel.trust > 1 or rel.affinity > 1
        blocked_goal = any(goal.status == "blocked" for goal in runtime.goals.values())
        unresolved_memory = any(
            keyword in memory.lower()
            for memory in perception.relevant_memories
            for keyword in ["conflict", "unresolved", "隐瞒", "怀疑", "冲突"]
        )

        readiness = self._leadership_readiness(state, profile)
        if target_agent and blocked_goal:
            action_type = "challenge" if low_trust_target or unresolved_memory else "suggest"
            intention = "press for a path around a blocked personal goal"
            will_say = [perception.active_goals[0]] if perception.active_goals else ["We need to settle what is blocking us."]
            topic = self._first_topic(target_agent)
        elif target_agent and has_secret and disclosure_policy.get("can_withhold", True) and (low_trust_target or unresolved_memory):
            action_type = "withhold"
            intention = "avoid exposing private information while staying responsive"
            will_hide = list(profile.secrets[:3])
            will_say = self._select_sayable_facts(state, profile, perception, target_agent, "withhold", 0, 1)
            if not will_say:
                will_say = ["I need to understand what you saw first."]
            topic = self._first_topic(target_agent)
        elif target_agent and (runtime.suspicions or low_trust_target or unresolved_memory):
            action_type = "accuse" if low_trust_target and readiness >= 3 else ("challenge" if readiness >= 2 else "ask")
            intention = "test reliability without claiming more than the character can support"
            will_say = runtime.suspicions[:1] if readiness >= 2 and runtime.suspicions else ["What makes you say that?"]
            topic = self._first_topic(target_agent)
        elif target_agent and high_trust_target and perception.known_facts:
            sayable = self._select_sayable_facts(state, profile, perception, target_agent, "share_info", 0, 1)
            action_type = "share_info" if sayable else "ask"
            intention = "support a trusted present character by keeping discussion focused on verification"
            will_say = sayable or ["I am with you on this, but we should verify it carefully."]
            topic = self._first_topic(target_agent)
        elif target_agent and perception.known_facts:
            sayable = self._select_sayable_facts(state, profile, perception, target_agent, "share_info", 0, 1)
            if sayable and readiness >= 1:
                action_type = "share_info"
                intention = "share one safe piece of known information with another present character"
                will_say = sayable
            else:
                action_type = "ask"
                intention = "ask for more context before taking the lead"
                will_say = ["Tell me what you noticed before we decide what it means."]
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
            private_interest=self._private_interest(profile),
            conflict_buttons=self._conflict_buttons(profile, action_type),
            claimed_fact_ids=self._fact_ids_for_texts(state, will_say),
            claim_mode="known" if action_type in {"share_info", "answer"} and will_say else "unknown",
        )
        runtime.current_intention = intent.intention
        runtime.last_intent_signature = f"{intent.action_type}:{intent.topic}:{intent.target_agents}:{intent.target_object}:{intent.target_location}"
        return intent

    def decide_reaction_intent(
        self,
        state: WorldState,
        profile: CharacterProfile,
        perception: AgentPerception,
        current_speaker: str,
        spoken_segment: SpeechSegment,
        turn_state: TurnState,
        interaction_context: dict | None = None,
    ) -> ReactionIntent:
        focus = spoken_segment.exposes_fact_ids[0] if spoken_segment.exposes_fact_ids else spoken_segment.content_summary
        buttons = set(self._conflict_buttons(profile, "challenge"))
        text = ""
        reaction_type = "hold"
        urgency = 0
        pressure_delta = 0
        reason = "no immediate need to take the turn"
        if spoken_segment.exposes_fact_ids and buttons & {"secret_exposure", "information_control"}:
            reaction_type = "block_disclosure"
            urgency = 5
            pressure_delta = 2
            text = "Stop. Don't say more about that."
            reason = "the segment threatens controlled information"
        elif spoken_segment.trigger_keywords and buttons & {"fear_trigger", "personal_stakes", "goal_obstruction"}:
            reaction_type = "challenge"
            urgency = 3
            pressure_delta = 1
            text = "Why are you bringing that up now?"
            reason = "the segment presses a conflict button"
        elif spoken_segment.exposure_level in {"medium", "high"}:
            reaction_type = "observe"
            urgency = 1
            reason = "the segment may reveal useful information"
        return ReactionIntent(
            reaction_id=f"react_{state.tick:04d}_{profile.id}_{spoken_segment.segment_id}",
            agent_id=profile.id,
            reaction_type=reaction_type,
            trigger_segment_id=spoken_segment.segment_id,
            target_speaker=current_speaker,
            spoken_text=text,
            reason=reason,
            urgency=urgency,
            pressure_delta=pressure_delta,
            focus=focus,
            intent_source="agent_mind",
        )

    def decide_post_interruption_reaction(
        self,
        state: WorldState,
        profile: CharacterProfile,
        interruption_result: InterruptionResult,
        facts_already_revealed: list[str],
        facts_prevented: list[str],
        pressure: int,
    ) -> ReactionIntent:
        reaction_type = "continue_speaking"
        spoken_text = "Let me finish."
        reason = "try to continue after being interrupted"
        if profile.secrets or facts_prevented:
            reaction_type = "deflect" if pressure >= 3 else "redirect"
            spoken_text = "That's not the point right now."
            reason = "avoid reopening the prevented disclosure"
        elif pressure >= 4:
            reaction_type = "challenge"
            spoken_text = "Why are you stopping me?"
            reason = "pressure makes the interruption feel hostile"
        return ReactionIntent(
            reaction_id=f"post_react_{state.tick:04d}_{profile.id}_{interruption_result.interruption_id}",
            agent_id=profile.id,
            reaction_type=reaction_type,
            trigger_segment_id=interruption_result.trigger_segment_id,
            target_speaker=interruption_result.interrupter,
            spoken_text=spoken_text,
            reason=reason,
            urgency=max(1, pressure // 2),
            pressure_delta=1 if reaction_type in {"challenge", "continue_speaking"} else 0,
            focus=",".join(facts_prevented or facts_already_revealed),
            intent_source="agent_mind",
        )

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
        if not intent.private_interest:
            intent.private_interest = self._private_interest(profile)
        if not intent.conflict_buttons:
            intent.conflict_buttons = self._conflict_buttons(profile, intent.action_type)
        if not intent.claimed_fact_ids:
            intent.claimed_fact_ids = self._fact_ids_for_texts(state, intent.claimed_facts or intent.will_say)
        return intent

    def _first_topic(self, target_agent: str) -> Optional[str]:
        topics = self.world.clues.all_topics_for_target(target_agent)
        return topics[0] if topics else None

    def _first_connected_location(self, location_id: str) -> Optional[str]:
        loc = self.world.map.get_location(location_id)
        return loc.connected_to[0] if loc.connected_to else None

    @staticmethod
    def _private_interest(profile: CharacterProfile) -> str:
        for key in ("private_motive", "personal_stakes", "withheld_information"):
            value = getattr(profile, key, "")
            if value:
                return str(value)
        if profile.goals:
            return str(profile.goals.get("short_term") or profile.goals.get("long_term") or profile.goals)
        if profile.fears:
            return f"avoid {profile.fears[0]}"
        if profile.secrets:
            return "keep private information controlled"
        return "preserve current position"

    @staticmethod
    def _conflict_buttons(profile: CharacterProfile, action_type: str) -> list[str]:
        buttons = []
        if profile.secrets or getattr(profile, "withheld_information", ""):
            buttons.extend(["secret_exposure", "information_control"])
        if profile.fears:
            buttons.append("fear_trigger")
        if profile.personal_stakes or getattr(profile, "private_motive", ""):
            buttons.append("personal_stakes")
        if profile.goals:
            buttons.append("goal_obstruction")
        if action_type in {"withhold", "lie", "refuse", "retreat", "escape"}:
            buttons.append("self_preservation")
        return list(dict.fromkeys(buttons or ["self_preservation"]))

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

    def _select_sayable_facts(
        self,
        state: WorldState,
        profile: CharacterProfile,
        perception: AgentPerception,
        target_agent: str | None,
        action_type: str,
        pressure: int,
        round_no: int,
    ) -> list[str]:
        direct_actions = {"answer", "share_info", "trade_info"}
        if action_type not in direct_actions and pressure < 3:
            return []
        runtime = state.characters[profile.id]
        relationship = runtime.relationships.get(target_agent) if target_agent else None
        trust = relationship.trust if relationship else 0
        suspicion = relationship.suspicion if relationship else 0
        candidates: list[tuple[int, str]] = []
        for fact_id, entry in state.world.fact_exposure.items():
            if profile.id not in entry.known_by:
                continue
            if entry.truth not in perception.known_facts and fact_id not in perception.known_facts:
                continue
            if entry.truth in profile.secrets or fact_id in profile.secrets:
                continue
            if pressure < entry.min_pressure_to_reveal:
                continue
            if round_no < entry.min_rounds_to_reveal:
                continue
            if suspicion > trust + 1 and pressure < 3:
                continue
            sensitive = entry.reveal_stage in {"hidden_fact", "secret", "forbidden"}
            if sensitive and pressure < max(3, entry.min_pressure_to_reveal):
                continue
            score = trust - suspicion + pressure - int(sensitive)
            candidates.append((score, entry.truth))
        candidates.sort(reverse=True)
        limit = 1 if pressure >= 3 else 2
        return [truth for _, truth in candidates[:limit]]

    @staticmethod
    def _leadership_readiness(state: WorldState, profile: CharacterProfile) -> int:
        runtime = state.characters[profile.id]
        evidence = len(runtime.known_facts)
        trusted_ties = sum(1 for rel in runtime.relationships.values() if rel.trust > rel.suspicion)
        danger_words = {"danger", "protect", "leader", "decisive", "brave", "冷静", "果断", "保护"}
        traits = profile.personality.get("traits") if isinstance(profile.personality, dict) else []
        trait_text = " ".join(str(item) for item in (traits if isinstance(traits, list) else [traits]))
        role_text = f"{profile.role} {' '.join(profile.narrative_function)} {trait_text}".lower()
        pressure = max((entry.min_pressure_to_reveal for entry in state.world.fact_exposure.values() if profile.id in entry.known_by), default=0)
        readiness = 0
        if evidence >= 2:
            readiness += 1
        if trusted_ties:
            readiness += 1
        if pressure >= 3 or any(word in role_text for word in danger_words):
            readiness += 1
        return readiness

    @staticmethod
    def _fact_ids_for_texts(state: WorldState, texts: list[str]) -> list[str]:
        fact_ids = []
        for fact_id, entry in state.world.fact_exposure.items():
            if entry.truth in texts or fact_id in texts or entry.public_label in texts:
                fact_ids.append(fact_id)
        return fact_ids
