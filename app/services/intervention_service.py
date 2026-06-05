from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

from app.models.event import EventLog
from app.models.state import WorldState
from app.models.tension import InterventionEvent, InterventionProposal, PlotValue


class InterventionService:
    """
    V3.2：干预执行服务
    将 Director 的干预建议转化为真实环境事件，写入 EventLog。
    """

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.applied_interventions: List[InterventionEvent] = []
        self.intervention_counter = 0

    def apply_intervention(
        self,
        proposal: InterventionProposal,
        state: WorldState,
        agent_id: str,
    ) -> Optional[InterventionEvent]:
        """执行导演干预，生成事件"""

        if not proposal.need_intervention:
            return None

        self.intervention_counter += 1

        # 转换为实际干预事件
        intervention_event = self._proposal_to_event(proposal, state)

        # 应用环境变化
        self._apply_environment_changes(intervention_event, state)

        self.applied_interventions.append(intervention_event)

        return intervention_event

    def _proposal_to_event(
        self, proposal: InterventionProposal, state: WorldState
    ) -> InterventionEvent:
        """将干预建议转换为可写入的事件"""

        event_id = f"evt_intervention_{self.intervention_counter:03d}"

        # 根据干预类型确定具体效果
        unlocked_routes = []
        unlocked_targets = []
        added_topics = {}

        if proposal.intervention_type == "environment_hint":
            # 环境暗示：开放新的可检查目标
            if "抽屉" in proposal.content or "抽屉" in proposal.content:
                unlocked_targets.append(f"hint_{event_id}_drawer")
            elif "门" in proposal.content or "门" in proposal.content:
                unlocked_routes.append(f"route_{event_id}_secret_door")
            elif "值班室" in proposal.content or "纸张" in proposal.content:
                unlocked_targets.append(f"hint_{event_id}_guard_room_desk")
            elif "锁" in proposal.content or "铁锁" in proposal.content:
                unlocked_targets.append(f"hint_{event_id}_gate_lock")
            elif "脚印" in proposal.content or "走廊" in proposal.content:
                unlocked_targets.append(f"hint_{event_id}_footprints")
            elif "文件柜" in proposal.content or "便签" in proposal.content:
                unlocked_targets.append(f"hint_{event_id}_file_cabinet")
            else:
                # 默认添加一个通用的可探索目标
                unlocked_targets.append(f"hint_{event_id}_investigate_point")

        elif proposal.intervention_type == "npc_pressure":
            # NPC 压力：可能开放新对话 topic
            added_topics = {
                "char_guard": ["why_nervous", "what_are_you_hiding"]
            }

        return InterventionEvent(
            event_id=event_id,
            event_type="director_intervention",
            intervention_type=proposal.intervention_type,
            location_id=proposal.target_location,
            result=proposal.content,
            visible_to=list(state.characters.keys()),  # 默认所有人都能看到
            unlocked_routes=unlocked_routes,
            unlocked_targets=unlocked_targets,
            added_topics=added_topics,
            plot_value=proposal.plot_value,
        )

    def _apply_environment_changes(
        self, event: InterventionEvent, state: WorldState
    ) -> None:
        """将干预效果应用到世界状态"""

        # 注意：这里我们不直接修改 discovered_facts
        # 干预只创造"机会"，不直接给出"答案"

        # 将解锁的目标添加到运行时环境中
        if event.unlocked_targets:
            for target_id in event.unlocked_targets:
                if target_id not in state.world.objects:
                    state.world.objects[target_id] = {
                        "location_id": event.location_id,
                        "discovered_by": event.visible_to,
                        "hint_source": event.event_id,
                    }

        # 如果有新增的话题，应该更新对应 NPC 的可用话题
        # （这里可以与 CharacterAgentService 集成）
        pass

    def to_event_log(self, intervention: InterventionEvent) -> EventLog:
        """转换为标准 EventLog 格式"""

        from app.models.action import ActionCommand

        return EventLog(
            event_id=intervention.event_id,
            event_level="plot",
            time="",  # 会在 simulation_runner 中设置
            event_type=intervention.event_type,
            location_id=intervention.location_id,
            result=intervention.result,
            actors=intervention.visible_to,
            visible_to=intervention.visible_to,
            discovered_facts=[],  # 干预不直接给线索，只给机会
            action=None,
            plot_value=intervention.plot_value.model_dump(),
        )

    def save_history(self) -> None:
        """保存干预历史"""
        history_file = self.output_dir / "intervention_history.jsonl"
        with open(history_file, "w", encoding="utf-8") as f:
            for event in self.applied_interventions:
                # Pydantic V2 model_dump_json 不支持 ensure_ascii，使用 json.dumps
                data = event.model_dump()
                f.write(json.dumps(data, ensure_ascii=False) + "\n")
