from __future__ import annotations

import json
import re
from typing import Optional

from .models import OpeningChapterPlan, ParsedSeed, EndingHook, Obstacle


class OpeningChapterGoalGenerator:
    """
    第 13 章：第一章目标生成
    必须包含：目标 / 私人动机 / 核心地点 / 2-3 条线索 / 阻力 / 灵异钩子 / 结尾悬念
    """

    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    def generate(self, parsed: ParsedSeed, protagonist_name: str = "主角") -> OpeningChapterPlan:
        if self.llm_client:
            plan = self._generate_with_llm(parsed, protagonist_name)
            if plan:
                return plan

        if parsed.cast_mode == "ensemble_survival":
            return self._generate_ensemble_fallback(parsed, protagonist_name)
        return self._generate_investigation_fallback(parsed, protagonist_name)

    def _generate_with_llm(
        self,
        parsed: ParsedSeed,
        protagonist_name: str,
    ) -> Optional[OpeningChapterPlan]:
        system = "你是长篇小说第一章目标设计器，必须返回 JSON object，不要输出额外解释。"
        user = f"""
请基于 ParsedSeed 设计第一章 opening_chapter_plan。

ParsedSeed:
{json.dumps(parsed.model_dump(), ensure_ascii=False, indent=2)}

主角名：{protagonist_name}

硬性要求：
- 返回字段：chapter_no, chapter_function, protagonist_goal, personal_stakes, must_events, selected_clues, obstacle, ending_hook, forbidden_reveals, initial_location。
- chapter_no 固定为 1，initial_location 优先为 location_gate。
- selected_clues 从这些 id 中选择至少 3 个：clue_new_lock_core, clue_frontdesk_key, clue_missing_mark, clue_fresh_footprints。
- 如果 cast_mode=ensemble_survival，第一章必须体现可见角色之间的共同处境、共同行动目标和生存代价，但具体事件由你根据 seed 自补全。
- 如果不是群像生存，按 seed 的调查/悬疑核心设计。
- 不要套用固定剧情模板，不要直接照抄示例句。
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
            return OpeningChapterPlan(**data)
        except Exception:
            return None

    def _generate_ensemble_fallback(
        self,
        parsed: ParsedSeed,
        protagonist_name: str,
    ) -> OpeningChapterPlan:
        location = parsed.core_location or "核心地点"
        group_goal = parsed.group_goal or parsed.protagonist_goal or "确认共同处境并寻找离开的办法"
        stakes = parsed.survival_stakes or "任何人脱离协作都会让群体承受更高风险"
        abnormal = parsed.supernatural_element or "异常规则"

        return OpeningChapterPlan(
            chapter_no=1,
            chapter_function=f"建立{location}的异常规则、群体处境和第一条可验证线索",
            protagonist_goal=group_goal,
            personal_stakes=f"{protagonist_name}必须判断该信任谁，并避免队伍在{location}中过早分裂；{stakes}",
            must_events=[
                "可见角色确认彼此都被卷入同一处境，并发现个人记忆或观察存在差异",
                f"角色们验证{location}的入口、边界或返回路径，确认现实规则已经不可靠",
                f"第一个与{abnormal}有关的痕迹出现，迫使众人决定是否共同行动",
            ],
            selected_clues=[
                "clue_new_lock_core",
                "clue_fresh_footprints",
                "clue_missing_mark",
                "clue_frontdesk_key",
            ],
            obstacle=Obstacle(
                type="group_conflict",
                character_id="npc_visible_ally_2",
            ),
            ending_hook=EndingHook(
                type="shared_survival_signal",
                content=f"某个新出现的痕迹证明，{location}正在回应众人的选择，而不是只针对某一个人。",
            ),
            forbidden_reveals=[
                f"{abnormal}的真实来源",
                "最终逃离条件",
                "隐藏行动者真实身份",
            ],
            initial_location="location_gate",
        )

    def _generate_investigation_fallback(
        self,
        parsed: ParsedSeed,
        protagonist_name: str,
    ) -> OpeningChapterPlan:
        location = parsed.core_location or "此处"
        missing = parsed.missing_person or "缺席者"
        abnormal = parsed.supernatural_element or "异常"

        return OpeningChapterPlan(
            chapter_no=1,
            chapter_function=f"建立{location}的异常氛围、调查动机和第一组可验证线索",
            protagonist_goal=parsed.protagonist_goal or f"确认{missing}是否曾进入{location}",
            personal_stakes=f"{protagonist_name}必须证明自己追查的不是幻觉，并找到{missing}留下的真实痕迹",
            must_events=[
                f"主角抵达{location}外围并确认此处近期仍有人活动",
                f"第一个与{abnormal}有关的细节打破正常解释",
                "阻碍者或目击者只透露一小部分事实，迫使主角寻找物证",
            ],
            selected_clues=[
                "clue_new_lock_core",
                "clue_fresh_footprints",
                "clue_missing_mark",
                "clue_frontdesk_key",
            ],
            obstacle=Obstacle(
                type="reluctant_witness",
                character_id="npc_gatekeeper",
            ),
            ending_hook=EndingHook(
                type="personalized_clue",
                content=f"某个细节显示{missing}确实与{location}发生过交集。",
            ),
            forbidden_reveals=[
                f"{abnormal}的真实来源",
                "旧事完整真相",
                "隐藏行动者真实身份",
            ],
            initial_location="location_gate",
        )
