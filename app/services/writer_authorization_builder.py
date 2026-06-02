from __future__ import annotations

from typing import Any, Dict, Iterable, List, Set

from app.models.event import EventLog
from app.models.state import WorldState
from app.models.world import WorldConfig


class WriterAuthorizationBuilder:
    def __init__(self, world: WorldConfig):
        self.world = world

    def build(
        self,
        state: WorldState | None,
        visible_events: Iterable[EventLog],
        safe_context: Dict[str, Any] | None,
        pov_id: str,
    ) -> Dict[str, Any]:
        events = list(visible_events)
        safe_context = safe_context or {}
        discovered_fact_ids = {
            fact_id for fact_id, discovered in getattr(getattr(state, "world", None), "discovered_facts", {}).items() if discovered
        }
        event_fact_ids = {fact_id for event in events for fact_id in (event.discovered_facts or [])}
        safe_fact_ids = self._ids_from_safe_facts(safe_context.get("allowed_facts"))
        suspected_fact_ids = self._ids_from_safe_facts(safe_context.get("suspected_facts"))
        authorized_fact_ids = discovered_fact_ids | event_fact_ids | safe_fact_ids | suspected_fact_ids
        all_clue_ids = {clue.id for clue in self.world.clues.clues}
        forbidden = set(safe_context.get("forbidden_fact_ids") or [])
        forbidden.update(self._ids_from_safe_facts(safe_context.get("forbidden_fact_labels")))
        forbidden.update(all_clue_ids - authorized_fact_ids)
        visible_location_ids = {event.location_id for event in events if event.location_id}
        locations = []
        for location in self.world.map.locations:
            locations.append(
                {
                    "id": location.id,
                    "name": location.name,
                    "visited": location.id in visible_location_ids,
                }
            )
        return {
            "authorized_entities": {
                "characters": [
                    {"id": character.id, "name": character.name}
                    for character in self.world.characters.characters
                ],
                "locations": locations,
                "objects": [
                    {"id": obj.id, "name": obj.name, "location_id": location.id}
                    for location in self.world.map.locations
                    for obj in location.objects
                ],
                "facts": sorted(authorized_fact_ids),
                "clues": [
                    {"id": clue.id, "name": clue.name, "content": clue.content}
                    for clue in self.world.clues.clues
                    if clue.id in authorized_fact_ids
                ],
                "rules": list(getattr(self.world.bible, "rules", []) or []),
            },
            "atmosphere_allowed": True,
            "forbidden_fact_ids": sorted(forbidden),
            "pov_known_fact_ids": sorted(authorized_fact_ids),
            "pov_visible_event_ids": [event.event_id for event in events],
            "pov_id": pov_id,
        }

    @staticmethod
    def _ids_from_safe_facts(items: Any) -> Set[str]:
        ids: Set[str] = set()
        for item in items or []:
            if isinstance(item, str):
                ids.add(item)
            elif isinstance(item, dict):
                for key in ("id", "fact_id", "clue_id"):
                    value = item.get(key)
                    if value:
                        ids.add(str(value))
                        break
        return ids
