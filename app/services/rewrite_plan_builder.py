from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from app.models.rewrite_plan import RewritePlan, RewriteProblem


class RewritePlanBuilder:
    DEFAULT_PLAN = [
        "压缩背景解释和事件复述。",
        "把可见事实改写成动作、感官和场景推进。",
        "增强每个场景末尾的悬念残留。",
        "减少总结句，避免后台术语。",
    ]

    def build(
        self,
        quality_report: Any = None,
        chapter_plan: Dict[str, Any] | None = None,
        scene_plan: Dict[str, Any] | None = None,
    ) -> RewritePlan:
        report_dict = self._to_dict(quality_report)
        problems = self._problems_from_report(report_dict)
        rewrite_items = self._rewrite_items(report_dict, problems)
        if not rewrite_items:
            rewrite_items = list(self.DEFAULT_PLAN)

        return RewritePlan(
            overall_goal="增强悬疑压迫感和小说正文质感，减少流水账，不新增事实。",
            problems=problems,
            rewrite_plan=rewrite_items,
            source_notes={
                "quality_score": report_dict.get("overall_score"),
                "rewrite_recommended": report_dict.get("rewrite_recommended", True),
                "scene_count": len((scene_plan or {}).get("scenes", [])),
                "chapter_title": (chapter_plan or {}).get("chapter_title", ""),
            },
        )

    def save(self, sim_dir: Path, rewrite_plan: RewritePlan) -> None:
        with open(sim_dir / "rewrite_plan.json", "w", encoding="utf-8") as f:
            json.dump(rewrite_plan.model_dump(), f, ensure_ascii=False, indent=2)

    @staticmethod
    def load(sim_dir: Path) -> RewritePlan | None:
        path = sim_dir / "rewrite_plan.json"
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return RewritePlan.model_validate(json.load(f))
        except Exception:
            return None

    def _problems_from_report(self, report: Dict[str, Any]) -> List[RewriteProblem]:
        raw_problems = list(report.get("problems") or []) + list(report.get("genre_problems") or [])
        result: List[RewriteProblem] = []
        for index, problem in enumerate(raw_problems[:8], start=1):
            problem_type = str(problem.get("type") or problem.get("category") or "style_issue")
            message = str(problem.get("message") or problem.get("description") or problem.get("evidence") or "")
            instruction = self._instruction_for(problem_type, message)
            result.append(
                RewriteProblem(
                    type=problem_type,
                    location=str(problem.get("location") or problem.get("scene_id") or f"problem_{index}"),
                    evidence=message[:300],
                    rewrite_instruction=instruction,
                )
            )
        if not result:
            result.append(
                RewriteProblem(
                    type="event_log_feel",
                    location="chapter",
                    evidence="默认风格润色：减少日志感，增强场景推进。",
                    rewrite_instruction="在不新增事实的前提下，把事件复述改成动作、感官和情绪节奏。",
                )
            )
        return result

    def _rewrite_items(self, report: Dict[str, Any], problems: List[RewriteProblem]) -> List[str]:
        suggestions = []
        for item in report.get("suggestions") or []:
            text = item.get("suggestion") or item.get("message") or item.get("instruction")
            if text:
                suggestions.append(str(text))
        suggestions.extend(problem.rewrite_instruction for problem in problems)
        result: List[str] = []
        seen = set()
        for item in suggestions:
            if item and item not in seen and not self._is_unsafe_instruction(item):
                result.append(item)
                seen.add(item)
        return result[:8]

    @staticmethod
    def _instruction_for(problem_type: str, message: str) -> str:
        lower = problem_type.lower()
        if "hook" in lower:
            return "强化结尾钩子，用具体感官或动作收束，不新增线索。"
        if "pacing" in lower or "event_log" in lower:
            return "压缩流水账表达，把连续事件组织成场景动作。"
        if "atmosphere" in lower or "horror" in lower:
            return "增强感官异常和压迫感，只使用已有环境与线索。"
        if "conflict" in lower or "relationship" in lower:
            return "只基于已有 interaction_events 和 relationship_updates 强化人物压力。"
        if "exposition" in lower:
            return "减少解释性句子，改为动作、停顿、观察和环境反馈。"
        return message[:160] or "提升小说表达，但不改变事实。"

    @staticmethod
    def _is_unsafe_instruction(text: str) -> bool:
        unsafe_words = ["新增线索", "新增角色", "新增地点", "加入一个新", "创造一个新"]
        return any(word in text for word in unsafe_words)

    @staticmethod
    def _to_dict(value: Any) -> Dict[str, Any]:
        if isinstance(value, dict):
            return value
        if hasattr(value, "to_dict"):
            return value.to_dict()
        if hasattr(value, "model_dump"):
            return value.model_dump()
        if hasattr(value, "__dict__"):
            return dict(value.__dict__)
        return {}
