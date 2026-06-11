from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.models.chapter_brief import ChapterBrief, EndingHookPolicy, LocationPolicy, RelationshipFocus, RevealPolicy
from app.models.world import CharacterProfile, Clue, WorldConfig


class ChapterBriefService:
    def __init__(self, world: WorldConfig):
        self.world = world

    def build(
        self,
        chapter_no: int = 1,
        target_chapters: int = 10,
        reveal_budget=None,
        quality_controls=None,
        chapter_function: Optional[Dict[str, Any]] = None,
        previous_chapter_context: Optional[Dict[str, Any]] = None,
    ) -> ChapterBrief:
        chapter_function = chapter_function or {}
        previous_chapter_context = previous_chapter_context or {}
        bible = self.world.bible
        pov_id = self.world.chapter_goal.pov
        pov = self._get_character(pov_id)
        threads = self._thread_ids()
        first_clues = self._first_clue_ids()
        hidden_truth = str(getattr(bible, "hidden_truth", "") or "").strip()
        forbidden_reveals = self._list_attr(bible, "forbidden_early_reveals")
        previous_summary = str(previous_chapter_context.get("previous_chapter_summary") or "").strip()
        previous_open_threads = self._meaningful_threads(self._strings(previous_chapter_context.get("open_threads")))
        next_chapter_seeds = self._meaningful_threads(self._strings(previous_chapter_context.get("next_chapter_seeds")))
        chapter_function_text = str(chapter_function.get("chapter_function") or "").strip()
        primary_thread = str(chapter_function.get("primary_thread") or "").strip()
        secondary_threads = self._strings(chapter_function.get("secondary_threads"))
        payoff_threads = self._strings(chapter_function.get("thread_payoffs"))
        planned_clues = self._strings(chapter_function.get("planned_clues"))

        if chapter_no <= 1:
            main_question = self._first_non_empty(
                getattr(bible, "main_question", ""),
                self.world.chapter_goal.goal,
                self._question_from_threads(threads),
                "本章中，POV 将发现什么无法用常理解释的异常？",
            )
            chapter_goal = self._first_non_empty(
                self.world.chapter_goal.goal,
                chapter_function_text,
                getattr(bible, "first_volume_goal", ""),
                "建立核心异常、打开主线悬念，并让 POV 产生继续行动的必要性。",
            )
            must_advance_threads = self._dedupe([primary_thread, *secondary_threads, *payoff_threads, *threads])[:3]
        else:
            continuation_goal = self._continuation_goal(previous_summary, next_chapter_seeds, previous_open_threads)
            main_question = self._first_non_empty(
                next_chapter_seeds[0] if next_chapter_seeds else "",
                previous_open_threads[0] if previous_open_threads else "",
                primary_thread,
                getattr(bible, "main_question", ""),
                self._question_from_threads(threads),
                "本章需要承接上一章悬念并推进新的可验证线索。",
            )
            chapter_goal = self._first_non_empty(
                chapter_function_text,
                continuation_goal,
                getattr(bible, "first_volume_goal", ""),
                "承接上一章悬念，推进调查、关系变化和新的阶段性线索。",
                self.world.chapter_goal.goal,
            )
            must_advance_threads = self._dedupe([
                *previous_open_threads,
                *next_chapter_seeds,
                primary_thread,
                *secondary_threads,
                *payoff_threads,
                *threads,
            ])[:5]

        tone = self._first_non_empty(
            bible.tone,
            ", ".join(bible.themes[:2]) if bible.themes else "",
            "克制、压迫、悬疑",
        )

        allowed_facts = [item.fact for item in reveal_budget.allowed_reveals] if reveal_budget else self._allowed_facts(first_clues)
        suspected_facts = [item.fact for item in reveal_budget.suspected_only] if reveal_budget else self._suspected_facts(hidden_truth, threads)
        forbidden_facts = [item.fact for item in reveal_budget.forbidden_reveals] if reveal_budget else [fact for fact in [hidden_truth, *forbidden_reveals] if fact]
        forbidden_facts = self._dedupe([*forbidden_facts, *self._strings(chapter_function.get("must_not_reveal"))])
        location_policy, location_policy_source = self._build_location_policy(chapter_function, chapter_function_text)
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
            must_advance_threads=must_advance_threads,
            must_include_clues=(planned_clues or first_clues)[:3],
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
            location_policy=location_policy,
            source_notes={
                "world_id": self.world.world_id,
                "pov": pov_id,
                "core_motif": getattr(bible, "core_motif", ""),
                "chapter_function": chapter_function_text,
                "act_id": chapter_function.get("act_id", ""),
                "previous_chapter_summary": previous_summary,
                "next_chapter_seeds": next_chapter_seeds,
                "open_threads": previous_open_threads,
                "truth_stage": chapter_function.get("truth_stage", ""),
                "planned_evidence": self._strings(chapter_function.get("planned_evidence")),
                "planned_locations": self._strings(chapter_function.get("planned_locations")),
                "character_arc_beats": self._strings(chapter_function.get("character_arc_beats")),
                "thread_payoffs": payoff_threads,
                "location_policy_source": location_policy_source,
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
            if not motive:
                continue
            expected = f"围绕对方隐瞒的信息产生试探或不信任：{motive}"
            result.append(RelationshipFocus(source=pov.id, target=character.id, expected_shift=expected))
            if len(result) >= 2:
                break
        return result

    def _find_clue(self, clue_id: str) -> Optional[Clue]:
        try:
            return self.world.clues.get_clue(clue_id)
        except KeyError:
            return None

    def _build_location_policy(self, chapter_function: Dict[str, Any], chapter_function_text: str) -> tuple[LocationPolicy, List[str]]:
        allowed = self._location_ids(chapter_function.get("allowed_location_ids"))
        preferred = self._location_ids(chapter_function.get("preferred_location_ids"))
        forbidden = self._location_ids(chapter_function.get("forbidden_location_ids"))
        forbidden_names = self._strings(chapter_function.get("forbidden_location_names"))
        boundary_notes = self._strings(chapter_function.get("boundary_notes"))
        source: List[str] = []

        for value in self._strings(chapter_function.get("must_not_enter_locations")):
            matched_ids, matched_names = self._match_locations(value)
            forbidden.extend(matched_ids)
            forbidden_names.extend(matched_names)
            boundary_notes.append(value)
            source.append(f"must_not_enter_locations:{value}")

        text_sources = [chapter_function_text, *self._strings(chapter_function.get("source_notes"))]
        for text in text_sources:
            if not text:
                continue
            for location in self.world.map.locations:
                if not location.name or location.name not in text:
                    continue
                if not self._has_forbidden_enter_phrase(text, location.name):
                    continue
                forbidden.append(location.id)
                forbidden_names.append(location.name)
                boundary_notes.append(f"不得进入{location.name}")
                source.append(f"text:{location.name}")

        return LocationPolicy(
            allowed_location_ids=self._dedupe(allowed),
            preferred_location_ids=self._dedupe(preferred),
            forbidden_location_ids=self._dedupe(forbidden),
            forbidden_location_names=self._dedupe(forbidden_names),
            boundary_notes=self._dedupe(boundary_notes),
        ), self._dedupe(source)

    def _location_ids(self, value: Any) -> List[str]:
        ids: List[str] = []
        for item in self._strings(value):
            matched_ids, _ = self._match_locations(item)
            ids.extend(matched_ids or [item])
        return ids

    def _match_locations(self, text: str) -> tuple[List[str], List[str]]:
        ids: List[str] = []
        names: List[str] = []
        normalized = str(text or "").strip()
        for location in self.world.map.locations:
            if not normalized:
                continue
            if normalized == location.id or normalized == location.name or location.id in normalized or (location.name and location.name in normalized):
                ids.append(location.id)
                if location.name:
                    names.append(location.name)
        return self._dedupe(ids), self._dedupe(names)

    @staticmethod
    def _has_forbidden_enter_phrase(text: str, location_name: str) -> bool:
        triggers = ["不得进入", "禁止进入", "不要进入", "不能进入", "不可进入", "不得去", "不要去", "不能去", "must not enter", "do not enter"]
        lowered = text.lower()
        location_index = text.find(location_name)
        if location_index < 0:
            return False
        for trigger in triggers:
            trigger_index = lowered.find(trigger.lower())
            if trigger_index >= 0 and trigger_index <= location_index and location_index - trigger_index <= 40:
                return True
        return False

    @staticmethod
    def _strings(value: Any) -> List[str]:
        if isinstance(value, str):
            items = [value]
        elif isinstance(value, list):
            items = value
        else:
            items = []
        result: List[str] = []
        for item in items:
            if isinstance(item, dict):
                text = item.get("question") or item.get("thread_id") or item.get("summary") or item.get("effect") or json.dumps(item, ensure_ascii=False)
            else:
                text = str(item)
            text = str(text or "").strip()
            if text and text not in result:
                result.append(text)
        return result

    @classmethod
    def _meaningful_threads(cls, values: List[str]) -> List[str]:
        result: List[str] = []
        for value in values:
            text = str(value or "").strip()
            if not text or cls._is_generic_thread_text(text):
                continue
            if text not in result:
                result.append(text)
        return result

    @staticmethod
    def _is_generic_thread_text(text: str) -> bool:
        normalized = str(text or "").strip()
        if not normalized:
            return True
        generic_texts = {
            "从表面合作转为轻微试探，保留信息差。",
            "这条线索真正指向什么？",
            "这个异常细节为什么会出现？",
            "本章异常真正指向什么？",
            "本章异常真正指向什么",
            "以线索钩子结束，不总结，不揭示隐藏真相。",
        }
        if normalized in generic_texts:
            return True
        generic_fragments = [
            "以线索钩子结束",
            "不总结",
            "不揭示隐藏真相",
            "这个事件如何推进悬念",
        ]
        if any(fragment in normalized for fragment in generic_fragments):
            return True
        return len(normalized) < 6

    @staticmethod
    def _continuation_goal(previous_summary: str, next_chapter_seeds: List[str], open_threads: List[str]) -> str:
        parts: List[str] = []
        if previous_summary:
            parts.append(f"承接上一章变化：{previous_summary}")
        if next_chapter_seeds:
            parts.append(f"推进下一步线索：{'；'.join(next_chapter_seeds[:2])}")
        if open_threads:
            parts.append(f"回应未兑现悬念：{'；'.join(open_threads[:2])}")
        if not parts:
            return ""
        return "；".join(parts)

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
