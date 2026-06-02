from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from app.services.encoding_health_checker import EncodingHealthChecker


class EncodingHealthCheckerTest(unittest.TestCase):
    def test_chapter_plan_mojibake_is_high(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            sim_dir = Path(tmp_dir)
            (sim_dir / "chapter_plan.json").write_text(
                json.dumps(
                    {
                        "chapter_title": "搴忕珷",
                        "emotional_curve": ["鍠"],
                        "beats": [{"purpose": "observe"}],
                        "writer_structured_context": {},
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            report = EncodingHealthChecker(sim_dir).check()

            self.assertEqual(report["status"], "failed")
            self.assertTrue(any(issue["severity"] == "high" for issue in report["issues"]))
            self.assertTrue((sim_dir / "encoding_health_report.json").exists())


if __name__ == "__main__":
    unittest.main()
