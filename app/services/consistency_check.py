from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.llm_client import OpenAICompatibleClient
from app.models.state import WorldState
from app.models.world import WorldConfig
from app.services.timeline_consistency_checker import TimelineConsistencyChecker
from app.services.world_state_service import WorldStateService


@dataclass
class Violation:
    type: str
    text: str
    reason: str
    suggested_fix: str = ""


class ConsistencyCheckService:
    """
    V1.1 三层一致性检查：
    - RuleCheck：程序可判断的先拦截
    - TimelineCheck：时间线一致性检查（V1.1 新增）
    - LLMCheck：语义层（可选，需 OPENAI_API_KEY）
    同时支持：最多自动修订一次。
    """

    REPORT_FILE = "consistency_report.json"

    def __init__(self, world_bible: Dict[str, Any] = None):
        self.state_svc = WorldStateService()
        self.llm = OpenAICompatibleClient.from_env()

        # V1.1 时间线检查器
        self.world_bible = world_bible or {}
        self.timeline_checker = TimelineConsistencyChecker(world_bible=self.world_bible)

    def check_and_maybe_revise(self, sim_dir: Path, world: WorldConfig) -> None:
        state = self.state_svc.load(sim_dir)
        draft_path = sim_dir / "chapter_draft.md"
        if not draft_path.exists():
            raise FileNotFoundError("chapter_draft.md not found, run NarrativeWriter first")

        chapter_text = draft_path.read_text(encoding="utf-8")
        violations = self.rule_check(chapter_text, state, world)

        llm_violations: List[Violation] = []
        if self.llm:
            llm_violations = self.llm_check(chapter_text, state, world)
        violations.extend(llm_violations)

        revised = False
        if violations:
            # V1：最多自动修订一次；如果无 LLM，则做极简“删除违规句”策略
            chapter_text2 = self.revise_once(chapter_text, violations, state, world)
            if chapter_text2 != chapter_text:
                revised = True
                chapter_text = chapter_text2
                draft_path.write_text(chapter_text, encoding="utf-8")

            # final check（只跑规则层，避免循环）
            final_violations = self.rule_check(chapter_text, state, world)
        else:
            final_violations = []

        report = {
            "passed": (len(final_violations) == 0),
            "revised_once": revised,
            "violations": [v.__dict__ for v in violations],
            "final_rule_violations": [v.__dict__ for v in final_violations],
        }
        (sim_dir / self.REPORT_FILE).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    # ----------------------------
    # RuleCheck
    # ----------------------------

    def rule_check(self, chapter_text: str, state: WorldState, world: WorldConfig) -> List[Violation]:
        violations: List[Violation] = []

        # 1) 未发现线索的 content 不应直接出现在正文（粗粒度：子串）
        for clue in world.clues.clues:
            if state.world.discovered_facts.get(clue.id, False):
                continue
            if clue.content and clue.content.strip() and clue.content.strip() in chapter_text:
                violations.append(
                    Violation(
                        type="forbidden_clue_leak",
                        text=clue.content.strip(),
                        reason=f"该线索 {clue.id} 未被发现，不应在正文中出现其明确表述。",
                        suggested_fix="删除或改写为不确定猜测。",
                    )
                )

        # 2) POV 元数据检查（来自 NarrativeWriter 的注释）
        m = re.search(r"<!--\s*POV:(?P<pov>[^ ]+)\s+ALLOWED_CLUES:(?P<clues>[^ ]*)\s*-->", chapter_text)
        if m:
            # 允许的线索 id
            allowed = set([c for c in m.group("clues").split(",") if c])
            # 若正文出现 hf_xxx 形式的 id，则必须在 allowed 中（防调试时误写）
            for found in re.findall(r"\bhf_\d+\b", chapter_text):
                if found not in allowed:
                    violations.append(
                        Violation(
                            type="clue_id_not_allowed",
                            text=found,
                            reason="正文出现了未允许的线索 ID（可能是误把日志 ID 写进正文）。",
                            suggested_fix="去掉线索 ID，改为自然语言描述。",
                        )
                    )

        # 3) 新地点/新对象（V1 粗检查）：若出现明显不在配置中的"固定词"
        forbidden_keywords = ["四楼", "地下室", "幕后人物", "真名"]
        for kw in forbidden_keywords:
            if kw in chapter_text:
                violations.append(
                    Violation(
                        type="suspicious_new_entity",
                        text=kw,
                        reason="正文出现疑似新地点/新设定关键词（V1 规则层保守拦截）。",
                        suggested_fix="删掉该词或改成更模糊的描述（不引入新地点/新规则）。",
                    )
                )

        # V1.1 4) 时间线一致性检查
        if self.world_bible:
            timeline_result = self.timeline_checker.check(chapter_text)
            for issue in timeline_result.get("issues", []):
                violations.append(
                    Violation(
                        type=issue.get("type", "timeline_issue"),
                        text=issue.get("phrase", ""),
                        reason=issue.get("reason", "时间线描述与标准时间不符。"),
                        suggested_fix=timeline_result.get("rewrite_suggestion", ""),
                    )
                )

        return violations

    # ----------------------------
    # LLMCheck（可选）
    # ----------------------------

    def llm_check(self, chapter_text: str, state: WorldState, world: WorldConfig) -> List[Violation]:
        if not self.llm:
            return []

        system = (
            "你是小说一致性审查器，不是作者。\n"
            "你需要检查正文是否：新增线索/新增真相/泄露 POV 不知道的信息/改变事件结果。\n"
            "请只输出 JSON：{passed:boolean, violations:[{type,text,reason,suggested_fix}]}\n"
        )
        user = (
            f"【世界规则】\n- " + "\n- ".join(world.bible.rules) + "\n\n"
            f"【已发现线索】\n{[cid for cid, ok in state.world.discovered_facts.items() if ok]}\n\n"
            f"【章节正文】\n{chapter_text}\n"
        )
        resp = self.llm.chat_json(system=system, user=user, temperature=0.0)
        if not resp.parsed_json:
            return []
        data = resp.parsed_json
        out: List[Violation] = []
        for v in data.get("violations", []) or []:
            try:
                out.append(
                    Violation(
                        type=str(v.get("type", "unknown")),
                        text=str(v.get("text", "")),
                        reason=str(v.get("reason", "")),
                        suggested_fix=str(v.get("suggested_fix", "")),
                    )
                )
            except Exception:
                continue
        return out

    # ----------------------------
    # revise once
    # ----------------------------

    def revise_once(self, chapter_text: str, violations: List[Violation], state: WorldState, world: WorldConfig) -> str:
        if self.llm and os.getenv("CONSISTENCY_AUTO_REVISE", "1") == "1":
            system = (
                "你是小说修订器，不是剧情创造者。\n"
                "你只能根据给定违规点修订文本，禁止新增事实/线索/地点。\n"
                "请输出修订后的完整正文（纯文本）。\n"
            )
            v_text = "\n".join([f"- {v.type}: {v.text} ({v.reason}) 修复建议：{v.suggested_fix}" for v in violations])
            user = f"【违规点】\n{v_text}\n\n【原正文】\n{chapter_text}\n"
            resp = self.llm.chat_json(system=system, user=user, temperature=0.2)
            return resp.text.strip() if resp.text.strip() else chapter_text

        # 无 LLM：极简修订（删除包含违规 text 的句子）
        text = chapter_text
        for v in violations:
            if not v.text:
                continue
            # 删除包含 v.text 的行
            lines = text.splitlines()
            lines2 = [ln for ln in lines if v.text not in ln]
            text = "\n".join(lines2)
        return text

