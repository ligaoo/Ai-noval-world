from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class LongRunTestConfig:
    """长篇稳定性测试配置"""
    test_id: str
    project_id: str
    target_words: int = 100000
    target_chapters: int = 30
    genre_id: str = "horror"
    sub_genre: str = "suspense_supernatural"
    seed: int = 12345
    thresholds: Dict[str, Any] = field(default_factory=lambda: {
        "average_quality_score_min": 7.0,
        "consistency_pass_rate_min": 0.95,
        "thread_resolution_rate_min": 0.7,
        "main_thread_resolution_required": True,
        "style_drift_max": 0.25,
        "npc_growth_max_per_chapter": 1.0,
        "final_closure_required": True,
    })


@dataclass
class LongRunReport:
    """长篇测试报告"""
    test_id: str
    chapters_generated: int = 0
    total_words: int = 0
    average_quality_score: float = 0.0
    consistency_pass_rate: float = 0.0
    genre_consistency_pass_rate: float = 0.0
    thread_resolution_rate: float = 0.0
    main_arc_closed: bool = False
    truth_chain_closed: bool = False
    style_drift_score: float = 0.0
    npc_growth_rate_per_chapter: float = 0.0
    final_status: str = "running"  # running / passed / failed
    major_issues: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_id": self.test_id,
            "chapters_generated": self.chapters_generated,
            "total_words": self.total_words,
            "average_quality_score": self.average_quality_score,
            "consistency_pass_rate": self.consistency_pass_rate,
            "genre_consistency_pass_rate": self.genre_consistency_pass_rate,
            "thread_resolution_rate": self.thread_resolution_rate,
            "main_arc_closed": self.main_arc_closed,
            "truth_chain_closed": self.truth_chain_closed,
            "style_drift_score": self.style_drift_score,
            "npc_growth_rate_per_chapter": self.npc_growth_rate_per_chapter,
            "final_status": self.final_status,
            "major_issues": self.major_issues,
        }


@dataclass
class ClosureCheckItem:
    """收束检查项"""
    name: str
    passed: bool
    message: str = ""


@dataclass
class FinalClosureReport:
    """终局收束报告"""
    closure_report_id: str
    novel_id: str
    passed: bool = False
    checks: Dict[str, bool] = field(default_factory=dict)
    unresolved_items: List[Dict[str, Any]] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "closure_report_id": self.closure_report_id,
            "novel_id": self.novel_id,
            "passed": self.passed,
            "checks": self.checks,
            "unresolved_items": self.unresolved_items,
            "recommendations": self.recommendations,
        }


@dataclass
class FullNovelConsistencyReport:
    """全书一致性报告"""
    novel_id: str
    checks_passed: bool = True
    issues: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "novel_id": self.novel_id,
            "checks_passed": self.checks_passed,
            "issues": self.issues,
        }
