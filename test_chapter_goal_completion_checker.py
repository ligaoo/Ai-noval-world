from __future__ import annotations

import unittest

from app.models.event import EventLog
from app.models.state import ChapterGoalStatus, CharacterRuntimeState, WorldRuntimeState, WorldState
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
from app.services.chapter_goal_completion_checker import ChapterGoalCompletionChecker


def build_world() -> WorldConfig:
    return WorldConfig(
        bible=WorldBible(world_id="test_world"),
        map=MapConfig(locations=[Location(id="room", name="房间", public_description="", objects=[])]),
        characters=CharactersConfig(
            characters=[CharacterProfile(id="pov", name="主角"), CharacterProfile(id="other", name="同伴")]
        ),
        clues=CluesConfig(clues=[]),
        chapter_goal=ChapterGoal(goal="test", pov="pov"),
        world_id="test_world",
    )


class ChapterGoalCompletionCheckerTest(unittest.TestCase):
    def test_completed_state_blocked_by_missing_relationship_update(self) -> None:
        world = build_world()
        state = WorldState(
            simulation_id="sim",
            chapter_goal_status=ChapterGoalStatus(goal="test", completed=True, progress=100),
            characters={
                "pov": CharacterRuntimeState(location_id="room"),
                "other": CharacterRuntimeState(location_id="room"),
            },
            world=WorldRuntimeState(discovered_facts={}),
        )
        events = [
            EventLog(
                event_id="evt_interaction",
                event_level="plot",
                time="day1_20:00",
                location_id="room",
                actors=["pov", "other"],
                event_type="interaction",
                result="They argued.",
                visible_to=["pov"],
            )
        ]

        report = ChapterGoalCompletionChecker(world).evaluate(state, events)

        self.assertFalse(report["effective_completed"])
        self.assertEqual(report["status"], "failed")
        self.assertTrue(any(check["name"] == "MIN_RELATIONSHIP_UPDATES" and not check["passed"] for check in report["checks"]))


if __name__ == "__main__":
    unittest.main()
