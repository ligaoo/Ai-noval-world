from __future__ import annotations

import json
import re
from typing import Optional

from .models import ParsedSeed, TruthChain, TruthRevealStage


class TruthChainGenerator:
    """
    第 9 章：真相链自动生成
    控制 4 个阶段：surface / partial / major / truth
    """

    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    def generate(self, parsed: ParsedSeed) -> TruthChain:
        if self.llm_client:
            truth = self._generate_with_llm(parsed)
            if truth:
                return truth

        if parsed.cast_mode == "ensemble_survival":
            return self._generate_ensemble_fallback(parsed)
        return self._generate_mystery_fallback(parsed)

    def _generate_with_llm(self, parsed: ParsedSeed) -> Optional[TruthChain]:
        system = "你是真相链生成器，必须返回 JSON object，不要输出额外解释。"
        user = f"""
请基于 ParsedSeed 生成长篇悬疑/恐怖故事的 truth_chain。

ParsedSeed:
{json.dumps(parsed.model_dump(), ensure_ascii=False, indent=2)}

硬性要求：
- 返回字段：truth_id, final_truth, reveal_steps。
- reveal_steps 必须包含 surface / partial / major / truth 四阶段。
- 每个阶段字段：stage, chapter_range, allowed_information, forbidden_information。
- final_truth 必须从 ParsedSeed 的地点、异常、故事类型、群像/单人结构推导；信息不足时可自行补全，但不要固定成十年前事故、医院旧案、失踪亲友真相。
- surface 阶段只能允许可观察现象，不直接揭示根因。
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
            return TruthChain(**data)
        except Exception:
            return None

    def _generate_ensemble_fallback(self, parsed: ParsedSeed) -> TruthChain:
        location = parsed.core_location or "核心地点"
        supernatural = parsed.supernatural_element or "异常规则"
        group_goal = parsed.group_goal or "共同寻找离开办法"
        stakes = parsed.survival_stakes or "群体选择会改变每个人的风险"

        return TruthChain(
            truth_id=f"truth_{parsed.bootstrap_template or 'ensemble'}",
            final_truth=(
                f"{location}中的{supernatural}会根据被卷入者的集体选择改变边界与线索，"
                f"真正的出路不只取决于单个角色，而取决于众人是否理解并承担{stakes}。"
            ),
            reveal_steps=[
                TruthRevealStage(
                    stage="surface",
                    chapter_range=[1, 5],
                    allowed_information=[
                        f"{location}的边界或出口不再符合正常经验",
                        "多个可见角色的观察彼此矛盾，但都能被现场痕迹部分验证",
                        "分散行动会带来更高风险的早期征兆",
                    ],
                    forbidden_information=[
                        f"{supernatural}的完整运行机制",
                        "最终离开条件",
                    ],
                ),
                TruthRevealStage(
                    stage="partial",
                    chapter_range=[6, 15],
                    allowed_information=[
                        f"{supernatural}会回应群体内部的选择和冲突",
                        f"{group_goal}需要可验证线索，而不是只靠直觉",
                    ],
                    forbidden_information=[
                        "未公开行动者的身份或性质",
                        "最终代价的完整形式",
                    ],
                ),
                TruthRevealStage(
                    stage="major",
                    chapter_range=[16, 24],
                    allowed_information=[
                        "未公开行动者一直在改变线索出现顺序",
                        "至少一个成员的隐瞒会影响所有人的生存路径",
                    ],
                    forbidden_information=[
                        "最终选择的全部后果",
                    ],
                ),
                TruthRevealStage(
                    stage="truth",
                    chapter_range=[25, 30],
                    allowed_information=[
                        f"{supernatural}的真实运行机制",
                        "未公开行动者影响群体的原因",
                        f"众人能否达成{group_goal}的最终条件",
                    ],
                    forbidden_information=[],
                ),
            ],
        )

    def _generate_mystery_fallback(self, parsed: ParsedSeed) -> TruthChain:
        location = parsed.core_location or "核心地点"
        missing = parsed.missing_person or "关键缺口"
        supernatural = parsed.supernatural_element or "异常现象"

        return TruthChain(
            truth_id=f"truth_{parsed.bootstrap_template or 'main'}",
            final_truth=(
                f"{location}中的{supernatural}并非孤立现象；它与被隐藏的关键事件、"
                f"围绕{missing}的矛盾信息以及未公开力量的干预共同构成真相。"
            ),
            reveal_steps=[
                TruthRevealStage(
                    stage="surface",
                    chapter_range=[1, 5],
                    allowed_information=[
                        f"{location}近期仍有活动痕迹",
                        f"{missing}可能与{location}发生过交集",
                        "现场痕迹不符合长期无人接触的状态",
                    ],
                    forbidden_information=[
                        f"{supernatural}的真实来源",
                        "未公开行动者的身份或性质",
                    ],
                ),
                TruthRevealStage(
                    stage="partial",
                    chapter_range=[6, 15],
                    allowed_information=[
                        f"{supernatural}与过去被隐瞒的关键事件有关",
                        "有人在刻意改变或移走记录",
                    ],
                    forbidden_information=[
                        "最终责任链",
                        "完整异常规则",
                    ],
                ),
                TruthRevealStage(
                    stage="major",
                    chapter_range=[16, 24],
                    allowed_information=[
                        f"{missing}曾接近核心真相",
                        "主角的目标与未公开行动者的目标发生直接冲突",
                    ],
                    forbidden_information=[
                        "最终真相的全部因果",
                    ],
                ),
                TruthRevealStage(
                    stage="truth",
                    chapter_range=[25, 30],
                    allowed_information=[
                        f"{supernatural}的真实来源",
                        "未公开行动者的真实目的",
                        f"{missing}缺席的真正原因",
                    ],
                    forbidden_information=[],
                ),
            ],
        )
