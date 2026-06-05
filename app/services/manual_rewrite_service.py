from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from app.llm_client import OpenAICompatibleClient
from app.models.quality_controls import RewriteRequest
from app.models.rewrite_plan import RewritePlan, RewriteProblem, StyleRewriteReport
from app.models.world import WorldConfig
from app.services.narrative_style_rewriter import NarrativeStyleRewriter


class ManualRewriteService:
    def __init__(self, world: WorldConfig, sim_dir: Path, llm_client: OpenAICompatibleClient | None = None):
        self.world = world
        self.sim_dir = Path(sim_dir)
        self.llm_client = llm_client

    def rewrite(self, request: RewriteRequest) -> Dict[str, Any]:
        draft_path = self.sim_dir / "chapter_draft.md"
        if not draft_path.exists():
            raise FileNotFoundError("chapter_draft.md not found")
        draft = draft_path.read_text(encoding="utf-8")
        scene_plan = self._read_json("scene_plan.json")
        chapter_debug = self._read_json("chapter_debug.json")
        writer_authorization = ((chapter_debug.get("traceability") or {}) if isinstance(chapter_debug.get("traceability"), dict) else {})
        rewrite_plan = self._rewrite_plan_for(request)
        rewritten = NarrativeStyleRewriter(self.llm_client).rewrite(draft, scene_plan, rewrite_plan, writer_authorization)

        index = self._next_index()
        draft_file = self.sim_dir / f"chapter_draft_rewrite_{index:03d}.md"
        report_file = self.sim_dir / f"manual_rewrite_report_{index:03d}.json"
        draft_file.write_text(rewritten, encoding="utf-8")
        report = StyleRewriteReport(
            style_profile="horror_suspense_default",
            input_draft_chars=len(draft),
            output_draft_chars=len(rewritten),
            rewrite_applied=True,
            rewrite_focus=rewrite_plan.rewrite_plan,
        ).model_dump()
        report["manual_rewrite_intent"] = request.rewrite_intent
        report["draft_file"] = draft_file.name
        report_file.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return report

    def _rewrite_plan_for(self, request: RewriteRequest) -> RewritePlan:
        mapping = {
            "加强悬念": "延迟解释、增强读者问题、强化异常细节，不新增线索。",
            "减少解释": "压缩背景说明，改成动作、停顿、观察和感官反馈。",
            "增强角色冲突": "只使用已有互动、关系压力和回避动作强化人物冲突。",
            "更像小说正文": "减少日志感，优化段落、节奏和句式，不改变事实。",
        }
        instruction = mapping.get(request.rewrite_intent, request.rewrite_intent)
        return RewritePlan(
            overall_goal=f"手动重写：{request.rewrite_intent}",
            problems=[RewriteProblem(type="manual_rewrite", location="chapter", evidence=request.rewrite_intent, rewrite_instruction=instruction)],
            rewrite_plan=[instruction],
        )

    def _read_json(self, filename: str) -> Dict[str, Any]:
        path = self.sim_dir / filename
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _next_index(self) -> int:
        existing = sorted(self.sim_dir.glob("manual_rewrite_report_*.json"))
        return len(existing) + 1
