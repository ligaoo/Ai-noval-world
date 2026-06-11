from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, Field


class RelationshipFocus(BaseModel):
    source: str = ""
    target: str = ""
    expected_shift: str = ""


class RevealPolicy(BaseModel):
    allowed_facts: List[str] = Field(default_factory=list)
    suspected_facts: List[str] = Field(default_factory=list)
    forbidden_facts: List[str] = Field(default_factory=list)


class EndingHookPolicy(BaseModel):
    type: str = "sensory_or_clue_hook"
    requirement: str = "以一个具体感官异常或线索缺口结束，不总结。"


class LocationPolicy(BaseModel):
    allowed_location_ids: List[str] = Field(default_factory=list)
    preferred_location_ids: List[str] = Field(default_factory=list)
    forbidden_location_ids: List[str] = Field(default_factory=list)
    forbidden_location_names: List[str] = Field(default_factory=list)
    boundary_notes: List[str] = Field(default_factory=list)


class ChapterBrief(BaseModel):
    version: str = "正式版V1.1"
    chapter_no: int = 1
    target_chapters: int = 10
    chapter_title_hint: str = ""
    main_question: str = ""
    chapter_goal: str = ""
    tone: str = ""
    must_advance_threads: List[str] = Field(default_factory=list)
    must_include_clues: List[str] = Field(default_factory=list)
    relationship_focus: List[RelationshipFocus] = Field(default_factory=list)
    reveal_policy: RevealPolicy = Field(default_factory=RevealPolicy)
    ending_hook: EndingHookPolicy = Field(default_factory=EndingHookPolicy)
    location_policy: LocationPolicy = Field(default_factory=LocationPolicy)
    source_notes: Dict[str, Any] = Field(default_factory=dict)
