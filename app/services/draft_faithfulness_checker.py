from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List

from app.models.event import EventLog
from app.models.state import WorldState
from app.models.world import WorldConfig


class DraftFaithfulnessChecker:
    PLOT_OBJECT_KEYWORDS = ["钥匙", "密码", "地图", "信封", "纸条", "笔记", "日记", "录音", "录像", "档案", "药瓶", "匕首", "枪", "门卡", "证件"]
    PLOT_ACTION_KEYWORDS = ["打开", "证明", "发现", "解锁", "指向", "揭示"]
    BACKEND_FIELDS = ["event_id", "interaction_id", "writer_structured_context", "allowed_facts", "forbidden_fact", "source_interaction"]
    RELATIONSHIP_CHANGE_KEYWORDS = ["彻底信任", "反目", "结盟", "背叛", "不再怀疑"]
    MOVE_KEYWORDS = ["进入", "走进", "抵达", "前往", "来到", "穿过", "移动"]

    def __init__(self, world: WorldConfig, sim_dir: Path):
        self.world = world
        self.sim_dir = Path(sim_dir)

    def check(
        self,
        draft: str,
        chapter_plan: Any,
        visible_events: Iterable[EventLog],
        state: WorldState | None,
    ) -> Dict[str, Any]:
        events = list(visible_events)
        plan_dict = self._to_dict(chapter_plan)
        authorization = ((plan_dict.get("writer_structured_context") or {}).get("writer_authorization") or {})
        issues: List[Dict[str, Any]] = []
        issues.extend(self._check_plot_objects(draft, authorization))
        issues.extend(self._check_undiscovered_clues(draft, state))
        issues.extend(self._check_unvisited_locations(draft, events))
        issues.extend(self._check_backend_fields(draft))
        issues.extend(self._check_relationship_changes(draft, plan_dict))
        report = self._build_report(issues)
        self._write_json(self.sim_dir / "draft_faithfulness_report.json", report)
        return report

    def _check_plot_objects(self, draft: str, authorization: Dict[str, Any]) -> List[Dict[str, Any]]:
        authorized_objects = {
            str(item.get("name") or item.get("id") or "")
            for item in ((authorization.get("authorized_entities") or {}).get("objects") or [])
            if isinstance(item, dict)
        }
        authorized_text = " ".join(authorized_objects)
        issues = []
        for sentence in self._sentences(draft):
            for keyword in self.PLOT_OBJECT_KEYWORDS:
                if keyword not in sentence or keyword in authorized_text:
                    continue
                severity = "high" if any(action in sentence for action in self.PLOT_ACTION_KEYWORDS) else "medium"
                issues.append(
                    {
                        "type": "UNAUTHORIZED_PLOT_OBJECT",
                        "severity": severity,
                        "message": f"Draft uses unauthorized plot object keyword: {keyword}.",
                        "details": {"keyword": keyword, "sentence": sentence[:200]},
                    }
                )
        return issues

    def _check_undiscovered_clues(self, draft: str, state: WorldState | None) -> List[Dict[str, Any]]:
        discovered = {
            clue_id for clue_id, ok in getattr(getattr(state, "world", None), "discovered_facts", {}).items() if ok
        }
        issues = []
        for clue in self.world.clues.clues:
            content = (clue.content or "").strip()
            if clue.id in discovered or len(content) < 4:
                continue
            if content in draft:
                issues.append(
                    {
                        "type": "UNDISCOVERED_CLUE_LEAK",
                        "severity": "high",
                        "message": "Draft directly contains undiscovered clue content.",
                        "details": {"clue_id": clue.id, "content_preview": content[:120]},
                    }
                )
        return issues

    def _check_unvisited_locations(self, draft: str, events: List[EventLog]) -> List[Dict[str, Any]]:
        visited_ids = {event.location_id for event in events if event.location_id}
        issues = []
        for location in self.world.map.locations:
            if location.id in visited_ids or not location.name or location.name not in draft:
                continue
            severity = "medium"
            sentence_hit = ""
            for sentence in self._sentences(draft):
                if location.name in sentence:
                    sentence_hit = sentence
                    if any(word in sentence for word in self.MOVE_KEYWORDS):
                        severity = "high"
                    break
            issues.append(
                {
                    "type": "UNVISITED_LOCATION_MENTION",
                    "severity": severity,
                    "message": "Draft mentions a location not visited by visible events.",
                    "details": {"location_id": location.id, "location_name": location.name, "sentence": sentence_hit[:200]},
                }
            )
        return issues

    def _check_backend_fields(self, draft: str) -> List[Dict[str, Any]]:
        issues = []
        for field in self.BACKEND_FIELDS:
            if field in draft:
                issues.append(
                    {
                        "type": "BACKEND_FIELD_LEAK",
                        "severity": "high",
                        "message": f"Draft exposes backend field: {field}.",
                        "details": {"field": field},
                    }
                )
        return issues

    def _check_relationship_changes(self, draft: str, plan_dict: Dict[str, Any]) -> List[Dict[str, Any]]:
        context = plan_dict.get("writer_structured_context") or {}
        relationship_updates = context.get("relationship_updates") or []
        if relationship_updates:
            return []
        return [
            {
                "type": "UNSUPPORTED_RELATIONSHIP_SHIFT",
                "severity": "medium",
                "message": f"Draft contains relationship-defining phrase without relationship_updates: {keyword}.",
                "details": {"keyword": keyword},
            }
            for keyword in self.RELATIONSHIP_CHANGE_KEYWORDS
            if keyword in draft
        ]

    @classmethod
    def _sentences(cls, text: str) -> List[str]:
        return [part.strip() for part in re.split(r"(?<=[。！？.!?])\s*|\n+", text) if part.strip()]

    @staticmethod
    def _to_dict(value: Any) -> Dict[str, Any]:
        if isinstance(value, dict):
            return value
        if hasattr(value, "model_dump"):
            return value.model_dump()
        return {}

    @staticmethod
    def _score(base: int, penalties: int) -> int:
        return max(0, min(100, base - penalties))

    def _build_report(self, issues: List[Dict[str, Any]]) -> Dict[str, Any]:
        high_count = sum(1 for issue in issues if issue.get("severity") in {"high", "critical"})
        medium_count = sum(1 for issue in issues if issue.get("severity") == "medium")
        scores = {
            "entity_faithfulness": self._score(100, 20 * sum(1 for i in issues if i.get("type") == "UNAUTHORIZED_PLOT_OBJECT")),
            "fact_faithfulness": self._score(100, 25 * sum(1 for i in issues if i.get("type") in {"BACKEND_FIELD_LEAK"})),
            "clue_faithfulness": self._score(100, 30 * sum(1 for i in issues if i.get("type") == "UNDISCOVERED_CLUE_LEAK")),
            "relationship_faithfulness": self._score(100, 20 * sum(1 for i in issues if i.get("type") == "UNSUPPORTED_RELATIONSHIP_SHIFT")),
            "location_faithfulness": self._score(100, 20 * sum(1 for i in issues if i.get("type") == "UNVISITED_LOCATION_MENTION")),
            "chronology_faithfulness": 100,
            "pov_faithfulness": self._score(100, 15 * high_count),
        }
        scores["overall"] = round(sum(scores.values()) / len(scores), 2)
        return {
            "checker": "draft_faithfulness",
            "status": "failed" if high_count else "warning" if medium_count else "passed",
            "passed": high_count == 0,
            "issue_count": len(issues),
            "high_count": high_count,
            "medium_count": medium_count,
            "scores": scores,
            "issues": issues,
        }

    @staticmethod
    def _write_json(path: Path, data: Dict[str, Any]) -> None:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
