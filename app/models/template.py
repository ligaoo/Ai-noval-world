from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class TemplateGenerationRequest:
    genre: str = "悬疑"
    theme: str = "选择与代价"
    protagonist_seed: str = "被卷入异常处境的人"
    core_location: str = "核心地点"
    target_length: str = "10 chapters"
    tone: str = "克制、压抑"
    complexity: str = "medium"
    preferred_elements: List[str] = field(default_factory=lambda: ["异常规则", "可验证线索", "隐藏行动者", "目击者"])
    forbidden_elements: List[str] = field(default_factory=lambda: ["爽文复仇", "直接鬼怪大战", "套用固定医院旧案模板"])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "genre": self.genre,
            "theme": self.theme,
            "protagonist_seed": self.protagonist_seed,
            "core_location": self.core_location,
            "target_length": self.target_length,
            "tone": self.tone,
            "complexity": self.complexity,
            "preferred_elements": self.preferred_elements,
            "forbidden_elements": self.forbidden_elements,
        }


@dataclass
class ChapterSeed:
    chapter_no: int
    chapter_function: str
    target_stage: str = "setup"
    must_introduce: List[str] = field(default_factory=list)
    suggested_threads: List[str] = field(default_factory=list)
    must_not_reveal: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chapter_no": self.chapter_no,
            "chapter_function": self.chapter_function,
            "target_stage": self.target_stage,
            "must_introduce": self.must_introduce,
            "suggested_threads": self.suggested_threads,
            "must_not_reveal": self.must_not_reveal,
        }


@dataclass
class ProjectTemplate:
    template_id: str
    world_bible: Dict[str, Any] = field(default_factory=dict)
    characters: List[Dict[str, Any]] = field(default_factory=list)
    npcs: List[Dict[str, Any]] = field(default_factory=list)
    map: Dict[str, Any] = field(default_factory=dict)
    clues: List[Dict[str, Any]] = field(default_factory=list)
    plot_arcs: List[Dict[str, Any]] = field(default_factory=list)
    character_arcs: List[Dict[str, Any]] = field(default_factory=list)
    style_bible: Dict[str, Any] = field(default_factory=dict)
    character_voice_profiles: List[Dict[str, Any]] = field(default_factory=list)
    chapter_seed_plan: List[ChapterSeed] = field(default_factory=list)
    validation_report: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "template_id": self.template_id,
            "world_bible": self.world_bible,
            "characters": self.characters,
            "npcs": self.npcs,
            "map": self.map,
            "clues": self.clues,
            "plot_arcs": self.plot_arcs,
            "character_arcs": self.character_arcs,
            "style_bible": self.style_bible,
            "character_voice_profiles": self.character_voice_profiles,
            "chapter_seed_plan": [c.to_dict() for c in self.chapter_seed_plan],
            "validation_report": self.validation_report,
        }
