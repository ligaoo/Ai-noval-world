from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ActPlan:
    """幕计划"""
    act_id: str
    name: str
    chapter_range: List[int]  # [start, end]
    word_range: List[int]  # [start_words, end_words]
    function: str
    plot_arc_stage: str = ""
    genre_stage: str = ""
    goals: List[str] = field(default_factory=list)
    must_not_reveal: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "act_id": self.act_id,
            "name": self.name,
            "chapter_range": self.chapter_range,
            "word_range": self.word_range,
            "function": self.function,
            "plot_arc_stage": self.plot_arc_stage,
            "genre_stage": self.genre_stage,
            "goals": self.goals,
            "must_not_reveal": self.must_not_reveal,
        }


@dataclass
class NovelBlueprint:
    """
    全书蓝图
    定义小说的整体结构、目标和约束
    """
    novel_id: str
    title: str
    target_words: int = 100000
    target_chapters: int = 30
    genre_id: str = "horror"
    sub_genre: str = "suspense_supernatural"
    theme: str = ""
    acts: List[ActPlan] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "novel_id": self.novel_id,
            "title": self.title,
            "target_words": self.target_words,
            "target_chapters": self.target_chapters,
            "genre_id": self.genre_id,
            "sub_genre": self.sub_genre,
            "theme": self.theme,
            "acts": [act.to_dict() for act in self.acts],
        }

    def get_act_for_chapter(self, chapter_no: int) -> Optional[ActPlan]:
        """获取指定章节所属的幕"""
        for act in self.acts:
            start, end = act.chapter_range
            if start <= chapter_no <= end:
                return act
        return None

    def get_act_for_word_count(self, word_count: int) -> Optional[ActPlan]:
        """获取指定字数所属的幕"""
        for act in self.acts:
            start, end = act.word_range
            if start <= word_count <= end:
                return act
        return None


@dataclass
class ChapterFunctionPlan:
    """
    章节功能计划
    每章必须有明确的章节功能
    """
    chapter_id: str
    chapter_no: int
    target_words: int = 3500
    act_id: str = ""
    chapter_function: str = ""
    primary_thread: str = ""
    secondary_threads: List[str] = field(default_factory=list)
    required_events: List[str] = field(default_factory=list)
    genre_context: Dict[str, Any] = field(default_factory=dict)
    must_not_reveal: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chapter_id": self.chapter_id,
            "chapter_no": self.chapter_no,
            "target_words": self.target_words,
            "act_id": self.act_id,
            "chapter_function": self.chapter_function,
            "primary_thread": self.primary_thread,
            "secondary_threads": self.secondary_threads,
            "required_events": self.required_events,
            "genre_context": self.genre_context,
            "must_not_reveal": self.must_not_reveal,
        }


@dataclass
class NovelProgress:
    """
    全书进度
    跟踪小说生产的当前状态
    """
    novel_id: str
    current_chapter: int = 0
    target_chapters: int = 30
    current_words: int = 0
    target_words: int = 100000
    current_act: str = ""
    progress_ratio: float = 0.0
    arc_progress: Dict[str, float] = field(default_factory=dict)
    thread_stats: Dict[str, int] = field(default_factory=dict)
    quality_stats: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"  # pending / running / paused / completed / failed

    def to_dict(self) -> Dict[str, Any]:
        return {
            "novel_id": self.novel_id,
            "current_chapter": self.current_chapter,
            "target_chapters": self.target_chapters,
            "current_words": self.current_words,
            "target_words": self.target_words,
            "current_act": self.current_act,
            "progress_ratio": self.progress_ratio,
            "arc_progress": self.arc_progress,
            "thread_stats": self.thread_stats,
            "quality_stats": self.quality_stats,
            "status": self.status,
        }


@dataclass
class ChapterWordBudget:
    """章节字数预算"""
    target_words: int = 3500
    min_words: int = 3000
    max_words: int = 4200
    current_draft_words: int = 0

    @property
    def status(self) -> str:
        if self.current_draft_words < self.min_words:
            return "too_short"
        elif self.current_draft_words > self.max_words:
            return "too_long"
        else:
            return "within_range"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_words": self.target_words,
            "min_words": self.min_words,
            "max_words": self.max_words,
            "current_draft_words": self.current_draft_words,
            "status": self.status,
        }
