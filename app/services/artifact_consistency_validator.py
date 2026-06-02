from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


class ArtifactConsistencyValidator:
    def __init__(self, sim_dir: Path):
        self.sim_dir = Path(sim_dir)

    def validate(self) -> Dict[str, Any]:
        issues: List[Dict[str, Any]] = []
        issues.extend(self._check_discovered_facts())
        issues.extend(self._check_chapter_plan_events())
        issues.extend(self._check_llm_trace_summary())
        issues.extend(self._check_quality_reports())
        report = self._build_report(issues)
        self._write_json(self.sim_dir / "artifact_consistency_report.json", report)
        return report

    def _check_discovered_facts(self) -> List[Dict[str, Any]]:
        state = self._read_json(self.sim_dir / "state.json") or {}
        plot_arc = self._read_json(self.sim_dir / "plot_arc_state.json") or {}
        state_discovered = {
            clue_id for clue_id, discovered in ((state.get("world") or {}).get("discovered_facts") or {}).items() if discovered
        }
        plot_discovered = set(plot_arc.get("discovered_clue_ids") or [])
        if not plot_arc or state_discovered == plot_discovered:
            return []
        return [
            {
                "type": "DISCOVERED_FACTS_MISMATCH",
                "severity": "high",
                "message": "state.world.discovered_facts and plot_arc_state.discovered_clue_ids differ.",
                "details": {
                    "state_only": sorted(state_discovered - plot_discovered),
                    "plot_arc_only": sorted(plot_discovered - state_discovered),
                },
            }
        ]

    def _check_chapter_plan_events(self) -> List[Dict[str, Any]]:
        plan = self._read_json(self.sim_dir / "chapter_plan.json") or {}
        events = self._read_jsonl(self.sim_dir / "events.jsonl")
        event_ids = {event.get("event_id") for event in events}
        missing = []
        for beat in plan.get("beats") or []:
            for event_id in beat.get("event_ids") or []:
                if event_id not in event_ids:
                    missing.append({"beat_id": beat.get("beat_id"), "event_id": event_id})
        if not missing:
            return []
        return [
            {
                "type": "CHAPTER_PLAN_EVENT_MISSING",
                "severity": "high",
                "message": "chapter_plan beats reference event_ids not present in events.jsonl.",
                "details": {"missing": missing},
            }
        ]

    def _check_llm_trace_summary(self) -> List[Dict[str, Any]]:
        trace_path = self.sim_dir / "llm_traces.jsonl"
        summary = self._read_json(self.sim_dir / "llm_summary.json") or {}
        if not trace_path.exists() or not summary:
            return []
        trace_count = len(self._read_jsonl(trace_path))
        total_calls = int(summary.get("total_calls") or 0)
        if abs(trace_count - total_calls) <= 1:
            return []
        return [
            {
                "type": "LLM_TRACE_SUMMARY_MISMATCH",
                "severity": "medium",
                "message": "llm_traces.jsonl line count and llm_summary.total_calls are inconsistent.",
                "details": {"trace_count": trace_count, "total_calls": total_calls},
            }
        ]

    def _check_quality_reports(self) -> List[Dict[str, Any]]:
        quality_dir = self.sim_dir / "quality_reports"
        if not quality_dir.exists():
            return []
        issues = []
        for path in sorted(quality_dir.glob("ch_*_quality.json")):
            report = self._read_json(path) or {}
            status = str(report.get("status") or "").lower()
            rewrite_priority = str(report.get("rewrite_priority") or "").lower()
            rewrite_recommended = bool(report.get("rewrite_recommended"))
            if status == "failed" or (rewrite_recommended and rewrite_priority == "high"):
                issues.append(
                    {
                        "type": "QUALITY_REPORT_BLOCKING_ISSUE",
                        "severity": "high",
                        "message": "Quality report failed or recommends high-priority rewrite.",
                        "details": {"path": path.name, "status": status, "rewrite_priority": rewrite_priority},
                    }
                )
        return issues

    @staticmethod
    def _build_report(issues: List[Dict[str, Any]]) -> Dict[str, Any]:
        high_count = sum(1 for issue in issues if issue.get("severity") in {"high", "critical"})
        medium_count = sum(1 for issue in issues if issue.get("severity") == "medium")
        return {
            "validator": "artifact_consistency",
            "status": "failed" if high_count else "warning" if medium_count else "passed",
            "passed": high_count == 0,
            "issue_count": len(issues),
            "high_count": high_count,
            "medium_count": medium_count,
            "issues": issues,
        }

    @staticmethod
    def _read_json(path: Path) -> Dict[str, Any] | None:
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None

    @staticmethod
    def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
        if not path.exists():
            return []
        rows = []
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except Exception:
                    rows.append({})
        return rows

    @staticmethod
    def _write_json(path: Path, data: Dict[str, Any]) -> None:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
