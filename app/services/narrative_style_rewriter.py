from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from app.llm_client import OpenAICompatibleClient
from app.models.rewrite_plan import RewritePlan


class NarrativeStyleRewriter:
    def __init__(self, llm_client: OpenAICompatibleClient | None = None, style_profile_id: str = "horror_suspense_default"):
        self.llm_client = llm_client
        self.style_profile_id = style_profile_id
        self.style_profile = self._load_style_profile(style_profile_id)

    def rewrite(
        self,
        draft: str,
        scene_plan: Dict[str, Any],
        rewrite_plan: RewritePlan,
        writer_authorization: Dict[str, Any],
    ) -> str:
        if not self.llm_client:
            return self._rule_based_polish(draft)

        system = self._system_prompt()
        user = self._user_prompt(draft, scene_plan, rewrite_plan, writer_authorization)
        resp = self.llm_client.chat(system=system, user=user, temperature=0.45, use_cache=False)
        text = (resp.text or "").strip()
        return text or draft

    def _system_prompt(self) -> str:
        return (
            "你是受约束的小说润色编辑。\n"
            "你只能改写语言、节奏、段落衔接和感官呈现。\n"
            "不得新增 plot-level facts、clues、objects、locations、rules、relationship changes。\n"
            "不得确认 suspected_facts，不得泄露 forbidden facts。\n"
            "不得输出说明、清单、系统字段名、scene_id、event_id。\n"
            "必须压缩装饰性描写：删除连续形容词，减少比喻，保留动作、对白和物证。\n"
            "每 3 段最多保留 1 个修饰性比喻；不得新增录音机、钥匙、地图、档案等未授权物件。\n"
            "如原文越过 scene_plan 的地点边界，只能改成回忆、怀疑或简短提及，不得展开新场景。\n"
            "只输出润色后的小说正文。\n"
        )

    def _user_prompt(
        self,
        draft: str,
        scene_plan: Dict[str, Any],
        rewrite_plan: RewritePlan,
        writer_authorization: Dict[str, Any],
    ) -> str:
        return "\n".join([
            "[Style profile]",
            json.dumps(self.style_profile, ensure_ascii=False, indent=2),
            "",
            "[Scene plan]",
            json.dumps(scene_plan, ensure_ascii=False, indent=2),
            "",
            "[Rewrite plan]",
            json.dumps(rewrite_plan.model_dump(), ensure_ascii=False, indent=2),
            "",
            "[Writer authorization]",
            json.dumps(writer_authorization, ensure_ascii=False, indent=2),
            "",
            "[Raw draft]",
            draft,
            "",
            "请在不改变事实的前提下润色。只输出最终小说正文。",
        ])

    def _rule_based_polish(self, draft: str) -> str:
        lines = [line.rstrip() for line in draft.splitlines()]
        result = []
        blank = False
        for line in lines:
            stripped = line.strip()
            if not stripped:
                if not blank:
                    result.append("")
                blank = True
                continue
            blank = False
            if stripped.startswith("事件") or stripped.startswith("event_id"):
                continue
            result.append(stripped)
        return "\n".join(result).strip() or draft

    @staticmethod
    def _load_style_profile(style_profile_id: str) -> Dict[str, Any]:
        profile_path = Path(__file__).parent.parent / "genre" / "style_profiles" / f"{style_profile_id}.json"
        try:
            with open(profile_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {
                "style_id": style_profile_id,
                "principles": ["少解释，多动作和感官。", "不新增事实。"],
                "avoid": ["流水账", "后台术语"],
            }
