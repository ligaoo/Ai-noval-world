from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class ArcStage(BaseModel):
    """人物弧光单阶段"""
    stage_id: str
    name: str
    description: str
    required_belief_changes: List[str] = []


class CharacterArc(BaseModel):
    """完整人物弧光配置"""
    character_id: str
    starting_state: str
    wound: str
    false_belief: str
    desire: str
    need: str
    current_stage: str = "avoidance"
    stages: List[ArcStage]
    completed_stages: List[str] = []
    progress: int = 0


class RelationshipUpdate(BaseModel):
    """关系更新"""
    target: str
    attitude_delta: int
    reason: str


class BeliefChange(BaseModel):
    """信念变化"""
    from_belief: str
    to_belief: str


class ReflectionResult(BaseModel):
    """一次反思的结果"""
    agent_id: str
    new_understanding: List[str]
    changed_beliefs: List[BeliefChange]
    relationship_updates: List[RelationshipUpdate]
    next_intentions: List[str]


class ArcContext(BaseModel):
    """注入 AgentContext 的人物弧光信息"""
    current_stage: str
    stage_name: str
    internal_conflict: str
    wound: str
    false_belief: str
    desire: str
    need: str
    recent_reflections: List[str] = []
    progress_percent: int = 0
