from __future__ import annotations

import json
import re
from typing import List, Optional

from .models import EvidenceItem, ParsedSeed


class EvidenceGraphGenerator:
    """
    第 10 章：证据链自动生成
    每条 evidence 都必须绑定 related_thread 与 truth_relevance
    """

    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    def generate(self, parsed: ParsedSeed) -> List[EvidenceItem]:
        if self.llm_client:
            evidence = self._generate_with_llm(parsed)
            if evidence:
                return evidence

        if parsed.cast_mode == "ensemble_survival":
            return self._generate_ensemble_fallback(parsed)
        return self._generate_mystery_fallback(parsed)

    def _generate_with_llm(self, parsed: ParsedSeed) -> Optional[List[EvidenceItem]]:
        system = "你是证据图生成器，必须返回 JSON object，不要输出额外解释。"
        user = f"""
请基于 ParsedSeed 生成 evidence_graph。

ParsedSeed:
{json.dumps(parsed.model_dump(), ensure_ascii=False, indent=2)}

硬性要求：
- 返回 JSON object，格式为 {"evidence_graph": [...]}，数组中每项字段：evidence_id, title, type, truth_relevance, purpose, related_thread, can_mislead, real_meaning, allowed_reveal_chapters。
- 至少 3 条证据，必须能支撑第一章线索和 truth_chain 的 surface 阶段。
- evidence_id 使用稳定英文 id；如需与现有 clue fallback 兼容，可使用 ev_new_lock_core、ev_fresh_footprints、ev_key_signal，但不要让 id 绑定固定剧情含义。
- 内容必须从 ParsedSeed 推导；信息不足时只补充结构性证据，不要固定成某个地点、旧案、物件或亲属失踪模板。
"""
        try:
            resp = self.llm_client.chat_json(system=system, user=user, temperature=0.45)
            data = resp.parsed_json
            if not data:
                text = resp.text.strip()
                if "```json" in text:
                    text = re.sub(r"```json\s*", "", text)
                    text = re.sub(r"\s*```", "", text)
                data = json.loads(text)
            if isinstance(data, dict):
                data = data.get("evidence_graph")
            if not isinstance(data, list):
                return None
            evidence = [EvidenceItem(**item) for item in data]
            return evidence if len(evidence) >= 3 else None
        except Exception:
            return None

    def _generate_ensemble_fallback(self, parsed: ParsedSeed) -> List[EvidenceItem]:
        location = parsed.core_location or "核心地点"
        stakes = parsed.survival_stakes or "群体选择会影响生存风险"

        return [
            EvidenceItem(
                evidence_id="ev_new_lock_core",
                title="边界被改动的痕迹",
                type="physical_trace",
                truth_relevance="surface",
                purpose=f"证明{location}的出入口或边界规则已经发生变化",
                related_thread="thread_shared_survival_rule",
                can_mislead=False,
                real_meaning=f"{location}并非稳定空间，角色无法按正常经验离开",
                allowed_reveal_chapters=[1, 3],
            ),
            EvidenceItem(
                evidence_id="ev_fresh_footprints",
                title="不属于当前队伍的行动痕迹",
                type="trace",
                truth_relevance="surface",
                purpose="证明除了可见角色之外，还有力量或人物在移动线索",
                related_thread="thread_hidden_actor_trace",
                can_mislead=True,
                real_meaning="隐藏行动者或异常机制改变了现场状态",
                allowed_reveal_chapters=[1, 4],
            ),
            EvidenceItem(
                evidence_id="ev_key_signal",
                title="共同处境的标记",
                type="shared_signal",
                truth_relevance="minor",
                purpose=f"把多个角色的个人遭遇绑定到{location}的同一套规则上",
                related_thread="thread_shared_survival_rule",
                can_mislead=False,
                real_meaning=stakes,
                allowed_reveal_chapters=[1, 5],
            ),
        ]

    def _generate_mystery_fallback(self, parsed: ParsedSeed) -> List[EvidenceItem]:
        location = parsed.core_location or "核心地点"
        missing = parsed.missing_person or "关键缺口"

        return [
            EvidenceItem(
                evidence_id="ev_new_lock_core",
                title="近期改动痕迹",
                type="physical_trace",
                truth_relevance="surface",
                purpose=f"证明{location}近期仍被人接触或改变",
                related_thread="thread_recent_entry",
                can_mislead=False,
                real_meaning=f"{location}不是完全静止的废弃空间",
                allowed_reveal_chapters=[1, 3],
            ),
            EvidenceItem(
                evidence_id="ev_fresh_footprints",
                title="新的行动痕迹",
                type="trace",
                truth_relevance="surface",
                purpose="证明有未确认的行动者在场或刚离开",
                related_thread="thread_recent_entry",
                can_mislead=True,
                real_meaning="隐藏行动者或关键知情者留下了可追踪痕迹",
                allowed_reveal_chapters=[1, 4],
            ),
            EvidenceItem(
                evidence_id="ev_key_signal",
                title=f"{missing}相关标记",
                type="personal_trace",
                truth_relevance="minor",
                purpose=f"把主角目标与{location}绑定",
                related_thread="thread_missing_trace",
                can_mislead=False,
                real_meaning=f"{missing}与{location}的异常存在交集",
                allowed_reveal_chapters=[1, 5],
            ),
        ]
