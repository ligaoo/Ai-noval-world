from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class HorrorStage:
    stage_id: str
    chapter_ratio_range: List[float]
    horror_intensity_range: List[int]
    function: str
    allowed_devices: List[str]
    forbidden_devices: List[str]


class HorrorProgressionController:
    def __init__(self, progression_curve_path: Optional[Path] = None):
        if progression_curve_path is None:
            progression_curve_path = Path(__file__).parent / "horror_progression_curve.json"

        self.stages = self._load_progression_curve(progression_curve_path)

    def _load_progression_curve(self, curve_path: Path) -> List[HorrorStage]:
        stages = []
        if curve_path.exists():
            with open(curve_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for stage_data in data.get("progression_curve", []):
                    stages.append(HorrorStage(**stage_data))
        return stages

    def get_current_stage(self, progress_ratio: float) -> HorrorStage:
        for stage in self.stages:
            min_ratio, max_ratio = stage.chapter_ratio_range
            if min_ratio <= progress_ratio < max_ratio:
                return stage

        if progress_ratio >= 1.0 and self.stages:
            return self.stages[-1]

        return self.stages[0] if self.stages else self._get_default_stage()

    def _get_default_stage(self) -> HorrorStage:
        return HorrorStage(
            stage_id="subtle_anomaly",
            chapter_ratio_range=[0.0, 1.0],
            horror_intensity_range=[3, 5],
            function="制造轻微异常和不安",
            allowed_devices=["声音异常", "旧物位置变化", "温度异常"],
            forbidden_devices=["鬼怪正面攻击", "灵异规则解释"],
        )

    def calculate_target_intensity(
        self,
        progress_ratio: float,
        previous_intensities: Optional[List[int]] = None,
    ) -> int:
        stage = self.get_current_stage(progress_ratio)
        min_intensity, max_intensity = stage.horror_intensity_range

        base_intensity = min_intensity + (max_intensity - min_intensity) * progress_ratio

        if previous_intensities and len(previous_intensities) >= 2:
            recent_avg = sum(previous_intensities[-2:]) / 2
            smoothed_intensity = (base_intensity + recent_avg) / 2
        else:
            smoothed_intensity = base_intensity

        target_intensity = max(min_intensity, min(max_intensity, int(smoothed_intensity)))
        return target_intensity

    def get_allowed_devices(self, progress_ratio: float) -> List[str]:
        stage = self.get_current_stage(progress_ratio)
        return stage.allowed_devices

    def get_forbidden_devices(self, progress_ratio: float) -> List[str]:
        stage = self.get_current_stage(progress_ratio)
        return stage.forbidden_devices

    def get_stage_function(self, progress_ratio: float) -> str:
        stage = self.get_current_stage(progress_ratio)
        return stage.function

    def build_horror_context(
        self,
        progress_ratio: float,
        previous_intensities: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        stage = self.get_current_stage(progress_ratio)
        target_intensity = self.calculate_target_intensity(progress_ratio, previous_intensities)

        return {
            "genre_stage": stage.stage_id,
            "target_horror_intensity": target_intensity,
            "allowed_devices": stage.allowed_devices,
            "forbidden_devices": stage.forbidden_devices,
            "atmosphere_goal": stage.function,
            "intensity_range": stage.horror_intensity_range,
        }

    def validate_horror_event(
        self,
        event_type: str,
        progress_ratio: float,
    ) -> tuple[bool, str]:
        stage = self.get_current_stage(progress_ratio)

        if event_type in stage.forbidden_devices:
            return False, f"事件类型 '{event_type}' 在阶段 '{stage.stage_id}' 被禁止"

        if event_type not in stage.allowed_devices:
            return True, f"注意: 事件类型 '{event_type}' 未在允许列表中，但未明确禁止"

        return True, "允许"
