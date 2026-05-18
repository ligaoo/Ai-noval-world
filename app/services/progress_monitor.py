from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from app.models.event import EventLog
from app.models.state import WorldState


@dataclass
class SoftHint:
    text: str


class ProgressMonitor:
    """无进展兜底（V1：轻量 soft_hint，不新增事实）。"""

    def __init__(self, no_progress_limit: int = 4):
        self.no_progress_limit = no_progress_limit

    def update_and_maybe_hint(self, state: WorldState, new_events: List[EventLog]) -> Optional[SoftHint]:
        progressed = any(
            (e.event_level == "plot")
            and (e.plot_value.progress > 0 or e.plot_value.mystery > 0 or e.plot_value.conflict > 0)
            for e in new_events
        )
        if progressed:
            state.no_progress_ticks = 0
            return None

        state.no_progress_ticks += 1
        if state.no_progress_ticks < self.no_progress_limit:
            return None

        # 触发一次 soft hint，然后重置计数（避免每 tick 都提示）
        state.no_progress_ticks = 0
        hint = self._build_hint(state)
        state.world.soft_hints.append(hint.text)
        return hint

    @staticmethod
    def _build_hint(state: WorldState) -> SoftHint:
        # V1：只给“注意某个可见对象/可问 topic”的提示，避免新增事实。
        visible_objects = [oid for oid, o in state.world.objects.items() if o.get("visible")]
        if visible_objects:
            obj = visible_objects[0]
            name = state.world.objects[obj].get("name", obj)
            return SoftHint(text=f"风从门缝钻进来，{name}轻轻碰撞了一下，发出几乎听不见的声响。")
        return SoftHint(text="空气里有股潮湿的味道，像是在提醒你：这里并不像传闻中那样死寂。")

