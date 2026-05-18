from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List

from app.genre.genre_pack import GenreValidationResult


class BaseGenreConsistencyChecker(ABC):
    genre_id: str

    def __init__(self, genre_id: str):
        self.genre_id = genre_id

    @abstractmethod
    def check_consistency(
        self,
        chapter_draft: str,
        chapter_plan: Dict[str, Any],
        selected_events: List[Any],
        genre_context: Dict[str, Any],
    ) -> GenreValidationResult:
        pass

    def _check_forbidden_devices(
        self,
        draft: str,
        forbidden_devices: List[str],
    ) -> List[Dict[str, Any]]:
        violations = []
        for device in forbidden_devices:
            if device in draft:
                violations.append({
                    "type": "forbidden_device_used",
                    "message": f"使用了当前阶段禁止的恐怖设备: {device}",
                    "severity": "medium",
                    "device": device,
                })
        return violations
