from __future__ import annotations

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from app.models.action import ActionCommand


class EmotionalImpact(BaseModel):
    # 角色 -> 情绪描述（V1 仅记录文本）
    impacts: Dict[str, str] = Field(default_factory=dict)


class PlotValue(BaseModel):
    """V3.1：事件对剧情的贡献值"""
    progress: int = 0      # 主线推进
    mystery: int = 0       # 悬念强度
    conflict: int = 0      # 冲突强度
    danger: int = 0        # 危险感
    relationship: int = 0  # 人物关系变化
    novelty: int = 0       # 新鲜度
    emotion: int = 0       # 人物情绪波动


class EventLog(BaseModel):
    event_id: str
    event_level: Literal["raw", "plot"] = "raw"
    time: str
    location_id: str
    actors: List[str]
    event_type: str
    action: Optional[ActionCommand] = None
    result: str
    visible_to: List[str] = Field(default_factory=list)
    hidden_effects: List[str] = Field(default_factory=list)
    discovered_facts: List[str] = Field(default_factory=list)
    emotional_impact: EmotionalImpact = Field(default_factory=EmotionalImpact)
    plot_value: PlotValue = Field(default_factory=PlotValue)

