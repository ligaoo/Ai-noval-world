from __future__ import annotations

from typing import Any

from app.models.event import EventLog
from app.models.state import WorldState


class ChapterCausalChainBuilder:
    def build(self, events: list[EventLog], state: WorldState | None = None) -> dict[str, Any]:
        chains: list[dict[str, Any]] = []
        event_by_interaction = {event.interaction_id: event for event in events if event.interaction_id}
        for event in events:
            if not event.discovered_facts:
                continue
            chain_events = [self._event_item(event, "clue_discovery")]
            discussion = self._following_discussion(event, events)
            if discussion:
                chain_events.append(self._event_item(discussion, "key_discussion"))
                source = discussion.source_interaction or {}
                relationship_updates = source.get("relationship_updates") or []
                if relationship_updates:
                    chain_events.append(
                        {
                            "chain_role": "relationship_update",
                            "event_id": discussion.event_id,
                            "interaction_id": discussion.interaction_id,
                            "updates": relationship_updates,
                        }
                    )
            chains.append(
                {
                    "root_event_id": event.event_id,
                    "related_fact_ids": list(event.discovered_facts),
                    "events": chain_events,
                }
            )
        unresolved_threads = list(state.world.open_threads) if state else []
        stance_changes = self._stance_changes(state) if state else []
        return {
            "key_event_chains": chains,
            "discussion_results": [self._discussion_result(event) for event in events if event.event_type == "interaction"],
            "relationship_updates": self._relationship_updates(events),
            "stance_changes": stance_changes,
            "unresolved_threads": unresolved_threads,
        }

    @staticmethod
    def should_force_keep(event: EventLog) -> bool:
        source = event.source_interaction or {}
        return bool(
            event.discovered_facts
            or (event.event_type == "interaction" and event.plot_value.relationship > 0)
            or source.get("relationship_updates")
            or source.get("group_decision")
        )

    @staticmethod
    def _following_discussion(root: EventLog, events: list[EventLog]) -> EventLog | None:
        try:
            start = events.index(root) + 1
        except ValueError:
            start = 0
        root_facts = set(root.discovered_facts)
        for event in events[start:start + 5]:
            if event.event_type != "interaction":
                continue
            source = event.source_interaction or {}
            text = f"{event.result} {source}"
            if any(fact_id in text for fact_id in root_facts) or source.get("relationship_updates") or source.get("agent_reactions"):
                return event
        return None

    @staticmethod
    def _event_item(event: EventLog, role: str) -> dict[str, Any]:
        return {
            "chain_role": role,
            "event_id": event.event_id,
            "interaction_id": event.interaction_id,
            "event_type": event.event_type,
            "result": event.result,
            "discovered_facts": list(event.discovered_facts),
        }

    @staticmethod
    def _discussion_result(event: EventLog) -> dict[str, Any]:
        source = event.source_interaction or {}
        return {
            "event_id": event.event_id,
            "interaction_id": event.interaction_id,
            "agent_reactions": source.get("agent_reactions") or [],
            "group_decision": source.get("group_decision"),
            "interaction_events": source.get("interaction_events") or [],
        }

    @staticmethod
    def _relationship_updates(events: list[EventLog]) -> list[dict[str, Any]]:
        updates: list[dict[str, Any]] = []
        for event in events:
            for update in (event.source_interaction or {}).get("relationship_updates") or []:
                item = dict(update)
                item["event_id"] = event.event_id
                item["interaction_id"] = event.interaction_id
                updates.append(item)
        return updates

    @staticmethod
    def _stance_changes(state: WorldState) -> list[dict[str, str]]:
        changes: list[dict[str, str]] = []
        for agent_id, runtime in state.characters.items():
            for target, stance in runtime.stance.items():
                changes.append({"agent_id": agent_id, "target": target, "stance": stance})
        return changes
