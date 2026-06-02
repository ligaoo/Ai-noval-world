from __future__ import annotations

from app.models.interaction import AgentIntent, InteractionProposal, ScenePresence
from app.models.state import KeyEventSignal, WorldState
from app.models.world import WorldConfig


class KeyEventDiscussionBuilder:
    def __init__(self, world: WorldConfig):
        self.world = world

    def build(
        self,
        state: WorldState,
        scene: ScenePresence,
        signal: KeyEventSignal,
    ) -> InteractionProposal:
        participants = self._participants(state, scene, signal)
        observers = [agent_id for agent_id in scene.present_agents if agent_id not in participants]
        intents = [self._intent_for(state, scene, signal, agent_id, index) for index, agent_id in enumerate(participants)]
        return InteractionProposal(
            interaction_id=f"key_{signal.signal_id}",
            interaction_type="information_pressure",
            scene_id=scene.scene_id,
            location_id=signal.location_id or scene.location_id,
            participants=participants,
            observers=observers,
            topic=signal.discussion_reason or signal.event_kind,
            primary_conflict={
                "key_event_signal_id": signal.signal_id,
                "event_kind": signal.event_kind,
                "related_fact_ids": signal.related_fact_ids,
                "reason": signal.discussion_reason,
            },
            intents=intents,
        )

    def _participants(self, state: WorldState, scene: ScenePresence, signal: KeyEventSignal) -> list[str]:
        ordered: list[str] = []
        for source in (signal.actor_ids, scene.present_agents, signal.visible_to, signal.affected_agents):
            for agent_id in source:
                if agent_id in state.characters and agent_id not in ordered:
                    ordered.append(agent_id)
        return ordered[:5]

    def _intent_for(
        self,
        state: WorldState,
        scene: ScenePresence,
        signal: KeyEventSignal,
        agent_id: str,
        index: int,
    ) -> AgentIntent:
        relationship_pressure = self._relationship_pressure(state, agent_id, signal.actor_ids)
        has_secret_stance = any("secret" in fact_id for fact_id in signal.related_fact_ids)
        if index == 0:
            action_type = "share_info" if signal.event_kind in {"clue_discovered", "fact_revealed"} else "call_out"
        elif has_secret_stance:
            action_type = "withhold"
        elif relationship_pressure >= 2:
            action_type = "challenge"
        else:
            action_type = "ask"
        return AgentIntent(
            agent_id=agent_id,
            intent_id=f"intent_key_{state.tick:04d}_{agent_id}_{signal.signal_id}",
            scene_id=scene.scene_id,
            intention=f"respond to key event: {signal.discussion_reason or signal.event_kind}",
            action_type=action_type,
            target_agents=[other for other in signal.actor_ids if other != agent_id][:1],
            topic=signal.discussion_reason or signal.event_kind,
            will_say=[signal.discussion_reason or signal.event_kind] if action_type in {"share_info", "call_out", "ask", "challenge"} else [],
            will_hide=list(signal.related_fact_ids) if action_type == "withhold" else [],
            referenced_fact_ids=list(signal.related_fact_ids),
            claimed_fact_ids=list(signal.related_fact_ids) if action_type in {"share_info", "call_out"} else [],
            claim_mode="known" if action_type in {"share_info", "call_out"} else "unknown",
            pressure_level=1 if action_type in {"ask", "challenge", "call_out"} else 0,
            risk_level="medium" if action_type in {"withhold", "challenge", "call_out"} else "low",
            intent_source="system_seed",
        )

    @staticmethod
    def _relationship_pressure(state: WorldState, agent_id: str, actor_ids: list[str]) -> int:
        runtime = state.characters.get(agent_id)
        if not runtime:
            return 0
        pressure = 0
        for actor_id in actor_ids:
            relationship = runtime.relationships.get(actor_id)
            if relationship:
                pressure = max(pressure, relationship.suspicion + relationship.hostility)
        return pressure
