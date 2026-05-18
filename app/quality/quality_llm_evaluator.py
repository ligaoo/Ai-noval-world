from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.llm_client import OpenAICompatibleClient
from app.services.trace_service import TraceService


@dataclass
class LLMEvaluationResult:
    """LLM 评估结果"""
    success: bool
    overall_score: float = 0.0
    scores: Dict[str, int] = field(default_factory=dict)
    problems: List[Dict[str, Any]] = field(default_factory=list)
    strengths: List[Dict[str, Any]] = field(default_factory=list)
    suggestions: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None
    raw_response: Optional[str] = None


class QualityLLMEvaluator:
    """
    V5.1 LLM 质量评估器
    使用 LLM 进行深度质量评估，输出结构化结果
    """

    VALID_PROBLEM_TYPES = {
        "weak_conflict",
        "slow_middle",
        "weak_hook",
        "flat_emotional_curve",
        "low_plot_progress",
        "thin_character_motivation",
        "dialogue_too_expository",
        "style_drift",
        "voice_drift",
        "over_explanation",
        "scene_repetition",
        "suspense_without_payoff",
        "too_many_threads_opened",
        "no_thread_progress",
        "payoff_too_abrupt",
        "low_scene_vividness",
        "unclear_character_goal",
        "poor_dialogue_voice",
    }

    VALID_SUGGESTION_TYPES = {
        "increase_conflict",
        "tighten_pacing",
        "improve_hook",
        "enhance_suspense",
        "deepen_character",
        "improve_dialogue",
        "polish_style",
        "reduce_exposition",
        "enhance_scene",
        "strengthen_payoff",
    }

    SCORE_DIMENSIONS = [
        "plot_progress",
        "conflict_strength",
        "character_depth",
        "emotional_curve",
        "suspense",
        "pacing",
        "scene_vividness",
        "dialogue_quality",
        "style_consistency",
        "chapter_hook",
        "payoff_quality",
        "readability",
    ]

    def __init__(
        self,
        llm_client: Optional[OpenAICompatibleClient] = None,
        trace_service: Optional[TraceService] = None,
        max_retry: int = 1,
    ):
        self.llm_client = llm_client
        self.trace_service = trace_service
        self.max_retry = max_retry

    def evaluate(
        self,
        chapter_plan: Any,
        chapter_draft: str,
        pre_analysis: Dict[str, Any],
        selected_events_summary: str,
        open_threads_summary: Optional[str] = None,
        plot_arc_state: Optional[Dict[str, Any]] = None,
        consistency_report: Optional[Dict[str, Any]] = None,
    ) -> LLMEvaluationResult:
        """执行 LLM 评估"""
        if not self.llm_client:
            return self._fallback_evaluation(pre_analysis)

        context = self._build_evaluation_context(
            chapter_plan,
            chapter_draft,
            pre_analysis,
            selected_events_summary,
            open_threads_summary,
            plot_arc_state,
            consistency_report,
        )

        prompt = self._build_prompt(context)

        for attempt in range(self.max_retry + 1):
            try:
                response = self.llm_client.chat_completion(
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    response_format={"type": "json_object"},
                )

                raw_response = response.choices[0].message.content
                result = self._parse_response(raw_response)

                if result.success:
                    result.raw_response = raw_response
                    return result

            except Exception as e:
                if attempt == self.max_retry:
                    return LLMEvaluationResult(
                        success=False,
                        error=f"LLM evaluation failed after {self.max_retry + 1} attempts: {str(e)}",
                    )

        return LLMEvaluationResult(success=False, error="Max retry reached")

    def _build_evaluation_context(
        self,
        chapter_plan: Any,
        chapter_draft: str,
        pre_analysis: Dict[str, Any],
        selected_events_summary: str,
        open_threads_summary: Optional[str],
        plot_arc_state: Optional[Dict[str, Any]],
        consistency_report: Optional[Dict[str, Any]],
    ) -> str:
        """构建评估上下文"""
        if isinstance(chapter_plan, dict):
            plan_json = json.dumps(chapter_plan, ensure_ascii=False, indent=2)
        else:
            plan_json = json.dumps(getattr(chapter_plan, "__dict__", {}), ensure_ascii=False, indent=2)

        parts = [
            "=== CHAPTER PLAN ===",
            plan_json,
            "",
            "=== CHAPTER DRAFT ===",
            chapter_draft[:4000],
            "",
            "=== PRE ANALYSIS ===",
            json.dumps(pre_analysis, ensure_ascii=False, indent=2),
            "",
            "=== SELECTED EVENTS ===",
            selected_events_summary,
        ]

        if open_threads_summary:
            parts.extend(["", "=== OPEN THREADS ===", open_threads_summary])

        if plot_arc_state:
            parts.extend(["", "=== PLOT ARC STATE ===", json.dumps(plot_arc_state, ensure_ascii=False, indent=2)])

        if consistency_report:
            parts.extend(["", "=== CONSISTENCY REPORT ===", json.dumps(consistency_report, ensure_ascii=False, indent=2)])

        return "\n".join(parts)

    def _build_prompt(self, context: str) -> str:
        """构建评估提示词"""
        return f"""你是小说沙盘引擎的 Story Quality Evaluator。

你的任务是评估章节质量，不是重写章节。

你必须根据以下输入进行评分：
1. chapter_plan
2. chapter_draft
3. pre_analysis
4. selected_events
5. open_threads
6. plot_arc_state
7. consistency_report

评分要求：
- 所有分数使用 0-10
- 必须输出 overall_score
- 必须输出每个维度分数
- 必须指出具体问题
- 必须给出可执行修改建议
- 建议不能新增 EventLog 中不存在的事实
- 建议不能要求提前泄露 forbidden_revelations
- 输出严格 JSON

评估维度：
- plot_progress：剧情推进程度
- conflict_strength：冲突强度
- character_depth：人物深度
- emotional_curve：情绪曲线变化
- suspense：悬念强度
- pacing：节奏把控
- scene_vividness：场景画面感
- dialogue_quality：对白质量
- style_consistency：文风一致性
- chapter_hook：章节钩子
- payoff_quality：伏笔回收质量
- readability：可读性

问题类型（type 字段）只能从以下列表中选择：
{', '.join(self.VALID_PROBLEM_TYPES)}

建议类型（type 字段）只能从以下列表中选择：
{', '.join(self.VALID_SUGGESTION_TYPES)}

【输入】
{context}

【输出 JSON 格式】
{{
  "overall_score": 7.4,
  "scores": {{
    "plot_progress": 8,
    "conflict_strength": 6,
    "character_depth": 7,
    "emotional_curve": 7,
    "suspense": 8,
    "pacing": 6,
    "scene_vividness": 7,
    "dialogue_quality": 6,
    "style_consistency": 8,
    "chapter_hook": 7,
    "payoff_quality": 5,
    "readability": 8
  }},
  "problems": [
    {{
      "problem_id": "prob_001",
      "type": "weak_conflict",
      "severity": "medium",
      "score_dimension": "conflict_strength",
      "message": "本章主要是调查和发现，人物之间的正面冲突偏弱。",
      "evidence": ["连续三个 beat 都是搜索/观察，没有角色阻碍或目标冲突。"],
      "can_be_rewritten": true
    }}
  ],
  "strengths": [
    {{
      "type": "effective_suspense",
      "score_dimension": "suspense",
      "message": "线索推进了悬念。"
    }}
  ],
  "suggestions": [
    {{
      "suggestion_id": "sug_001",
      "type": "increase_conflict",
      "message": "可以强化看守人阻拦的紧张感。",
      "rewrite_task": "increase_conflict",
      "target_sections": ["sec_004"],
      "priority": 8,
      "constraints": [
        "只能强化已有阻拦事件的表达",
        "不能改变事件结果"
      ]
    }}
  ]
}}

只输出 JSON，不要输出其他内容。
"""

    def _parse_response(self, raw_response: str) -> LLMEvaluationResult:
        """解析 LLM 响应"""
        try:
            data = json.loads(raw_response)
        except json.JSONDecodeError as e:
            json_match = re.search(r"\{.*\}", raw_response, re.DOTALL)
            if json_match:
                try:
                    data = json.loads(json_match.group())
                except json.JSONDecodeError:
                    return LLMEvaluationResult(success=False, error=f"JSON parse error: {e}")
            else:
                return LLMEvaluationResult(success=False, error=f"JSON parse error: {e}")

        try:
            overall_score = float(data.get("overall_score", 0))
            scores = data.get("scores", {})

            scores = self._normalize_scores(scores)

            problems = data.get("problems", [])
            problems = self._validate_problems(problems)

            strengths = data.get("strengths", [])

            suggestions = data.get("suggestions", [])
            suggestions = self._validate_suggestions(suggestions)

            return LLMEvaluationResult(
                success=True,
                overall_score=overall_score,
                scores=scores,
                problems=problems,
                strengths=strengths,
                suggestions=suggestions,
            )

        except Exception as e:
            return LLMEvaluationResult(success=False, error=f"Response validation error: {e}")

    def _normalize_scores(self, scores: Dict[str, Any]) -> Dict[str, int]:
        """标准化分数"""
        normalized = {}
        for dim in self.SCORE_DIMENSIONS:
            score = scores.get(dim, 7)
            try:
                int_score = int(float(score))
                int_score = max(0, min(10, int_score))
                normalized[dim] = int_score
            except (ValueError, TypeError):
                normalized[dim] = 7
        return normalized

    def _validate_problems(self, problems: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """验证问题列表"""
        validated = []
        for i, p in enumerate(problems):
            problem_type = p.get("type", "low_plot_progress")
            if problem_type not in self.VALID_PROBLEM_TYPES:
                problem_type = "low_plot_progress"

            severity = p.get("severity", "medium")
            if severity not in {"high", "medium", "low"}:
                severity = "medium"

            validated.append({
                "problem_id": p.get("problem_id", f"prob_{i:03d}"),
                "type": problem_type,
                "severity": severity,
                "score_dimension": p.get("score_dimension", ""),
                "message": p.get("message", ""),
                "evidence": p.get("evidence", []),
                "can_be_rewritten": bool(p.get("can_be_rewritten", True)),
            })
        return validated

    def _validate_suggestions(self, suggestions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """验证建议列表"""
        validated = []
        for i, s in enumerate(suggestions):
            suggestion_type = s.get("type", "enhance_suspense")
            if suggestion_type not in self.VALID_SUGGESTION_TYPES:
                suggestion_type = "enhance_suspense"

            priority = s.get("priority", 7)
            try:
                priority = max(1, min(10, int(priority)))
            except (ValueError, TypeError):
                priority = 7

            validated.append({
                "suggestion_id": s.get("suggestion_id", f"sug_{i:03d}"),
                "type": suggestion_type,
                "message": s.get("message", ""),
                "rewrite_task": s.get("rewrite_task", suggestion_type),
                "target_sections": s.get("target_sections", []),
                "priority": priority,
                "constraints": s.get("constraints", []),
            })
        return validated

    def _fallback_evaluation(self, pre_analysis: Dict[str, Any]) -> LLMEvaluationResult:
        """当没有 LLM 时的降级评估"""
        flags = pre_analysis.get("possible_flags", [])

        scores = {dim: 7 for dim in self.SCORE_DIMENSIONS}

        if "low_conflict" in flags:
            scores["conflict_strength"] = 4

        if "low_plot_progress" in flags:
            scores["plot_progress"] = 5

        if "repetitive_search_events" in flags:
            scores["pacing"] = 5

        if "weak_hook" in flags:
            scores["chapter_hook"] = 5

        if "too_many_threads_opened" in flags:
            scores["suspense"] = 5

        problems = []
        for flag in flags:
            problem_type = self._flag_to_problem_type(flag)
            if problem_type:
                problems.append({
                    "problem_id": f"prob_{len(problems):03d}",
                    "type": problem_type,
                    "severity": "medium",
                    "score_dimension": self._flag_to_dimension(flag),
                    "message": self._flag_to_message(flag),
                    "evidence": [f"Rule-based flag: {flag}"],
                    "can_be_rewritten": True,
                })

        overall_score = sum(scores.values()) / len(scores)

        return LLMEvaluationResult(
            success=True,
            overall_score=round(overall_score, 1),
            scores=scores,
            problems=problems,
            strengths=[],
            suggestions=[],
        )

    def _flag_to_problem_type(self, flag: str) -> Optional[str]:
        """将 flag 转换为问题类型"""
        mapping = {
            "low_conflict": "weak_conflict",
            "repetitive_search_events": "slow_middle",
            "weak_hook": "weak_hook",
            "low_plot_progress": "low_plot_progress",
            "too_many_threads_opened": "too_many_threads_opened",
            "no_thread_progress": "no_thread_progress",
        }
        return mapping.get(flag)

    def _flag_to_dimension(self, flag: str) -> str:
        """将 flag 转换为评分维度"""
        mapping = {
            "low_conflict": "conflict_strength",
            "repetitive_search_events": "pacing",
            "weak_hook": "chapter_hook",
            "low_plot_progress": "plot_progress",
            "too_many_threads_opened": "suspense",
            "no_thread_progress": "plot_progress",
        }
        return mapping.get(flag, "")

    def _flag_to_message(self, flag: str) -> str:
        """将 flag 转换为问题描述"""
        mapping = {
            "low_conflict": "本章缺乏明确的角色冲突或张力不足。",
            "repetitive_search_events": "本章连续多个搜索/观察事件，节奏可能拖沓。",
            "weak_hook": "本章结尾钩子较弱，可能降低读者的兴趣。",
            "low_plot_progress": "本章没有发现新线索，剧情推进有限。",
            "too_many_threads_opened": "本章开启了过多的悬念线，可能导致读者困惑。",
            "no_thread_progress": "本章没有推进任何已有的悬念线。",
        }
        return mapping.get(flag, f"检测到潜在问题: {flag}")
