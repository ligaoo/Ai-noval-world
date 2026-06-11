from __future__ import annotations

from typing import Any, Dict, List


class NarrativeReadinessError(RuntimeError):
    def __init__(self, report: Dict[str, Any]):
        self.report = report
        message = "; ".join(error.get("message", "Narrative readiness failed.") for error in report.get("errors", []))
        super().__init__(message or "Narrative readiness failed.")


class NarrativeReadinessGuard:
    GENERIC_TEXTS = {
        "从表面合作转为轻微试探，保留信息差。",
        "这条线索真正指向什么？",
        "这个异常细节为什么会出现？",
        "本章异常真正指向什么？",
        "本章异常真正指向什么",
        "以线索钩子结束，不总结，不揭示隐藏真相。",
    }

    def check(self, chapter_plan: Dict[str, Any], force_rule_based: bool = False) -> Dict[str, Any]:
        chapter_brief = chapter_plan.get("chapter_brief") or {}
        scene_plan = chapter_plan.get("scene_plan") or {}
        structured_context = chapter_plan.get("writer_structured_context") or {}
        selected_event_ids = chapter_plan.get("selected_event_ids") or []
        scenes = scene_plan.get("scenes") or []
        counts = structured_context.get("counts") or {}
        writer_authorization = structured_context.get("writer_authorization") or {}
        visible_event_ids = writer_authorization.get("pov_visible_event_ids") or []
        source_notes = chapter_brief.get("source_notes") or {}
        must_threads = self._meaningful(chapter_brief.get("must_advance_threads") or [])
        open_threads = self._meaningful(source_notes.get("open_threads") or [])
        next_seeds = self._meaningful(source_notes.get("next_chapter_seeds") or [])
        selected_semantic_keys = self._selected_semantic_keys(scenes)
        location_policy = chapter_brief.get("location_policy") or {}
        forbidden_location_ids = set(location_policy.get("forbidden_location_ids") or [])
        allowed_location_ids = set(location_policy.get("allowed_location_ids") or [])
        scene_location_ids = [scene.get("location_id") for scene in scenes if scene.get("location_id")]

        errors: List[Dict[str, Any]] = []
        if not selected_event_ids:
            errors.append(self._error("NO_SELECTED_EVENTS", "没有可用于正文承接的 selected events。"))
        if not scenes:
            errors.append(self._error("NO_SCENES", "scene_plan 为空，无法形成章节骨架。"))
        if not visible_event_ids:
            errors.append(self._error("NO_VISIBLE_EVENTS", "Writer authorization 中没有 POV 可见事件。"))

        interaction_count = sum(
            int(counts.get(key) or 0)
            for key in [
                "agent_reaction_count",
                "group_decision_count",
                "private_tendency_trigger_count",
                "relationship_update_count",
                "interaction_event_count",
            ]
        )
        has_scene_events = bool(selected_event_ids or visible_event_ids)
        if interaction_count == 0 and not has_scene_events:
            errors.append(self._error("WEAK_WRITER_CONTEXT", "角色 Agent 结构化上下文为空，且没有可见场景事件。", {"counts": counts}))

        if not (must_threads or open_threads or next_seeds):
            errors.append(self._error("NO_MEANINGFUL_THREADS", "章节 brief 没有有效悬念、open thread 或下一章 seed。"))

        forbidden_scene_locations = [location_id for location_id in scene_location_ids if location_id in forbidden_location_ids]
        if forbidden_scene_locations:
            errors.append(
                self._error(
                    "FORBIDDEN_SCENE_LOCATION",
                    "scene_plan 包含章节地点契约禁止进入的地点。",
                    {"location_ids": forbidden_scene_locations},
                )
            )
        if allowed_location_ids and scene_location_ids and all(location_id not in allowed_location_ids for location_id in scene_location_ids):
            errors.append(
                self._error(
                    "NO_ALLOWED_SCENE_LOCATION",
                    "scene_plan 没有使用章节地点契约允许的地点。",
                    {"allowed_location_ids": sorted(allowed_location_ids), "scene_location_ids": scene_location_ids},
                )
            )

        selected_count = len(selected_event_ids)
        unique_semantic_count = len(selected_semantic_keys)
        if selected_count >= 5 and unique_semantic_count < 2:
            errors.append(
                self._error(
                    "REPETITIVE_SELECTED_EVENTS",
                    "selected events 语义重复过高，继续写作会放大成重复场景。",
                    {"selected_event_count": selected_count, "unique_semantic_count": unique_semantic_count},
                )
            )

        blocking_errors = [error for error in errors if error["code"] in {"NO_SELECTED_EVENTS", "NO_SCENES", "NO_VISIBLE_EVENTS", "NO_MEANINGFUL_THREADS", "REPETITIVE_SELECTED_EVENTS", "FORBIDDEN_SCENE_LOCATION", "NO_ALLOWED_SCENE_LOCATION"}]
        passed = not blocking_errors or force_rule_based
        return {
            "passed": passed,
            "status": "passed" if passed else "failed",
            "errors": errors,
            "metrics": {
                "selected_event_count": selected_count,
                "scene_count": len(scenes),
                "visible_event_count": len(visible_event_ids),
                "interaction_count": interaction_count,
                "meaningful_thread_count": len(must_threads) + len(open_threads) + len(next_seeds),
                "unique_selected_semantic_count": unique_semantic_count,
                "force_rule_based": force_rule_based,
            },
        }

    @classmethod
    def is_generic_text(cls, value: Any) -> bool:
        text = str(value or "").strip()
        if not text or text in cls.GENERIC_TEXTS:
            return True
        fragments = ["以线索钩子结束", "不总结", "不揭示隐藏真相", "这个事件如何推进悬念"]
        return any(fragment in text for fragment in fragments) or len(text) < 6

    @classmethod
    def _meaningful(cls, values: List[Any]) -> List[str]:
        result = []
        for value in values:
            if isinstance(value, dict):
                text = value.get("question") or value.get("thread_id") or value.get("summary") or value.get("effect") or ""
            else:
                text = str(value or "")
            text = text.strip()
            if text and not cls.is_generic_text(text) and text not in result:
                result.append(text)
        return result

    @staticmethod
    def _selected_semantic_keys(scenes: List[Dict[str, Any]]) -> set[str]:
        keys = set()
        for scene in scenes:
            text = "|".join(
                str(scene.get(key) or "")
                for key in ["scene_goal", "conflict", "ending_beat", "consequence_or_change", "information_action_pair"]
            )
            normalized = "".join(text.split())[:120]
            if normalized:
                keys.add(normalized)
        return keys

    @staticmethod
    def _error(code: str, message: str, details: Dict[str, Any] | None = None) -> Dict[str, Any]:
        return {"code": code, "message": message, "details": details or {}}
