from __future__ import annotations

import json
import re
from typing import Optional

from .models import ParsedSeed


class SeedInterpreter:
    """
    从一句话模糊设定解析结构化 seed 信息
    （不需要 LLM 时也能基于关键词+正则做保底解析）
    """

    # 经典题材关键词
    LOCATION_PATTERNS = {
        r"医院|旧院|病院": "旧医院",
        r"学校|校舍|宿舍": "废弃学校",
        r"别墅|山庄|公馆": "废弃别墅",
        r"公寓|住宅|大楼": "灵异公寓",
        r"森林|山林|树海": "原始森林",
        r"岛屿|孤岛": "孤岛",
        r"监狱|看守所|牢房": "废弃监狱",
        r"戏院|剧院|影院": "废弃戏院",
        r"旅馆|酒店|宾馆": "诡异旅馆",
    }

    GOAL_PATTERNS = {
        r"调查|寻找|找": "寻找失踪者",
        r"妹妹|姐姐|弟弟|哥哥|家人|朋友": "寻找失踪的亲友",
        r"真相|谜团": "探寻事件真相",
        r"父亲|母亲|父亲|母亲": "调查亲人失踪原因",
        r"女儿|儿子": "找回失去的孩子",
    }

    SUPERNATURAL_PATTERNS = {
        r"五楼|楼层|不存在的楼": "午夜出现的不存在的楼层",
        r"回声|声音|没人却有": "无人却有脚步声",
        r"镜像|镜子": "镜中映出不存在的人影",
        r"时间|循环|重复": "时间异常循环",
        r"影子|人影": "不属于任何人的影子",
        r"电话|座机": "来自过去的电话",
        r"死亡|死人|死者": "死者留下的痕迹",
    }

    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    def interpret(self, user_seed: str) -> ParsedSeed:
        """
        解析模糊设定，优先 LLM，失败时退化为正则
        """
        if self.llm_client:
            parsed = self._interpret_with_llm(user_seed)
            if parsed:
                return parsed

        return self._interpret_with_rules(user_seed)

    def _interpret_with_llm(self, user_seed: str) -> Optional[ParsedSeed]:
        if not self.llm_client:
            return None

        system = "你是故事设定解析专家，必须返回 JSON object。"
        user = f"""
请从以下一句话模糊设定中，提取结构化信息并输出 JSON。

用户输入：{user_seed}

输出格式（JSON only，不要额外解释）：
{{
  "genre": "题材：horror / suspense / thriller / mystery",
  "sub_genre": "子题材：suspense_supernatural / psychological_thriller / old_case_investigation",
  "core_location": "核心地点，如 '旧医院'",
  "supernatural_element": "灵异元素，如 '午夜出现不存在的五楼'",
  "protagonist_goal": "主角目标，如 '调查妹妹失踪'",
  "missing_person": "缺席人物；如果用户明确给出关系或姓名则提取，否则为空字符串",
  "story_type": "故事类型：missing_person / survival_escape / abandoned_place / old_case_reopen",
  "bootstrap_template": "推荐模板：old_hospital_missing_person / villa_cult_investigation / generic_suspense",
  "cast_mode": "角色结构：solo_investigation / ensemble_survival / ensemble_investigation",
  "ensemble_size": "如果是群像，主要活跃可见角色数量；单人故事填 1",
  "group_goal": "群体共同目标，没有则为空字符串",
  "survival_stakes": "生存代价或失败后果，没有则为空字符串",
  "opening_mode": "开场结构：solo_arrival / group_wake_up / group_trapped / investigation_entry"
}}
"""
        try:
            resp = self.llm_client.chat_json(system=system, user=user, temperature=0.2)
            data = resp.parsed_json
            if not data:
                text = resp.text.strip()
                if "```json" in text:
                    text = re.sub(r"```json\s*", "", text)
                    text = re.sub(r"\s*```", "", text)
                data = json.loads(text)
            return ParsedSeed(**data)
        except Exception:
            return None

    def _interpret_with_rules(self, user_seed: str) -> ParsedSeed:
        core_location = "神秘地点"
        for pattern, name in self.LOCATION_PATTERNS.items():
            if re.search(pattern, user_seed):
                core_location = name
                break

        protagonist_goal = "探寻真相"
        for pattern, goal in self.GOAL_PATTERNS.items():
            if re.search(pattern, user_seed):
                protagonist_goal = goal
                break

        supernatural_element = ""
        for pattern, element in self.SUPERNATURAL_PATTERNS.items():
            if re.search(pattern, user_seed):
                supernatural_element = element
                break

        missing_person = ""
        m = re.search(r"(妹妹|姐姐|弟弟|哥哥|朋友|家人)(：|:|是)?[\s]*([\u4e00-\u9fa5a-zA-Z0-9]+)?", user_seed)
        if m:
            missing_person = m.group(1) + (m.group(3) or "")

        group_pattern = r"大家|众人|几个人|一群|所有人|一起|小队|队伍|同伴"
        survival_pattern = r"活下去|生存|逃生|逃出去|出口|被困|困住|天亮前|不能死"
        nightmare_pattern = r"噩梦|梦境|梦里|醒来|梦魇"
        is_group = bool(re.search(group_pattern, user_seed))
        is_survival = bool(re.search(survival_pattern, user_seed))
        is_nightmare = bool(re.search(nightmare_pattern, user_seed))
        if is_group and (is_survival or is_nightmare):
            story_type = "survival_escape"
            cast_mode = "ensemble_survival"
            ensemble_size = 4
            group_goal = "让所有被卷入的人尽可能活着离开"
            survival_stakes = "分散或拖延会让成员被异常逐个吞没"
            opening_mode = "group_trapped" if is_survival else "group_wake_up"
            if protagonist_goal == "探寻真相":
                protagonist_goal = group_goal
        else:
            story_type = "missing_person" if missing_person else "abandoned_place"
            cast_mode = "solo_investigation"
            ensemble_size = 1
            group_goal = ""
            survival_stakes = ""
            opening_mode = "solo_arrival"

        template_mapping = {
            "旧医院": "old_hospital_missing_person",
            "废弃学校": "school_supernatural_case",
            "废弃别墅": "villa_cult_investigation",
            "灵异公寓": "apartment_time_loop",
        }
        bootstrap_template = template_mapping.get(core_location, "generic_suspense")

        return ParsedSeed(
            genre="horror",
            sub_genre="suspense_supernatural",
            core_location=core_location,
            supernatural_element=supernatural_element,
            protagonist_goal=protagonist_goal,
            missing_person=missing_person,
            story_type=story_type,
            bootstrap_template=bootstrap_template,
            cast_mode=cast_mode,
            ensemble_size=ensemble_size,
            group_goal=group_goal,
            survival_stakes=survival_stakes,
            opening_mode=opening_mode,
        )
