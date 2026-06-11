from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from typing import Dict, List


@dataclass(frozen=True)
class StageWindow:
    stage: str
    start: int
    end: int

    @property
    def chapters(self) -> List[int]:
        return list(range(self.start, self.end + 1))


def build_stage_windows(target_chapters: int) -> Dict[str, StageWindow]:
    total = max(4, int(target_chapters or 30))
    surface_end = max(1, ceil(total * 0.18))
    partial_end = max(surface_end + 1, ceil(total * 0.50))
    major_end = max(partial_end + 1, ceil(total * 0.82))
    major_end = min(major_end, total - 1)
    return {
        "surface": StageWindow("surface", 1, surface_end),
        "partial": StageWindow("partial", surface_end + 1, partial_end),
        "major": StageWindow("major", partial_end + 1, major_end),
        "truth": StageWindow("truth", major_end + 1, total),
    }


def window_for_stage(target_chapters: int, stage: str) -> List[int]:
    windows = build_stage_windows(target_chapters)
    key = stage if stage in windows else "surface"
    window = windows[key]
    return [window.start, window.end]


def chapters_for_stage(target_chapters: int, stage: str) -> List[int]:
    windows = build_stage_windows(target_chapters)
    key = stage if stage in windows else "surface"
    return windows[key].chapters


def stage_for_chapter(target_chapters: int, chapter_no: int) -> str:
    chapter = max(1, int(chapter_no or 1))
    for stage, window in build_stage_windows(target_chapters).items():
        if window.start <= chapter <= window.end:
            return stage
    return "truth"
