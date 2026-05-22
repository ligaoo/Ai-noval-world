from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel


class PlotValue(BaseModel):
    """事件对剧情的贡献值（0-10）"""
    progress: int = 0      # 主线推进
    mystery: int = 0       # 悬念强度
    conflict: int = 0      # 冲突强度
    danger: int = 0        # 危险感
    relationship: int = 0  # 人物关系变化
    novelty: int = 0       # 新鲜度
    emotion: int = 0       # 人物情绪波动


class TensionScores(BaseModel):
    """张力评分"""
    progress: float = 0.0
    mystery: float = 0.0
    conflict: float = 0.0
    danger: float = 0.0
    relationship: float = 0.0
    novelty: float = 0.0
    emotion: float = 0.0


class TensionReport(BaseModel):
    """张力报告"""
    simulation_id: str
    tick: int
    window: str
    scores: TensionScores
    window_event_count: int = 0
    diagnosis: List[str] = []
    recommended_intervention_types: List[str] = []
    need_intervention: bool = False


class InterventionProposal(BaseModel):
    """导演干预建议"""
    need_intervention: bool
    reason: str
    intervention_type: str  # environment_hint / npc_pressure / danger_signal / clue_route_hint
    target_location: str
    content: str
    allowed_followup_actions: List[str]
    forbidden_effects: List[str]
    plot_value: PlotValue

    # ===== P1 新增字段 =====
    # 用于 InterventionDeduplicator 去重
    hint_key: Optional[str] = None
    # clue_route_hint 专用：让干预可以引导到具体 clue 的发现
    target_clue_id: Optional[str] = None
    target_object_id: Optional[str] = None
    source_character_id: Optional[str] = None  # 这个 hint 是哪个 NPC 留下的
    creates_object: Optional[Dict] = None

    model_config = {"extra": "allow"}


class InterventionEvent(BaseModel):
    """干预事件（写入 EventLog）"""
    event_id: str
    event_type: str = "director_intervention"
    intervention_type: str
    location_id: str
    result: str
    visible_to: List[str]
    unlocked_routes: List[str] = []
    unlocked_targets: List[str] = []
    added_topics: Dict[str, List[str]] = {}
    created_objects: Dict[str, Dict] = {}
    plot_value: PlotValue
