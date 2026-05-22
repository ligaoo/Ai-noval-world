"""
MultiAgentScheduler（plan §14）

把"只让主角行动"升级为"让所有 active_agent 行动"。

调度顺序（§14.3）：
1. 主角
2. 当前地点 NPC
3. 隐藏行动者（hidden_actor）
4. （世界规则触发由 EnvironmentEngine 自动处理）
5. （Director 纠偏由 SimulationRunner 自身处理）

它本身不会"代替"原 SimulationRunner 的 character loop，而是提供
`build_order(...)` 与 `should_act(...)`，供 runner 在 tick 循环里调用。
"""
from __future__ import annotations

from typing import Dict, List, Optional

from app.models.state import WorldState
from app.models.world import CharacterProfile, WorldConfig


class MultiAgentScheduler:
    """多角色调度器：决定每个 tick 谁能行动 + 行动顺序"""

    def __init__(self, world: WorldConfig):
        self.world = world
        self._cache_char_meta: Dict[str, Dict] = self._load_char_meta()

    def _load_char_meta(self) -> Dict[str, Dict]:
        """从 world.characters 里读 active_agent / visibility 等扩展字段
        （由 Bootstrap 写入；旧 world 没有这些字段时全部视为 active=True/visible）"""
        meta: Dict[str, Dict] = {}
        for c in self.world.characters.characters:
            d = c.model_dump() if hasattr(c, "model_dump") else {}
            meta[c.id] = {
                "active_agent": d.get("active_agent", True),
                "visibility": d.get("visibility", "visible"),
                "role": d.get("role", c.role),
                "narrative_function": d.get("narrative_function", []),
            }
        return meta

    def build_order(self, state: WorldState) -> List[str]:
        """构造一次 tick 内的行动顺序

        顺序：
          1) POV 主角
          2) 与主角同地点的 NPC（active_agent=true，visibility!=absent，非 hidden）
          3) hidden_actor（active_agent=true, visibility=hidden）
          4) 其他地点的 active 角色
        """
        pov_id = self.world.chapter_goal.pov
        pov_loc = state.characters.get(pov_id).location_id if pov_id in state.characters else None

        same_loc_npcs: List[str] = []
        hidden_actors: List[str] = []
        other_active: List[str] = []
        for cid, st in state.characters.items():
            if cid == pov_id:
                continue
            meta = self._cache_char_meta.get(cid, {})
            if not meta.get("active_agent", True):
                continue
            visibility = meta.get("visibility", "visible")
            if visibility == "absent":
                continue
            if visibility == "hidden":
                hidden_actors.append(cid)
                continue
            if st.location_id == pov_loc:
                same_loc_npcs.append(cid)
            else:
                other_active.append(cid)

        order: List[str] = []
        if pov_id in state.characters:
            order.append(pov_id)
        order.extend(same_loc_npcs)
        order.extend(hidden_actors)
        order.extend(other_active)
        return order

    def is_hidden_actor(self, character_id: str) -> bool:
        return self._cache_char_meta.get(character_id, {}).get("visibility") == "hidden"

    def is_pov(self, character_id: str) -> bool:
        return character_id == self.world.chapter_goal.pov

    def role_of(self, character_id: str) -> str:
        return self._cache_char_meta.get(character_id, {}).get("role", "")
