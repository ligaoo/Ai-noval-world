from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List

from app.models.event import EventLog
from app.models.state import WorldState
from app.models.world import WorldConfig


class DraftFaithfulnessChecker:
    STRONG_PLOT_OBJECT_KEYWORDS = ["钥匙", "密码", "地图", "日记", "录音", "录像", "档案", "药瓶", "匕首", "枪", "门卡"]
    GENERIC_PLOT_OBJECT_KEYWORDS = ["信封", "纸条", "笔记", "证件"]
    PLOT_OBJECT_KEYWORDS = [*STRONG_PLOT_OBJECT_KEYWORDS, *GENERIC_PLOT_OBJECT_KEYWORDS]
    PLOT_ACTION_KEYWORDS = ["打开", "证明", "发现", "解锁", "指向", "揭示"]
    GENERIC_PLOT_ACTION_KEYWORDS = ["证明", "揭示", "解锁"]
    BACKEND_FIELDS = ["event_id", "interaction_id", "writer_structured_context", "allowed_facts", "forbidden_fact", "source_interaction"]
    RELATIONSHIP_CHANGE_KEYWORDS = ["彻底信任", "反目", "结盟", "背叛", "不再怀疑"]
    MOVE_KEYWORDS = ["进入", "走进", "抵达", "前往", "来到", "穿过", "移动", "回到", "推门进"]
    MENTION_ONLY_LOCATION_KEYWORDS = ["想起", "提到", "听说", "据说", "怀疑", "可能", "不能去", "别去", "不得进入", "禁止进入", "不要进入"]
    UNSUPPORTED_INFERENCE_TERMS = [
        "车票",
        "买了票",
        "买票",
        "回老家",
        "老家",
        "离开临江",
        "离开这座城",
        "家里",
        "父母",
        "订单金额",
        "藏了",
        "卖了",
    ]

    def __init__(self, world: WorldConfig, sim_dir: Path):
        self.world = world
        self.sim_dir = Path(sim_dir)
        self.policy_whitelist_keywords = self._load_policy_whitelist_keywords()

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
        issues.extend(self._check_unsupported_inferences(draft, plan_dict, events))
        report = self._build_report(issues)
        self._write_json(self.sim_dir / "draft_faithfulness_report.json", report)
        return report

    def _check_plot_objects(self, draft: str, authorization: Dict[str, Any]) -> List[Dict[str, Any]]:
        authorized_text = self._authorized_plot_object_text(authorization)
        issues = []
        for sentence in self._sentences(draft):
            for keyword in self.PLOT_OBJECT_KEYWORDS:
                if keyword not in sentence or keyword in authorized_text:
                    continue
                has_plot_action = any(action in sentence for action in self.PLOT_ACTION_KEYWORDS)
                has_generic_plot_action = any(action in sentence for action in self.GENERIC_PLOT_ACTION_KEYWORDS)
                if keyword in self.GENERIC_PLOT_OBJECT_KEYWORDS and not has_generic_plot_action:
                    continue
                severity = "high" if has_plot_action and keyword in self.STRONG_PLOT_OBJECT_KEYWORDS else "medium"
                issues.append(
                    {
                        "type": "UNAUTHORIZED_PLOT_OBJECT",
                        "severity": severity,
                        "message": f"Draft uses unauthorized plot object keyword: {keyword}.",
                        "details": {"keyword": keyword, "sentence": sentence[:200]},
                    }
                )
        return issues

    def _authorized_plot_object_text(self, authorization: Dict[str, Any]) -> str:
        pieces: List[str] = []
        for item in ((authorization.get("authorized_entities") or {}).get("objects") or []):
            if isinstance(item, dict):
                pieces.extend(str(item.get(key) or "") for key in ["name", "id", "description"])
        pieces.extend(self.policy_whitelist_keywords)
        pieces.append(json.dumps(self.world.bible.model_dump(), ensure_ascii=False))
        for clue in self.world.clues.clues:
            pieces.extend([clue.name, clue.content])
        for location in self.world.map.locations:
            for obj in location.objects:
                pieces.extend([obj.id, obj.name, obj.description, obj.state])
                aliases = getattr(obj, "aliases", None)
                if isinstance(aliases, list):
                    pieces.extend(str(alias) for alias in aliases)
        for character in self.world.characters.characters:
            pieces.extend(str(item) for item in getattr(character, "inventory", []) or [])
        return " ".join(piece for piece in pieces if piece)

    def _load_policy_whitelist_keywords(self) -> List[str]:
        policy_path = self._resolve_project_root() / "worlds" / self.world.world_id / "quality_policy.json"
        if not policy_path.exists():
            return []
        try:
            data = json.loads(policy_path.read_text(encoding="utf-8"))
        except Exception:
            return []
        keywords = data.get("faithfulness_whitelist_keywords") or []
        return [str(keyword) for keyword in keywords if str(keyword).strip()]

    def _resolve_project_root(self) -> Path:
        for candidate in [self.sim_dir, *self.sim_dir.parents]:
            if (candidate / "worlds").exists() and (candidate / "outputs").exists():
                return candidate
        return self.sim_dir.parent.parent

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
            severity = "low"
            sentence_hit = ""
            staged = False
            for sentence in self._sentences(draft):
                if location.name in sentence:
                    sentence_hit = sentence
                    if any(word in sentence for word in self.MENTION_ONLY_LOCATION_KEYWORDS):
                        staged = False
                        break
                    if any(word in sentence for word in self.MOVE_KEYWORDS):
                        severity = "high"
                        staged = True
                    break
            if not staged:
                continue
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

    def _check_unsupported_inferences(
        self,
        draft: str,
        plan_dict: Dict[str, Any],
        events: List[EventLog],
    ) -> List[Dict[str, Any]]:
        authorized_text = self._authorized_inference_text(plan_dict, events)
        issues = []
        for sentence in self._sentences(draft):
            matched_terms = [term for term in self.UNSUPPORTED_INFERENCE_TERMS if term in sentence]
            if not matched_terms:
                continue
            unsupported_terms = [term for term in matched_terms if term not in authorized_text]
            if not unsupported_terms:
                continue
            is_dialogue_or_question = any(mark in sentence for mark in ["？", "?", "“", "”", "\""])
            severity = "high" if is_dialogue_or_question else "medium"
            issues.append(
                {
                    "type": "UNSUPPORTED_CHARACTER_INFERENCE",
                    "severity": severity,
                    "message": "Draft contains a concrete character inference without visible upstream basis.",
                    "details": {
                        "terms": unsupported_terms,
                        "sentence": sentence[:200],
                    },
                }
            )
        return issues

    def _authorized_inference_text(self, plan_dict: Dict[str, Any], events: List[EventLog]) -> str:
        pieces: List[str] = []
        for event in events:
            pieces.append(event.result or "")
            pieces.extend(event.discovered_facts or [])
            pieces.extend(event.hidden_effects or [])
            source = event.source_interaction or {}
            pieces.append(json.dumps(source, ensure_ascii=False))
        context = plan_dict.get("writer_structured_context") or {}
        pieces.append(json.dumps(context, ensure_ascii=False))
        pieces.append(json.dumps(plan_dict.get("chapter_brief") or {}, ensure_ascii=False))
        pieces.append(json.dumps(plan_dict.get("reveal_budget") or {}, ensure_ascii=False))
        pieces.append(json.dumps(plan_dict.get("scene_plan") or {}, ensure_ascii=False))
        return "\n".join(piece for piece in pieces if piece)

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
            "inference_faithfulness": self._score(100, 25 * sum(1 for i in issues if i.get("type") == "UNSUPPORTED_CHARACTER_INFERENCE")),
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
