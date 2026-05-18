from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class RewriteMode(str, Enum):
    SECTION_REWRITE = "section_rewrite"
    FULL_CHAPTER_REWRITE = "full_chapter_rewrite"


class RewriteTaskType(str, Enum):
    TIGHTEN_PACING = "tighten_pacing"
    INCREASE_CONFLICT = "increase_conflict"
    DEEPEN_CHARACTER = "deepen_character"
    IMPROVE_HOOK = "improve_hook"
    POLISH_STYLE = "polish_style"
    REDUCE_EXPOSITION = "reduce_exposition"
    IMPROVE_DIALOGUE = "improve_dialogue"
    ENHANCE_SUSPENSE = "enhance_suspense"
    ENHANCE_HORROR_ATMOSPHERE = "enhance_horror_atmosphere"
    RESTORE_GENRE_CONSTRAINTS = "restore_genre_constraints"
    RESTORE_CHARACTER_VOICE = "restore_character_voice"


@dataclass
class RewriteConstraint:
    """修稿约束"""
    cannot_add_new_facts: bool = True
    cannot_change_event_outcome: bool = True
    cannot_add_new_characters: bool = True
    cannot_add_new_locations: bool = True
    cannot_add_new_clues: bool = True
    cannot_spoil_forbidden_revelations: bool = True
    pov_boundary: Optional[str] = None
    genre_constraints: List[str] = field(default_factory=list)


@dataclass
class RewriteGoal:
    """修稿目标"""
    task_id: str
    type: RewriteTaskType
    priority: int = 5
    reason: str = ""
    target_sections: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)


@dataclass
class RewritePlan:
    """修稿计划"""
    rewrite_plan_id: str
    simulation_id: str
    chapter_id: str
    source_quality_report_id: str
    rewrite_mode: RewriteMode = RewriteMode.SECTION_REWRITE
    rewrite_goals: List[RewriteGoal] = field(default_factory=list)
    global_constraints: List[str] = field(default_factory=list)
    max_rewrite_attempts: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rewrite_plan_id": self.rewrite_plan_id,
            "simulation_id": self.simulation_id,
            "chapter_id": self.chapter_id,
            "source_quality_report_id": self.source_quality_report_id,
            "rewrite_mode": self.rewrite_mode.value,
            "rewrite_goals": [
                {
                    "task_id": g.task_id,
                    "type": g.type.value,
                    "priority": g.priority,
                    "reason": g.reason,
                    "target_sections": g.target_sections,
                    "constraints": g.constraints,
                }
                for g in self.rewrite_goals
            ],
            "global_constraints": self.global_constraints,
            "max_rewrite_attempts": self.max_rewrite_attempts,
        }


@dataclass
class ChangedSection:
    """变更的段落"""
    section_id: str
    change_type: str
    summary: str
    before_content: Optional[str] = None
    after_content: Optional[str] = None


@dataclass
class RewriteResult:
    """修稿结果"""
    rewrite_result_id: str
    rewrite_plan_id: str
    chapter_id: str
    status: str = "success"
    rewritten_draft_file: str = ""
    changed_sections: List[ChangedSection] = field(default_factory=list)
    consistency_check: Dict[str, Any] = field(default_factory=dict)
    quality_before: float = 0.0
    quality_after: float = 0.0
    accepted: bool = False
    accept_reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rewrite_result_id": self.rewrite_result_id,
            "rewrite_plan_id": self.rewrite_plan_id,
            "chapter_id": self.chapter_id,
            "status": self.status,
            "rewritten_draft_file": self.rewritten_draft_file,
            "changed_sections": [
                {
                    "section_id": s.section_id,
                    "change_type": s.change_type,
                    "summary": s.summary,
                }
                for s in self.changed_sections
            ],
            "consistency_check": self.consistency_check,
            "quality_before": self.quality_before,
            "quality_after": self.quality_after,
            "accepted": self.accepted,
            "accept_reason": self.accept_reason,
        }


@dataclass
class RewriteAcceptancePolicy:
    """修稿接受策略"""
    auto_accept_enabled: bool = True
    require_consistency_passed: bool = True
    require_genre_consistency_passed: bool = True
    min_quality_improvement: float = 0.4
    reject_if_new_fact_detected: bool = True
    reject_if_forbidden_revelation_detected: bool = True
    fallback_to_original_if_failed: bool = True
