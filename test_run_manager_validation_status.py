from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from app.models.state import ChapterGoalStatus, WorldRuntimeState, WorldState
from app.models.world import (
    ChapterGoal,
    CharacterProfile,
    CharactersConfig,
    CluesConfig,
    Location,
    MapConfig,
    WorldBible,
    WorldConfig,
)
from app.services.run_manager_lite import RunManagerLite


def build_world() -> WorldConfig:
    return WorldConfig(
        bible=WorldBible(world_id="test_world"),
        map=MapConfig(locations=[Location(id="room", name="房间", public_description="", objects=[])]),
        characters=CharactersConfig(characters=[CharacterProfile(id="pov", name="主角")]),
        clues=CluesConfig(clues=[]),
        chapter_goal=ChapterGoal(goal="test", pov="pov", tick_limit=1),
        world_id="test_world",
    )


class RunManagerValidationStatusTest(unittest.TestCase):
    def test_complete_with_validation_writes_status_fields(self) -> None:
        world = build_world()
        state = WorldState(
            simulation_id="sim",
            tick=1,
            chapter_goal_status=ChapterGoalStatus(goal="test", completed=True, progress=100),
            world=WorldRuntimeState(discovered_facts={}),
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            sim_dir = Path(tmp_dir)
            manager = RunManagerLite(sim_dir, world, seed=1, tick_limit=1)
            manager.initialize()
            errors = [{"type": "TEST_VALIDATION", "severity": "high", "message": "failed"}]

            manager.complete_with_validation(state, "failed", errors, {})

            status = json.loads((sim_dir / "run_status.json").read_text(encoding="utf-8"))
            self.assertEqual(status["status"], "completed_with_validation_errors")
            self.assertEqual(status["generation_status"], "completed")
            self.assertEqual(status["validation_status"], "failed")
            self.assertEqual(status["validation_errors"], errors)
            metrics = json.loads((sim_dir / "metrics.json").read_text(encoding="utf-8"))
            self.assertEqual(metrics["validation"]["status"], "failed")


if __name__ == "__main__":
    unittest.main()
