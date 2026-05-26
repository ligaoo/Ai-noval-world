from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Tuple

from app.models.interaction import AgentIntent, InteractionProposal


class ActionArbitrator:
    SOCIAL_ACTIONS = {
        "ask",
        "answer",
        "refuse",
        "lie",
        "withhold",
        "suggest",
        "challenge",
        "share_info",
        "trade_info",
        "accuse",
        "call_out",
        "block",
        "listen",
        "protect",
        "force_check",
    }
    SIMPLE_ACTIONS = {"observe", "inspect", "search", "move", "wait"}

    def split_intents(
        self, intents: List[AgentIntent]
    ) -> tuple[List[AgentIntent], List[InteractionProposal]]:
        social = [intent for intent in intents if intent.action_type in self.SOCIAL_ACTIONS]
        simple = [intent for intent in intents if intent.action_type not in self.SOCIAL_ACTIONS]
        proposals = self.arbitrate(social)
        return simple, proposals

    def arbitrate(self, intents: List[AgentIntent]) -> List[InteractionProposal]:
        groups: Dict[Tuple[str, str, str], List[AgentIntent]] = defaultdict(list)
        for intent in intents:
            target_key = ",".join(sorted(intent.target_agents)) if intent.target_agents else "scene"
            topic_key = intent.topic or intent.target_object or "general"
            groups[(intent.scene_id, target_key, topic_key)].append(intent)
        proposals: List[InteractionProposal] = []
        for index, ((scene_id, _, topic), group) in enumerate(groups.items(), start=1):
            location_id = scene_id.replace("scene_", "").rsplit("_", 1)[0]
            participants = sorted(
                {
                    intent.agent_id
                    for intent in group
                }
                | {
                    target
                    for intent in group
                    for target in intent.target_agents
                }
            )
            proposals.append(
                InteractionProposal(
                    interaction_id=f"int_{scene_id}_{index:02d}",
                    interaction_type=self._interaction_type(group),
                    scene_id=scene_id,
                    location_id=location_id,
                    participants=participants,
                    observers=sorted(
                        {
                            intent.agent_id
                            for intent in group
                            if intent.action_type in {"observe", "listen"}
                        }
                    ),
                    topic=None if topic == "general" else topic,
                    primary_conflict=self._primary_conflict(group),
                    intents=group,
                )
            )
        return proposals

    def _interaction_type(self, intents: List[AgentIntent]) -> str:
        actions = {intent.action_type for intent in intents}
        if actions & {"accuse", "challenge"}:
            return "accusation"
        if actions & {"lie", "withhold", "refuse"} and actions & {"ask", "challenge"}:
            return "information_pressure"
        if actions & {"trade_info"}:
            return "information_trade"
        if actions & {"share_info", "suggest"}:
            return "cooperation"
        if actions & {"lie", "withhold"}:
            return "deception"
        return "trust_test"

    def _primary_conflict(self, intents: List[AgentIntent]) -> dict:
        holder = next(
            (intent.agent_id for intent in intents if intent.action_type in {"withhold", "lie", "refuse"}),
            None,
        )
        seeker = next(
            (intent.agent_id for intent in intents if intent.action_type in {"ask", "challenge", "accuse"}),
            None,
        )
        buttons = sorted({button for intent in intents for button in intent.conflict_buttons})
        private_interests = {
            intent.agent_id: intent.private_interest
            for intent in intents
            if intent.private_interest
        }
        pressure_required = max((intent.pressure_level for intent in intents), default=0)
        if holder or seeker:
            return {
                "type": "information_control",
                "holder": holder,
                "seeker": seeker,
                "buttons": buttons,
                "private_interests": private_interests,
                "pressure_required": max(2, pressure_required),
            }
        return {
            "type": "social_exchange",
            "buttons": buttons,
            "private_interests": private_interests,
            "pressure_required": max(1, pressure_required),
        }
