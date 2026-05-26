from __future__ import annotations

import json
import re
from typing import List, Optional

from .models import CharacterWithAgent, DisclosurePolicy, ParsedSeed


class MinimumCastGenerator:
    """
    第 7 章：最小角色组生成
    必须保证：
      - 1 主角（active）
      - 1 缺席人物（inactive）
      - 至少 2 个 active NPC
      - 1 隐藏行动者（active, visibility=hidden）
    """

    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    def generate(self, parsed: ParsedSeed, gate_location_id: str = "location_gate") -> List[CharacterWithAgent]:
        if self.llm_client:
            cast = self._generate_with_llm(parsed, gate_location_id)
            if cast:
                return self._polish_cast(cast, parsed)

        if parsed.cast_mode == "ensemble_survival":
            return self._polish_cast(self._generate_ensemble_fallback(parsed, gate_location_id), parsed)
        return self._polish_cast(self._generate_investigation_fallback(parsed, gate_location_id), parsed)

    def _generate_with_llm(
        self,
        parsed: ParsedSeed,
        gate_location_id: str,
    ) -> Optional[List[CharacterWithAgent]]:
        system = "你是故事角色配置生成器，必须返回 JSON array，不要输出额外解释。"
        user = f"""
请基于 ParsedSeed 生成可运行的最小角色组。

ParsedSeed:
{json.dumps(parsed.model_dump(), ensure_ascii=False, indent=2)}

硬性要求：
- 返回 JSON array。
- 每个对象字段必须兼容：character_id, name, role, active_agent, location_id, goal, personal_stakes, public_motive, private_motive, withheld_information, suspicious_micro_actions, private_hook, emotional_core, known_facts, suspicions, inventory, personality_traits, fears, secrets, background, narrative_function, visibility, llm_temperature。
- 禁止使用“同行者甲/乙”“缺席者”“隐藏行动者”“知情者甲”“目击者乙”“NPC1”等测试感或功能标签式姓名；必须使用自然中文姓名或带具体职业/关系的称谓。
- 每个 visible NPC 必须有公开目标、私人动机、隐瞒信息，以及至少 1 个容易被主角误读的 suspicious_micro_actions。
- hidden_actor 必须有具体身份、利益目标和可追踪痕迹，不能只是“幕后黑手”。
- 必须有 1 个 role=protagonist 且 active_agent=true。
- 必须有 1 个 active_agent=false 且 visibility=absent 的缺席/背景钩子角色。
- 必须至少有 2 个 visible active NPC；如果 cast_mode 是 ensemble_survival，这些 NPC 必须是共同处境中的可见同伴，而不是只在远处提供信息的人。
- 必须有 1 个 visibility=hidden 且 active_agent=true 的 hidden_actor。
- active visible characters 的 location_id 优先放在 {gate_location_id}，除非世界设定明确需要分散。
- 内容必须从 ParsedSeed 推导；如果 ParsedSeed 信息不足，请自行补全，但不要套用固定姓名、固定事故或固定场景模板。
"""
        try:
            resp = self.llm_client.chat_json(system=system, user=user, temperature=0.55)
            data = resp.parsed_json
            if not data:
                text = resp.text.strip()
                if "```json" in text:
                    text = re.sub(r"```json\s*", "", text)
                    text = re.sub(r"\s*```", "", text)
                data = json.loads(text)
            cast = [CharacterWithAgent(**item) for item in data]
            return cast if self._is_valid_minimum_cast(cast) else None
        except Exception:
            return None

    def _is_valid_minimum_cast(self, cast: List[CharacterWithAgent]) -> bool:
        protagonists = [c for c in cast if c.role == "protagonist" and c.active_agent]
        visible_active_npcs = [
            c for c in cast
            if c.role not in ("protagonist", "missing_person")
            and c.active_agent
            and c.visibility == "visible"
        ]
        hidden = [c for c in cast if c.visibility == "hidden" and c.active_agent]
        absent = [c for c in cast if not c.active_agent and c.visibility == "absent"]
        return bool(protagonists and len(visible_active_npcs) >= 2 and hidden and absent)

    def _generate_ensemble_fallback(
        self,
        parsed: ParsedSeed,
        gate_location_id: str,
    ) -> List[CharacterWithAgent]:
        location = parsed.core_location or "核心地点"
        group_goal = parsed.group_goal or parsed.protagonist_goal or "和其他被卷入者共同确认处境并寻找出路"
        stakes = parsed.survival_stakes or "如果群体失去协作，所有人都会暴露在更高风险中"
        absent_name = self._absent_name(parsed)

        return [
            CharacterWithAgent(
                character_id="char_protagonist",
                name="林砚",
                role="protagonist",
                active_agent=True,
                location_id=gate_location_id,
                goal=group_goal,
                personal_stakes=stakes,
                background=f"被卷入{location}异常处境的人之一，需要在信息不足时组织行动。",
                personality_traits=["警觉", "克制", "重视证据"],
                fears=["判断失误害死同伴", "队伍失去互信"],
                secrets=["隐瞒了自己最先察觉异常的细节"],
                llm_temperature=0.3,
                narrative_function=["pov", "group_anchor"],
            ),
            CharacterWithAgent(
                character_id="char_absent_anchor",
                name=absent_name,
                role="missing_person",
                active_agent=False,
                visibility="absent",
                background=f"曾经与{location}异常有关，当前不在场，但留下的痕迹牵引主线。",
                narrative_function=["main_thread_anchor"],
            ),
            CharacterWithAgent(
                character_id="npc_visible_ally_1",
                name="许照",
                role="survivor",
                active_agent=True,
                location_id=gate_location_id,
                goal=group_goal,
                personal_stakes=stakes,
                background=f"同样被困在{location}附近，掌握与主角不同的第一手观察。",
                personality_traits=["谨慎", "务实", "不轻信"],
                fears=["被单独留下", "出口规则变化"],
                secrets=["知道自己进入这里前漏掉了一段记忆"],
                narrative_function=["visible_companion", "survival_pressure"],
                llm_temperature=0.45,
            ),
            CharacterWithAgent(
                character_id="npc_visible_ally_2",
                name="周岚",
                role="survivor",
                active_agent=True,
                location_id=gate_location_id,
                goal=group_goal,
                personal_stakes=stakes,
                background=f"与其他人一起面对{location}的异常，但对共同行动是否有效抱有怀疑。",
                personality_traits=["敏感", "急躁", "保护欲强"],
                fears=["时间耗尽", "同伴互相隐瞒"],
                secrets=["曾在异常发生前听见过不该存在的提示"],
                narrative_function=["visible_companion", "conflict_source"],
                llm_temperature=0.55,
            ),
            CharacterWithAgent(
                character_id="npc_hidden_actor",
                name="程疏影",
                role="hidden_actor",
                active_agent=True,
                visibility="hidden",
                location_id="location_inner",
                goal="在不暴露身份的情况下影响关键线索的出现顺序",
                background=f"与{location}的异常机制存在关联，只通过痕迹和后果影响可见角色。",
                personality_traits=["谨慎", "果断", "回避正面接触"],
                narrative_function=["hidden_actor", "trace_only"],
                llm_temperature=0.4,
            ),
        ]

    def _generate_investigation_fallback(
        self,
        parsed: ParsedSeed,
        gate_location_id: str,
    ) -> List[CharacterWithAgent]:
        protagonist_name = "林砚"
        missing_name = self._absent_name(parsed)
        location = parsed.core_location or "此处"

        return [
            CharacterWithAgent(
                character_id="char_protagonist",
                name=protagonist_name,
                role="protagonist",
                active_agent=True,
                location_id=gate_location_id,
                goal=parsed.protagonist_goal or f"寻找{missing_name}的踪迹",
                personal_stakes=f"必须确认{missing_name}与{location}异常之间是否有关",
                background=f"为了查清{location}附近的异常线索而进入现场。",
                personality_traits=["克制", "对细节敏感", "多疑"],
                fears=["发现真相超出理解", "自己也被卷入异常"],
                secrets=["隐瞒了进入现场的真实原因"],
                llm_temperature=0.25,
                narrative_function=["pov", "investigator"],
            ),
            CharacterWithAgent(
                character_id="char_missing",
                name=missing_name,
                role="missing_person",
                active_agent=False,
                visibility="absent",
                background=f"在{location}附近最后一次留下可验证痕迹，之后失联。",
                narrative_function=["main_thread_anchor"],
            ),
            CharacterWithAgent(
                character_id="npc_gatekeeper",
                name="沈伯衡",
                role="gatekeeper",
                active_agent=True,
                location_id=gate_location_id,
                goal="阻止外人深入，同时避免自己知道的事被追问",
                personal_stakes="秘密被揭开会让自己承担代价",
                background=f"长期接触{location}外围事务，知道部分异常规律但不愿完整说明。",
                personality_traits=["警惕", "怕惹事", "内心有愧"],
                fears=["秘密暴露", "被牵连"],
                secrets=["知道某些不该知道的真相"],
                narrative_function=["obstructor", "reluctant_witness"],
                disclosure_policy=DisclosurePolicy(
                    style="reluctant",
                    max_new_facts_per_dialogue=1,
                    avoid_exposition=True,
                ),
                llm_temperature=0.45,
            ),
            CharacterWithAgent(
                character_id="npc_witness",
                name="罗敏",
                role="witness",
                active_agent=True,
                location_id="location_witness_point",
                goal="保住自己的日常生活，不愿被异常事件拖进去",
                background=f"在{location}外围活动，见过不寻常的出入痕迹。",
                personality_traits=["谨慎", "话多但有分寸"],
                narrative_function=["witness", "local_information_source"],
                llm_temperature=0.55,
            ),
            CharacterWithAgent(
                character_id="npc_hidden_actor",
                name="程疏影",
                role="hidden_actor",
                active_agent=True,
                visibility="hidden",
                location_id="location_inner",
                goal="回收或改写关键线索，避免被可见角色直接发现",
                background=f"身份未知，但显然知道{location}曾发生过的事。",
                personality_traits=["谨慎", "果决", "不留痕迹"],
                narrative_function=["hidden_actor", "trace_only"],
                llm_temperature=0.4,
            ),
        ]

    def _absent_name(self, parsed: ParsedSeed) -> str:
        name = parsed.missing_person or "顾行舟"
        if " " in name:
            name = name.split()[-1]
        return "顾行舟" if self._is_placeholder_name(name) else name

    @staticmethod
    def _is_placeholder_name(name: str) -> bool:
        text = (name or "").strip()
        if not text:
            return True
        exact = {
            "主角", "同行者甲", "同行者乙", "同行者丙", "知情者甲", "知情者乙", "目击者甲", "目击者乙",
            "隐藏行动者", "未露面的行动者", "神秘人", "缺席者", "失踪者", "主线关联者", "NPC", "NPC1", "NPC2",
            "被卷入的同行者", "持异议的同行者", "主要视角角色", "关键角色", "不安的目击者",
            "守口如瓶的知情人", "不安的信息提供者",
        }
        if text in exact:
            return True
        patterns = [
            r"^同行者[甲乙丙丁]$",
            r"^知情者[甲乙丙丁]$",
            r"^目击者[甲乙丙丁]$",
            r"^NPC\d*$",
            r".*同行者$",
            r".*行动者$",
            r".*信息提供者$",
            r".*知情人$",
            r".*目击者$",
        ]
        return any(re.fullmatch(pattern, text, flags=re.IGNORECASE) for pattern in patterns)

    def _replacement_name(
        self,
        character: CharacterWithAgent,
        parsed: ParsedSeed,
        index: int,
        used_names: set[str],
    ) -> str:
        if character.role == "missing_person":
            candidates = [self._absent_name(parsed), "顾行舟", "许知远"]
        elif character.role == "protagonist":
            candidates = ["林砚", "陈明棠", "叶初衡"]
        elif character.visibility == "hidden" or character.role == "hidden_actor":
            candidates = ["程疏影", "陆微澜", "韩述"]
        elif character.role == "gatekeeper":
            candidates = ["沈伯衡", "秦守安", "丁槐"]
        elif character.role == "witness":
            candidates = ["罗敏", "何青禾", "赵闻溪"]
        elif character.role == "survivor":
            candidates = ["许照", "周岚", "孟其声", "唐棠"]
        else:
            candidates = ["梁既白", "苏明夏", "江予安", "白承宁"]
        for candidate in candidates:
            if not self._is_placeholder_name(candidate) and candidate not in used_names:
                return candidate
        return f"{candidates[-1]}{index}"

    def _polish_cast(self, cast: List[CharacterWithAgent], parsed: ParsedSeed) -> List[CharacterWithAgent]:
        motif = parsed.core_motif or "异常"
        location = parsed.core_location or "现场"
        used_names = set()
        for index, character in enumerate(cast, start=1):
            if self._is_placeholder_name(character.name) or character.name in used_names:
                character.name = self._replacement_name(character, parsed, index, used_names)
            used_names.add(character.name)
            if not character.public_motive:
                character.public_motive = character.goal or f"在{location}中维持表面秩序"
            if not character.private_motive:
                if character.role == "protagonist":
                    character.private_motive = f"弄清自己为什么会被{motif}持续牵动，并避免这个弱点影响判断"
                elif character.visibility == "hidden":
                    character.private_motive = f"控制他人接近{motif}核心含义的速度，以保护自身利益"
                else:
                    character.private_motive = f"隐瞒自己与{motif}有关的一段经历，避免被其他人怀疑"
            if not character.withheld_information:
                character.withheld_information = f"掌握一段会改变他人对{motif}理解的信息，但暂时不愿公开"
            if not character.suspicious_micro_actions:
                character.suspicious_micro_actions = [f"当话题触及{motif}时短暂停顿，并调整自己的说法"]
            if not character.private_hook:
                character.private_hook = character.private_motive
            if not character.emotional_core:
                character.emotional_core = character.personal_stakes or character.private_motive
        return cast
