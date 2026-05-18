from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class ChapterGoalStatus(BaseModel):
    goal: str
    completed: bool = False
    progress: int = 0  # 0..100


class CharacterRuntimeState(BaseModel):
    location_id: str
    mental_state: str = ""
    known_facts: List[str] = Field(default_factory=list)
    suspicions: List[str] = Field(default_factory=list)
    inventory: List[str] = Field(default_factory=list)
    last_action: Optional[str] = None
    repeat_action_count: int = 0

    # 对话态度（V1 用一个整数即可）
    attitude_to: Dict[str, int] = Field(default_factory=dict)


class WorldRuntimeState(BaseModel):
    discovered_facts: Dict[str, bool] = Field(default_factory=dict)
    objects: Dict[str, dict] = Field(default_factory=dict)
    soft_hints: List[str] = Field(default_factory=list)


class WorldState(BaseModel):
    simulation_id: str
    tick: int = 0
    world_time: str = "day1_20:00"
    random_seed: int = 0
    chapter_goal_status: ChapterGoalStatus
    no_progress_ticks: int = 0
    characters: Dict[str, CharacterRuntimeState] = Field(default_factory=dict)
    world: WorldRuntimeState = Field(default_factory=WorldRuntimeState)

