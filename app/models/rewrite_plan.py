from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, Field


class RewriteProblem(BaseModel):
    type: str = "style_issue"
    location: str = "chapter"
    evidence: str = ""
    rewrite_instruction: str = ""


class RewritePlan(BaseModel):
    version: str = "正式版V1.3"
    overall_goal: str = "增强小说质感，减少事件复述，不新增事实。"
    problems: List[RewriteProblem] = Field(default_factory=list)
    rewrite_plan: List[str] = Field(default_factory=list)
    forbidden_changes: List[str] = Field(default_factory=lambda: [
        "不得新增地点。",
        "不得新增角色。",
        "不得新增线索、物件、规则或路线。",
        "不得确认 suspected_facts。",
        "不得新增关系变化。",
    ])
    source_notes: Dict[str, Any] = Field(default_factory=dict)


class StyleRewriteReport(BaseModel):
    version: str = "正式版V1.3"
    style_profile: str = "horror_suspense_default"
    input_draft_chars: int = 0
    output_draft_chars: int = 0
    rewrite_applied: bool = False
    rewrite_focus: List[str] = Field(default_factory=list)
    consistency_after_rewrite: Dict[str, Any] = Field(default_factory=dict)
    faithfulness_after_rewrite: Dict[str, Any] = Field(default_factory=dict)
    fallback_reason: str = ""
