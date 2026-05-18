from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.genre.genre_profile import GenreProfile


@dataclass
class GenreContext:
    genre_id: str
    genre_stage: str = ""
    genre_tension_level: int = 0
    genre_progression_target: Dict[str, Any] = field(default_factory=dict)
    genre_constraints: List[str] = field(default_factory=list)
    genre_allowed_devices: List[str] = field(default_factory=list)
    genre_forbidden_devices: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "genre_id": self.genre_id,
            "genre_stage": self.genre_stage,
            "genre_tension_level": self.genre_tension_level,
            "genre_progression_target": self.genre_progression_target,
            "genre_constraints": self.genre_constraints,
            "genre_allowed_devices": self.genre_allowed_devices,
            "genre_forbidden_devices": self.genre_forbidden_devices,
        }


@dataclass
class GenreQualityResult:
    genre_scores: Dict[str, int] = field(default_factory=dict)
    genre_problems: List[Dict[str, Any]] = field(default_factory=list)
    genre_suggestions: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "genre_scores": self.genre_scores,
            "genre_problems": self.genre_problems,
            "genre_suggestions": self.genre_suggestions,
        }


@dataclass
class GenreValidationResult:
    passed: bool = True
    violations: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "violations": self.violations,
            "warnings": self.warnings,
        }


class GenrePack(ABC):
    genre_id: str

    def __init__(self, genre_id: str):
        self.genre_id = genre_id

    @abstractmethod
    def load_profile(self) -> GenreProfile:
        pass

    @abstractmethod
    def build_genre_context(
        self,
        state: Any,
        chapter_plan: Dict[str, Any],
        novel_progress: Optional[Dict[str, Any]] = None,
    ) -> GenreContext:
        pass

    @abstractmethod
    def get_progression_target(self, novel_progress: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @abstractmethod
    def evaluate_genre_quality(
        self,
        quality_context: Dict[str, Any],
        chapter_draft: str,
        selected_events: List[Any],
    ) -> GenreQualityResult:
        pass

    @abstractmethod
    def validate_genre_rules(
        self,
        validation_input: Dict[str, Any],
    ) -> GenreValidationResult:
        pass

    def adapt_prompt_context(self, base_prompt_context: Dict[str, Any]) -> Dict[str, Any]:
        return base_prompt_context
