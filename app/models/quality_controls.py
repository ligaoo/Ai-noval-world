from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field


class QualityControls(BaseModel):
    style_focus: List[str] = Field(default_factory=list)
    generation_strength: str = "平衡"
    ending_hook_type: str = "线索钩子"
    rewrite_policy: str = "auto_once"


class RewriteRequest(BaseModel):
    rewrite_intent: str
    preserve_facts: bool = True
    preserve_scene_plan: bool = True
