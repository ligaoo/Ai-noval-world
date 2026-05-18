from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class CharacterChange(BaseModel):
    """人物状态变化"""
    mental_state: str
    goal_updated: str
    new_beliefs: List[str] = []


class ChapterSummary(BaseModel):
    """章节摘要（用于章节间继承）"""
    chapter_id: str
    chapter_title: str
    summary: str
    tick_count: int
    event_count: int

    # 发现与认知
    new_facts: List[str]
    new_beliefs: Dict[str, List[str]]  # char_id -> beliefs

    # 悬念线程
    open_threads: List[str]
    resolved_threads: List[str]

    # 人物变化
    character_changes: Dict[str, CharacterChange]

    # 下一章种子
    next_chapter_seeds: List[str]

    # 状态快照
    final_character_states: Dict[str, Any] = {}
    discovered_clues: List[str] = []


class ChapterContext(BaseModel):
    """下一章注入的上下文"""
    chapter_number: int
    previous_chapter_summary: str
    open_threads: List[str]
    next_chapter_seeds: List[str]
    inherited_facts: List[str]
    inherited_beliefs: Dict[str, List[str]]

    # 导演压力（soft）
    soft_director_pressure: List[str] = []
