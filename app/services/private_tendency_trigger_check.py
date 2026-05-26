from __future__ import annotations

import uuid
from typing import List, Optional

from app.models.interaction import (
    AgentReaction,
    InteractionProposal,
    PrivateTendencyTrigger,
)
from app.models.state import WorldState
from app.models.world import CharacterProfile, WorldConfig


class PrivateTendencyTriggerCheck:
    """
    私人倾向触发检查。
    检测 Agent 的秘密、个人恩怨、隐藏议程、恐惧等私人因素是否会改变其行为。
    不绑定任何固定剧情逻辑。
    """

    def __init__(self, world: WorldConfig):
        self.world = world

    def check_triggers(
        self,
        proposal: InteractionProposal,
        reactions: List[AgentReaction],
        state: WorldState,
    ) -> List[PrivateTendencyTrigger]:
        """
        检查所有参与者的私人倾向触发。
        """
        triggers: List[PrivateTendencyTrigger] = []
        all_agents = set(proposal.participants + proposal.observers)

        for agent_id in all_agents:
            profile = self._get_agent_profile(agent_id)
            if not profile:
                continue

            runtime = state.characters.get(agent_id)
            if not runtime:
                continue

            agent_triggers = self._check_agent_triggers(
                agent_id,
                profile,
                runtime,
                proposal,
                reactions,
                state,
            )
            triggers.extend(agent_triggers)

        return triggers

    def _check_agent_triggers(
        self,
        agent_id: str,
        profile: CharacterProfile,
        runtime,
        proposal: InteractionProposal,
        reactions: List[AgentReaction],
        state: WorldState,
    ) -> List[PrivateTendencyTrigger]:
        triggers: List[PrivateTendencyTrigger] = []

        triggers.extend(self._check_secret_protection(agent_id, profile, proposal, state))
        triggers.extend(self._check_hidden_agenda(agent_id, profile, proposal, state))
        triggers.extend(self._check_fear_response(agent_id, profile, proposal, state))
        triggers.extend(self._check_loyalty_override(agent_id, profile, runtime, proposal, state))
        triggers.extend(self._check_personal_grudge(agent_id, profile, runtime, proposal, state))

        self._apply_trigger_effects(triggers, reactions, agent_id)

        return triggers

    def _check_secret_protection(
        self,
        agent_id: str,
        profile: CharacterProfile,
        proposal: InteractionProposal,
        state: WorldState,
    ) -> List[PrivateTendencyTrigger]:
        triggers: List[PrivateTendencyTrigger] = []

        topic_text = proposal.topic or ""
        intent_text = " ".join(i.intention for i in proposal.intents)
        full_context = f"{topic_text} {intent_text}".lower()

        for idx, secret in enumerate(profile.secrets):
            secret_lower = secret.lower()
            overlap = self._word_overlap_count(secret_lower, full_context)
            if overlap >= 2:
                intensity = min(1.0, overlap / 4)
                trigger = PrivateTendencyTrigger(
                    trigger_id=f"tend_{uuid.uuid4().hex[:8]}",
                    agent_id=agent_id,
                    trigger_type="secret_protection",
                    trigger_condition=f"Discussion threatens secret #{idx}",
                    intensity=intensity,
                    overrides_intent=intensity > 0.7,
                    resulting_bias=f"Will withhold or deflect information related to secret #{idx}",
                    related_secret_index=idx,
                )
                triggers.append(trigger)

        return triggers

    def _check_hidden_agenda(
        self,
        agent_id: str,
        profile: CharacterProfile,
        proposal: InteractionProposal,
        state: WorldState,
    ) -> List[PrivateTendencyTrigger]:
        triggers: List[PrivateTendencyTrigger] = []

        hidden_agendas = self._extract_hidden_agendas(profile)
        for agenda in hidden_agendas:
            if self._agenda_is_impacted(agenda, proposal):
                trigger = PrivateTendencyTrigger(
                    trigger_id=f"tend_{uuid.uuid4().hex[:8]}",
                    agent_id=agent_id,
                    trigger_type="hidden_agenda",
                    trigger_condition="Discussion impacts hidden agenda",
                    intensity=0.6,
                    overrides_intent=False,
                    resulting_bias=f"Bias aligned with agenda: {agenda[:50]}",
                )
                triggers.append(trigger)

        return triggers

    def _check_fear_response(
        self,
        agent_id: str,
        profile: CharacterProfile,
        proposal: InteractionProposal,
        state: WorldState,
    ) -> List[PrivateTendencyTrigger]:
        triggers: List[PrivateTendencyTrigger] = []

        fears = self._extract_fears(profile)
        context_text = (proposal.topic or "").lower()
        for intent in proposal.intents:
            context_text += " " + intent.intention.lower()
            if intent.action_type in ("accuse", "challenge", "force_check"):
                fears.append("being accused")

        for fear in fears:
            fear_lower = fear.lower()
            if fear_lower in context_text or self._word_overlap_count(fear_lower, context_text) >= 2:
                trigger = PrivateTendencyTrigger(
                    trigger_id=f"tend_{uuid.uuid4().hex[:8]}",
                    agent_id=agent_id,
                    trigger_type="fear_response",
                    trigger_condition=f"Fear triggered: {fear[:30]}",
                    intensity=0.7,
                    overrides_intent=True,
                    resulting_bias="Will avoid or deflect from the feared topic",
                )
                triggers.append(trigger)

        return triggers

    def _check_loyalty_override(
        self,
        agent_id: str,
        profile: CharacterProfile,
        runtime,
        proposal: InteractionProposal,
        state: WorldState,
    ) -> List[PrivateTendencyTrigger]:
        triggers: List[PrivateTendencyTrigger] = []

        relations = runtime.relationships

        for intent in proposal.intents:
            target_agents = intent.target_agents or []
            for target in target_agents:
                rel = relations.get(target)
                if rel and rel.trust > 5:
                    if intent.action_type in ("accuse", "challenge", "force_check"):
                        trigger = PrivateTendencyTrigger(
                            trigger_id=f"tend_{uuid.uuid4().hex[:8]}",
                            agent_id=agent_id,
                            trigger_type="loyalty_override",
                            trigger_condition=f"Loyalty to {target} overrides neutral judgment",
                            intensity=rel.trust / 10,
                            overrides_intent=rel.trust > 7,
                            resulting_bias=f"Will defend {target} regardless of evidence",
                        )
                        triggers.append(trigger)

        return triggers

    def _check_personal_grudge(
        self,
        agent_id: str,
        profile: CharacterProfile,
        runtime,
        proposal: InteractionProposal,
        state: WorldState,
    ) -> List[PrivateTendencyTrigger]:
        triggers: List[PrivateTendencyTrigger] = []

        relations = runtime.relationships
        grudges = [
            target_id
            for target_id, rel in relations.items()
            if rel.hostility > 5 or rel.trust < -5
        ]

        for intent in proposal.intents:
            if intent.agent_id in grudges:
                trigger = PrivateTendencyTrigger(
                    trigger_id=f"tend_{uuid.uuid4().hex[:8]}",
                    agent_id=agent_id,
                    trigger_type="personal_grudge",
                    trigger_condition=f"Personal grudge against {intent.agent_id}",
                    intensity=0.8,
                    overrides_intent=True,
                    resulting_bias=f"Will oppose {intent.agent_id} regardless of merit",
                )
                triggers.append(trigger)

        return triggers

    def _apply_trigger_effects(
        self,
        triggers: List[PrivateTendencyTrigger],
        reactions: List[AgentReaction],
        agent_id: str,
    ) -> None:
        agent_reactions = [r for r in reactions if r.agent_id == agent_id]

        for trigger in triggers:
            if trigger.overrides_intent:
                for reaction in agent_reactions:
                    if reaction.reaction_type in ("support", "agree", "request_share"):
                        reaction.reaction_type = "withhold"
                        reaction.will_express = False
                        reaction.reasoning = trigger.resulting_bias
                        trigger.suppressed_reaction_ids.append(reaction.reaction_id)
                    elif reaction.reaction_type in ("challenge", "accuse", "deny"):
                        reaction.urgency = min(5, reaction.urgency + 2)
                        reaction.confidence = min(1.0, reaction.confidence + 0.2)
                        trigger.amplified_reaction_ids.append(reaction.reaction_id)

    def _get_agent_profile(self, agent_id: str) -> Optional[CharacterProfile]:
        for char in self.world.characters.characters:
            if char.id == agent_id:
                return char
        return None

    @staticmethod
    def _word_overlap_count(a: str, b: str) -> int:
        words_a = set(a.split())
        words_b = set(b.split())
        return len(words_a & words_b)

    @staticmethod
    def _extract_hidden_agendas(profile: CharacterProfile) -> List[str]:
        agendas = []
        if isinstance(profile.narrative_function, list):
            for func in profile.narrative_function:
                if "withhold" in func.lower() or "secret" in func.lower() or "agenda" in func.lower():
                    agendas.append(func)
        agendas.extend(profile.secrets)
        return agendas

    @staticmethod
    def _extract_fears(profile: CharacterProfile) -> List[str]:
        return list(profile.fears) if profile.fears else []


    @staticmethod
    def _agenda_is_impacted(agenda: str, proposal: InteractionProposal) -> bool:
        agenda_lower = agenda.lower()
        topic = (proposal.topic or "").lower()
        for intent in proposal.intents:
            intention = intent.intention.lower()
            if agenda_lower in topic or agenda_lower in intention:
                return True
        return False
