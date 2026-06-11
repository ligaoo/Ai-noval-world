from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

from app.models.state import (
    ChapterGoalStatus,
    CharacterRuntimeState,
    FactExposureEntry,
    GoalRuntimeState,
    RelationshipRuntimeState,
    WorldRuntimeState,
    WorldState,
)
from app.models.world import WorldConfig


class WorldStateService:
    """WorldState 本地文件存储（state.json）。"""

    STATE_FILE = "state.json"

    def init_state(self, simulation_id: str, world: WorldConfig, seed: int) -> WorldState:
        # 初始化 discovered_facts
        discovered = {cid: False for cid in world.clues.clue_ids()}

        # 初始化 objects（按 location objects 扁平化）
        objects: Dict[str, dict] = {}
        for loc in world.map.locations:
            for obj in loc.objects:
                objects[obj.id] = {
                    "name": obj.name,
                    "visible": obj.visible,
                    "state": obj.state,
                    "description": obj.description,
                    "location_id": loc.id,
                }

        character_ids = world.characters.ids()
        location_ids = {loc.id for loc in world.map.locations}
        start_location = world.map.locations[0].id
        characters: Dict[str, CharacterRuntimeState] = {}
        for c in world.characters.characters:
            initial_location = c.initial_location if c.initial_location in location_ids else start_location
            relationships = {
                other_id: RelationshipRuntimeState()
                for other_id in character_ids
                if other_id != c.id
            }
            goals = self._runtime_goals_from_profile(c.id, c.goals)
            characters[c.id] = CharacterRuntimeState(
                location_id=initial_location,
                mental_state="",
                known_facts=list(c.known_facts),
                suspicions=list(c.suspicions),
                inventory=list(c.inventory),
                last_action=None,
                repeat_action_count=0,
                attitude_to={},
                relationships=relationships,
                hidden_status=c.visibility,
                goals=goals,
                stance={},
            )

        fact_exposure: Dict[str, FactExposureEntry] = {}
        for clue in world.clues.clues:
            known_by = [
                cid
                for cid, runtime in characters.items()
                if clue.content in runtime.known_facts or clue.id in runtime.known_facts
            ]
            fact_exposure[clue.id] = FactExposureEntry(
                fact_id=clue.id,
                truth=clue.content,
                known_by=known_by,
                source="clue",
                reveal_stage=getattr(clue, "truth_level", ""),
            )
        for c in world.characters.characters:
            for idx, secret in enumerate(c.secrets):
                fact_id = f"{c.id}_secret_{idx + 1}"
                if fact_id not in fact_exposure:
                    fact_exposure[fact_id] = FactExposureEntry(
                        fact_id=fact_id,
                        truth=secret,
                        known_by=[c.id],
                        source="character_secret",
                        reveal_stage="hidden_fact",
                    )

        return WorldState(
            simulation_id=simulation_id,
            tick=0,
            world_time=world.chapter_goal.start_time,
            random_seed=seed,
            chapter_goal_status=ChapterGoalStatus(goal=world.chapter_goal.goal, completed=False, progress=0),
            no_progress_ticks=0,
            characters=characters,
            world=WorldRuntimeState(
                discovered_facts=discovered,
                objects=objects,
                soft_hints=[],
                fact_exposure=fact_exposure,
            ),
        )

    def continue_state(
        self,
        previous_state: WorldState,
        simulation_id: str,
        world: WorldConfig,
        seed: int,
        chapter_goal_text: str,
    ) -> WorldState:
        state = self.init_state(simulation_id=simulation_id, world=world, seed=seed)
        state.world_time = previous_state.world_time
        state.chapter_goal_status = ChapterGoalStatus(
            goal=chapter_goal_text or world.chapter_goal.goal,
            completed=False,
            progress=0,
        )
        state.no_progress_ticks = 0

        for character_id, previous_character in previous_state.characters.items():
            state.characters[character_id] = previous_character.model_copy(deep=True)
            state.characters[character_id].last_action = None
            state.characters[character_id].repeat_action_count = 0
            state.characters[character_id].last_intent_signature = None

        baseline_world = state.world
        state.world = previous_state.world.model_copy(deep=True)
        for fact_id, discovered in baseline_world.discovered_facts.items():
            state.world.discovered_facts.setdefault(fact_id, discovered)
        for object_id, obj in baseline_world.objects.items():
            state.world.objects.setdefault(object_id, obj)
        for fact_id, exposure in baseline_world.fact_exposure.items():
            state.world.fact_exposure.setdefault(fact_id, exposure)
        state.world.soft_hints = []
        state.world.pending_key_events = []
        return state

    def _runtime_goals_from_profile(self, character_id: str, goals: Dict[str, object]) -> Dict[str, GoalRuntimeState]:
        runtime_goals: Dict[str, GoalRuntimeState] = {}
        priority = 10
        for goal_type in ("short_term", "long_term"):
            raw_goal = goals.get(goal_type)
            if not raw_goal:
                continue
            goal_items = raw_goal if isinstance(raw_goal, list) else [raw_goal]
            for index, item in enumerate(goal_items, start=1):
                description = str(item).strip()
                if not description:
                    continue
                goal_id = f"{character_id}_{goal_type}_{index}"
                runtime_goals[goal_id] = GoalRuntimeState(
                    goal_id=goal_id,
                    owner_agent_id=character_id,
                    description=description,
                    goal_type=goal_type,
                    status="active",
                    priority=priority,
                    source="character_profile",
                )
                priority -= 1
        return runtime_goals

    def load(self, sim_dir: Path) -> WorldState:
        path = sim_dir / self.STATE_FILE
        data = json.loads(path.read_text(encoding="utf-8"))
        return WorldState.model_validate(data)

    def save(self, sim_dir: Path, state: WorldState) -> None:
        path = sim_dir / self.STATE_FILE
        path.write_text(json.dumps(state.model_dump(mode="json"), ensure_ascii=False, indent=2), encoding="utf-8")

