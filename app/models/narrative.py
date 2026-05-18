from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from app.models.event import EventLog


@dataclass
class ChapterBeat:
    """章节段落（beat）结构"""
    beat_id: str
    purpose: str
    event_ids: List[str]
    events: List[EventLog]


@dataclass
class ChapterPlan:
    """章节大纲（规则生成）"""
    chapter_title: str
    pov: str
    chapter_goal: str
    emotional_curve: List[str]
    beats: List[ChapterBeat]
    ending_hook_event_id: Optional[str]
