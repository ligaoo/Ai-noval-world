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
- 返回字段：chapter_no, chapter_function, protagonist_goal, personal_stakes, must_events, selected_clues, obstacle, ending_hook, protagonist_private_hook, required_conflict_beat, concrete_ending_hook, forbidden_reveals, initial_location。
- chapter_no 固定为 1，initial_location 优先为 location_gate。
- protagonist_private_hook 必须说明主角为什么不能把事件当成普通谜题处理。
- required_conflict_beat 必须是一组可见角色之间的利益、证词或行动分歧。
- concrete_ending_hook 必须是一个具体可见/可听/可触异常，禁止写成“更大的秘密浮出水面”这类总结。
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
            selected_clues=[],
            obstacle=Obstacle(
                type="group_conflict",
                character_id="npc_visible_ally_2",
            ),
            ending_hook=EndingHook(
                type="shared_survival_signal",
                content=f"一个刚被所有人确认过的安全细节发生反向变化，证明{location}正在回应群体选择。",
            ),
            protagonist_private_hook=f"{protagonist_name}发现这次异常触碰到自己不愿公开的私人弱点，因此无法只把它当成群体逃生事件。",
            required_conflict_beat="至少两名可见角色对下一步行动提出互相排斥的方案，且双方都各自隐瞒了判断依据。",
            concrete_ending_hook=f"一个刚被所有人确认过的安全细节发生反向变化，证明{location}正在回应群体选择。",
            forbidden_reveals=[
                f"{abnormal}的真实来源",
                "最终逃离条件",
                "未公开行动者的身份或性质",
            ],
            initial_location="location_gate",
        )

    def _generate_investigation_fallback(
        self,
        parsed: ParsedSeed,
        protagonist_name: str,
    ) -> OpeningChapterPlan:
        location = parsed.core_location or "此处"
        missing = parsed.missing_person or "关键缺口"
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
            selected_clues=[],
            obstacle=Obstacle(
                type="reluctant_witness",
                character_id="npc_gatekeeper",
            ),
            ending_hook=EndingHook(
                type="personalized_clue",
                content=f"一个与{missing}相关的具体物证出现了无法用正常时间或空间解释的变化。",
            ),
            protagonist_private_hook=f"{protagonist_name}与{missing}或核心事件存在未公开的私人牵连，因此这次调查不是普通任务。",
            required_conflict_beat="至少两名信息提供者给出不能同时成立的说法，迫使主角用物证而非证词推进。",
            concrete_ending_hook=f"一个与{missing}相关的具体物证出现了无法用正常时间或空间解释的变化。",
            forbidden_reveals=[
                f"{abnormal}的真实来源",
                "旧事完整真相",
                "未公开行动者的身份或性质",
            ],
            initial_location="location_gate",
        )
