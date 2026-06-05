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
                return self._ensure_thematic_thread(threads, parsed)

        if parsed.cast_mode == "ensemble_survival":
            return self._ensure_thematic_thread(self._generate_ensemble_fallback(parsed), parsed)
        return self._ensure_thematic_thread(self._generate_mystery_fallback(parsed), parsed)

    def _generate_with_llm(self, parsed: ParsedSeed) -> Optional[List[OpenThread]]:
        system = "你是悬念池生成器，必须返回 JSON object，不要输出额外解释。"
        user = f"""
请基于 ParsedSeed 生成第一章初始 open_threads。

ParsedSeed:
{json.dumps(parsed.model_dump(), ensure_ascii=False, indent=2)}

硬性要求：
- 返回 JSON object，格式为 {"open_threads": [...]}，数组中每项字段：thread_id, question, priority, status, opened_at_chapter, related_evidence_ids, thread_type, motif, thematic_keyword, payoff_hint。
- 至少 3 条，status 固定 open，opened_at_chapter 固定 1。
- 如果 ParsedSeed 有 core_motif 或 motif_keywords，必须生成 1 条 thread_type=thematic 的主题悬念，追问这个母题如何改变角色对处境、目标或彼此可信度的理解。
- thread_id 使用稳定英文 id，不要把中文剧情词直接拼入 id。
- 内容必须从 ParsedSeed 推导；信息不足时只补结构性悬念，不要固定成某个地点、物件、旧案或亲属失踪模板。
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
            if isinstance(data, dict):
                data = data.get("open_threads")
            if not isinstance(data, list):
                return None
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
            ),
            OpenThread(
                thread_id="thread_hidden_actor_trace",
                question="除了可见角色之外，还有谁或什么在改变现场痕迹？",
                priority=8,
                status="open",
                opened_at_chapter=1,
            ),
            OpenThread(
                thread_id="thread_group_conflict",
                question="队伍内部的隐瞒和分歧会怎样影响所有人的生存机会？",
                priority=7,
                status="open",
                opened_at_chapter=1,
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
        missing = parsed.missing_person or "关键缺口"
        supernatural = parsed.supernatural_element or "异常"

        threads = [
            OpenThread(
                thread_id="thread_missing_trace",
                question=f"{missing}与{location}之间究竟发生过什么交集？",
                priority=10,
                status="open",
                opened_at_chapter=1,
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
                question="未被看见的力量或角色正在以什么方式影响局势推进？",
                priority=7,
                status="open",
                opened_at_chapter=1,
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

    def _ensure_thematic_thread(self, threads: List[OpenThread], parsed: ParsedSeed) -> List[OpenThread]:
        motif = parsed.core_motif or (parsed.motif_keywords[0] if parsed.motif_keywords else "异常")
        if any(t.thread_type == "thematic" or t.thematic_keyword == motif for t in threads):
            return threads
        threads.append(OpenThread(
            thread_id="thread_core_motif",
            question=f"“{motif}”为什么会反复改变角色对当前处境的理解？",
            priority=9,
            status="open",
            opened_at_chapter=1,
            thread_type="thematic",
            motif=motif,
            thematic_keyword=motif,
            payoff_hint=f"后续通过角色选择、线索误读或环境变化，逐步揭示“{motif}”的叙事作用。",
        ))
        return threads
