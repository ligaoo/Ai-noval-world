from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ClassifiedProblem:
    """分类后的问题"""
    problem_id: str
    type: str
    severity: str
    score_dimension: str
    message: str
    evidence: List[str] = field(default_factory=list)
    related_events: List[str] = field(default_factory=list)
    can_be_rewritten: bool = True
    priority: int = 5

    def to_dict(self) -> Dict[str, Any]:
        return {
            "problem_id": self.problem_id,
            "type": self.type,
            "severity": self.severity,
            "score_dimension": self.score_dimension,
            "message": self.message,
            "evidence": self.evidence,
            "related_events": self.related_events,
            "can_be_rewritten": self.can_be_rewritten,
        }


class QualityProblemClassifier:
    """
    V5.1 质量问题分类器
    对问题进行分类、优先级排序和严重程度评估
    """

    PROBLEM_SEVERITY_RULES = {
        "weak_conflict": {"base_severity": "medium", "score_threshold": 5},
        "slow_middle": {"base_severity": "medium", "score_threshold": 5},
        "weak_hook": {"base_severity": "low", "score_threshold": 5},
        "flat_emotional_curve": {"base_severity": "medium", "score_threshold": 5},
        "low_plot_progress": {"base_severity": "high", "score_threshold": 5},
        "thin_character_motivation": {"base_severity": "medium", "score_threshold": 5},
        "dialogue_too_expository": {"base_severity": "low", "score_threshold": 6},
        "style_drift": {"base_severity": "medium", "score_threshold": 6},
        "voice_drift": {"base_severity": "medium", "score_threshold": 6},
        "over_explanation": {"base_severity": "low", "score_threshold": 7},
        "scene_repetition": {"base_severity": "medium", "score_threshold": 5},
        "suspense_without_payoff": {"base_severity": "high", "score_threshold": 5},
        "too_many_threads_opened": {"base_severity": "medium", "score_threshold": 6},
        "no_thread_progress": {"base_severity": "high", "score_threshold": 5},
        "payoff_too_abrupt": {"base_severity": "medium", "score_threshold": 5},
        "low_scene_vividness": {"base_severity": "low", "score_threshold": 6},
        "unclear_character_goal": {"base_severity": "medium", "score_threshold": 5},
        "poor_dialogue_voice": {"base_severity": "medium", "score_threshold": 6},
    }

    PROBLEM_DIMENSION_MAPPING = {
        "weak_conflict": "conflict_strength",
        "slow_middle": "pacing",
        "weak_hook": "chapter_hook",
        "flat_emotional_curve": "emotional_curve",
        "low_plot_progress": "plot_progress",
        "thin_character_motivation": "character_depth",
        "dialogue_too_expository": "dialogue_quality",
        "style_drift": "style_consistency",
        "voice_drift": "style_consistency",
        "over_explanation": "readability",
        "scene_repetition": "pacing",
        "suspense_without_payoff": "suspense",
        "too_many_threads_opened": "suspense",
        "no_thread_progress": "plot_progress",
        "payoff_too_abrupt": "payoff_quality",
        "low_scene_vividness": "scene_vividness",
        "unclear_character_goal": "character_depth",
        "poor_dialogue_voice": "dialogue_quality",
    }

    PROBLEM_PRIORITY_WEIGHTS = {
        "low_plot_progress": 9,
        "no_thread_progress": 9,
        "suspense_without_payoff": 8,
        "weak_conflict": 7,
        "payoff_too_abrupt": 7,
        "slow_middle": 6,
        "flat_emotional_curve": 6,
        "unclear_character_goal": 6,
        "thin_character_motivation": 6,
        "style_drift": 5,
        "voice_drift": 5,
        "poor_dialogue_voice": 5,
        "scene_repetition": 4,
        "weak_hook": 4,
        "dialogue_too_expository": 3,
        "low_scene_vividness": 3,
        "over_explanation": 2,
        "too_many_threads_opened": 2,
    }

    def classify_problems(
        self,
        raw_problems: List[Dict[str, Any]],
        scores: Dict[str, int],
        pre_analysis: Dict[str, Any],
    ) -> List[ClassifiedProblem]:
        """分类和增强问题列表"""
        classified = []

        for i, raw_problem in enumerate(raw_problems):
            problem = self._classify_single_problem(raw_problem, i, scores, pre_analysis)
            classified.append(problem)

        classified.sort(key=lambda p: p.priority, reverse=True)

        return classified

    def _classify_single_problem(
        self,
        raw_problem: Dict[str, Any],
        index: int,
        scores: Dict[str, int],
        pre_analysis: Dict[str, Any],
    ) -> ClassifiedProblem:
        """分类单个问题"""
        problem_type = raw_problem.get("type", "low_plot_progress")
        problem_id = raw_problem.get("problem_id", f"prob_{index:03d}")

        rules = self.PROBLEM_SEVERITY_RULES.get(problem_type, {})
        base_severity = rules.get("base_severity", "medium")
        score_threshold = rules.get("score_threshold", 6)

        dimension = self.PROBLEM_DIMENSION_MAPPING.get(problem_type, "")
        dimension_score = scores.get(dimension, 7) if dimension else 7

        severity = self._calculate_severity(
            base_severity,
            dimension_score,
            score_threshold,
        )

        priority = self._calculate_priority(problem_type, severity, dimension_score)

        evidence = raw_problem.get("evidence", [])
        if pre_analysis.get("possible_flags"):
            if problem_type.replace("_", "") in "".join(pre_analysis["possible_flags"]).replace("_", ""):
                evidence.append(f"Rule-based flag detected: {pre_analysis['possible_flags']}")

        return ClassifiedProblem(
            problem_id=problem_id,
            type=problem_type,
            severity=severity,
            score_dimension=dimension,
            message=raw_problem.get("message", ""),
            evidence=evidence,
            related_events=raw_problem.get("related_events", []),
            can_be_rewritten=raw_problem.get("can_be_rewritten", True),
            priority=priority,
        )

    def _calculate_severity(
        self,
        base_severity: str,
        dimension_score: int,
        score_threshold: int,
    ) -> str:
        """计算问题严重程度"""
        if dimension_score < score_threshold - 2:
            return "high"
        elif dimension_score < score_threshold:
            return base_severity
        else:
            severity_order = ["low", "medium", "high"]
            try:
                base_index = severity_order.index(base_severity)
                if base_index > 0:
                    return severity_order[base_index - 1]
            except ValueError:
                pass
            return base_severity

    def _calculate_priority(
        self,
        problem_type: str,
        severity: str,
        dimension_score: int,
    ) -> int:
        """计算问题优先级"""
        base_priority = self.PROBLEM_PRIORITY_WEIGHTS.get(problem_type, 5)

        severity_bonus = {
            "high": 2,
            "medium": 0,
            "low": -1,
        }.get(severity, 0)

        score_penalty = max(0, (7 - dimension_score) // 2)

        return min(10, max(1, base_priority + severity_bonus + score_penalty))

    def get_high_severity_problems(
        self,
        classified_problems: List[ClassifiedProblem],
    ) -> List[ClassifiedProblem]:
        """获取高优先级问题"""
        return [p for p in classified_problems if p.severity == "high"]

    def get_rewritable_problems(
        self,
        classified_problems: List[ClassifiedProblem],
    ) -> List[ClassifiedProblem]:
        """获取可修复的问题"""
        return [p for p in classified_problems if p.can_be_rewritten]

    def merge_duplicate_problems(
        self,
        classified_problems: List[ClassifiedProblem],
    ) -> List[ClassifiedProblem]:
        """合并重复的问题"""
        type_groups: Dict[str, List[ClassifiedProblem]] = {}

        for problem in classified_problems:
            if problem.type not in type_groups:
                type_groups[problem.type] = []
            type_groups[problem.type].append(problem)

        merged = []
        for problem_type, group in type_groups.items():
            if len(group) == 1:
                merged.append(group[0])
                continue

            highest_priority = max(group, key=lambda p: p.priority)
            highest_severity = max(group, key=lambda p: {"high": 3, "medium": 2, "low": 1}[p.severity])

            all_evidence = []
            for p in group:
                all_evidence.extend(p.evidence)

            merged.append(
                ClassifiedProblem(
                    problem_id=highest_priority.problem_id,
                    type=problem_type,
                    severity=highest_severity.severity,
                    score_dimension=highest_priority.score_dimension,
                    message=self._merge_messages([p.message for p in group]),
                    evidence=list(dict.fromkeys(all_evidence)),
                    related_events=list(dict.fromkeys([e for p in group for e in p.related_events])),
                    can_be_rewritten=any(p.can_be_rewritten for p in group),
                    priority=highest_priority.priority,
                )
            )

        return sorted(merged, key=lambda p: p.priority, reverse=True)

    def _merge_messages(self, messages: List[str]) -> str:
        """合并多条消息"""
        if len(messages) == 1:
            return messages[0]

        unique_messages = list(dict.fromkeys(messages))
        if len(unique_messages) == 1:
            return unique_messages[0]

        return " ".join(unique_messages[:2])
