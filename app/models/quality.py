from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ProblemType(str, Enum):
    WEAK_CONFLICT = "weak_conflict"
    SLOW_MIDDLE = "slow_middle"
    WEAK_HOOK = "weak_hook"
    FLAT_EMOTIONAL_CURVE = "flat_emotional_curve"
    LOW_PLOT_PROGRESS = "low_plot_progress"
    THIN_CHARACTER_MOTIVATION = "thin_character_motivation"
    DIALOGUE_TOO_EXPOSITORY = "dialogue_too_expository"
    STYLE_DRIFT = "style_drift"
    VOICE_DRIFT = "voice_drift"
    OVER_EXPLANATION = "over_explanation"
    SCENE_REPETITION = "scene_repetition"
    SUSPENSE_WITHOUT_PAYOFF = "suspense_without_payoff"
    TOO_MANY_THREADS_OPENED = "too_many_threads_opened"
    NO_THREAD_PROGRESS = "no_thread_progress"
    PAYOFF_TOO_ABRUPT = "payoff_too_abrupt"


class Severity(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RewriteTaskType(str, Enum):
    TIGHTEN_PACING = "tighten_pacing"
    INCREASE_CONFLICT = "increase_conflict"
    DEEPEN_CHARACTER = "deepen_character"
    IMPROVE_HOOK = "improve_hook"
    POLISH_STYLE = "polish_style"
    REDUCE_EXPOSITION = "reduce_exposition"
    IMPROVE_DIALOGUE = "improve_dialogue"
    ENHANCE_SUSPENSE = "enhance_suspense"
    IMPROVE_SCENE_TRANSITION = "improve_scene_transition"
    STRENGTHEN_PAYOFF = "strengthen_payoff"


@dataclass
class QualityDimension:
    plot_progress: int = 7
    conflict_strength: int = 7
    character_depth: int = 7
    emotional_curve: int = 7
    suspense: int = 7
    pacing: int = 7
    scene_vividness: int = 7
    dialogue_quality: int = 7
    style_consistency: int = 7
    chapter_hook: int = 7
    payoff_quality: int = 7
    readability: int = 7


@dataclass
class QualityThreshold:
    overall_min: float = 7.0
    conflict_strength_min: int = 6
    pacing_min: int = 6
    style_consistency_min: int = 7


@dataclass
class Location:
    section_id: Optional[str] = None
    paragraph_range: Optional[List[int]] = None


@dataclass
class QualityProblem:
    problem_id: str
    type: ProblemType
    severity: Severity
    message: str
    location: Optional[Location] = None
    evidence: List[str] = field(default_factory=list)


@dataclass
class QualityStrength:
    type: str
    message: str


@dataclass
class RewriteSuggestion:
    suggestion_id: str
    type: RewriteTaskType
    message: str
    target_sections: List[str] = field(default_factory=list)


@dataclass
class QualityReport:
    report_id: str
    simulation_id: str
    chapter_id: str
    chapter_no: int
    evaluated_target: str
    overall_score: float
    grade: str
    scores: QualityDimension
    thresholds: QualityThreshold
    problems: List[QualityProblem] = field(default_factory=list)
    strengths: List[QualityStrength] = field(default_factory=list)
    suggestions: List[RewriteSuggestion] = field(default_factory=list)
    rewrite_recommended: bool = False
    event_analysis: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "simulation_id": self.simulation_id,
            "chapter_id": self.chapter_id,
            "chapter_no": self.chapter_no,
            "evaluated_target": self.evaluated_target,
            "overall_score": self.overall_score,
            "grade": self.grade,
            "scores": self.scores.__dict__,
            "thresholds": self.thresholds.__dict__,
            "problems": [
                {
                    "problem_id": p.problem_id,
                    "type": p.type.value if isinstance(p.type, Enum) else p.type,
                    "severity": p.severity.value if isinstance(p.severity, Enum) else p.severity,
                    "message": p.message,
                    "location": p.location.__dict__ if p.location else None,
                    "evidence": p.evidence,
                }
                for p in self.problems
            ],
            "strengths": [s.__dict__ for s in self.strengths],
            "suggestions": [
                {
                    "suggestion_id": s.suggestion_id,
                    "type": s.type.value if isinstance(s.type, Enum) else s.type,
                    "message": s.message,
                    "target_sections": s.target_sections,
                }
                for s in self.suggestions
            ],
            "rewrite_recommended": self.rewrite_recommended,
            "event_analysis": self.event_analysis,
        }
