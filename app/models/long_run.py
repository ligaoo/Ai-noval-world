from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class LongRunTestConfig:
    test_id: str
    world_id: str
    seed: int = 42
    chapter_limit: int = 10
    tick_limit_per_chapter: int = 50
    enabled_checks: List[str] = field(default_factory=list)
    thresholds: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.enabled_checks:
            self.enabled_checks = [
                "main_arc_continuity",
                "character_state_consistency",
                "open_thread_growth",
                "npc_growth",
                "world_state_conflict",
                "style_drift",
                "quality_trend",
                "consistency_pass_rate",
            ]

        if not self.thresholds:
            self.thresholds = {
                "average_quality_score_min": 7.0,
                "consistency_pass_rate_min": 0.95,
                "npc_growth_max_per_chapter": 1.2,
                "open_thread_max": 10,
                "style_drift_max": 0.25,
                "resolved_thread_reopened_max": 1,
            }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_id": self.test_id,
            "world_id": self.world_id,
            "seed": self.seed,
            "chapter_limit": self.chapter_limit,
            "tick_limit_per_chapter": self.tick_limit_per_chapter,
            "enabled_checks": self.enabled_checks,
            "thresholds": self.thresholds,
        }


@dataclass
class ChapterMetrics:
    chapter_no: int
    quality_score: float = 0.0
    consistency_passed: bool = True
    npc_count: int = 0
    open_thread_count: int = 0
    resolved_thread_count: int = 0
    style_drift_score: float = 0.0
    events_generated: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chapter_no": self.chapter_no,
            "quality_score": self.quality_score,
            "consistency_passed": self.consistency_passed,
            "npc_count": self.npc_count,
            "open_thread_count": self.open_thread_count,
            "resolved_thread_count": self.resolved_thread_count,
            "style_drift_score": self.style_drift_score,
            "events_generated": self.events_generated,
        }


@dataclass
class LongRunReport:
    test_id: str
    world_id: str
    seed: int
    chapters_generated: int
    passed: bool = False
    summary: Dict[str, Any] = field(default_factory=dict)
    growth_metrics: Dict[str, Any] = field(default_factory=dict)
    chapter_metrics: List[ChapterMetrics] = field(default_factory=list)
    issues: List[Dict[str, Any]] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_id": self.test_id,
            "world_id": self.world_id,
            "seed": self.seed,
            "chapters_generated": self.chapters_generated,
            "passed": self.passed,
            "summary": self.summary,
            "growth_metrics": self.growth_metrics,
            "chapter_metrics": [m.to_dict() for m in self.chapter_metrics],
            "issues": self.issues,
            "recommendations": self.recommendations,
        }
