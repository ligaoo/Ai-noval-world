from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict

from .models import ParsedSeed


class WorldBibleGenerator:
    """
    第 6 章：自动补全世界设定
    输入：ParsedSeed
    输出：world_bible.json（兼容现有 WorldConfig/WoldBible 模型字段）
    """

    TONE_TEMPLATES = {
        "horror": "压抑、克制，现实中透出诡异",
        "suspense": "紧张、不安，每一步都可能是陷阱",
        "thriller": "急促、逼仄，威胁持续逼近",
        "mystery": "迷离、混沌，真相藏在细节里",
    }

    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    def generate(self, parsed: ParsedSeed, world_id: str, extra: Dict[str, Any] | None = None) -> Dict[str, Any]:
        template = parsed.bootstrap_template or "generic_suspense"

        if self.llm_client:
            bible = self._generate_with_llm(parsed, template, world_id)
            if bible:
                return bible

        return self._generate_with_rules(parsed, template, world_id)

    def _generate_with_rules(self, parsed: ParsedSeed, template: str, world_id: str) -> Dict[str, Any]:
        location = parsed.core_location or "核心地点"
        supernatural = parsed.supernatural_element or "异常现象"
        title = self._fallback_title(parsed, world_id)
        tone = self.TONE_TEMPLATES.get(parsed.genre, self.TONE_TEMPLATES["horror"])
        rules = self._fallback_rules(parsed, location, supernatural)
        themes = self._fallback_themes(parsed)

        return {
            "world_id": world_id,
            "title": title,
            "genre": parsed.genre,
            "sub_genre": parsed.sub_genre,
            "era": "现代都市",
            "tone": tone,
            "core_location": parsed.core_location,
            "themes": themes,
            "rules": rules,
            "core_motif": parsed.core_motif or (parsed.motif_keywords[0] if parsed.motif_keywords else supernatural),
            "main_question": self._main_question(parsed, location, supernatural),
            "hidden_truth": f"{supernatural}背后的真实机制暂时不能在第一章确认，只能通过{location}的痕迹制造怀疑。",
            "first_volume_goal": parsed.group_goal or parsed.protagonist_goal or f"逐步确认{location}异常与角色目标之间的关系。",
            "ending_direction": "真相应通过多章线索逐步逼近，而不是一次性解释。",
            "forbidden_early_reveals": ["隐藏行动者身份", "异常完整规则", "最终真相"],
            "timeline": {
                "origin_event": "异常或关键事件首次留下可追踪痕迹",
                "escalation_event": "近期出现新的现场变化",
                "opening_event": "角色在第一章进入或醒于核心地点",
            },
        }

    def _main_question(self, parsed: ParsedSeed, location: str, supernatural: str) -> str:
        if parsed.cast_mode == "ensemble_survival":
            goal = parsed.group_goal or "共同脱离当前处境"
            return f"被卷入{location}的角色必须理解什么规则，才可能{goal}？"
        target = parsed.missing_person or parsed.protagonist_goal or "关键真相"
        return f"{target}与{location}中出现的{supernatural}究竟有什么关系？"

    def _fallback_title(self, parsed: ParsedSeed, world_id: str) -> str:
        location = parsed.core_location or "异境"
        candidates = [
            f"{location}边界",
            f"{location}回声",
            f"{location}未明",
            f"{location}深处",
        ]
        return candidates[hash(world_id) % len(candidates)]

    def _fallback_rules(self, parsed: ParsedSeed, location: str, supernatural: str) -> list[str]:
        if parsed.cast_mode == "ensemble_survival":
            return [
                f"{location}的边界会根据群体行动状态发生变化",
                f"{supernatural}只通过可验证痕迹逐步显现，不会一次性暴露完整规则",
                "角色分散、隐瞒或误判会改变后续线索出现顺序",
            ]
        return [
            f"{location}中的异常只会通过可检查痕迹和角色行动反馈显现",
            "知情者和隐藏行动者都不会主动交代完整真相",
            "每条关键线索必须能被现场行动验证，而不是凭空获得",
        ]

    def _fallback_themes(self, parsed: ParsedSeed) -> list[str]:
        if parsed.cast_mode == "ensemble_survival":
            return [
                "人在共同危机中如何建立或破坏信任",
                "生存选择是否必然牺牲他人",
                "群体记忆与个人记忆冲突时谁更可信",
            ]
        return [
            "记忆与证据之间的冲突",
            "隐瞒如何改变当下的选择",
            "追查真相时个人代价是否可以承受",
        ]

    def _generate_with_llm(self, parsed: ParsedSeed, template: str, world_id: str) -> Dict[str, Any] | None:
        if not self.llm_client:
            return None

        system = "你是故事世界设定生成专家，必须返回 JSON object。"
        user = f"""
请基于以下解析后的 seed，生成完整 world_bible。

解析信息：
- core_location: {parsed.core_location}
- supernatural_element: {parsed.supernatural_element}
- protagonist_goal: {parsed.protagonist_goal}
- missing_person: {parsed.missing_person}
- story_type: {parsed.story_type}
- cast_mode: {parsed.cast_mode}
- ensemble_size: {parsed.ensemble_size}
- group_goal: {parsed.group_goal}
- survival_stakes: {parsed.survival_stakes}
- opening_mode: {parsed.opening_mode}
- template: {template}

要求：
- title：2-6 个汉字，不要用"神秘之地"之类泛化词
- genre / sub_genre：保留 seed 中的值
- era：如"现代都市""民国""近未来"
- tone：描述整个世界的整体氛围基调
- themes：3 条深刻主题，不要鸡汤
- rules：3 条可验证的世界规则（不是道德）
- timeline：3 个时间点（事件、废弃、官方关闭）

输出 JSON only，不要额外文字：
"""
        try:
            resp = self.llm_client.chat_json(system=system, user=user, temperature=0.5)
            data = resp.parsed_json
            if not data:
                text = resp.text.strip()
                if "```json" in text:
                    text = re.sub(r"```json\s*", "", text)
                    text = re.sub(r"\s*```", "", text)
                data = json.loads(text)
            data["world_id"] = world_id
            return data
        except Exception:
            return None

    def save_to_dir(self, world_dir: Path, bible: Dict[str, Any]) -> None:
        world_dir.mkdir(parents=True, exist_ok=True)
        with open(world_dir / "world_bible.json", "w", encoding="utf-8") as f:
            json.dump(bible, f, ensure_ascii=False, indent=2)
