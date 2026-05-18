from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.genre import GenreContext, GenreRegistry, GenreValidationResult
from app.quality.quality_pre_analyzer import QualityPreAnalyzer
from app.quality.quality_problem_classifier import QualityProblemClassifier
from app.quality.quality_llm_evaluator import QualityLLMEvaluator
from app.quality.rewrite_suggestion_generator import RewriteSuggestionGenerator


@dataclass
class QualityReport:
    report_id: str
    simulation_id: str
    chapter_id: str
    chapter_no: int
    status: str = "success"
    evaluated_target: str = "final_draft"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    overall_score: float = 7.0
    grade: str = "B"
    base_scores: Dict[str, int] = field(default_factory=dict)
    genre_scores: Dict[str, int] = field(default_factory=dict)
    thresholds: Dict[str, Any] = field(default_factory=dict)
    pre_analysis: Dict[str, Any] = field(default_factory=dict)
    problems: List[Dict[str, Any]] = field(default_factory=list)
    strengths: List[Dict[str, Any]] = field(default_factory=list)
    suggestions: List[Dict[str, Any]] = field(default_factory=list)
    genre_problems: List[Dict[str, Any]] = field(default_factory=list)
    genre_suggestions: List[Dict[str, Any]] = field(default_factory=list)
    rewrite_recommended: bool = False
    rewrite_priority: str = "low"
    rewrite_reasons: List[str] = field(default_factory=list)
    genre_consistency_result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    evaluation_time_ms: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "simulation_id": self.simulation_id,
            "chapter_id": self.chapter_id,
            "chapter_no": self.chapter_no,
            "status": self.status,
            "evaluated_target": self.evaluated_target,
            "created_at": self.created_at,
            "overall_score": self.overall_score,
            "grade": self.grade,
            "base_scores": self.base_scores,
            "genre_scores": self.genre_scores,
            "thresholds": self.thresholds,
            "pre_analysis": self.pre_analysis,
            "problems": self.problems,
            "strengths": self.strengths,
            "suggestions": self.suggestions,
            "genre_problems": self.genre_problems,
            "genre_suggestions": self.genre_suggestions,
            "rewrite_recommended": self.rewrite_recommended,
            "rewrite_priority": self.rewrite_priority,
            "rewrite_reasons": self.rewrite_reasons,
            "genre_consistency_result": self.genre_consistency_result,
            "error": self.error,
            "evaluation_time_ms": self.evaluation_time_ms,
        }

    @classmethod
    def failed(
        cls,
        simulation_id: str,
        chapter_id: str,
        chapter_no: int,
        error_message: str,
        error_type: str = "QUALITY_EVALUATION_ERROR",
    ) -> "QualityReport":
        return cls(
            report_id=f"qr_{simulation_id}_{chapter_id}_failed",
            simulation_id=simulation_id,
            chapter_id=chapter_id,
            chapter_no=chapter_no,
            status="failed",
            error={
                "message": error_message,
                "type": error_type,
            },
        )


