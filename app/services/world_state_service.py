from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

from app.models.state import ChapterGoalStatus, CharacterRuntimeState, WorldRuntimeState, WorldState
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

        location_ids = {loc.id for loc in world.map.locations}
        start_location = world.map.locations[0].id
        characters: Dict[str, CharacterRuntimeState] = {}
        for c in world.characters.characters:
            initial_location = c.initial_location if c.initial_location in location_ids else start_location
            characters[c.id] = CharacterRuntimeState(
                location_id=initial_location,
                mental_state="",
                known_facts=list(c.known_facts),
                suspicions=list(c.suspicions),
                inventory=list(c.inventory),
                last_action=None,
                repeat_action_count=0,
                attitude_to={},
            )

        return WorldState(
            simulation_id=simulation_id,
            tick=0,
            world_time=world.chapter_goal.start_time,
            random_seed=seed,
            chapter_goal_status=ChapterGoalStatus(goal=world.chapter_goal.goal, completed=False, progress=0),
            no_progress_ticks=0,
            characters=characters,
            world=WorldRuntimeState(discovered_facts=discovered, objects=objects, soft_hints=[]),
        )

    def load(self, sim_dir: Path) -> WorldState:
        path = sim_dir / self.STATE_FILE
        data = json.loads(path.read_text(encoding="utf-8"))
        return WorldState.model_validate(data)

    def save(self, sim_dir: Path, state: WorldState) -> None:
        path = sim_dir / self.STATE_FILE
        path.write_text(json.dumps(state.model_dump(mode="json"), ensure_ascii=False, indent=2), encoding="utf-8")

