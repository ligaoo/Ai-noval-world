from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class AllowedReveal(BaseModel):
    fact: str = ""
    level: str = "surface"
    source: str = ""


class SuspectedOnly(BaseModel):
    fact: str = ""
    reason: str = "只能作为怀疑、异常感或未确认线索处理。"


class ForbiddenReveal(BaseModel):
    fact: str = ""
    until_chapter: Optional[int] = None


class PayoffTarget(BaseModel):
    thread_id: str = ""
    expected_payoff_chapter: int = 3


class RevealBudget(BaseModel):
    version: str = "正式版V1.4"
    chapter_no: int = 1
    allowed_reveals: List[AllowedReveal] = Field(default_factory=list)
    suspected_only: List[SuspectedOnly] = Field(default_factory=list)
    forbidden_reveals: List[ForbiddenReveal] = Field(default_factory=list)
    required_questions: List[str] = Field(default_factory=list)
    payoff_targets: List[PayoffTarget] = Field(default_factory=list)
