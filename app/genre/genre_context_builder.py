from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from app.genre.genre_pack import GenreContext, GenrePack
from app.genre.genre_registry import GenreRegistry


@dataclass
class NovelProgress:
    chapter_no: int
    target_chapters: int
    current_act: str = ""
    plot_arc_stage: str = ""
    current_progress_ratio: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chapter_no": self.chapter_no,
            "target_chapters": self.target_chapters,
            "current_act": self.current_act,
            "plot_arc_stage": self.plot_arc_stage,
            "current_progress_ratio": self.current_progress_ratio,
        }


class GenreContextBuilder:
    def __init__(self, genre_registry: GenreRegistry):
        self.genre_registry = genre_registry

    def build_for_chapter(
        self,
        genre_id: str,
        state: Any,
        chapter_plan: Dict[str, Any],
        novel_progress: Optional[NovelProgress] = None,
    ) -> GenreContext:
        genre_pack = self.genre_registry.get_genre_pack(genre_id)
        if not genre_pack:
            return self._build_default_context(genre_id)

        if novel_progress is None:
            novel_progress = NovelProgress(
                chapter_no=chapter_plan.get("chapter_no", 1),
                target_chapters=30,
            )

        return genre_pack.build_genre_context(
            state=state,
            chapter_plan=chapter_plan,
            novel_progress=novel_progress.to_dict(),
        )

    def _build_default_context(self, genre_id: str) -> GenreContext:
        return GenreContext(
            genre_id=genre_id,
            genre_stage="development",
            genre_tension_level=5,
            genre_progression_target={
                "target": "continue_story",
                "description": "继续推进故事情节",
            },
        )

    def get_progression_target(
        self,
        genre_id: str,
        novel_progress: NovelProgress,
    ) -> Dict[str, Any]:
        genre_pack = self.genre_registry.get_genre_pack(genre_id)
        if not genre_pack:
            return {
                "target": "continue_story",
                "description": "继续推进故事情节",
            }

        return genre_pack.get_progression_target(novel_progress.to_dict())
