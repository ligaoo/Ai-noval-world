from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

from app.models.chapter_brief import ChapterBrief, EndingHookPolicy, RelationshipFocus, RevealPolicy
from app.models.world import CharacterProfile, Clue, WorldConfig


class ChapterBriefService:
    def __init__(self, world: WorldConfig):
        self.world = world

    def build(self, chapter_no: int = 1, target_chapters: int = 10, reveal_budget=None, quality_controls=None) -> ChapterBrief:
        bible = self.world.bible
        pov_id = self.world.chapter_goal.pov
        pov = self._get_character(pov_id)
        threads = self._thread_ids()
        first_clues = self._first_clue_ids()
        hidden_truth = str(getattr(bible, "hidden_truth", "") or "").strip()
        forbidden_reveals = self._list_attr(bible, "forbidden_early_reveals")

        main_question = self._first_non_empty(
            getattr(bible, "main_question", ""),
            self.world.chapter_goal.goal,
            self._question_from_threads(threads),
            "本章中，POV 将发现什么无法用常理解释的异常？",
        )
        chapter_goal = self._first_non_empty(
            self.world.chapter_goal.goal,
            getattr(bible, "first_volume_goal", ""),
            "建立核心异常、打开主线悬念，并让 POV 产生继续行动的必要性。",
        )
        tone = self._first_non_empty(
            bible.tone,
            ", ".join(bible.themes[:2]) if bible.themes else "",
            "克制、压迫、悬疑",
        )

        allowed_facts = [item.fact for item in reveal_budget.allowed_reveals] if reveal_budget else self._allowed_facts(first_clues)
        suspected_facts = [item.fact for item in reveal_budget.suspected_only] if reveal_budget else self._suspected_facts(hidden_truth, threads)
        forbidden_facts = [item.fact for item in reveal_budget.forbidden_reveals] if reveal_budget else [fact for fact in [hidden_truth, *forbidden_reveals] if fact]
        if quality_controls and quality_controls.style_focus:
            tone = f"{tone}；重点：{'、'.join(quality_controls.style_focus)}"
        ending_hook_type = quality_controls.ending_hook_type if quality_controls else "线索钩子"

        return ChapterBrief(
            chapter_no=chapter_no,
            target_chapters=target_chapters,
            chapter_title_hint=self._chapter_title_hint(first_clues),
            main_question=main_question,
            chapter_goal=chapter_goal,
            tone=tone,
            must_advance_threads=threads[:3],
            must_include_clues=first_clues[:3],
            relationship_focus=self._relationship_focus(pov),
            reveal_policy=RevealPolicy(
                allowed_facts=allowed_facts,
                suspected_facts=suspected_facts,
                forbidden_facts=forbidden_facts,
            ),
            ending_hook=EndingHookPolicy(
                type=ending_hook_type,
                requirement=f"以{ending_hook_type}结束，不总结，不揭示隐藏真相。",
            ),
            source_notes={
                "world_id": self.world.world_id,
                "pov": pov_id,
                "core_motif": getattr(bible, "core_motif", ""),
            },
        )

    def save(self, sim_dir: Path, brief: ChapterBrief) -> None:
        with open(sim_dir / "chapter_brief.json", "w", encoding="utf-8") as f:
            json.dump(brief.model_dump(), f, ensure_ascii=False, indent=2)

    @staticmethod
    def load(sim_dir: Path) -> Optional[ChapterBrief]:
        path = sim_dir / "chapter_brief.json"
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return ChapterBrief.model_validate(json.load(f))
        except Exception:
            return None

    def _get_character(self, character_id: str) -> Optional[CharacterProfile]:
        try:
            return self.world.characters.get_character(character_id)
        except KeyError:
            return None

    def _thread_ids(self) -> List[str]:
        ids: List[str] = []
        for clue in self.world.clues.clues:
            thread = getattr(clue, "related_thread", None)
            if thread and thread not in ids:
                ids.append(thread)
        return ids

    def _first_clue_ids(self) -> List[str]:
        clues = sorted(
            self.world.clues.clues,
            key=lambda clue: getattr(clue, "importance", 0),
            reverse=True,
        )
        return [clue.id for clue in clues if clue.discover_routes][:5]

    def _chapter_title_hint(self, clue_ids: List[str]) -> str:
        if clue_ids:
            clue = self._find_clue(clue_ids[0])
            if clue and clue.name:
                return clue.name
        if self.world.map.locations:
            return self.world.map.locations[0].name
        return "序章"

    def _allowed_facts(self, clue_ids: List[str]) -> List[str]:
        facts: List[str] = []
        for clue_id in clue_ids[:3]:
            clue = self._find_clue(clue_id)
            if not clue:
                continue
            if clue.truth_level in {"visible_fact", "surface", "minor", "rumor"}:
                facts.append(clue.bootstrap_fact or clue.content)
        return self._dedupe(facts)

    def _suspected_facts(self, hidden_truth: str, threads: List[str]) -> List[str]:
        facts: List[str] = []
        for clue in self.world.clues.clues:
            if clue.truth_level in {"hidden_fact", "rumor"}:
                facts.append(clue.bootstrap_fact or clue.content)
        if hidden_truth:
            facts.append(f"隐藏真相只能作为异常感或怀疑存在：{hidden_truth}")
        for thread in threads[:3]:
            facts.append(f"悬念仍未解决：{thread}")
        return self._dedupe(facts)[:8]

    def _relationship_focus(self, pov: Optional[CharacterProfile]) -> List[RelationshipFocus]:
        if not pov:
            return []
        result: List[RelationshipFocus] = []
        for character in self.world.characters.characters:
            if character.id == pov.id or character.visibility != "visible" or not character.active_agent:
                continue
            motive = getattr(character, "private_motive", "") or getattr(character, "withheld_information", "") or character.personal_stakes
            if motive:
                expected = f"围绕对方隐瞒的信息产生试探或不信任：{motive}"
            else:
                expected = "从表面合作转为轻微试探，保留信息差。"
            result.append(RelationshipFocus(source=pov.id, target=character.id, expected_shift=expected))
            if len(result) >= 2:
                break
        return result

    def _find_clue(self, clue_id: str) -> Optional[Clue]:
        try:
            return self.world.clues.get_clue(clue_id)
        except KeyError:
            return None

    @staticmethod
    def _first_non_empty(*values: str) -> str:
        for value in values:
            text = str(value or "").strip()
            if text:
                return text
        return ""

    @staticmethod
    def _question_from_threads(threads: List[str]) -> str:
        if not threads:
            return ""
        return f"本章需要推进这些悬念：{'、'.join(threads[:3])}。"

    @staticmethod
    def _list_attr(obj, key: str) -> List[str]:
        value = getattr(obj, key, [])
        if isinstance(value, list):
            return [str(item) for item in value if str(item).strip()]
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        return []

    @staticmethod
    def _dedupe(values: List[str]) -> List[str]:
        result: List[str] = []
        seen = set()
        for value in values:
            text = str(value or "").strip()
            if text and text not in seen:
                result.append(text)
                seen.add(text)
        return result
