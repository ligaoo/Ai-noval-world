from __future__ import annotations

import json
import re
from typing import Optional

from .models import OpeningChapterPlan, ParsedSeed, WriterStoryAnchor


class WriterStoryAnchorGenerator:
    """
    第 20 章：叙事锚点生成
    防止 NarrativeWriter 写成通用模板
    """

    FORBIDDEN_PHRASES = [
        "神秘之地", "发现真相", "重要的东西", "说不清的直觉",
        "有些问题只有走进去才能找到答案", "我已经做好继续走下去的准备",
        "Mysterious Place", "the truth will be revealed",
    ]

    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    def generate(
        self,
        title: str,
        parsed: ParsedSeed,
        opening: OpeningChapterPlan,
        protagonist_name: str = "主角",
    ) -> WriterStoryAnchor:
        if self.llm_client:
            anchors = self._generate_with_llm(title, parsed, opening, protagonist_name)
            if anchors:
                return anchors

        if parsed.cast_mode == "ensemble_survival":
            return self._generate_ensemble_fallback(title, parsed, opening, protagonist_name)
        return self._generate_investigation_fallback(title, parsed, opening, protagonist_name)

    def _generate_with_llm(
        self,
        title: str,
        parsed: ParsedSeed,
        opening: OpeningChapterPlan,
        protagonist_name: str,
    ) -> Optional[WriterStoryAnchor]:
        system = "你是小说正文叙事锚点生成器，必须返回 JSON object，不要输出额外解释。"
        user = f"""
请基于标题、ParsedSeed 和 opening_chapter_plan 生成 writer_story_anchors。

标题：{title}
主角名：{protagonist_name}
ParsedSeed:
{json.dumps(parsed.model_dump(), ensure_ascii=False, indent=2)}
OpeningChapterPlan:
{json.dumps(opening.model_dump(), ensure_ascii=False, indent=2)}

硬性要求：
- 返回字段：title, protagonist_name, protagonist_goal, personal_stakes, current_chapter_goal, main_question, required_emotional_beat, forbidden_generic_phrases, world_tone。
- 必须承接 ParsedSeed 和 opening_chapter_plan，不要把群像生存写成单人调查。
- 如果 seed 信息不足，请自行补全叙事锚点，但不要套用固定失踪亲友、固定电话、固定旧案模板。
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
            data.setdefault("forbidden_generic_phrases", self.FORBIDDEN_PHRASES[:])
            return WriterStoryAnchor(**data)
        except Exception:
            return None

    def _generate_ensemble_fallback(
        self,
        title: str,
        parsed: ParsedSeed,
        opening: OpeningChapterPlan,
        protagonist_name: str,
    ) -> WriterStoryAnchor:
        location = parsed.core_location or "核心地点"
        group_goal = parsed.group_goal or opening.protagonist_goal
        stakes = parsed.survival_stakes or opening.personal_stakes

        return WriterStoryAnchor(
            title=title,
            protagonist_name=protagonist_name,
            protagonist_goal=opening.protagonist_goal,
            personal_stakes=opening.personal_stakes,
            current_chapter_goal=opening.chapter_function or group_goal,
            main_question=f"被卷入{location}的可见角色能否找出共同处境的规则，并在付出代价前形成协作？",
            required_emotional_beat=f"{protagonist_name}意识到这不是只属于自己的危机；每一次选择都会改变其他人的生存机会。{stakes}",
            forbidden_generic_phrases=self.FORBIDDEN_PHRASES[:],
            world_tone="压迫、群体互疑、现实规则逐步失效",
        )

    def _generate_investigation_fallback(
        self,
        title: str,
        parsed: ParsedSeed,
        opening: OpeningChapterPlan,
        protagonist_name: str,
    ) -> WriterStoryAnchor:
        location = parsed.core_location or "此处"
        missing = parsed.missing_person or "缺席者"

        return WriterStoryAnchor(
            title=title,
            protagonist_name=protagonist_name,
            protagonist_goal=opening.protagonist_goal,
            personal_stakes=opening.personal_stakes,
            current_chapter_goal=opening.chapter_function or f"在{location}找到第一组可验证线索",
            main_question=f"{missing}留下的痕迹是否能证明{location}的异常真实存在？",
            required_emotional_beat=f"{protagonist_name}第一次意识到，自己追查的线索正在反过来影响当下的安全。",
            forbidden_generic_phrases=self.FORBIDDEN_PHRASES[:],
            world_tone="压抑、克制、现实中透出诡异",
        )
