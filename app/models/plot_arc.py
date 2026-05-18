from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class StageConfig(BaseModel):
    """单阶段配置"""
    stage_id: str
    name: str
    purpose: str
    required_events: List[str] = []
    allowed_clue_levels: List[str] = ["surface", "minor"]
    forbidden_revelations: List[str] = []


class PlotArc(BaseModel):
    """完整剧情弧配置"""
    arc_id: str
    name: str
    status: str = "active"
    current_stage: str = "setup"
    progress: int = 0
    stages: List[StageConfig]
    completed_stages: List[str] = []


class PlotArcState(BaseModel):
    """剧情弧运行时状态"""
    active_arc: PlotArc
    discovered_clue_ids: List[str] = []
    triggered_events: List[str] = []
    unresolved_questions: List[str] = []
    resolved_questions: List[str] = []

    def get_current_stage(self) -> Optional[StageConfig]:
        """获取当前阶段配置"""
        for stage in self.active_arc.stages:
            if stage.stage_id == self.active_arc.current_stage:
                return stage
        return None

    def is_clue_allowed(self, clue: Dict[str, Any]) -> bool:
        """检查线索是否允许在当前阶段发现"""
        stage = self.get_current_stage()
        if not stage:
            return True

        clue_level = clue.get("level", "surface")
        allowed_levels = stage.allowed_clue_levels

        if clue_level not in allowed_levels:
            return False

        # 检查 allowed_stages
        allowed_stages = clue.get("allowed_stages", [])
        if allowed_stages and self.active_arc.current_stage not in allowed_stages:
            return False

        return True

    def can_advance_stage(self) -> bool:
        """检查是否可以推进到下一阶段"""
        stage = self.get_current_stage()
        if not stage:
            return False

        # 检查 required_events 是否已触发
        for req in stage.required_events:
            if req not in self.triggered_events:
                return False

        return True

    def advance_to_next_stage(self) -> Optional[str]:
        """推进到下一阶段"""
        if not self.can_advance_stage():
            return None

        current_idx = -1
        for i, stage in enumerate(self.active_arc.stages):
            if stage.stage_id == self.active_arc.current_stage:
                current_idx = i
                break

        if current_idx >= 0 and current_idx + 1 < len(self.active_arc.stages):
            next_stage = self.active_arc.stages[current_idx + 1]
            self.active_arc.completed_stages.append(self.active_arc.current_stage)
            self.active_arc.current_stage = next_stage.stage_id
            return next_stage.stage_id

        return None
