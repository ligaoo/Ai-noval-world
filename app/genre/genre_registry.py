from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional, Type

from app.genre.genre_pack import GenrePack
from app.genre.genre_profile import GenreProfile


class GenreRegistry:
    def __init__(self, genre_packs_dir: Path):
        self.genre_packs_dir = genre_packs_dir
        self._registered_genres: Dict[str, Type[GenrePack]] = {}
        self._loaded_profiles: Dict[str, GenreProfile] = {}
        self._registry_config: Dict[str, Any] = self._load_registry_config()

    def _load_registry_config(self) -> Dict[str, Any]:
        config_file = self.genre_packs_dir / "registry.json"
        if config_file.exists():
            with open(config_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {
            "registered_genres": [
                {
                    "genre_id": "generic",
                    "enabled": True,
                    "path": "generic",
                },
                {
                    "genre_id": "horror",
                    "enabled": True,
                    "path": "horror",
                },
            ],
            "default_genre": "generic",
        }

    def register_genre(self, genre_id: str, genre_class: Type[GenrePack]) -> None:
        self._registered_genres[genre_id] = genre_class

    def get_genre_pack(self, genre_id: str) -> Optional[GenrePack]:
        if not self.is_genre_enabled(genre_id):
            genre_id = self._registry_config.get("default_genre", "generic")

        if genre_id not in self._registered_genres:
            self._load_genre_class(genre_id)

        genre_class = self._registered_genres.get(genre_id)
        if not genre_class:
            return None

        return genre_class(genre_id)

    def is_genre_enabled(self, genre_id: str) -> bool:
        for genre in self._registry_config.get("registered_genres", []):
            if genre.get("genre_id") == genre_id and genre.get("enabled", False):
                return True
        return False

    def _load_genre_class(self, genre_id: str) -> None:
        if genre_id == "generic":
            from app.genre_packs.generic.generic_genre_pack import GenericGenrePack
            self._registered_genres[genre_id] = GenericGenrePack
        elif genre_id == "horror":
            from app.genre_packs.horror.horror_genre_pack import HorrorGenrePack
            self._registered_genres[genre_id] = HorrorGenrePack

    def get_genre_profile(self, genre_id: str) -> Optional[GenreProfile]:
        if genre_id in self._loaded_profiles:
            return self._loaded_profiles[genre_id]

        for genre_config in self._registry_config.get("registered_genres", []):
            if genre_config.get("genre_id") == genre_id:
                profile_path = self.genre_packs_dir / genre_config["path"] / f"{genre_id}_genre_profile.json"
                if profile_path.exists():
                    profile = GenreProfile.from_json(profile_path)
                    self._loaded_profiles[genre_id] = profile
                    return profile

        return self.get_genre_profile("generic")

    def get_default_genre_id(self) -> str:
        return self._registry_config.get("default_genre", "generic")

    def list_available_genres(self) -> list[Dict[str, str]]:
        return [
            {
                "genre_id": g["genre_id"],
                "genre_name": self.get_genre_profile(g["genre_id"]).genre_name if self.get_genre_profile(g["genre_id"]) else g["genre_id"],
                "enabled": g.get("enabled", False),
            }
            for g in self._registry_config.get("registered_genres", [])
        ]