class StoryQualityEvaluatorService:
    def __init__(
        self,
        sim_dir: Path,
        genre_id: str = "horror",
        genre_registry: Optional[GenreRegistry] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        self.sim_dir = sim_dir
        self.genre_id = genre_id
        self.config = config or {}

        if genre_registry:
            self.genre_registry = genre_registry
        else:
            registry_path = Path(__file__).parent.parent / "genre_packs"
            self.genre_registry = GenreRegistry(registry_path)

        self.genre_pack = self.genre_registry.get_genre_pack(genre_id)
        self.genre_profile = self.genre_registry.get_genre_profile(genre_id)

        self.pre_analyzer = QualityPreAnalyzer()
        self.llm_evaluator = QualityLLMEvaluator()
        self.problem_classifier = QualityProblemClassifier()
        self.suggestion_generator = RewriteSuggestionGenerator()

        self.quality_reports_dir = sim_dir / "quality_reports"
        self.quality_reports_dir.mkdir(exist_ok=True)

        self.thresholds = {
            "overall_min": self.config.get("overall_score_min", 6.5),
            "dimension_thresholds": self.config.get("dimension_thresholds", {
                "plot_progress": 5,
                "conflict_strength": 5,
                "pacing": 5,
                "horror_atmosphere": 5,
                "chapter_hook": 5,
            }),
        }

    def evaluate(
        self,
        chapter_plan: Dict[str, Any],
        chapter_draft: str,
        selected_events: List[Any],
        chapter_no: int,
        novel_progress: Optional[Dict[str, Any]] = None,
        open_threads: Optional[List[Dict[str, Any]]] = None,
        consistency_report: Optional[Dict[str, Any]] = None,
        state: Optional[Any] = None,
        fail_open: bool = True,
    ) -> QualityReport:
        simulation_id = self.sim_dir.name
        chapter_id = f"ch_{chapter_no:03d}"
        report_id = f"qr_{simulation_id}_{chapter_id}"

        start_time = datetime.now()

        try:
            pre_analysis_result = self.pre_analyzer.analyze(
                selected_events=selected_events,
                chapter_draft=chapter_draft,
                open_threads=open_threads,
                chapter_plan=chapter_plan,
            )
            pre_analysis_dict = self.pre_analyzer.to_dict(pre_analysis_result)

            genre_context = self.genre_pack.build_genre_context(
                state=state,
                chapter_plan=chapter_plan,
                novel_progress=novel_progress,
            )

            base_result = self.llm_evaluator.evaluate(
                chapter_plan=chapter_plan,
                chapter_draft=chapter_draft,
                pre_analysis=pre_analysis_dict,
                selected_events_summary=self._build_events_summary(selected_events),
                open_threads_summary=self._build_threads_summary(open_threads),
                plot_arc_state=None,
                consistency_report=consistency_report,
            )

            base_scores = base_result.scores
            base_problems = base_result.problems
            base_strengths = base_result.strengths

            classified_problems = self.problem_classifier.classify_problems(
                raw_problems=base_problems,
                scores=base_scores,
                pre_analysis=pre_analysis_dict,
            )
            classified_problems = self.problem_classifier.merge_duplicate_problems(classified_problems)

            base_suggestions = self.suggestion_generator.generate_suggestions(
                classified_problems=classified_problems,
                scores=base_scores,
                pre_analysis=pre_analysis_dict,
            )

            quality_context = {
                "chapter_plan": chapter_plan,
                "genre_context": genre_context.to_dict(),
                "base_quality_result": {
                    "scores": base_scores,
                    "problems": base_problems,
                    "strengths": base_strengths,
                },
            }
            genre_result = self.genre_pack.evaluate_genre_quality(
                quality_context=quality_context,
                chapter_draft=chapter_draft,
                selected_events=selected_events,
            )

            genre_validation_result = self.genre_pack.validate_genre_rules({
                "chapter_draft": chapter_draft,
                "chapter_plan": chapter_plan,
                "selected_events": selected_events,
                "genre_context": genre_context.to_dict(),
            })

            overall_score = self._calculate_weighted_overall_score(base_scores, genre_result.genre_scores)
            grade = self._calculate_grade(overall_score)

            rewrite_recommended, rewrite_priority, rewrite_reasons = self.suggestion_generator.should_rewrite(
                suggestions=base_suggestions,
                overall_score=overall_score,
                scores={**base_scores, **genre_result.genre_scores},
                thresholds=self.thresholds,
            )

            all_problems = [p.__dict__ if hasattr(p, '__dict__') else p for p in classified_problems]

            elapsed = datetime.now() - start_time

            return QualityReport(
                report_id=report_id,
                simulation_id=simulation_id,
                chapter_id=chapter_id,
                chapter_no=chapter_no,
                status="success",
                overall_score=round(overall_score, 1),
                grade=grade,
                base_scores=base_scores,
                genre_scores=genre_result.genre_scores,
                thresholds=self.thresholds,
                pre_analysis=pre_analysis_dict,
                problems=all_problems,
                strengths=base_strengths,
                suggestions=[s.to_dict() for s in base_suggestions],
                genre_problems=genre_result.genre_problems,
                genre_suggestions=genre_result.genre_suggestions,
                rewrite_recommended=rewrite_recommended,
                rewrite_priority=rewrite_priority,
                rewrite_reasons=rewrite_reasons,
                genre_consistency_result=genre_validation_result.to_dict(),
                evaluation_time_ms=int(elapsed.total_seconds() * 1000),
            )

        except Exception as e:
            if fail_open:
                return QualityReport.failed(
                    simulation_id=simulation_id,
                    chapter_id=chapter_id,
                    chapter_no=chapter_no,
                    error_message=str(e),
                )
            raise

    def _calculate_weighted_overall_score(
        self,
        base_scores: Dict[str, int],
        genre_scores: Dict[str, int],
    ) -> float:
        weights = self.genre_profile.get_merged_quality_weights()
        all_scores = {**base_scores, **genre_scores}

        weighted_sum = 0.0
        total_weight = 0.0

        for dimension, score in all_scores.items():
            weight = weights.get(dimension, 0.05)
            weighted_sum += score * weight
            total_weight += weight

        if total_weight == 0:
            return 7.0

        return weighted_sum / total_weight

    def _calculate_grade(self, score: float) -> str:
        if score >= 9.0:
            return "S"
        elif score >= 8.5:
            return "A"
        elif score >= 8.0:
            return "A-"
        elif score >= 7.5:
            return "B+"
        elif score >= 7.0:
            return "B"
        elif score >= 6.5:
            return "B-"
        elif score >= 6.0:
            return "C"
        elif score >= 5.0:
            return "D"
        else:
            return "F"

    def _build_events_summary(self, events: List[Any]) -> str:
        if not events:
            return "No events selected"

        summaries = []
        for i, event in enumerate(events[:15]):
            if hasattr(event, 'event_type') and hasattr(event, 'result'):
                summaries.append(f"{i+1}. [{event.event_type}] {event.result[:80]}")
            elif isinstance(event, dict):
                event_type = event.get('event_type', 'unknown')
                result = event.get('result', '')[:80]
                summaries.append(f"{i+1}. [{event_type}] {result}")

        if len(events) > 15:
            summaries.append(f"... and {len(events) - 15} more events")

        return "\n".join(summaries)

    def _build_threads_summary(self, open_threads: Optional[List[Dict[str, Any]]]) -> Optional[str]:
        if not open_threads:
            return None

        summaries = []
        for i, thread in enumerate(open_threads[:10]):
            question = thread.get("question", "")[:80]
            status = thread.get("status", "open")
            summaries.append(f"{i+1}. [{status}] {question}")

        if len(open_threads) > 10:
            summaries.append(f"... and {len(open_threads) - 10} more threads")

        return "\n".join(summaries)

    def save_report(self, report: QualityReport) -> None:
        report_file = self.quality_reports_dir / f"{report.chapter_id}_quality.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report.to_dict(), f, ensure_ascii=False, indent=2)

    def load_report(self, chapter_id: str) -> Optional[QualityReport]:
        report_file = self.quality_reports_dir / f"{chapter_id}_quality.json"
        if not report_file.exists():
            return None
        with open(report_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return QualityReport(**data)

    def get_all_reports(self) -> List[Dict[str, Any]]:
        reports = []
        for report_file in sorted(self.quality_reports_dir.glob("ch_*_quality.json")):
            with open(report_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                reports.append({
                    "chapter_id": data.get("chapter_id"),
                    "chapter_no": data.get("chapter_no"),
                    "overall_score": data.get("overall_score"),
                    "grade": data.get("grade"),
                    "rewrite_recommended": data.get("rewrite_recommended", False),
                    "status": data.get("status", "success"),
                })
        return reports

    def get_quality_trend(self) -> Dict[str, Any]:
        reports = self.get_all_reports()

        if not reports:
            return {
                "simulation_id": self.sim_dir.name,
                "trend": [],
                "average_score": 0,
                "total_chapters": 0,
            }

        scores = [r.get("overall_score", 7.0) for r in reports if r.get("status") == "success"]
        avg_score = sum(scores) / len(scores) if scores else 0

        return {
            "simulation_id": self.sim_dir.name,
            "trend": reports,
            "average_score": round(avg_score, 1),
            "total_chapters": len(reports),
        }
