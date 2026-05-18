from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from app.models.world import (
    ChapterGoal,
    CharactersConfig,
    CluesConfig,
    MapConfig,
    WorldBible,
    WorldConfig,
)


class WorldConfigService:
    """加载世界配置（JSON 文件）。"""

    def __init__(self, project_root: Path):
        self.project_root = project_root

    def load_world(self, world_id: str) -> WorldConfig:
        world_dir = self.project_root / "worlds" / world_id
        if not world_dir.exists():
            raise FileNotFoundError(f"world not found: {world_dir}")

        bible = self._load_json(world_dir / "world_bible.json", WorldBible)
        map_cfg = self._load_json(world_dir / "map.json", MapConfig)
        chars = self._load_json(world_dir / "characters.json", CharactersConfig)
        clues = self._load_json(world_dir / "clues.json", CluesConfig)
        goal = self._load_json(world_dir / "chapter_goal.json", ChapterGoal)

        # 基础一致性检查
        char_ids = set(chars.ids())
        for clue in clues.clues:
            for r in clue.discover_routes:
                if r.action_type in ("ask", "talk") and r.target not in char_ids:
                    raise ValueError(
                        f"clue route target must be a character for ask/talk: {clue.id}/{r.route_id}"
                    )

        return WorldConfig(bible=bible, map=map_cfg, characters=chars, clues=clues, chapter_goal=goal)

    @staticmethod
    def _load_json(path: Path, model_cls):
        if not path.exists():
            raise FileNotFoundError(f"missing config file: {path}")
        data = json.loads(path.read_text(encoding="utf-8"))
        try:
            return model_cls.model_validate(data)
        except ValidationError as e:
            raise ValueError(f"invalid config: {path}\n{e}") from e

