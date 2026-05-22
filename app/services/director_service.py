from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

from app.models.state import WorldState
from app.models.tension import InterventionProposal, PlotValue, TensionReport
from app.services.intervention_deduplicator import InterventionDeduplicator


class DirectorService:
    """
    V3.1：导演服务
    根据张力报告，决定是否干预、如何干预。
    只改变环境机会，不直接替角色做决定。

    P1 升级（V1 Bootstrap 计划 §15-§16）：
    - 优先生成 clue_route_hint，把 hint 绑到具体 clue 的 discover_route
    - 通过 InterventionDeduplicator 用 hint_key 去重，避免反复生成同类提示
    - 当 world 中加载了 bootstrap 的 clues.json（含 bootstrap_fact），
      Director 会优先补"还未被发现的 clue"
    """

    def __init__(self, world_config_dir: Path):
        self.world_config_dir = world_config_dir
        self.intervention_history: List[InterventionProposal] = []
        self.intervention_count = 0
        self.last_intervention_tick: int = 0
        self.cooldown_ticks: int = 3  # 干预冷却间隔
        self.deduplicator = InterventionDeduplicator()
        # 加载 world 的 clues.json 给 clue_route_hint 用
        self._world_clues: List[Dict] = self._load_world_clues()
        self._world_locations: Dict[str, Dict] = self._load_world_locations()
        self._world_characters: Dict[str, Dict] = self._load_world_characters()

    def _load_world_clues(self) -> List[Dict]:
        try:
            clues_file = self.world_config_dir / "clues.json"
            if clues_file.exists():
                data = json.loads(clues_file.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return data.get("clues", [])
                if isinstance(data, list):
                    return data
        except Exception:
            return []
        return []

    def _load_world_locations(self) -> Dict[str, Dict]:
        try:
            map_file = self.world_config_dir / "map.json"
            if map_file.exists():
                data = json.loads(map_file.read_text(encoding="utf-8"))
                locations = data.get("locations", []) if isinstance(data, dict) else data
                return {loc.get("id"): loc for loc in locations if loc.get("id")}
        except Exception:
            return {}
        return {}

    def _load_world_characters(self) -> Dict[str, Dict]:
        try:
            characters_file = self.world_config_dir / "characters.json"
            if characters_file.exists():
                data = json.loads(characters_file.read_text(encoding="utf-8"))
                characters = data.get("characters", []) if isinstance(data, dict) else data
                return {c.get("id"): c for c in characters if c.get("id")}
        except Exception:
            return {}
        return {}

    def propose_intervention(
        self,
        state: WorldState,
        tension_report: TensionReport,
        chapter_goal: str,
    ) -> Optional[InterventionProposal]:
        """根据当前状态提出干预建议"""

        if not tension_report.need_intervention:
            return None

        # 冷却机制：避免频繁干预
        if state.tick - self.last_intervention_tick < self.cooldown_ticks:
            return None

        # 总干预数限制（避免过度干预
        if self.intervention_count >= 5:
            return None

        diagnosis = tension_report.diagnosis
        recommendations = tension_report.recommended_intervention_types

        # 选择干预类型（优先解决主线问题）
        intervention_type = self._select_best_intervention(recommendations, diagnosis)

        if not intervention_type:
            return None

        # 生成具体干预内容
        proposal = self._generate_intervention(
            intervention_type, state, chapter_goal, diagnosis
        )

        if proposal:
            # P1: 去重（hint_key 重复 → 丢弃，避免反复生成同类提示）
            if self.deduplicator.is_duplicate(proposal, state):
                return None
            self.deduplicator.record(proposal)

            self.intervention_history.append(proposal)
            self.intervention_count += 1
            self.last_intervention_tick = state.tick

        return proposal

    def _select_best_intervention(
        self, recommendations: List[str], diagnosis: List[str]
    ) -> Optional[str]:
        """选择最合适的干预类型

        P1 优先级（plan §15.3）：
        1. clue_route_hint  — 当存在未发现 clue 且诊断为推进不足时，优先用它
        2. environment_hint — 通用氛围/解锁路径
        3. npc_pressure
        4. danger_signal
        5. relationship_trigger
        """
        # 若存在未发现 clue，且 diagnosis 提示推进不足，优先 clue_route_hint
        if self._has_undiscovered_clue() and self._needs_progress(diagnosis):
            return "clue_route_hint"

        priority_order = [
            "clue_route_hint",
            "environment_hint",
            "npc_pressure",
            "danger_signal",
            "relationship_trigger",
        ]

        for t in priority_order:
            if t in recommendations:
                return t

        return recommendations[0] if recommendations else None

    def _has_undiscovered_clue(self) -> bool:
        return any(c for c in self._world_clues if c.get("id"))

    def _location_name(self, location: str) -> str:
        loc = self._world_locations.get(location, {})
        return loc.get("name") or location

    @staticmethod
    def _needs_progress(diagnosis: List[str]) -> bool:
        keys = ["progress", "推进", "停滞", "main_thread"]
        joined = " ".join(diagnosis or [])
        return any(k in joined for k in keys)

    def _generate_intervention(
        self,
        intervention_type: str,
        state: WorldState,
        chapter_goal: str,
        diagnosis: List[str],
    ) -> Optional[InterventionProposal]:
        """生成具体干预内容"""

        # 确定主角所在地点（作为默认目标）
        pov_char = next(iter(state.characters.keys()), None)
        if not pov_char:
            return None
        target_location = state.characters[pov_char].location_id

        # 根据类型生成内容
        if intervention_type == "clue_route_hint":
            return self._make_clue_route_hint(target_location, diagnosis, state)
        if intervention_type == "environment_hint":
            return self._make_environment_hint(target_location, diagnosis)
        elif intervention_type == "npc_pressure":
            return self._make_npc_pressure(target_location, diagnosis)
        elif intervention_type == "danger_signal":
            return self._make_danger_signal(target_location, diagnosis)
        elif intervention_type == "time_pressure":
            return self._make_time_pressure(diagnosis)
        else:
            return None

    def _make_clue_route_hint(
        self, location: str, diagnosis: List[str], state: WorldState
    ) -> Optional[InterventionProposal]:
        """P1 新增（plan §15.2）：
        把 hint 绑到具体 clue 的 discover_route，生成一个可被 inspect/search 的对象。
        """
        # 选一个未发现的 clue
        target_clue = None
        for c in self._world_clues:
            cid = c.get("id")
            if not cid:
                continue
            if state.world.discovered_facts.get(cid, False):
                continue
            target_clue = c
            break

        if not target_clue:
            return None

        routes = target_clue.get("discover_routes") or []
        if not routes:
            return None
        route = next((r for r in routes if r.get("location_id") == location), routes[0])

        target_loc = route.get("location_id") or location
        object_id = route.get("target") or route.get("object_id") or f"hint_{target_clue.get('id')}"
        content = (
            route.get("result_text")
            or target_clue.get("content")
            or target_clue.get("name")
            or "现场出现了一处异常的痕迹。"
        )
        action_type = route.get("action_type") or route.get("action") or "inspect"

        return InterventionProposal(
            need_intervention=True,
            reason=f"补 clue {target_clue.get('id')}：当前 PlotArc 阶段缺少 required event",
            intervention_type="clue_route_hint",
            target_location=target_loc,
            content=content,
            allowed_followup_actions=[action_type, "observe"],
            forbidden_effects=[
                "不能直接暴露核心真相",
                "不能让角色凭空知道线索内容",
            ],
            plot_value=PlotValue(
                progress=2,
                mystery=4,
                conflict=0,
                danger=1,
                relationship=0,
                novelty=3,
                emotion=2,
            ),
            hint_key=f"clue_route__{target_clue.get('id')}",
            target_clue_id=target_clue.get("id"),
            target_object_id=object_id,
            creates_object={
                "object_id": object_id,
                "location_id": target_loc,
                "description": content,
                "allowed_actions": [action_type],
                "hint_key": f"clue_route__{target_clue.get('id')}",
                "target_clue_id": target_clue.get("id"),
                "source_character_id": None,
            },
        )

    def _make_environment_hint(
        self, location: str, diagnosis: List[str]
    ) -> InterventionProposal:
        """环境暗示：开放新的探索机会"""

        loc = self._world_locations.get(location, {})
        loc_name = loc.get("name") or location
        objects = loc.get("objects") or []
        if objects:
            obj = objects[self.intervention_count % len(objects)]
            obj_name = obj.get("name") or obj.get("id") or "某个可疑对象"
            obj_desc = obj.get("description") or "细节显示它近期被触碰或改变过。"
            content = f"{loc_name}里的{obj_name}出现了新的可检查细节：{obj_desc}"
        else:
            content = f"{loc_name}的环境状态发生了细微变化，留下一个可以观察或检查的新机会。"

        return InterventionProposal(
            need_intervention=True,
            reason="主线推进不足，提供新的探索机会",
            intervention_type="environment_hint",
            target_location=location,
            content=content,
            allowed_followup_actions=["observe", "inspect", "search", "move"],
            forbidden_effects=[
                "不能直接暴露核心真相",
                "不能让角色凭空知道线索内容",
            ],
            plot_value=PlotValue(
                progress=2,
                mystery=4,
                conflict=0,
                danger=1,
                relationship=0,
                novelty=3,
                emotion=2,
            ),
        )

    def _make_npc_pressure(
        self, location: str, diagnosis: List[str]
    ) -> InterventionProposal:
        """NPC 压力：增加冲突，推进对话"""

        visible_npcs = [
            c for c in self._world_characters.values()
            if c.get("role") != "protagonist"
            and c.get("visibility", "visible") == "visible"
            and c.get("active_agent", True)
        ]
        if visible_npcs:
            npc = visible_npcs[self.intervention_count % len(visible_npcs)]
            npc_name = npc.get("name") or npc.get("id") or "某个角色"
            npc_goal = (npc.get("goals") or {}).get("short_term") or "坚持自己的判断"
            content = f"{npc_name}在{self._location_name(location)}表现出明显压力，坚持要优先处理：{npc_goal}。"
        else:
            content = f"{self._location_name(location)}附近出现来自未确认角色的压力，迫使当前行动必须立刻作出回应。"

        return InterventionProposal(
            need_intervention=True,
            reason="冲突强度偏低，增加 NPC 压力",
            intervention_type="npc_pressure",
            target_location=location,
            content=content,
            allowed_followup_actions=["ask", "talk", "observe", "inspect"],
            forbidden_effects=[
                "不能直接暴露 NPC 知道的全部真相",
                "不能让 NPC 做出不符合设定的行为",
            ],
            plot_value=PlotValue(
                progress=1,
                mystery=3,
                conflict=5,
                danger=2,
                relationship=3,
                novelty=2,
                emotion=4,
            ),
        )

    def _make_danger_signal(
        self, location: str, diagnosis: List[str]
    ) -> InterventionProposal:
        """危险信号：增加紧张气氛"""

        loc_name = self._location_name(location)
        danger_content = [
            f"{loc_name}的环境反馈突然变得不稳定，原本安全的行动窗口正在缩小。",
            f"{loc_name}附近出现无法立即确认来源的动静，迫使角色重新评估风险。",
            f"{loc_name}的感官细节发生异常变化，说明当前位置不宜停留太久。",
            f"{loc_name}与外部的联系感进一步减弱，行动选择变得更少。",
        ]

        content = danger_content[self.intervention_count % len(danger_content)]

        return InterventionProposal(
            need_intervention=True,
            reason="危险感不足，增加紧张气氛",
            intervention_type="danger_signal",
            target_location=location,
            content=content,
            allowed_followup_actions=["observe", "inspect", "move"],
            forbidden_effects=[
                "不能直接造成角色伤害",
                "不能暴露超自然元素的核心真相",
            ],
            plot_value=PlotValue(
                progress=0,
                mystery=5,
                conflict=1,
                danger=6,
                relationship=0,
                novelty=4,
                emotion=5,
            ),
        )

    def _make_time_pressure(self, diagnosis: List[str]) -> InterventionProposal:
        """时间压力：压缩行动窗口"""

        content = "当前世界的时间窗口正在收紧，角色必须在更多线索消失或环境恶化前推进下一步。"

        return InterventionProposal(
            need_intervention=True,
            reason="节奏拖沓，增加时间压力",
            intervention_type="time_pressure",
            target_location="global",
            content=content,
            allowed_followup_actions=["inspect", "search", "move", "ask"],
            forbidden_effects=[
                "不能直接结束游戏",
                "不能让时间突然跳到不可挽回的地步",
            ],
            plot_value=PlotValue(
                progress=1,
                mystery=2,
                conflict=2,
                danger=4,
                relationship=0,
                novelty=1,
                emotion=3,
            ),
        )

    def save_history(self, output_dir: Path) -> None:
        """保存干预历史"""
        history_file = output_dir / "director_history.jsonl"
        with open(history_file, "w", encoding="utf-8") as f:
            for proposal in self.intervention_history:
                # Pydantic V2 model_dump_json 不支持 ensure_ascii，使用 json.dumps
                data = proposal.model_dump()
                f.write(json.dumps(data, ensure_ascii=False) + "\n")
