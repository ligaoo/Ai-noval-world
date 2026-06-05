from __future__ import annotations

import json
import re
from typing import List, Optional

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

    def generate(self, parsed: ParsedSeed) -> List[BootstrapClue]:
        if self.llm_client:
            clues = self._generate_with_llm(parsed)
            if clues:
                return clues

        if parsed.cast_mode == "ensemble_survival":
            return self._generate_ensemble_fallback(parsed)
        return self._generate_mystery_fallback(parsed)

    def _generate_with_llm(self, parsed: ParsedSeed) -> Optional[List[BootstrapClue]]:
        system = "你是线索与发现路径生成器，必须返回 JSON object，不要输出额外解释。"
        user = f"""
请基于 ParsedSeed 生成第一章可发现 clues。

ParsedSeed:
{json.dumps(parsed.model_dump(), ensure_ascii=False, indent=2)}

硬性要求：
- 返回 JSON object，格式为 {"clues": [...]}，数组中每项字段：clue_id, title, content, level, related_event, related_thread, discover_routes, on_discovered。
- 至少 4 条，并保留这些 clue_id：clue_new_lock_core, clue_frontdesk_key, clue_missing_mark, clue_fresh_footprints。
- discover_routes 中 location_id 必须从 location_gate, location_frontdesk, location_hallway, location_archive 中选择；object_id 必须匹配默认地图对象：obj_gate_lock, obj_frontdesk_drawer, obj_fresh_footprints, obj_missing_file，或为空。
- on_discovered 字段：add_known_fact, add_inventory_item, trigger_event, plot_progress。
- 内容必须从 ParsedSeed 推导；信息不足时可自行补全，但不要固定成前台钥匙、医院病案、十年前事故或固定失踪亲友。
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
            return clues if expected.issubset({c.clue_id for c in clues}) else None
        except Exception:
            return None

    def _generate_ensemble_fallback(self, parsed: ParsedSeed) -> List[BootstrapClue]:
        location = parsed.core_location or "核心地点"
        supernatural = parsed.supernatural_element or "异常规则"
        stakes = parsed.survival_stakes or "群体选择会影响生存风险"

        return [
            BootstrapClue(
                clue_id="clue_new_lock_core",
                title="边界被改动的痕迹",
                content=f"{location}的入口或边界出现了不符合常识的改动，像是在众人抵达后才被重新定义。",
                level="surface",
                related_event="发现边界规则异常",
                related_thread="thread_shared_survival_rule",
                discover_routes=[DiscoverRoute(
                    location_id="location_gate",
                    object_id="obj_gate_lock",
                    action="inspect",
                    difficulty=1,
                )],
                on_discovered=OnDiscovered(
                    add_known_fact=f"{location}的边界状态会变化，不能按正常入口理解。",
                    trigger_event="发现边界规则异常",
                    plot_progress=12,
                ),
            ),
            BootstrapClue(
                clue_id="clue_frontdesk_key",
                title="可协同行动的线索物",
                content="一个需要进一步确认用途的小物件被留在显眼又不安全的位置，像是在引导众人进入下一处地点。",
                level="minor",
                related_event="发现需要协作验证的线索物",
                related_thread="thread_shared_survival_rule",
                discover_routes=[DiscoverRoute(
                    location_id="location_frontdesk",
                    object_id="obj_frontdesk_drawer",
                    action="search",
                    difficulty=1,
                )],
                on_discovered=OnDiscovered(
                    add_known_fact="队伍获得了一个可用于验证下一处地点规则的线索物。",
                    add_inventory_item="item_route_token",
                    trigger_event="发现需要协作验证的线索物",
                    plot_progress=8,
                ),
            ),
            BootstrapClue(
                clue_id="clue_missing_mark",
                title="共同处境的标记",
                content=f"现场出现的标记同时指向多个角色的遭遇，证明{supernatural}并非只针对某一个人。",
                level="minor",
                related_event="发现共同处境标记",
                related_thread="thread_group_conflict",
                discover_routes=[DiscoverRoute(
                    location_id="location_frontdesk",
                    action="inspect",
                    difficulty=2,
                )],
                on_discovered=OnDiscovered(
                    add_known_fact=f"多个角色都被{location}的同一套异常规则卷入。{stakes}",
                    trigger_event="发现共同处境标记",
                    plot_progress=15,
                ),
            ),
            BootstrapClue(
                clue_id="clue_fresh_footprints",
                title="未知行动痕迹",
                content="一组新近留下的痕迹避开了可见角色的行动路线，说明现场还有未被确认的行动源。",
                level="surface",
                related_event="发现未知行动痕迹",
                related_thread="thread_hidden_actor_trace",
                discover_routes=[DiscoverRoute(
                    location_id="location_hallway",
                    object_id="obj_fresh_footprints",
                    action="inspect",
                    difficulty=1,
                )],
                on_discovered=OnDiscovered(
                    add_known_fact="现场存在不属于当前可见角色的行动痕迹。",
                    trigger_event="发现未知行动痕迹",
                    plot_progress=10,
                ),
            ),
        ]

    def _generate_mystery_fallback(self, parsed: ParsedSeed) -> List[BootstrapClue]:
        location = parsed.core_location or "核心地点"
        missing = parsed.missing_person or "关键缺口"
        supernatural = parsed.supernatural_element or "异常"

        return [
            BootstrapClue(
                clue_id="clue_new_lock_core",
                title="近期改动痕迹",
                content=f"{location}入口附近有近期被接触或改动过的痕迹，与长期无人进入的表象矛盾。",
                level="surface",
                related_event="发现近期改动痕迹",
                related_thread="thread_recent_entry",
                discover_routes=[DiscoverRoute(
                    location_id="location_gate",
                    object_id="obj_gate_lock",
                    action="inspect",
                    difficulty=1,
                )],
                on_discovered=OnDiscovered(
                    add_known_fact=f"{location}近期被人接触或改变过。",
                    trigger_event="发现近期改动痕迹",
                    plot_progress=12,
                ),
            ),
            BootstrapClue(
                clue_id="clue_frontdesk_key",
                title="可开启下一步调查的线索物",
                content="一个不起眼的小物件被藏在可搜索的位置，显示有人希望后来者继续深入。",
                level="minor",
                related_event="发现推进调查的线索物",
                related_thread="thread_recent_entry",
                discover_routes=[DiscoverRoute(
                    location_id="location_frontdesk",
                    object_id="obj_frontdesk_drawer",
                    action="search",
                    difficulty=1,
                )],
                on_discovered=OnDiscovered(
                    add_known_fact="现场藏着一个能推进下一步调查的线索物。",
                    add_inventory_item="item_route_token",
                    trigger_event="发现推进调查的线索物",
                    plot_progress=8,
                ),
            ),
            BootstrapClue(
                clue_id="clue_missing_mark",
                title=f"{missing}相关标记",
                content=f"某个不起眼的位置留下了与{missing}有关的标记，说明这条线索并非随机出现。",
                level="minor",
                related_event=f"发现{missing}相关痕迹",
                related_thread="thread_missing_trace",
                discover_routes=[DiscoverRoute(
                    location_id="location_frontdesk",
                    action="inspect",
                    difficulty=2,
                )],
                on_discovered=OnDiscovered(
                    add_known_fact=f"{missing}与{location}的异常存在可验证交集。",
                    trigger_event=f"发现{missing}相关痕迹",
                    plot_progress=15,
                ),
            ),
            BootstrapClue(
                clue_id="clue_fresh_footprints",
                title="未知行动痕迹",
                content=f"{location}内部出现不属于正常环境变化的新痕迹，方向指向更深处。",
                level="surface",
                related_event="发现未知行动痕迹",
                related_thread="thread_hidden_actor_trace",
                discover_routes=[DiscoverRoute(
                    location_id="location_hallway",
                    object_id="obj_fresh_footprints",
                    action="inspect",
                    difficulty=1,
                )],
                on_discovered=OnDiscovered(
                    add_known_fact=f"{location}内部存在近期移动过的未知行动痕迹，可能与{supernatural}有关。",
                    trigger_event="发现未知行动痕迹",
                    plot_progress=10,
                ),
            ),
        ]
