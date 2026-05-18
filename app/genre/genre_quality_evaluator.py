from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List

from app.genre.genre_pack import GenreQualityResult


class BaseGenreQualityEvaluator(ABC):
    genre_id: str

    def __init__(self, genre_id: str):
        self.genre_id = genre_id

    @abstractmethod
    def evaluate(
        self,
        chapter_draft: str,
        chapter_plan: Dict[str, Any],
        selected_events: List[Any],
        genre_context: Dict[str, Any],
        base_quality_result: Dict[str, Any],
    ) -> GenreQualityResult:
        pass

    def _check_forbidden_patterns(
        self,
        draft: str,
        forbidden_patterns: List[str],
    ) -> List[Dict[str, Any]]:
        problems = []
        for pattern in forbidden_patterns:
            if pattern in draft:
                problems.append({
                    "type": "forbidden_pattern_detected",
                    "message": f"检测到禁用模式: {pattern}",
                    "severity": "medium",
                    "pattern": pattern,
                })
        return problems
