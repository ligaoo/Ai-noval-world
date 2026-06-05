from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SelectedEvent(BaseModel):
    event_id: str
    importance: float = 0.0
    scene_role: str = "setup"
    reason: str = ""
    thread_ids: List[str] = Field(default_factory=list)
    character_impact: List[Dict[str, str]] = Field(default_factory=list)
    reader_question: str = ""


class CompressedEventGroup(BaseModel):
    source_event_ids: List[str] = Field(default_factory=list)
    summary: str = ""


class DiscardedEvent(BaseModel):
    event_id: str
    reason: str = ""


class SelectedEventsReport(BaseModel):
    version: str = "正式版V1.2"
    selected_events: List[SelectedEvent] = Field(default_factory=list)
    compressed_events: List[CompressedEventGroup] = Field(default_factory=list)
    discarded_events: List[DiscardedEvent] = Field(default_factory=list)


class SceneRevealBudget(BaseModel):
    allowed: List[str] = Field(default_factory=list)
    suspected: List[str] = Field(default_factory=list)
    forbidden: List[str] = Field(default_factory=list)


class SceneSpec(BaseModel):
    scene_id: str
    scene_goal: str = ""
    location_id: str = ""
    pov_state: str = ""
    conflict: str = ""
    event_ids: List[str] = Field(default_factory=list)
    scene_role: str = "setup"
    reveal_budget: SceneRevealBudget = Field(default_factory=SceneRevealBudget)
    emotional_turn: str = "观察 -> 不安"
    ending_beat: str = ""


class ChapterHook(BaseModel):
    type: str = "clue_hook"
    event_id: Optional[str] = None
    requirement: str = "以未解释的物理痕迹或感官异常结束。"


class ScenePlan(BaseModel):
    version: str = "正式版V1.2"
    chapter_title: str = ""
    pov: str = ""
    scenes: List[SceneSpec] = Field(default_factory=list)
    chapter_hook: ChapterHook = Field(default_factory=ChapterHook)
    source_notes: Dict[str, Any] = Field(default_factory=dict)
