from __future__ import annotations

import json
import re
from typing import List, Optional

from .models import OpenThread, ParsedSeed


class OpenThreadSeedGenerator:
    """
    第 12 章：初始悬念池生成
    每个 thread 必须带 question / priority / status
    """

    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    def generate(self, parsed: ParsedSeed) -> List[OpenThread]:
        if self.llm_client:
            threads = self._generate_with_llm(parsed)
            if threads:
                return threads

        if parsed.cast_mode == "ensemble_survival":
            return self._generate_ensemble_fallback(parsed)
        return self._generate_mystery_fallback(parsed)

    def _generate_with_llm(self, parsed: ParsedSeed) -> Optional[List[OpenThread]]:
        system = "你是悬念池生成器，必须返回 JSON array，不要输出额外解释。"
        user = f"""
请基于 ParsedSeed 生成第一章初始 open_threads。

ParsedSeed:
{json.dumps(parsed.model_dump(), ensure_ascii=False, indent=2)}

硬性要求：
- 返回 JSON array，每项字段：thread_id, question, priority, status, opened_at_chapter, related_evidence_ids。
- 至少 3 条，status 固定 open，opened_at_chapter 固定 1。
- thread_id 尽量使用 thread_recent_entry, thread_missing_trace, thread_hidden_actor_trace, thread_shared_survival_rule, thread_supernatural 这些稳定 id。
- 内容必须从 ParsedSeed 推导；信息不足时可自行补全，但不要固定成前台抽屉钥匙、医院旧案或固定失踪亲属。
"""
        try:
            resp = self.llm_client.chat_json(system=system, user=user, temperature=0.4)
            data = resp.parsed_json
            if not data:
                text = resp.text.strip()
                if "```json" in text:
                    text = re.sub(r"```json\s*", "", text)
                    text = re.sub(r"\s*```", "", text)
                data = json.loads(text)
            threads = [OpenThread(**item) for item in data]
            return threads if len(threads) >= 3 else None
        except Exception:
            return None

    def _generate_ensemble_fallback(self, parsed: ParsedSeed) -> List[OpenThread]:
        location = parsed.core_location or "核心地点"
        supernatural = parsed.supernatural_element or "异常规则"
        group_goal = parsed.group_goal or "共同离开"

        return [
            OpenThread(
                thread_id="thread_shared_survival_rule",
                question=f"被卷入{location}的角色必须遵守什么共同规则，才可能{group_goal}？",
                priority=10,
                status="open",
                opened_at_chapter=1,
                related_evidence_ids=["ev_new_lock_core", "ev_missing_mark"],
            ),
            OpenThread(
                thread_id="thread_hidden_actor_trace",
                question="除了可见角色之外，还有谁或什么在改变现场痕迹？",
                priority=8,
                status="open",
                opened_at_chapter=1,
                related_evidence_ids=["ev_fresh_footprints"],
            ),
            OpenThread(
                thread_id="thread_group_conflict",
                question="队伍内部的隐瞒和分歧会怎样影响所有人的生存机会？",
                priority=7,
                status="open",
                opened_at_chapter=1,
                related_evidence_ids=["ev_missing_mark"],
            ),
            OpenThread(
                thread_id="thread_supernatural",
                question=f"{supernatural}究竟如何回应众人的选择？",
                priority=10,
                status="open",
                opened_at_chapter=1,
            ),
        ]

    def _generate_mystery_fallback(self, parsed: ParsedSeed) -> List[OpenThread]:
        location = parsed.core_location or "核心地点"
        missing = parsed.missing_person or "缺席者"
        supernatural = parsed.supernatural_element or "异常"

        threads = [
            OpenThread(
                thread_id="thread_missing_trace",
                question=f"{missing}与{location}之间究竟发生过什么交集？",
                priority=10,
                status="open",
                opened_at_chapter=1,
                related_evidence_ids=["ev_missing_mark"],
            ),
            OpenThread(
                thread_id="thread_recent_entry",
                question=f"是谁近期接触或改变了{location}的现场状态？",
                priority=8,
                status="open",
                opened_at_chapter=1,
                related_evidence_ids=["ev_new_lock_core", "ev_fresh_footprints"],
            ),
            OpenThread(
                thread_id="thread_hidden_actor_trace",
                question="隐藏行动者为什么要干预线索出现的顺序？",
                priority=7,
                status="open",
                opened_at_chapter=1,
                related_evidence_ids=["ev_fresh_footprints"],
            ),
        ]

        if supernatural:
            threads.append(OpenThread(
                thread_id="thread_supernatural",
                question=f"{supernatural}究竟是什么？",
                priority=10,
                status="open",
                opened_at_chapter=1,
            ))

        return threads
