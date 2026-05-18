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
from app.genre_packs.horror.horror_consistency_checker import HorrorConsistencyChecker
from app.genre_packs.horror.horror_progression_controller import HorrorProgressionController
from app.genre_packs.horror.horror_quality_evaluator import HorrorQualityEvaluator


class HorrorGenrePack(GenrePack):
    def __init__(self, genre_id: str = "horror"):
        super().__init__(genre_id)
        self._profile: Optional[GenreProfile] = None
        self._progression_controller = HorrorProgressionController()
        self._quality_evaluator = HorrorQualityEvaluator(genre_id)
        self._consistency_checker = HorrorConsistencyChecker(genre_id)

    def load_profile(self) -> GenreProfile:
        if self._profile is None:
            profile_path = Path(__file__).parent / "horror_genre_profile.json"
            self._profile = GenreProfile.from_json(profile_path)
        return self._profile

    def build_genre_context(
        self,
        state: Any,
        chapter_plan: Dict[str, Any],
        novel_progress: Optional[Dict[str, Any]] = None,
    ) -> GenreContext:
        progress = novel_progress or {"current_progress_ratio": 0.3}
        progress_ratio = progress.get("current_progress_ratio", 0.3)

        horror_context = self._progression_controller.build_horror_context(
            progress_ratio=progress_ratio,
            previous_intensities=progress.get("previous_intensities"),
        )

        return GenreContext(
            genre_id=self.genre_id,
            genre_stage=horror_context["genre_stage"],
            genre_tension_level=horror_context["target_horror_intensity"],
            genre_progression_target={
                "target": horror_context["genre_stage"],
                "description": horror_context["atmosphere_goal"],
            },
            genre_constraints=self._build_constraints(horror_context),
            genre_allowed_devices=horror_context["allowed_devices"],
            genre_forbidden_devices=horror_context["forbidden_devices"],
        )

    def _build_constraints(self, horror_context: Dict[str, Any]) -> List[str]:
        stage = horror_context["genre_stage"]
        constraints = [
            "不能直接解释灵异规则的来源",
            "保持恐怖来源的未知感",
        ]

        if stage == "subtle_anomaly":
            constraints.append("只展示轻微异常，不出现鬼怪正面攻击")
        elif stage == "clear_threat":
            constraints.append("威胁显形，但保留未知性和神秘感")
        elif stage == "rule_discovery":
            constraints.append("可以揭示部分规则，但保留最终真相")
        elif stage == "truth_and_resolution":
            constraints.append("揭示核心真相，但避免机械解释所有细节")

        return constraints

    def get_progression_target(self, novel_progress: Dict[str, Any]) -> Dict[str, Any]:
        progress_ratio = novel_progress.get("current_progress_ratio", 0.3)
        horror_context = self._progression_controller.build_horror_context(progress_ratio)

        return {
            "target": horror_context["genre_stage"],
            "description": horror_context["atmosphere_goal"],
            "target_intensity": horror_context["target_horror_intensity"],
            "intensity_range": horror_context["intensity_range"],
        }

    def evaluate_genre_quality(
        self,
        quality_context: Dict[str, Any],
        chapter_draft: str,
        selected_events: List[Any],
    ) -> GenreQualityResult:
        return self._quality_evaluator.evaluate(
            chapter_draft=chapter_draft,
            chapter_plan=quality_context.get("chapter_plan", {}),
            selected_events=selected_events,
            genre_context=quality_context.get("genre_context", {}),
            base_quality_result=quality_context.get("base_quality_result", {}),
        )

    def validate_genre_rules(
        self,
        validation_input: Dict[str, Any],
    ) -> GenreValidationResult:
        return self._consistency_checker.check_consistency(
            chapter_draft=validation_input.get("chapter_draft", ""),
            chapter_plan=validation_input.get("chapter_plan", {}),
            selected_events=validation_input.get("selected_events", []),
            genre_context=validation_input.get("genre_context", {}),
        )

    def adapt_prompt_context(self, base_prompt_context: Dict[str, Any]) -> Dict[str, Any]:
        genre_context = base_prompt_context.get("genre_context", {})
        stage = genre_context.get("genre_stage", "subtle_anomaly")
        allowed_devices = genre_context.get("genre_allowed_devices", [])
        forbidden_devices = genre_context.get("genre_forbidden_devices", [])

        horror_prompt_instructions = [
            f"当前恐怖阶段: {stage}",
            f"目标恐怖强度: {genre_context.get('genre_tension_level', 5)}",
            f"允许的恐怖手法: {', '.join(allowed_devices)}",
            f"禁止的恐怖手法: {', '.join(forbidden_devices)}",
            "保持心理恐怖为主，避免直接的血腥描写",
            "重点营造环境氛围和角色的心理压力",
            "不直接解释灵异现象，让读者自己体会",
        ]

        adapted_context = base_prompt_context.copy()
        adapted_context["horror_instructions"] = horror_prompt_instructions

        return adapted_context

    def get_horror_progression_controller(self) -> HorrorProgressionController:
        return self._progression_controller
