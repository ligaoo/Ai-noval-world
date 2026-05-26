from __future__ import annotations

from typing import List

from app.models.interaction import (
    ExposureUpdate,
    InterruptionResult,
    ReactionIntent,
    ScenePresence,
    SpeechSegment,
)
from app.models.state import WorldState


class ExposureTracker:
    def build_update(
        self,
        state: WorldState,
        scene: ScenePresence,
        spoken_segments: List[SpeechSegment],
        prevented_segments: List[SpeechSegment],
        reactions: List[ReactionIntent],
        interruptions: List[InterruptionResult],
    ) -> ExposureUpdate:
        known_by = self._audible_agents(scene)
        update = ExposureUpdate(
            spoken_segment_ids=[segment.segment_id for segment in spoken_segments],
            prevented_segment_ids=[segment.segment_id for segment in prevented_segments],
        )
        for segment in spoken_segments:
            for fact_id in segment.exposes_fact_ids:
                update.revealed_facts.append(
                    {
                        "fact_id": fact_id,
                        "label": self._fact_label(state, fact_id),
                        "status": "revealed",
                        "known_by": list(known_by),
                        "source": segment.segment_id,
                    }
                )
        for segment in prevented_segments:
            for fact_id in segment.exposes_fact_ids:
                update.prevented_facts.append(
                    {
                        "fact_id": fact_id,
                        "label": self._fact_label(state, fact_id),
                        "status": "prevented",
                        "source": segment.segment_id,
                    }
                )
        withheld_by_segment = {
            segment.segment_id: segment.withheld_fact_ids
            for segment in spoken_segments
            if segment.withheld_fact_ids
        }
        for reaction in reactions:
            if reaction.reaction_type == "observe" and reaction.focus:
                fact_id = self._fact_id_for_label(state, reaction.focus) or reaction.focus
                update.suspected_facts.append(
                    {
                        "fact_id": fact_id,
                        "label": self._fact_label(state, fact_id),
                        "status": "suspected",
                        "suspected_by": [reaction.agent_id],
                        "confidence": 0.45,
                        "source": reaction.reaction_id,
                    }
                )
            if reaction.reaction_type in {"observe", "probe", "clarify", "challenge"}:
                for fact_id in withheld_by_segment.get(reaction.trigger_segment_id or "", []):
                    update.suspected_facts.append(
                        {
                            "fact_id": fact_id,
                            "label": self._fact_label(state, fact_id),
                            "status": "suspected",
                            "suspected_by": [reaction.agent_id],
                            "confidence": 0.45,
                            "source": reaction.reaction_id,
                        }
                    )
        for interruption in interruptions:
            if interruption.success and interruption.interrupter:
                observers = [agent_id for agent_id in known_by if agent_id != interruption.interrupter]
                update.suspected_facts.append(
                    {
                        "fact_id": f"interruption_{interruption.trigger_segment_id}",
                        "label": "the conversation was cut short",
                        "status": "suspected",
                        "suspected_by": observers,
                        "confidence": 0.4,
                        "source": interruption.interruption_id,
                    }
                )
        return update

    @staticmethod
    def _audible_agents(scene: ScenePresence) -> List[str]:
        agents = list(scene.present_agents)
        for nearby in scene.nearby_agents:
            if nearby.can_hear and nearby.character_id not in agents:
                agents.append(nearby.character_id)
        return sorted(agents)

    @staticmethod
    def _fact_id_for_label(state: WorldState, label: str) -> str | None:
        for fact_id, entry in state.world.fact_exposure.items():
            if label == fact_id or label == entry.public_label or label == entry.truth:
                return fact_id
        return None

    @staticmethod
    def _fact_label(state: WorldState, fact_id: str) -> str:
        entry = state.world.fact_exposure.get(fact_id)
        return (entry.public_label or fact_id) if entry else fact_id
