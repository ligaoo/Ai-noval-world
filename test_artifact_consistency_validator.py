from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from app.services.artifact_consistency_validator import ArtifactConsistencyValidator


class ArtifactConsistencyValidatorTest(unittest.TestCase):
    def test_detects_discovered_mismatch_and_missing_plan_event(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            sim_dir = Path(tmp_dir)
            (sim_dir / "state.json").write_text(
                json.dumps({"world": {"discovered_facts": {"clue_a": True, "clue_b": False}}}),
                encoding="utf-8",
            )
            (sim_dir / "plot_arc_state.json").write_text(
                json.dumps({"discovered_clue_ids": ["clue_c"]}),
                encoding="utf-8",
            )
            (sim_dir / "chapter_plan.json").write_text(
                json.dumps({"beats": [{"beat_id": "b001", "event_ids": ["evt_missing"]}]}),
                encoding="utf-8",
            )
            (sim_dir / "events.jsonl").write_text(
                json.dumps({"event_id": "evt_present"}) + "\n",
                encoding="utf-8",
            )

            report = ArtifactConsistencyValidator(sim_dir).validate()

            self.assertEqual(report["status"], "failed")
            issue_types = {issue["type"] for issue in report["issues"]}
            self.assertIn("DISCOVERED_FACTS_MISMATCH", issue_types)
            self.assertIn("CHAPTER_PLAN_EVENT_MISSING", issue_types)
            self.assertTrue((sim_dir / "artifact_consistency_report.json").exists())


if __name__ == "__main__":
    unittest.main()
