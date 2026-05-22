"""
VisibleEventFilter（plan §19）

沙盘里可以有 hidden_actor 行动，但正文只写主角可感知部分：
- 主角亲眼看到 = 可写
- 主角听到的声音 = 可写
- 主角发现的痕迹 = 可写
- 隐藏角色真实行动 = 不可直接写
- 系统真相 = 不可直接写
- NPC 内心 = 除非 POV 允许，否则不可写

它被接入到：
  1. EventLogService.append 之前做可见性映射，给 visible_to 赋值
  2. NarrativeService.generate_chapter 之前过滤事件，不让 hidden 内容进 LLM prompt
"""
from __future__ import annotations

from typing import List

from app.models.event import EventLog


class VisibleEventFilter:
    def filter_events(
        self,
        events: List[EventLog],
        pov_id: str,
        scheduler=None,  # MultiAgentScheduler，给 visible_to 打标用
    ) -> List[EventLog]:
        """
        给事件打 visible_to 标签，并过滤：
        - hidden_actor 自身的事件只对他自己可见，除非它留下痕迹
        - 正常角色的事件默认对同地点的人可见
        - 带 `leaves_trace` 标记的 hidden_actor 事件，痕迹的 visible_to 含 pov_id
        """
        result: List[EventLog] = []
        for e in events:
            if e is None:
                continue

            # 如果事件已经有 visible_to，不覆盖；但补充 pov_id 进去（兜底）
            if e.visible_to is None or not e.visible_to:
                # 推断事件发起者
                initiator = None
                if e.actors and len(e.actors) == 1:
                    initiator = e.actors[0]
                elif e.action and e.action.agent_id:
                    initiator = e.action.agent_id

                if initiator and scheduler and scheduler.is_hidden_actor(initiator):
                    # hidden_actor 的事件：只让自己 + 留下的痕迹可见
                    # 注意：痕迹类事件本身的 result 应该是环境描述，而不是"某人做了什么"
                    action_type = e.action.action_type if e.action else ""
                    if e.event_type == "leave_trace" or action_type == "leave_trace":
                        e.visible_to = [pov_id] if pov_id else []
                    else:
                        e.visible_to = [initiator]
                else:
                    # 默认：同地点角色 + POV 都可见
                    e.visible_to = [pov_id] if pov_id else []

            result.append(e)
        return result

    def filter_for_narrative(self, events: List[EventLog], pov_id: str) -> List[EventLog]:
        """只给 LLM 写正文用的过滤：只保留 POV 可感知的内容"""
        return [e for e in events if e and (pov_id in (e.visible_to or []))]

    @staticmethod
    def has_sensitive_content(event: EventLog) -> bool:
        """检测事件是否直接暴露了 hidden_actor 身份或系统真相（应避免写进正文）"""
        text = (event.result or "") + " " + " ".join(event.hidden_effects or [])
        keywords = ["hidden_actor", "系统真相", "真实身份", "unknown", "UNKNOWN"]
        return any(k in text for k in keywords) if text else False
