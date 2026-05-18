from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.models.event import EventLog


@dataclass
class PreAnalysisResult:
    """规则预分析结果"""
    plot_event_count: int = 0
    discovery_event_count: int = 0
    conflict_event_count: int = 0
    dialogue_event_count: int = 0
    relationship_change_event_count: int = 0
    new_open_thread_count: int = 0
    thread_progress_count: int = 0
    resolved_thread_count: int = 0
    selected_event_types: Dict[str, int] = field(default_factory=dict)
    possible_flags: List[str] = field(default_factory=list)
    word_count: int = 0
    paragraph_count: int = 0
    avg_paragraph_length: float = 0.0


class QualityPreAnalyzer:
    """
    V5.1 质量预分析器
    基于规则的快速分析，为 LLM 评估提供上下文，降低成本
    """

    DISCOVERY_EVENT_TYPES = {"discovery", "soft_hint", "hard_hint", "clue_found"}
    CONFLICT_EVENT_TYPES = {"conflict", "tension", "confrontation", "argument"}
    DIALOGUE_EVENT_TYPES = {"ask", "talk", "say", "discuss", "argue"}
    RELATIONSHIP_EVENT_TYPES = {"relationship_change", "trust_change", "alliance"}

    def analyze(
        self,
        selected_events: List[EventLog],
        chapter_draft: str,
        open_threads: Optional[List[Dict[str, Any]]] = None,
        chapter_plan: Optional[Dict[str, Any]] = None,
    ) -> PreAnalysisResult:
        """执行预分析"""
        result = PreAnalysisResult()

        self._analyze_events(result, selected_events)
        self._analyze_draft(result, chapter_draft)
        self._analyze_threads(result, open_threads, selected_events)
        self._generate_flags(result, chapter_plan)

        return result

    def _analyze_events(self, result: PreAnalysisResult, events: List[EventLog]) -> None:
        """分析事件统计"""
        result.plot_event_count = len(events)

        event_type_counts: Dict[str, int] = {}
        for event in events:
            action_type = event.action.action_type if event.action else None
            event_type = event.event_type

            if event_type in self.DISCOVERY_EVENT_TYPES or (action_type and "search" in action_type):
                result.discovery_event_count += 1

            if event_type in self.CONFLICT_EVENT_TYPES:
                result.conflict_event_count += 1

            if action_type in self.DIALOGUE_EVENT_TYPES:
                result.dialogue_event_count += 1

            if event_type in self.RELATIONSHIP_EVENT_TYPES:
                result.relationship_change_event_count += 1

            if action_type:
                event_type_counts[action_type] = event_type_counts.get(action_type, 0) + 1
            elif event_type:
                event_type_counts[event_type] = event_type_counts.get(event_type, 0) + 1

        result.selected_event_types = event_type_counts

    def _analyze_draft(self, result: PreAnalysisResult, draft: str) -> None:
        """分析正文统计"""
        result.word_count = len(draft)

        paragraphs = [p.strip() for p in draft.split("\n\n") if p.strip()]
        result.paragraph_count = len(paragraphs)

        if paragraphs:
            total_length = sum(len(p) for p in paragraphs)
            result.avg_paragraph_length = total_length / len(paragraphs)

    def _analyze_threads(
        self,
        result: PreAnalysisResult,
        open_threads: Optional[List[Dict[str, Any]]],
        events: List[EventLog],
    ) -> None:
        """分析悬念线程"""
        if not open_threads:
            return

        thread_ids = {t.get("thread_id") for t in open_threads if t.get("thread_id")}

        new_threads = [
            t for t in open_threads
            if t.get("opened_at_event") and t.get("opened_at_event") in {e.event_id for e in events}
        ]
        result.new_open_thread_count = len(new_threads)

        progressed_threads = [
            t for t in open_threads
            if t.get("last_progress_chapter") and t.get("last_progress_chapter") > 0
        ]
        result.thread_progress_count = len(progressed_threads)

        resolved_threads = [
            t for t in open_threads
            if t.get("status") == "resolved"
        ]
        result.resolved_thread_count = len(resolved_threads)

    def _generate_flags(
        self,
        result: PreAnalysisResult,
        chapter_plan: Optional[Dict[str, Any]] = None,
    ) -> None:
        """生成问题标志"""
        flags = []

        if result.conflict_event_count == 0:
            flags.append("low_conflict")

        search_count = result.selected_event_types.get("search", 0)
        inspect_count = result.selected_event_types.get("inspect", 0)
        if search_count + inspect_count >= 4 and result.conflict_event_count == 0:
            flags.append("repetitive_search_events")

        if result.discovery_event_count == 0 and result.thread_progress_count == 0:
            flags.append("low_plot_progress")

        if result.new_open_thread_count > 2:
            flags.append("too_many_threads_opened")

        if result.thread_progress_count == 0 and result.resolved_thread_count == 0:
            flags.append("no_thread_progress")

        if chapter_plan:
            ending_hook = chapter_plan.get("ending_hook") if isinstance(chapter_plan, dict) else getattr(chapter_plan, "ending_hook", None)
            if not ending_hook or len(str(ending_hook).strip()) < 10:
                flags.append("weak_hook")

        if result.paragraph_count > 0 and result.avg_paragraph_length > 300:
            flags.append("long_paragraphs")

        result.possible_flags = flags

    def to_dict(self, result: PreAnalysisResult) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "plot_event_count": result.plot_event_count,
            "discovery_event_count": result.discovery_event_count,
            "conflict_event_count": result.conflict_event_count,
            "dialogue_event_count": result.dialogue_event_count,
            "relationship_change_event_count": result.relationship_change_event_count,
            "new_open_thread_count": result.new_open_thread_count,
            "thread_progress_count": result.thread_progress_count,
            "resolved_thread_count": result.resolved_thread_count,
            "selected_event_types": result.selected_event_types,
            "possible_flags": result.possible_flags,
            "word_count": result.word_count,
            "paragraph_count": result.paragraph_count,
            "avg_paragraph_length": round(result.avg_paragraph_length, 1),
        }
