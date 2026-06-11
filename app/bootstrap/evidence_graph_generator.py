from __future__ import annotations

import json
import re
from typing import List, Optional

from .long_form_pacing import chapters_for_stage
from .models import EvidenceItem, ParsedSeed


class EvidenceGraphGenerator:
    """
    第 10 章：证据链自动生成
    每条 evidence 都必须绑定 related_thread 与 truth_relevance
    """

    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    def generate(self, parsed: ParsedSeed, target_chapters: int = 30) -> List[EvidenceItem]:
        if self.llm_client:
            evidence = self._generate_with_llm(parsed, target_chapters)
            if evidence:
                return evidence

        if parsed.cast_mode == "ensemble_survival":
            return self._generate_ensemble_fallback(parsed, target_chapters)
        return self._generate_mystery_fallback(parsed, target_chapters)

    def _generate_with_llm(self, parsed: ParsedSeed, target_chapters: int) -> Optional[List[EvidenceItem]]:
        system = "你是证据图生成器，必须返回 JSON object，不要输出额外解释。"
        user = f"""
请基于 ParsedSeed 生成 evidence_graph。

ParsedSeed:
{json.dumps(parsed.model_dump(), ensure_ascii=False, indent=2)}

硬性要求：
- 返回 JSON object，格式为 {{"evidence_graph": [...]}}，数组中每项字段：evidence_id, title, type, truth_relevance, purpose, related_thread, can_mislead, real_meaning, allowed_reveal_chapters。
- 至少 8 条证据，覆盖 surface / partial / major / truth 四阶段，章节范围必须在 1..{target_chapters}。
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
            return evidence if len(evidence) >= 8 else None
        except Exception:
            return None

    def _generate_ensemble_fallback(self, parsed: ParsedSeed, target_chapters: int = 30) -> List[EvidenceItem]:
        location = parsed.core_location or "核心地点"
        stakes = parsed.survival_stakes or "群体选择会影响生存风险"
        return self._staged_evidence(
            location=location,
            personal_anchor="队伍共同处境",
            surface_thread="thread_shared_survival_rule",
            motive_thread="thread_group_conflict",
            hidden_thread="thread_hidden_actor_trace",
            supernatural_thread="thread_supernatural",
            target_chapters=target_chapters,
            stakes=stakes,
        )

    def _generate_mystery_fallback(self, parsed: ParsedSeed, target_chapters: int = 30) -> List[EvidenceItem]:
        location = parsed.core_location or "核心地点"
        missing = parsed.missing_person or "关键缺口"
        return self._staged_evidence(
            location=location,
            personal_anchor=missing,
            surface_thread="thread_recent_entry",
            motive_thread="thread_missing_trace",
            hidden_thread="thread_hidden_actor_trace",
            supernatural_thread="thread_supernatural",
            target_chapters=target_chapters,
            stakes=f"{missing}与{location}的异常存在交集",
        )

    def _staged_evidence(
        self,
        location: str,
        personal_anchor: str,
        surface_thread: str,
        motive_thread: str,
        hidden_thread: str,
        supernatural_thread: str,
        target_chapters: int,
        stakes: str,
    ) -> List[EvidenceItem]:
        surface = chapters_for_stage(target_chapters, "surface")
        partial = chapters_for_stage(target_chapters, "partial")
        major = chapters_for_stage(target_chapters, "major")
        truth = chapters_for_stage(target_chapters, "truth")
        return [
            EvidenceItem(
                evidence_id="ev_new_lock_core",
                title="边界被改动的痕迹",
                type="physical_trace",
                truth_relevance="surface",
                purpose=f"证明{location}近期仍被接触或边界规则已改变",
                related_thread=surface_thread,
                can_mislead=False,
                real_meaning=f"{location}不是稳定空间，正常经验已经失效",
                allowed_reveal_chapters=surface[:3],
            ),
            EvidenceItem(
                evidence_id="ev_fresh_footprints",
                title="未知行动痕迹",
                type="trace",
                truth_relevance="surface",
                purpose="证明现场有未被确认的行动源",
                related_thread=hidden_thread,
                can_mislead=True,
                real_meaning="隐藏行动者或异常机制改变了现场状态",
                allowed_reveal_chapters=surface[:4],
            ),
            EvidenceItem(
                evidence_id="ev_key_signal",
                title=f"{personal_anchor}相关标记",
                type="personal_trace",
                truth_relevance="surface",
                purpose=f"把角色目标与{location}绑定",
                related_thread=motive_thread,
                can_mislead=False,
                real_meaning=stakes,
                allowed_reveal_chapters=surface[:5],
            ),
            EvidenceItem(
                evidence_id="ev_rule_contradiction",
                title="互相矛盾的规则痕迹",
                type="rule_trace",
                truth_relevance="partial",
                purpose="提示幸存者掌握的规则并不完全可靠",
                related_thread=supernatural_thread,
                can_mislead=True,
                real_meaning="异常会通过错误规则诱导角色做出危险选择",
                allowed_reveal_chapters=partial[:4],
            ),
            EvidenceItem(
                evidence_id="ev_repeated_pattern",
                title="重复出现的模式",
                type="pattern",
                truth_relevance="partial",
                purpose="让角色从单次异常转向规则验证",
                related_thread=surface_thread,
                can_mislead=False,
                real_meaning="异常具有可验证的触发边界",
                allowed_reveal_chapters=partial[:5],
            ),
            EvidenceItem(
                evidence_id="ev_false_safety",
                title="伪安全区域的破绽",
                type="environmental_contradiction",
                truth_relevance="major",
                purpose="打破角色对安全地点或官方解释的信任",
                related_thread=hidden_thread,
                can_mislead=True,
                real_meaning="避难方案本身可能已被异常利用",
                allowed_reveal_chapters=major[:4],
            ),
            EvidenceItem(
                evidence_id="ev_cost_record",
                title="代价记录",
                type="record",
                truth_relevance="major",
                purpose="证明每次规避异常都需要付出身份、记忆、睡眠或关系代价",
                related_thread=motive_thread,
                can_mislead=False,
                real_meaning="生存规则不是免费工具，而是交换机制",
                allowed_reveal_chapters=major[:5],
            ),
            EvidenceItem(
                evidence_id="ev_origin_key",
                title="源头关键证据",
                type="origin_evidence",
                truth_relevance="truth",
                purpose="支撑最终真相而不是凭角色口述收束",
                related_thread=supernatural_thread,
                can_mislead=False,
                real_meaning=f"{location}异常的源头与角色先前误读的证据链相连",
                allowed_reveal_chapters=truth,
            ),
        ]
