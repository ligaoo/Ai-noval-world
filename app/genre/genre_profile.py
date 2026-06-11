from __future__ import annotations

import json
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class GenreProfile:
    genre_id: str
    genre_name: str
    description: str = ""
    extends: Optional[str] = None
    base_dimensions: List[str] = field(default_factory=list)
    genre_dimensions: List[str] = field(default_factory=list)
    story_drivers: List[str] = field(default_factory=list)
    tension_axes: List[str] = field(default_factory=list)
    default_arc_structure: List[str] = field(default_factory=list)
    quality_weights: Dict[str, float] = field(default_factory=dict)
    quality_weights_override: Dict[str, float] = field(default_factory=dict)
    thread_policy: Dict[str, Any] = field(default_factory=dict)
    generic_narrative_quality: Dict[str, Any] = field(default_factory=dict)
    forbidden_patterns: List[str] = field(default_factory=list)

    @classmethod
    def from_json(cls, file_path: Path) -> GenreProfile:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        allowed_fields = {item.name for item in fields(cls)}
        return cls(**{key: value for key, value in data.items() if key in allowed_fields})

    def to_dict(self) -> Dict[str, Any]:
        return {
            "genre_id": self.genre_id,
            "genre_name": self.genre_name,
            "description": self.description,
            "extends": self.extends,
            "base_dimensions": self.base_dimensions,
            "genre_dimensions": self.genre_dimensions,
            "story_drivers": self.story_drivers,
            "tension_axes": self.tension_axes,
            "default_arc_structure": self.default_arc_structure,
            "quality_weights": self.quality_weights,
            "quality_weights_override": self.quality_weights_override,
            "thread_policy": self.thread_policy,
            "forbidden_patterns": self.forbidden_patterns,
        }

    def get_all_dimensions(self) -> List[str]:
        return self.base_dimensions + self.genre_dimensions

    def get_merged_quality_weights(self) -> Dict[str, float]:
        merged = self.quality_weights.copy()
        merged.update(self.quality_weights_override)
        return merged
