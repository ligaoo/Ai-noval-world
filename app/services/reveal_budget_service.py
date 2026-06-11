from __future__ import annotations

import json
from pathlib import Path
from typing import Any, List, Optional

from app.models.reveal_budget import AllowedReveal, ForbiddenReveal, PayoffTarget, RevealBudget, SuspectedOnly
from app.models.world import WorldConfig


class RevealBudgetService:
    def __init__(self, world: WorldConfig):
        self.world = world

    def build(self, chapter_no: int = 1, target_chapters: int = 30, chapter_function: Optional[Dict[str, Any]] = None) -> RevealBudget:
        chapter_function = chapter_function or {}
        allowed: List[AllowedReveal] = []
        suspected: List[SuspectedOnly] = []
        forbidden: List[ForbiddenReveal] = []
        questions: List[str] = []
        payoff_targets: List[PayoffTarget] = []

        for fact in chapter_function.get("allowed_reveals") or []:
            allowed.append(AllowedReveal(fact=str(fact), level=str(chapter_function.get("truth_stage") or "surface"), source="chapter_function"))
        planned_clues = set(str(item) for item in chapter_function.get("planned_clues") or [])

        for clue in sorted(self.world.clues.clues, key=lambda item: item.importance, reverse=True):
            fact = clue.bootstrap_fact or clue.content or clue.name
            if clue.id in planned_clues and len(allowed) < 4:
                allowed.append(AllowedReveal(fact=fact, level=str(chapter_function.get("truth_stage") or "surface"), source=clue.id))
            elif clue.truth_level in {"visible_fact", "surface", "minor"} and len(allowed) < 3:
                allowed.append(AllowedReveal(fact=fact, level="surface", source=clue.id))
            elif len(suspected) < 5:
                suspected.append(SuspectedOnly(fact=fact, reason=f"线索 {clue.id} 本章只能形成怀疑，不能确认真相。"))
            if clue.related_thread:
                questions.append(f"{clue.related_thread} 目前真正指向什么？")
                payoff_targets.append(PayoffTarget(thread_id=clue.related_thread, expected_payoff_chapter=min(target_chapters, max(chapter_no + 2, 3))))

        bible = self.world.bible
        hidden_truth = getattr(bible, "hidden_truth", "") or "最终真相"
        if hidden_truth:
            forbidden.append(ForbiddenReveal(fact=hidden_truth, until_chapter=max(chapter_no + 3, 4)))
        for fact in getattr(bible, "forbidden_early_reveals", []) or []:
            forbidden.append(ForbiddenReveal(fact=str(fact), until_chapter=max(chapter_no + 2, 3)))
        for fact in chapter_function.get("must_not_reveal") or []:
            forbidden.append(ForbiddenReveal(fact=str(fact), until_chapter=target_chapters))
        for thread_id in chapter_function.get("thread_payoffs") or []:
            payoff_targets.append(PayoffTarget(thread_id=str(thread_id), expected_payoff_chapter=chapter_no))

        if not questions:
            questions.append(getattr(bible, "main_question", "本章异常真正指向什么？") or "本章异常真正指向什么？")

        return RevealBudget(
            chapter_no=chapter_no,
            allowed_reveals=allowed[:3],
            suspected_only=self._dedupe_suspected(suspected)[:5],
            forbidden_reveals=self._dedupe_forbidden(forbidden),
            required_questions=self._dedupe_text(questions)[:5],
            payoff_targets=self._dedupe_payoffs(payoff_targets)[:5],
        )

    def save(self, sim_dir: Path, budget: RevealBudget) -> None:
        with open(sim_dir / "reveal_budget.json", "w", encoding="utf-8") as f:
            json.dump(budget.model_dump(), f, ensure_ascii=False, indent=2)

    @staticmethod
    def load(sim_dir: Path) -> Optional[RevealBudget]:
        path = sim_dir / "reveal_budget.json"
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return RevealBudget.model_validate(json.load(f))
        except Exception:
            return None

    @staticmethod
    def _dedupe_text(values: List[str]) -> List[str]:
        result = []
        seen = set()
        for value in values:
            text = str(value or "").strip()
            if text and text not in seen:
                result.append(text)
                seen.add(text)
        return result

    def _dedupe_suspected(self, values: List[SuspectedOnly]) -> List[SuspectedOnly]:
        seen = set()
        result = []
        for item in values:
            if item.fact and item.fact not in seen:
                result.append(item)
                seen.add(item.fact)
        return result

    def _dedupe_forbidden(self, values: List[ForbiddenReveal]) -> List[ForbiddenReveal]:
        seen = set()
        result = []
        for item in values:
            if item.fact and item.fact not in seen:
                result.append(item)
                seen.add(item.fact)
        return result

    def _dedupe_payoffs(self, values: List[PayoffTarget]) -> List[PayoffTarget]:
        seen = set()
        result = []
        for item in values:
            if item.thread_id and item.thread_id not in seen:
                result.append(item)
                seen.add(item.thread_id)
        return result
