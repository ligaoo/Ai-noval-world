from __future__ import annotations

import json
import re
from typing import List, Optional

from .long_form_pacing import chapters_for_stage
from .models import BootstrapClue, DiscoverRoute, OnDiscovered, ParsedSeed


class ClueRouteGenerator:
    """
    第 11 章：可发现线索入口自动生成
    必须保证：
      - 每个 clue 有 discover_routes
      - discover_route 对应真实 location_id
      - on_discovered 包含 add_known_fact + plot_progress
    """

    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    def generate(self, parsed: ParsedSeed, target_chapters: int = 30) -> List[BootstrapClue]:
        if self.llm_client:
            clues = self._generate_with_llm(parsed, target_chapters)
            if clues:
                return clues

        if parsed.cast_mode == "ensemble_survival":
            return self._expand_long_form_clues(self._generate_ensemble_fallback(parsed), parsed, target_chapters)
        return self._expand_long_form_clues(self._generate_mystery_fallback(parsed), parsed, target_chapters)

    def _generate_with_llm(self, parsed: ParsedSeed, target_chapters: int) -> Optional[List[BootstrapClue]]:
        system = "你是线索与发现路径生成器，必须返回 JSON object，不要输出额外解释。"
        user = f"""
请基于 ParsedSeed 生成长篇 clues。

ParsedSeed:
{json.dumps(parsed.model_dump(), ensure_ascii=False, indent=2)}

硬性要求：
- 返回 JSON object，格式为 {{"clues": [...]}}，数组中每项字段：clue_id, title, content, level, related_event, related_thread, discover_routes, on_discovered, planned_chapters, evidence_ids, related_truth, reveal_role。
- 至少 10 条，覆盖 opening/surface、partial、major、truth/payoff，不要全部集中在第一章。
- 必须保留首章 clue_id：clue_new_lock_core, clue_frontdesk_key, clue_missing_mark, clue_fresh_footprints。
- discover_routes 中 location_id 必须从生成地图的稳定地点中选择：location_gate, location_frontdesk, location_hallway, location_archive, location_basement, location_witness_point, location_inner。
- 线索必须是可检查现实痕迹、行动后果或证词矛盾；不要固定成前台钥匙、医院病案、十年前事故或固定失踪亲友。
- planned_chapters 必须落在 1..{target_chapters}。
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
                data = data.get("clues")
            if not isinstance(data, list):
                return None
            clues = [BootstrapClue(**item) for item in data]
            expected = {"clue_new_lock_core", "clue_frontdesk_key", "clue_missing_mark", "clue_fresh_footprints"}
            return clues if len(clues) >= 10 and expected.issubset({c.clue_id for c in clues}) else None
        except Exception:
            return None

    def _generate_ensemble_fallback(self, parsed: ParsedSeed) -> List[BootstrapClue]:
        location = parsed.core_location or "核心地点"
        supernatural = parsed.supernatural_element or "异常规则"
        stakes = parsed.survival_stakes or "群体选择会影响生存风险"
        return [
            self._base_clue("clue_new_lock_core", "边界被改动的痕迹", f"{location}的入口或边界出现了不符合常识的改动，像是在众人抵达后才被重新定义。", "thread_shared_survival_rule", "location_gate", "obj_gate_lock", f"{location}的边界状态会变化，不能按正常入口理解。", 12),
            self._base_clue("clue_frontdesk_key", "可协同行动的线索物", "一个需要进一步确认用途的小物件被留在显眼又不安全的位置，像是在引导众人进入下一处地点。", "thread_shared_survival_rule", "location_frontdesk", "obj_frontdesk_drawer", "队伍获得了一个可用于验证下一处地点规则的线索物。", 8),
            self._base_clue("clue_missing_mark", "共同处境的标记", f"现场出现的标记同时指向多个角色的遭遇，证明{supernatural}并非只针对某一个人。", "thread_group_conflict", "location_frontdesk", None, f"多个角色都被{location}的同一套异常规则卷入。{stakes}", 15),
            self._base_clue("clue_fresh_footprints", "未知行动痕迹", "一组新近留下的痕迹避开了可见角色的行动路线，说明现场还有未被确认的行动源。", "thread_hidden_actor_trace", "location_hallway", "obj_fresh_footprints", "现场存在不属于当前可见角色的行动痕迹。", 10),
        ]

    def _generate_mystery_fallback(self, parsed: ParsedSeed) -> List[BootstrapClue]:
        location = parsed.core_location or "核心地点"
        missing = parsed.missing_person or "关键缺口"
        supernatural = parsed.supernatural_element or "异常"
        return [
            self._base_clue("clue_new_lock_core", "近期改动痕迹", f"{location}入口附近有近期被接触或改动过的痕迹，与长期无人进入的表象矛盾。", "thread_recent_entry", "location_gate", "obj_gate_lock", f"{location}近期被人接触或改变过。", 12),
            self._base_clue("clue_frontdesk_key", "可开启下一步调查的线索物", "一个不起眼的小物件被藏在可搜索的位置，显示有人希望后来者继续深入。", "thread_recent_entry", "location_frontdesk", "obj_frontdesk_drawer", "现场藏着一个能推进下一步调查的线索物。", 8),
            self._base_clue("clue_missing_mark", f"{missing}相关标记", f"某个不起眼的位置留下了与{missing}有关的标记，说明这条线索并非随机出现。", "thread_missing_trace", "location_frontdesk", None, f"{missing}与{location}的异常存在可验证交集。", 15),
            self._base_clue("clue_fresh_footprints", "未知行动痕迹", f"{location}内部出现不属于正常环境变化的新痕迹，方向指向更深处。", "thread_hidden_actor_trace", "location_hallway", "obj_fresh_footprints", f"{location}内部存在近期移动过的未知行动痕迹，可能与{supernatural}有关。", 10),
        ]

    @staticmethod
    def _base_clue(clue_id: str, title: str, content: str, thread_id: str, location_id: str, object_id: Optional[str], fact: str, progress: int) -> BootstrapClue:
        return BootstrapClue(
            clue_id=clue_id,
            title=title,
            content=content,
            level="surface",
            related_event=title,
            related_thread=thread_id,
            discover_routes=[DiscoverRoute(location_id=location_id, object_id=object_id, action="inspect", difficulty=1)],
            on_discovered=OnDiscovered(add_known_fact=fact, trigger_event=title, plot_progress=progress),
        )

    def _expand_long_form_clues(self, clues: List[BootstrapClue], parsed: ParsedSeed, target_chapters: int) -> List[BootstrapClue]:
        surface = chapters_for_stage(target_chapters, "surface")
        partial = chapters_for_stage(target_chapters, "partial")
        major = chapters_for_stage(target_chapters, "major")
        truth = chapters_for_stage(target_chapters, "truth")
        for index, clue in enumerate(clues):
            clue.planned_chapters = [surface[min(index, len(surface) - 1)]] if surface else [1]
            clue.evidence_ids = [self._evidence_for_role(index)]
            clue.related_truth = "surface"
            clue.reveal_role = "introduce"

        location = parsed.core_location or "核心地点"
        supernatural = parsed.supernatural_element or "异常规则"
        additions = [
            self._long_clue("clue_rule_contradiction", "互相矛盾的规则", f"关于{supernatural}的两条规则无法同时成立，说明幸存者掌握的信息可能被污染。", "thread_supernatural", "ev_rule_contradiction", partial[:2], "partial", "complicate", "location_archive", "obj_missing_file"),
            self._long_clue("clue_repeated_pattern", "重复出现的异常模式", f"{location}的异常并非随机出现，而是在相似选择后重复留下同类痕迹。", "thread_recent_entry", "ev_repeated_pattern", partial[2:4] or partial[:2], "partial", "confirm", "location_hallway", "obj_fresh_footprints"),
            self._long_clue("clue_false_safety", "伪安全区域的破绽", "被认为安全的地方留下了同样的异常痕迹，说明避难方案可能已经失效。", "thread_hidden_actor_trace", "ev_false_safety", major[:2], "major", "reversal", "location_witness_point", None),
            self._long_clue("clue_cost_record", "代价记录", "每次规避异常后都会少掉某种现实证明，生存规则本身需要交换。", "thread_core_motif", "ev_cost_record", major[2:4] or major[:2], "major", "confirm", "location_archive", "obj_missing_file"),
            self._long_clue("clue_origin_key", "源头关键证据", f"最终证据表明{supernatural}的源头与此前被误读的痕迹相连。", "thread_supernatural", "ev_origin_key", truth[:2], "truth", "payoff", "location_inner", None),
        ]
        existing = {clue.clue_id for clue in clues}
        for clue in additions:
            if clue.clue_id not in existing:
                clues.append(clue)
        return clues

    @staticmethod
    def _evidence_for_role(index: int) -> str:
        return ["ev_new_lock_core", "ev_key_signal", "ev_key_signal", "ev_fresh_footprints"][min(index, 3)]

    @staticmethod
    def _long_clue(
        clue_id: str,
        title: str,
        content: str,
        thread_id: str,
        evidence_id: str,
        planned_chapters: List[int],
        truth_stage: str,
        reveal_role: str,
        location_id: str,
        object_id: Optional[str],
    ) -> BootstrapClue:
        return BootstrapClue(
            clue_id=clue_id,
            title=title,
            content=content,
            level=truth_stage,
            related_event=title,
            related_thread=thread_id,
            discover_routes=[DiscoverRoute(location_id=location_id, object_id=object_id, action="inspect", difficulty=3)],
            on_discovered=OnDiscovered(add_known_fact=content, trigger_event=title, plot_progress=8),
            planned_chapters=planned_chapters or [1],
            evidence_ids=[evidence_id],
            related_truth=truth_stage,
            reveal_role=reveal_role,
        )
