from __future__ import annotations

from app.models.event import EventLog
from app.models.interaction import InteractionResult
from app.models.state import KeyEventSignal, WorldState


class KeyEventDetector:
    def detect_from_event(self, state: WorldState, event: EventLog) -> list[KeyEventSignal]:
        signals: list[KeyEventSignal] = []
        if event.discovered_facts:
            signals.append(self._signal(state, event, "clue_discovered", 8, True, "new clue discovered"))
        if int(event.fact_exposure_delta.get("revealed_count", 0) or 0) > 0:
            signals.append(self._signal(state, event, "fact_revealed", 7, True, "fact exposure changed"))
        if int(event.fact_exposure_delta.get("suspected_count", 0) or 0) > 0:
            signals.append(self._signal(state, event, "fact_suspected", 6, True, "new suspicion formed"))
        if event.plot_value.relationship > 0:
            signals.append(self._signal(state, event, "relationship_shift", 5, True, "relationship shifted"))
        if event.plot_value.danger >= 3:
            signals.append(self._signal(state, event, "danger_escalation", 7, True, "danger escalated"))
        if event.plot_value.conflict >= 3:
            signals.append(self._signal(state, event, "goal_conflict", 6, True, "conflict escalated"))
        source = event.source_interaction or {}
        if source.get("group_decision"):
            signals.append(self._signal(state, event, "group_decision", 6, True, "group decision requires reactions"))
        return self._dedupe(signals)

    def detect_from_interaction(self, state: WorldState, result: InteractionResult) -> list[KeyEventSignal]:
        event = EventLog(
            event_id=f"evt_{result.interaction_id}",
            event_level="plot",
            time=state.world_time,
            location_id=result.location_id,
            actors=list(result.participants),
            event_type="interaction",
            result=result.topic or result.interaction_type,
            visible_to=list(result.visible_to),
            perceived_by=list(result.visible_to),
            discovered_facts=[],
            plot_value={"relationship": len(result.relationship_changes), "conflict": len(result.relationship_changes)},
            interaction_id=result.interaction_id,
            scene_id=result.scene_id,
            fact_exposure_delta={
                "revealed_count": len(result.revealed_facts),
                "suspected_count": sum(len(v) for v in result.suspected_facts.values()),
                "revealed_fact_ids": list(result.revealed_facts),
                "suspected_fact_ids": list(result.suspected_facts.keys()),
            },
            source_interaction={"group_decision": result.group_decision.model_dump(mode="json") if result.group_decision else None},
        )
        return self.detect_from_event(state, event)

    def _signal(
        self,
        state: WorldState,
        event: EventLog,
        event_kind: str,
        priority: int,
        requires_discussion: bool,
        reason: str,
    ) -> KeyEventSignal:
        related_fact_ids = list(event.discovered_facts)
        related_fact_ids.extend(str(fid) for fid in event.fact_exposure_delta.get("revealed_fact_ids", []) or [])
        return KeyEventSignal(
            signal_id=f"sig_{event.event_id}_{event_kind}",
            source_event_id=event.event_id,
            source_interaction_id=event.interaction_id or "",
            tick=state.tick,
            location_id=event.location_id,
            event_kind=event_kind,
            actor_ids=list(event.actors),
            visible_to=list(event.visible_to),
            related_fact_ids=list(dict.fromkeys(related_fact_ids)),
            affected_agents=list(dict.fromkeys(list(event.visible_to) + list(event.actors))),
            priority=priority,
            requires_discussion=requires_discussion,
            discussion_reason=reason,
        )

    @staticmethod
    def _dedupe(signals: list[KeyEventSignal]) -> list[KeyEventSignal]:
        unique: dict[str, KeyEventSignal] = {}
        for signal in signals:
            unique[signal.signal_id] = signal
        return list(unique.values())
