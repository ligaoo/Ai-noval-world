from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from app.genre import BaseGenreConsistencyChecker, GenreValidationResult


class HorrorConsistencyChecker(BaseGenreConsistencyChecker):
    def __init__(self, genre_id: str = "horror"):
        super().__init__(genre_id)
        self._load_progression_curve()

    def _load_progression_curve(self) -> None:
        curve_path = Path(__file__).parent / "horror_progression_curve.json"
        if curve_path.exists():
            with open(curve_path, "r", encoding="utf-8") as f:
                self.progression_curve = json.load(f).get("progression_curve", [])
        else:
            self.progression_curve = []

    def check_consistency(
        self,
        chapter_draft: str,
        chapter_plan: Dict[str, Any],
        selected_events: List[Any],
        genre_context: Dict[str, Any],
    ) -> GenreValidationResult:
        violations = []
        warnings = []

        stage_violations = self._check_genre_stage_consistency(chapter_draft, genre_context)
        violations.extend(stage_violations)

        device_violations = self._check_forbidden_devices(chapter_draft, genre_context)
        violations.extend(device_violations)

        rule_violations = self._check_supernatural_rules(chapter_draft, genre_context)
        violations.extend(rule_violations)

        intensity_warnings = self._check_intensity_progression(chapter_draft, genre_context)
        warnings.extend(intensity_warnings)

        # V1.1 新增：第一章特定检查
        chapter_no = chapter_plan.get("chapter_no", 1)
        if chapter_no == 1:
            chapter1_violations = self._check_chapter1_constraints(chapter_draft, chapter_plan)
            violations.extend(chapter1_violations)

        return GenreValidationResult(
            passed=len([v for v in violations if v.get("severity") == "error"]) == 0,
            violations=violations,
            warnings=warnings,
        )

    def _check_genre_stage_consistency(
        self,
        draft: str,
        genre_context: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        violations = []
        current_stage = genre_context.get("genre_stage", "subtle_anomaly")

        stage_explanation_restrictions = {
            "subtle_anomaly": ["真相", "原来", "规则", "所以"],
            "clear_threat": ["全部真相", "完整规则", "鬼怪来源"],
            "rule_discovery": ["最终真相", "完全解释"],
        }

        restricted_words = stage_explanation_restrictions.get(current_stage, [])
        for word in restricted_words:
            if word in draft:
                violations.append({
                    "type": "supernatural_rule_revealed_too_early",
                    "message": f"阶段 '{current_stage}' 不允许过早解释规则: '{word}'",
                    "severity": "error",
                    "stage": current_stage,
                })

        return violations

    def _check_forbidden_devices(
        self,
        draft: str,
        genre_context: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        violations = []
        forbidden_devices = genre_context.get("genre_forbidden_devices", [])

        for device in forbidden_devices:
            if device in draft:
                violations.append({
                    "type": "forbidden_horror_device_used",
                    "message": f"使用了当前阶段禁止的恐怖手法: '{device}'",
                    "severity": "error",
                    "device": device,
                })

        return violations

    def _check_supernatural_rules(
        self,
        draft: str,
        genre_context: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        violations = []

        boundary_violation_patterns = [
            "鬼怪被打败", "消灭了鬼怪", "杀死了鬼怪",
            "一拳打", "一脚踢", "拔刀", "开枪",
        ]

        for pattern in boundary_violation_patterns:
            if pattern in draft:
                violations.append({
                    "type": "ghost_power_boundary_violation",
                    "message": f"鬼怪能力边界被打破: '{pattern}'，心理恐怖不应有直接战斗",
                    "severity": "error",
                })

        explanation_patterns = [
            "这是因为", "原因就是", "科学解释",
            "其实就是", "只不过是",
        ]

        explanation_count = sum(1 for p in explanation_patterns if p in draft)
        if explanation_count >= 3:
            violations.append({
                "type": "over_explanation_of_horror",
                "message": "恐怖元素被过度解释，削弱了未知感",
                "severity": "warning",
            })

        return violations

    def _check_intensity_progression(
        self,
        draft: str,
        genre_context: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        warnings = []
        target_level = genre_context.get("genre_tension_level", 5)

        strong_horror_words = ["崩溃", "尖叫", "惨死", "鲜血", "恐怖"]
        current_intensity = sum(1 for w in strong_horror_words if w in draft)

        if current_intensity > target_level + 2:
            warnings.append({
                "type": "horror_intensity_jump",
                "message": f"恐怖强度跳跃过大，当前{current_intensity}，目标{target_level}",
            })
        elif current_intensity < max(1, target_level - 2):
            warnings.append({
                "type": "horror_intensity_too_low",
                "message": f"恐怖强度不足，当前{current_intensity}，目标{target_level}",
            })

        return warnings

    # V1.1 新增：第一章特定约束检查
    def _check_chapter1_constraints(
        self,
        draft: str,
        chapter_plan: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        第一章特定约束检查
        - 不能出现强灵异/直接攻击
        - 不能解释完整规则
        - 必须有轻异常钩子（结尾）
        """
        violations = []

        # 1. 检查是否出现过强灵异（直接攻击、鬼怪露面）
        strong_encounter_patterns = [
            "扑过来", "冲过来", "抓", "咬", "掐住",
            "鬼怪", "鬼出现", "看到了鬼", "怪物",
            "鲜血淋漓", "血肉模糊", "尸体"
        ]

        for pattern in strong_encounter_patterns:
            if pattern in draft:
                violations.append({
                    "type": "chapter1_too_strong_horror",
                    "message": f"第一章出现过强的灵异元素：'{pattern}'，第一章应只建立轻微异常感",
                    "severity": "error",
                    "pattern": pattern,
                })

        # 2. 检查是否过早解释完整规则
        rule_explanation_patterns = [
            "规则就是", "原来是这样", "只要", "就不会",
            "所以说", "这就是为什么", "原来如此"
        ]

        explanation_count = sum(1 for p in rule_explanation_patterns if p in draft)
        if explanation_count >= 2:
            violations.append({
                "type": "chapter1_premature_rule_explanation",
                "message": f"第一章过早解释灵异规则（检测到{explanation_count}处解释性语句）",
                "severity": "error",
            })

        # 3. 检查结尾是否有轻异常钩子
        ending_text = draft[-300:] if len(draft) > 300 else draft

        subtle_hook_patterns = [
            "声音", "冷", "影子", "不对", "奇怪", "错觉",
            "好像", "似乎", "仿佛", "动了", "变了",
        ]

        hook_found = any(p in ending_text for p in subtle_hook_patterns)

        # 从配置中获取第一章要求
        chapter1_config = None
        for stage in self.progression_curve:
            if stage.get("stage_id") == "subtle_anomaly":
                chapter1_config = stage.get("chapter1_specific", {})
                break

        if chapter1_config and chapter1_config.get("required_ending_hook"):
            if not hook_found:
                violations.append({
                    "type": "chapter1_missing_subtle_hook",
                    "message": "第一章结尾缺少轻异常钩子，建议添加轻微的不安感描写",
                    "severity": "warning",
                })

        # 4. 第一章强度限制
        max_chapter1_intensity = chapter1_config.get("max_horror_intensity", 2) if chapter1_config else 2
        strong_horror_words = ["崩溃", "尖叫", "惨死", "鲜血", "恐怖", "吓死"]
        actual_intensity = sum(1 for w in strong_horror_words if w in draft)

        if actual_intensity > max_chapter1_intensity:
            violations.append({
                "type": "chapter1_intensity_exceeded",
                "message": f"第一章恐怖强度过高，实际{actual_intensity}，限制{max_chapter1_intensity}",
                "severity": "warning",
            })

        return violations
