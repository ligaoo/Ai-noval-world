from __future__ import annotations

from app.models.interaction import InteractionResult
from app.models.state import WorldState
from app.models.world import WorldConfig
from app.services.fact_exposure_matrix import FactExposureMatrix


class DirectorRiskChecker:
    def __init__(self, world: WorldConfig, fact_matrix: FactExposureMatrix, plot_arc_service=None):
        self.world = world
        self.fact_matrix = fact_matrix
        self.plot_arc_service = plot_arc_service

    def check_and_correct(
        self,
        state: WorldState,
        result: InteractionResult,
    ) -> InteractionResult:
        blocked_truths: list[str] = []
        blocked_fact_ids: set[str] = set()
        allowed_reveals = []
        if result.exposure_update:
            allowed_exposure_reveals = []
            for item in result.exposure_update.revealed_facts:
                fact_id = str(item.get("fact_id") or "")
                if fact_id and not self.fact_matrix.can_reveal(fact_id, self.plot_arc_service):
                    blocked_fact_ids.add(fact_id)
                    entry = state.world.fact_exposure.get(fact_id)
                    label = entry.public_label or fact_id if entry else fact_id
                    if entry:
                        blocked_truths.append(entry.truth)
                    result.exposure_update.prevented_facts.append(
                        {
                            "fact_id": fact_id,
                            "label": label,
                            "status": "prevented",
                            "source": item.get("source") or "director_risk_correction",
                        }
                    )
                    result.exposure_update.suspected_facts.append(
                        {
                            "fact_id": fact_id,
                            "label": label,
                            "status": "suspected",
                            "suspected_by": list(result.visible_to),
                            "confidence": 0.4,
                            "source": "director_risk_correction",
                        }
                    )
                else:
                    allowed_exposure_reveals.append(item)
            result.exposure_update.revealed_facts = allowed_exposure_reveals
        for fact in result.revealed_facts:
            fact_id = self.fact_matrix._find_fact_id(state, fact)
            if fact_id and (fact_id in blocked_fact_ids or not self.fact_matrix.can_reveal(fact_id, self.plot_arc_service)):
                blocked_fact_ids.add(fact_id)
                blocked_truths.append(fact)
            else:
                allowed_reveals.append(fact)
        if blocked_fact_ids:
            result.revealed_facts = allowed_reveals
            for fact_id in blocked_fact_ids:
                entry = state.world.fact_exposure.get(fact_id)
                label = entry.public_label or fact_id if entry else fact_id
                result.suspected_facts.setdefault(label, {})
                for character_id in result.visible_to:
                    result.suspected_facts[label][character_id] = max(
                        0.4,
                        result.suspected_facts[label].get(character_id, 0.0),
                    )
            self._downgrade_spoken_text(result, state, blocked_fact_ids, blocked_truths)
            result.director_intervention = {
                "type": "downgrade_premature_reveal",
                "blocked_count": len(blocked_fact_ids),
                "intent_source": "director_intervention",
                "boundary": "risk_correction_only",
            }
        return result

    def _downgrade_spoken_text(
        self,
        result: InteractionResult,
        state: WorldState,
        blocked_fact_ids: set[str],
        blocked_truths: list[str],
    ) -> None:
        replacements = {
            fact_id: self._public_label(state, fact_id)
            for fact_id in blocked_fact_ids
        }
        for segment in result.spoken_segments:
            if not blocked_fact_ids.intersection(segment.exposes_fact_ids):
                continue
            label = self._public_label(state, segment.exposes_fact_ids[0])
            segment.exposes_fact_ids = [fact_id for fact_id in segment.exposes_fact_ids if fact_id not in blocked_fact_ids]
            segment.spoken_text = self._safe_text(segment.spoken_text, blocked_truths, replacements, label)
            segment.content_summary = self._safe_text(segment.content_summary, blocked_truths, replacements, label)
            segment.exposure_level = "safe"
        for round_item in result.rounds:
            round_item.says_summary = self._safe_text(round_item.says_summary, blocked_truths, replacements, "something withheld")

    @staticmethod
    def _public_label(state: WorldState, fact_id: str) -> str:
        entry = state.world.fact_exposure.get(fact_id)
        return entry.public_label or fact_id if entry else fact_id

    @staticmethod
    def _safe_text(text: str, blocked_truths: list[str], replacements: dict[str, str], fallback: str) -> str:
        if not text:
            return text
        safe = text
        changed = False
        for truth in blocked_truths:
            if truth and truth in safe:
                safe = safe.replace(truth, fallback)
                changed = True
        for fact_id, label in replacements.items():
            if fact_id in safe:
                safe = safe.replace(fact_id, label)
                changed = True
        return safe if changed else text
