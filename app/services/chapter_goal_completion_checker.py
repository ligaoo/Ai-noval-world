from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List

from app.models.event import EventLog
from app.models.state import WorldState
from app.models.world import WorldConfig


@dataclass
class ChapterGoalCompletionChecklist:
    required_clue_ids: List[str] = field(default_factory=list)
    required_visible_clue_ids: List[str] = field(default_factory=list)
    min_relationship_updates: int = 0
    min_key_discussions: int = 0


class ChapterGoalCompletionChecker:
    def __init__(self, world: WorldConfig, sim_dir: Path | None = None):
        self.world = world
        self.sim_dir = Path(sim_dir) if sim_dir is not None else None

    def evaluate(self, state: WorldState, events: Iterable[EventLog]) -> Dict[str, Any]:
        event_list = list(events)
        checklist = self._build_default_checklist(event_list)
        discovered = {
            clue_id for clue_id, ok in state.world.discovered_facts.items() if ok
        }
        visible_discovered = {fact_id for event in event_list for fact_id in (event.discovered_facts or [])}
        relationship_updates = self._relationship_update_count(event_list)
        key_discussions = self._key_discussion_count(event_list)
        checks = [
            self._check(
                "STATE_COMPLETED",
                bool(state.chapter_goal_status.completed),
                "Chapter goal status is marked completed by state.",
                "medium",
                {"completed": state.chapter_goal_status.completed, "progress": state.chapter_goal_status.progress},
            ),
            self._check(
                "REQUIRED_CLUES_DISCOVERED",
                set(checklist.required_clue_ids).issubset(discovered),
                "Required clue ids are discovered.",
                "high",
                {"required": checklist.required_clue_ids, "discovered": sorted(discovered)},
            ),
            self._check(
                "REQUIRED_VISIBLE_CLUES_DISCOVERED",
                set(checklist.required_visible_clue_ids).issubset(visible_discovered),
                "Required visible clue ids appear in visible events.",
                "high",
                {"required": checklist.required_visible_clue_ids, "visible_discovered": sorted(visible_discovered)},
            ),
            self._check(
                "MIN_RELATIONSHIP_UPDATES",
                relationship_updates >= checklist.min_relationship_updates,
                "Minimum relationship update count is satisfied.",
                "high",
                {"required": checklist.min_relationship_updates, "actual": relationship_updates},
            ),
            self._check(
                "MIN_KEY_DISCUSSIONS",
                key_discussions >= checklist.min_key_discussions,
                "Minimum key discussion count is satisfied.",
                "medium",
                {"required": checklist.min_key_discussions, "actual": key_discussions},
            ),
        ]
        failed_checks = [check for check in checks if not check["passed"]]
        high_count = sum(1 for check in failed_checks if check.get("severity") in {"high", "critical"})
        medium_count = sum(1 for check in failed_checks if check.get("severity") == "medium")
        report = {
            "checker": "chapter_goal_completion",
            "status": "failed" if high_count else "warning" if medium_count else "passed",
            "passed": high_count == 0,
            "completed_by_state": state.chapter_goal_status.completed,
            "effective_completed": state.chapter_goal_status.completed and high_count == 0,
            "checklist": asdict(checklist),
            "checks": checks,
            "issue_count": len(failed_checks),
            "high_count": high_count,
            "medium_count": medium_count,
            "stats": {
                "discovered_clue_count": len(discovered),
                "visible_discovered_clue_count": len(visible_discovered),
                "key_discussion_count": key_discussions,
                "relationship_update_count": relationship_updates,
                "belief_count": sum(len(char.beliefs) for char in state.characters.values()),
                "stance_count": sum(len(char.stance) for char in state.characters.values()),
                "goal_count": sum(len(char.goals) for char in state.characters.values()),
                "open_thread_count": len(state.world.open_threads),
            },
        }
        if self.sim_dir is not None:
            self._write_json(self.sim_dir / "chapter_goal_completion_report.json", report)
        return report

    def _build_default_checklist(self, events: List[EventLog]) -> ChapterGoalCompletionChecklist:
        interaction_events = [event for event in events if event.event_type == "interaction" or event.interaction_id]
        discovered_facts = [fact_id for event in events for fact_id in (event.discovered_facts or [])]
        return ChapterGoalCompletionChecklist(
            min_relationship_updates=1 if interaction_events and len(self.world.characters.characters) > 1 else 0,
            min_key_discussions=1 if discovered_facts else 0,
        )

    @staticmethod
    def _relationship_update_count(events: List[EventLog]) -> int:
        count = 0
        for event in events:
            source = event.source_interaction or {}
            count += len(source.get("relationship_updates") or [])
            metrics = source.get("agent_debug_metrics") or {}
            count += int(metrics.get("relationship_update_count") or 0)
        return count

    @staticmethod
    def _key_discussion_count(events: List[EventLog]) -> int:
        count = 0
        for event in events:
            source = event.source_interaction or {}
            if source.get("group_decision"):
                count += 1
            count += len(source.get("discussion_results") or [])
            metrics = source.get("agent_debug_metrics") or {}
            count += int(metrics.get("key_discussion_count") or 0)
        return count

    @staticmethod
    def _check(name: str, passed: bool, message: str, severity: str, details: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "name": name,
            "passed": passed,
            "severity": severity,
            "message": message,
            "details": details,
        }

    @staticmethod
    def _write_json(path: Path, data: Dict[str, Any]) -> None:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
