from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from app.genre import (
    GenreContext,
    GenrePack,
    GenreProfile,
    GenreQualityResult,
    GenreValidationResult,
)


class GenericGenrePack(GenrePack):
    def __init__(self, genre_id: str = "generic"):
        super().__init__(genre_id)
        self._profile: Optional[GenreProfile] = None

    def load_profile(self) -> GenreProfile:
        if self._profile is None:
            profile_path = Path(__file__).parent / "generic_genre_profile.json"
            self._profile = GenreProfile.from_json(profile_path)
        return self._profile

    def build_genre_context(
        self,
        state: Any,
        chapter_plan: Dict[str, Any],
        novel_progress: Optional[Dict[str, Any]] = None,
    ) -> GenreContext:
        progress = novel_progress or {"current_progress_ratio": 0.5}
        ratio = progress.get("current_progress_ratio", 0.5)

        if ratio < 0.2:
            stage = "setup"
        elif ratio < 0.5:
            stage = "development"
        elif ratio < 0.8:
            stage = "crisis"
        elif ratio < 0.95:
            stage = "climax"
        else:
            stage = "resolution"

        return GenreContext(
            genre_id=self.genre_id,
            genre_stage=stage,
            genre_tension_level=int(ratio * 10),
            genre_progression_target=self.get_progression_target(progress),
            genre_constraints=[
                "保持故事逻辑连贯",
                "人物行为符合性格设定",
            ],
        )

    def get_progression_target(self, novel_progress: Dict[str, Any]) -> Dict[str, Any]:
        ratio = novel_progress.get("current_progress_ratio", 0.5)

        if ratio < 0.2:
            return {
                "target": "setup",
                "description": "建立背景、角色和核心冲突",
            }
        elif ratio < 0.5:
            return {
                "target": "development",
                "description": "发展情节，增加复杂性和张力",
            }
        elif ratio < 0.8:
            return {
                "target": "crisis",
                "description": "危机升级，增加赌注",
            }
        elif ratio < 0.95:
            return {
                "target": "climax",
                "description": "最终对决，高潮迭起",
            }
        else:
            return {
                "target": "resolution",
                "description": "收束线索，给出合理解答",
            }

    def evaluate_genre_quality(
        self,
        quality_context: Dict[str, Any],
        chapter_draft: str,
        selected_events: List[Any],
    ) -> GenreQualityResult:
        profile = self.load_profile()

        genre_scores = {}
        for dim in profile.genre_dimensions:
            genre_scores[dim] = 7

        genre_problems = []
        genre_suggestions = []

        return GenreQualityResult(
            genre_scores=genre_scores,
            genre_problems=genre_problems,
            genre_suggestions=genre_suggestions,
        )

    def validate_genre_rules(
        self,
        validation_input: Dict[str, Any],
    ) -> GenreValidationResult:
        chapter_draft = validation_input.get("chapter_draft", "")
        genre_context = validation_input.get("genre_context", {})

        violations = []
        warnings = []

        profile = self.load_profile()
        forbidden = self._check_forbidden_patterns(chapter_draft, profile.forbidden_patterns)
        violations.extend(forbidden)

        return GenreValidationResult(
            passed=len([v for v in violations if v.get("severity") == "error"]) == 0,
            violations=violations,
            warnings=warnings,
        )

    def _check_forbidden_patterns(
        self,
        draft: str,
        forbidden_patterns: List[str],
    ) -> List[Dict[str, Any]]:
        violations = []
        for pattern in forbidden_patterns:
            if pattern in draft:
                violations.append({
                    "type": "forbidden_pattern",
                    "message": f"检测到禁用模式: {pattern}",
                    "severity": "warning",
                })
        return violations
