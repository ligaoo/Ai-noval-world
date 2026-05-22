"""
InterventionDeduplicator（plan §16）

防止 Director 反复生成同类 hint。
每个 intervention 必须带 hint_key，重复 key 直接丢弃。
"""
from __future__ import annotations

from typing import Set

from app.models.state import WorldState
from app.models.tension import InterventionProposal


class InterventionDeduplicator:
    """Director 干预去重器"""

    def __init__(self):
        self.seen_hint_keys: Set[str] = set()
        self.dropped_count: int = 0

    def is_duplicate(self, intervention: InterventionProposal, state: WorldState) -> bool:
        if intervention is None:
            return False
        hint_key = intervention.hint_key
        if not hint_key:
            # 自动派生一个 fallback hint_key（location + content hash 前 16 位）
            hint_key = self._auto_hint_key(intervention)
            intervention.hint_key = hint_key

        # 内存内已生成过
        if hint_key in self.seen_hint_keys:
            self.dropped_count += 1
            return True

        # 世界中已存在同 hint_key 的对象（避免重启或多次启动 Director 时重复）
        try:
            for obj_id, obj_meta in (state.world.objects or {}).items():
                if isinstance(obj_meta, dict) and obj_meta.get("hint_key") == hint_key:
                    self.dropped_count += 1
                    return True
        except Exception:
            pass

        return False

    def record(self, intervention: InterventionProposal) -> None:
        if intervention and intervention.hint_key:
            self.seen_hint_keys.add(intervention.hint_key)

    @staticmethod
    def _auto_hint_key(intervention: InterventionProposal) -> str:
        loc = intervention.target_location or "unknown"
        obj = intervention.target_object_id or intervention.target_clue_id or ""
        content = (intervention.content or "")[:24]
        return f"{loc}__{obj}__{abs(hash(content)) % (10 ** 8):08d}"
