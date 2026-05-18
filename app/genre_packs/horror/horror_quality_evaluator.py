from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List

from app.genre import BaseGenreQualityEvaluator, GenreQualityResult


class HorrorQualityEvaluator(BaseGenreQualityEvaluator):
    def __init__(self, genre_id: str = "horror"):
        super().__init__(genre_id)
        self._load_dimensions_config()

    def _load_dimensions_config(self) -> None:
        config_path = Path(__file__).parent / "horror_genre_profile.json"
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                self.config = json.load(f)
        else:
            self.config = {}

    def evaluate(
        self,
        chapter_draft: str,
        chapter_plan: Dict[str, Any],
        selected_events: List[Any],
        genre_context: Dict[str, Any],
        base_quality_result: Dict[str, Any],
    ) -> GenreQualityResult:
        genre_scores = self._evaluate_genre_scores(
            chapter_draft,
            chapter_plan,
            selected_events,
            genre_context,
        )

        genre_problems = self._detect_genre_problems(
            chapter_draft,
            genre_context,
        )

        genre_suggestions = self._generate_genre_suggestions(genre_problems)

        return GenreQualityResult(
            genre_scores=genre_scores,
            genre_problems=genre_problems,
            genre_suggestions=genre_suggestions,
        )

    def _evaluate_genre_scores(
        self,
        draft: str,
        chapter_plan: Dict[str, Any],
        events: List[Any],
        genre_context: Dict[str, Any],
    ) -> Dict[str, int]:
        scores = {}

        scores["horror_atmosphere"] = self._evaluate_horror_atmosphere(draft)
        scores["uncanny_effect"] = self._evaluate_uncanny_effect(draft)
        scores["fear_escalation"] = self._evaluate_fear_escalation(draft, genre_context)
        scores["supernatural_rule_consistency"] = self._evaluate_rule_consistency(draft)
        scores["taboo_pressure"] = self._evaluate_taboo_pressure(draft)
        scores["unknown_threat_strength"] = self._evaluate_unknown_threat_strength(draft)

        return scores

    def _evaluate_horror_atmosphere(self, draft: str) -> int:
        atmosphere_keywords = [
            "黑暗", "阴暗", "昏暗", "阴影", "寂静", "死寂",
            "冰冷", "寒冷", "刺骨", "压抑", "窒息",
            "诡异", "奇怪", "异常", "不对劲",
        ]

        score = 5
        for keyword in atmosphere_keywords:
            if keyword in draft:
                score = min(10, score + 1)

        if len(draft) > 500:
            sensory_details = len(re.findall(r"听|看|闻|摸|感觉|感受", draft))
            if sensory_details >= 3:
                score = min(10, score + 1)

        return score

    def _evaluate_uncanny_effect(self, draft: str) -> int:
        uncanny_patterns = [
            "不一样", "不对", "错了", "变了",
            "消失", "出现", "多了", "少了",
            "重复", "循环", "一模一样",
            "声音", "脚步声", "低语",
        ]

        score = 5
        for pattern in uncanny_patterns:
            if pattern in draft:
                score = min(10, score + 0.5)

        return int(score)

    def _evaluate_fear_escalation(
        self,
        draft: str,
        genre_context: Dict[str, Any],
    ) -> int:
        target_intensity = genre_context.get("genre_tension_level", 5)

        strong_fear_words = ["恐惧", "害怕", "惊恐", "绝望", "崩溃"]
        medium_fear_words = ["紧张", "不安", "焦虑", "担心", "奇怪"]

        strong_count = sum(1 for w in strong_fear_words if w in draft)
        medium_count = sum(1 for w in medium_fear_words if w in draft)

        actual_intensity = min(10, 3 + strong_count * 1.5 + medium_count * 0.5)
        deviation = abs(actual_intensity - target_intensity)

        if deviation <= 1:
            score = 10
        elif deviation <= 2:
            score = 8
        elif deviation <= 3:
            score = 6
        else:
            score = 4

        return score

    def _evaluate_rule_consistency(self, draft: str) -> int:
        rule_violation_patterns = [
            "原来是这样", "这就是真相", "所以说",
            "我明白了", "原来如此", "也就是说",
        ]

        explanation_count = sum(1 for p in rule_violation_patterns if p in draft)
        score = max(4, 10 - explanation_count * 2)

        return score

    def _evaluate_taboo_pressure(self, draft: str) -> int:
        taboo_words = ["禁忌", "不能", "不准", "禁止", "警告", "千万"]
        consequence_words = ["后果", "代价", "死亡", "消失", "出事"]

        taboo_count = sum(1 for w in taboo_words if w in draft)
        consequence_count = sum(1 for w in consequence_words if w in draft)

        score = 5 + taboo_count * 0.8 + consequence_count * 0.5
        return min(10, int(score))

    def _evaluate_unknown_threat_strength(self, draft: str) -> int:
        unknown_patterns = ["不知道", "不清楚", "无法", "看不到", "是什么"]
        threat_patterns = ["危险", "威胁", "可怕", "恐怖", "吓人"]

        unknown_count = sum(1 for p in unknown_patterns if p in draft)
        threat_count = sum(1 for p in threat_patterns if p in draft)

        score = 5 + unknown_count * 0.5 + threat_count * 0.8
        return min(10, int(score))

    def _detect_genre_problems(
        self,
        draft: str,
        genre_context: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        problems = []

        forbidden_devices = genre_context.get("genre_forbidden_devices", [])
        for device in forbidden_devices:
            if device in draft:
                problems.append({
                    "type": "forbidden_horror_device",
                    "message": f"当前阶段使用了禁用的恐怖手法: {device}",
                    "severity": "high",
                    "device": device,
                })

        explanation_count = len(re.findall(r"原来|因为|所以", draft))
        if explanation_count > 5:
            problems.append({
                "type": "over_explained_supernatural",
                "message": "过多解释超自然现象，削弱恐怖感",
                "severity": "medium",
            })

        if len(re.findall(r"打|杀|战斗", draft)) > 3:
            problems.append({
                "type": "suddenly_became_action",
                "message": "突然转向战斗模式，偏离心理恐怖风格",
                "severity": "high",
            })

        forbidden_patterns = self.config.get("forbidden_patterns", [])
        for pattern in forbidden_patterns:
            if pattern in draft:
                problems.append({
                    "type": "forbidden_pattern_detected",
                    "message": f"检测到禁用模式: {pattern}",
                    "severity": "medium",
                })

        return problems

    def _generate_genre_suggestions(
        self,
        problems: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        suggestions = []

        for problem in problems:
            problem_type = problem.get("type")

            if problem_type == "over_explained_supernatural":
                suggestions.append({
                    "type": "reduce_explanation",
                    "message": "减少对超自然现象的直接解释，用细节暗示替代说明",
                    "target_sections": ["explanation_paragraphs"],
                })
            elif problem_type == "forbidden_horror_device":
                suggestions.append({
                    "type": "replace_horror_device",
                    "message": f"将禁用的恐怖手法替换为当前阶段允许的手法",
                    "target_sections": ["horror_scenes"],
                })
            elif problem_type == "suddenly_became_action":
                suggestions.append({
                    "type": "restore_psychological_horror",
                    "message": "回归心理恐怖，用环境和心理压力替代直接战斗",
                    "target_sections": ["action_scenes"],
                })

        if not any(p.get("type") == "horror_atmosphere_weak" for p in problems):
            suggestions.append({
                "type": "enhance_sensory_details",
                "message": "可通过增强感官细节（听觉、触觉、视觉）提升恐怖氛围",
                "priority": "low",
            })

        return suggestions
