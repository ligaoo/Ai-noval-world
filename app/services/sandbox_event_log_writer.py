from __future__ import annotations

import json
from typing import List

from app.models.event import EventLog, PlotValue
from app.models.interaction import InteractionResult
from app.models.state import WorldState


class SandboxEventLogWriter:
    def events_from_interaction(
        self,
        state: WorldState,
        result: InteractionResult,
    ) -> List[EventLog]:
        summary = self._visible_summary(result)
        plot_value = PlotValue(
            progress=int(result.plot_changes.get("progress_delta", 0)),
            mystery=len(result.suspected_facts),
            conflict=len(result.relationship_changes),
            relationship=len(result.relationship_changes),
        )
        return [
            EventLog(
                event_id=f"evt_{result.interaction_id}",
                event_level="plot",
                time=state.world_time,
                location_id=result.location_id,
                actors=result.participants,
                event_type="interaction",
                action=None,
                result=summary,
                visible_to=list(result.visible_to),
                hidden_effects=list(result.hidden_effects),
                discovered_facts=list(result.revealed_facts),
                plot_value=plot_value,
                interaction_id=result.interaction_id,
                scene_id=result.scene_id,
                perceived_by=list(result.visible_to),
                fact_exposure_delta={
                    "revealed_facts": result.revealed_facts,
                    "suspected_facts": result.suspected_facts,
                },
                source_interaction=result.model_dump(mode="json"),
            )
        ]

    @staticmethod
    def _visible_summary(result: InteractionResult) -> str:
        parts = []
        for round_item in result.rounds:
            if round_item.says_summary:
                parts.append(f"{round_item.speaker}: {round_item.says_summary}")
            else:
                parts.append(f"{round_item.speaker}: {round_item.action}")
        if result.suspected_facts:
            parts.append("New suspicions emerged among participants.")
        return " | ".join(parts) if parts else json.dumps(result.agent_goal_results, ensure_ascii=False)
