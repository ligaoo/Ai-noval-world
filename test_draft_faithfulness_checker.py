from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.models.state import ChapterGoalStatus, WorldRuntimeState, WorldState
from app.models.world import (
    ChapterGoal,
    CharacterProfile,
    CharactersConfig,
    Clue,
    CluesConfig,
    Location,
    MapConfig,
    WorldBible,
    WorldConfig,
)
from app.services.draft_faithfulness_checker import DraftFaithfulnessChecker


def build_world() -> WorldConfig:
    return WorldConfig(
        bible=WorldBible(world_id="test_world"),
        map=MapConfig(locations=[Location(id="room", name="房间", public_description="", objects=[])]),
        characters=CharactersConfig(characters=[CharacterProfile(id="pov", name="主角")]),
        clues=CluesConfig(clues=[Clue(id="clue_secret", content="秘密内容")]),
        chapter_goal=ChapterGoal(goal="test", pov="pov"),
        world_id="test_world",
    )


class DraftFaithfulnessCheckerTest(unittest.TestCase):
    def test_unauthorized_plot_object_high(self) -> None:
        world = build_world()
        state = WorldState(
            simulation_id="sim",
            chapter_goal_status=ChapterGoalStatus(goal="test", completed=False, progress=0),
            world=WorldRuntimeState(discovered_facts={"clue_secret": False}),
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            report = DraftFaithfulnessChecker(world, Path(tmp_dir)).check(
                draft="他用钥匙打开暗门。",
                chapter_plan={"writer_structured_context": {"writer_authorization": {"authorized_entities": {"objects": []}}}},
                visible_events=[],
                state=state,
            )

            self.assertEqual(report["status"], "failed")
            self.assertTrue(
                any(issue["type"] == "UNAUTHORIZED_PLOT_OBJECT" and issue["severity"] == "high" for issue in report["issues"])
            )


if __name__ == "__main__":
    unittest.main()
