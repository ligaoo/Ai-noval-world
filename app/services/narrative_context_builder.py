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
            "visible_events": [self._safe_event_projection(event) for event in visible_events],
            "allowed_facts": self.fact_matrix.allowed_facts_for(state, pov_id),
            "suspected_facts": self._suspected_facts(state, pov_id),
            "forbidden_fact_ids": self.fact_matrix.forbidden_fact_ids_for(state, pov_id),
            "forbidden_fact_labels": self.fact_matrix.forbidden_fact_labels_for(state, pov_id),
            "allowed_entities": self._allowed_entities(state, pov_id),
            "character_display_names": {
                character.id: character.name for character in self.world.characters.characters
            },
            "relationship_state_visible_to_pov": self._relationships(state, pov_id),
        }

    def _character_name(self, character_id: str | None) -> str:
        if not character_id:
            return "unknown"
        try:
            return self.world.characters.get_character(character_id).name or character_id
        except KeyError:
            return character_id

    def _character_ref(self, character_id: str | None) -> dict:
        return {"id": character_id, "name": self._character_name(character_id)}

    def _location_name(self, location_id: str | None) -> str:
        if not location_id:
            return "unknown"
        try:
            return self.world.map.get_location(location_id).name or location_id
        except KeyError:
            return location_id

    def _allowed_entities(self, state: WorldState, pov_id: str) -> Dict[str, List[str]]:
        runtime = state.characters[pov_id]
        location_id = runtime.location_id
        loc = self.world.map.get_location(location_id)
        character_ids = [pov_id]
        character_ids.extend(
            cid
            for cid, other in state.characters.items()
            if other.location_id == location_id and cid != pov_id
        )
        return {
            "characters": [self._character_name(cid) for cid in character_ids],
            "character_ids": character_ids,
            "locations": [self._location_name(location_id)],
            "location_ids": [location_id],
            "objects": [obj.name or obj.id for obj in loc.objects],
            "object_ids": [obj.id for obj in loc.objects],
        }

    def _safe_event_projection(self, event: EventLog) -> Dict[str, Any]:
        source = event.source_interaction or {}
        projection = {
            "event_id": event.event_id,
            "time": event.time,
            "location_id": event.location_id,
            "location_name": self._location_name(event.location_id),
            "actors": list(event.actors),
            "actors_display": [self._character_ref(cid) for cid in event.actors],
            "event_type": event.event_type,
            "result": event.result,
            "plot_value": event.plot_value.model_dump(mode="json"),
        }
        if source:
            exposure = source.get("exposure_update") or {}
            projection["spoken_segments"] = [self._decorate_segment(segment) for segment in source.get("spoken_segments", [])]
            projection["interruption_results"] = [
                self._decorate_interruption(item) for item in source.get("interruption_results", [])
            ]
            projection["post_interruption_reactions"] = [
                self._decorate_reaction(item) for item in source.get("post_interruption_reactions", [])
            ]
            projection["observations"] = [
                self._decorate_reaction(reaction)
                for reaction in source.get("reaction_intents", [])
                if reaction.get("reaction_type") == "observe"
            ]
            projection["suspected_facts"] = [
                item.get("label") or item.get("fact_id")
                for item in exposure.get("suspected_facts", [])
            ]
            projection["prevented_facts"] = [
                {"fact_id": item.get("fact_id"), "label": item.get("label"), "source": item.get("source")}
                for item in exposure.get("prevented_facts", [])
            ]
        return projection

    def _decorate_segment(self, segment: dict) -> dict:
        decorated = dict(segment)
        speaker = decorated.get("speaker")
        decorated["speaker_name"] = decorated.get("speaker_name") or self._character_name(speaker)
        return decorated

    def _decorate_reaction(self, reaction: dict) -> dict:
        decorated = dict(reaction)
        decorated["agent_name"] = decorated.get("agent_name") or self._character_name(decorated.get("agent_id"))
        target = decorated.get("target_speaker")
        decorated["target_speaker_name"] = decorated.get("target_speaker_name") or (self._character_name(target) if target else None)
        return decorated

    def _decorate_interruption(self, interruption: dict) -> dict:
        decorated = dict(interruption)
        decorated["interrupter_name"] = decorated.get("interrupter_name") or self._character_name(decorated.get("interrupter"))
        decorated["interrupted_speaker_name"] = decorated.get("interrupted_speaker_name") or self._character_name(decorated.get("interrupted_speaker"))
        turn_owner = decorated.get("turn_owner")
        decorated["turn_owner_name"] = decorated.get("turn_owner_name") or (self._character_name(turn_owner) if turn_owner else None)
        return decorated

    @staticmethod
    def _suspected_facts(state: WorldState, pov_id: str) -> List[str]:
        return [
            entry.public_label or entry.fact_id
            for entry in state.world.fact_exposure.values()
            if pov_id in entry.suspected_by and pov_id not in entry.known_by
        ]

    def _relationships(self, state: WorldState, pov_id: str) -> Dict[str, Dict[str, Any]]:
        runtime = state.characters[pov_id]
        relationships: Dict[str, Dict[str, Any]] = {}
        for target_id, relationship in runtime.relationships.items():
            data = relationship.model_dump(mode="json")
            relationships[target_id] = {
                "id": target_id,
                "name": self._character_name(target_id),
                "role": self._character_role(target_id),
                **data,
            }
        return relationships

    def _character_role(self, character_id: str) -> str:
        try:
            return self.world.characters.get_character(character_id).role
        except KeyError:
            return ""