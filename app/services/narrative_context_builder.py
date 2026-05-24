from __future__ import annotations

from typing import Any, Dict, List

from app.models.event import EventLog
from app.models.state import WorldState
from app.models.world import WorldConfig
from app.services.fact_exposure_matrix import FactExposureMatrix
from app.services.visible_event_filter import VisibleEventFilter


class NarrativeContextBuilder:
    def __init__(self, world: WorldConfig):
        self.world = world
        self.fact_matrix = FactExposureMatrix(world)
        self.visible_filter = VisibleEventFilter()

    def build(
        self,
        state: WorldState,
        events: List[EventLog],
        pov_id: str,
    ) -> Dict[str, Any]:
        visible_events = [
            event
            for event in self.visible_filter.filter_for_narrative(events, pov_id)
            if not self.visible_filter.has_sensitive_content(event)
        ]
        return {
            "visible_events": [event.model_dump(mode="json") for event in visible_events],
            "allowed_facts": self.fact_matrix.allowed_facts_for(state, pov_id),
            "forbidden_facts": self.fact_matrix.forbidden_facts_for(state, pov_id),
            "allowed_entities": self._allowed_entities(state, pov_id),
            "relationship_state_visible_to_pov": self._relationships(state, pov_id),
        }

    def _allowed_entities(self, state: WorldState, pov_id: str) -> Dict[str, List[str]]:
        runtime = state.characters[pov_id]
        location_id = runtime.location_id
        loc = self.world.map.get_location(location_id)
        characters = [pov_id]
        characters.extend(
            cid
            for cid, other in state.characters.items()
            if other.location_id == location_id and cid != pov_id
        )
        return {
            "characters": characters,
            "locations": [location_id],
            "objects": [obj.id for obj in loc.objects],
        }

    @staticmethod
    def _relationships(state: WorldState, pov_id: str) -> Dict[str, Dict[str, int]]:
        runtime = state.characters[pov_id]
        return {
            target_id: relationship.model_dump(mode="json")
            for target_id, relationship in runtime.relationships.items()
        }
