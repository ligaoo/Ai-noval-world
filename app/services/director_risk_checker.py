from __future__ import annotations

from typing import Optional

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
        blocked = []
        allowed_reveals = []
        for fact in result.revealed_facts:
            fact_id = self.fact_matrix._find_fact_id(state, fact)
            if fact_id and not self.fact_matrix.can_reveal(fact_id, self.plot_arc_service):
                blocked.append(fact)
            else:
                allowed_reveals.append(fact)
        if blocked:
            result.revealed_facts = allowed_reveals
            for fact in blocked:
                result.suspected_facts.setdefault(fact, {})
                for character_id in result.visible_to:
                    result.suspected_facts[fact][character_id] = max(
                        0.4,
                        result.suspected_facts[fact].get(character_id, 0.0),
                    )
            result.director_intervention = {
                "type": "downgrade_premature_reveal",
                "blocked_count": len(blocked),
            }
        return result
