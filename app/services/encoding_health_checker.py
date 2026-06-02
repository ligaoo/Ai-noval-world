from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


class EncodingHealthChecker:
    MARKERS = ["瑙", "涓", "绱", "鍠", "鎮", "锛", "鍙", "鐢", "鍒", "搴", "�"]
    FILES = [
        "chapter_plan.json",
        "chapter_debug.json",
        "state.json",
        "events.jsonl",
        "consistency_report.json",
        "tuning_report.md",
    ]

    def __init__(self, sim_dir: Path):
        self.sim_dir = Path(sim_dir)

    def check(self) -> Dict[str, Any]:
        issues: List[Dict[str, Any]] = []
        for file_name in self.FILES:
            path = self.sim_dir / file_name
            if not path.exists():
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            if file_name == "chapter_plan.json":
                issues.extend(self._check_chapter_plan(path, text))
            else:
                markers = self._find_markers(text)
                if markers:
                    issues.append(
                        {
                            "type": "MOJIBAKE_MARKER_DETECTED",
                            "severity": self._default_severity(file_name),
                            "message": f"Mojibake markers found in {file_name}.",
                            "details": {"path": file_name, "markers": markers},
                        }
                    )
        report = self._build_report(issues)
        self._write_json(self.sim_dir / "encoding_health_report.json", report)
        return report

    def _check_chapter_plan(self, path: Path, text: str) -> List[Dict[str, Any]]:
        data = self._read_json(path)
        if not isinstance(data, dict):
            markers = self._find_markers(text)
            if not markers:
                return []
            return [
                {
                    "type": "MOJIBAKE_MARKER_DETECTED",
                    "severity": "high",
                    "message": "Mojibake markers found in chapter_plan.json.",
                    "details": {"path": path.name, "markers": markers},
                }
            ]
        issues = []
        fields = {
            "chapter_title": data.get("chapter_title"),
            "emotional_curve": data.get("emotional_curve"),
            "writer_structured_context": data.get("writer_structured_context"),
        }
        for index, beat in enumerate(data.get("beats") or []):
            fields[f"beats[{index}].purpose"] = beat.get("purpose")
        for field, value in fields.items():
            markers = self._find_markers(json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value)
            if markers:
                issues.append(
                    {
                        "type": "MOJIBAKE_MARKER_DETECTED",
                        "severity": "high",
                        "message": f"Mojibake markers found in chapter_plan.json {field}.",
                        "details": {"path": path.name, "field": field, "markers": markers},
                    }
                )
        return issues

    def _find_markers(self, text: str) -> List[str]:
        return [marker for marker in self.MARKERS if marker in text]

    @staticmethod
    def _default_severity(file_name: str) -> str:
        if file_name in {"chapter_debug.json", "consistency_report.json"}:
            return "medium"
        if file_name == "tuning_report.md":
            return "low"
        return "medium"

    @staticmethod
    def _build_report(issues: List[Dict[str, Any]]) -> Dict[str, Any]:
        high_count = sum(1 for issue in issues if issue.get("severity") in {"high", "critical"})
        medium_count = sum(1 for issue in issues if issue.get("severity") == "medium")
        low_count = sum(1 for issue in issues if issue.get("severity") == "low")
        return {
            "checker": "encoding_health",
            "status": "failed" if high_count else "warning" if medium_count or low_count else "passed",
            "passed": high_count == 0,
            "issue_count": len(issues),
            "high_count": high_count,
            "medium_count": medium_count,
            "low_count": low_count,
            "issues": issues,
        }

    @staticmethod
    def _read_json(path: Path) -> Dict[str, Any] | None:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None

    @staticmethod
    def _write_json(path: Path, data: Dict[str, Any]) -> None:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
