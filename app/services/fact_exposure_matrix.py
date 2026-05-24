from __future__ import annotations

from typing import List, Optional

from app.models.interaction import InteractionResult
from app.models.state import FactExposureEntry, WorldState
from app.models.world import WorldConfig


class FactExposureMatrix:
    def __init__(self, world: WorldConfig):
        self.world = world

    def initialize_if_missing(self, state: WorldState) -> None:
        if state.world.fact_exposure:
            return
        for clue in self.world.clues.clues:
            state.world.fact_exposure[clue.id] = FactExposureEntry(
                fact_id=clue.id,
                truth=clue.content,
                known_by=[
                    cid
                    for cid, runtime in state.characters.items()
                    if clue.content in runtime.known_facts or clue.id in runtime.known_facts
                ],
                source="clue",
                reveal_stage=clue.truth_level,
                created_tick=state.tick,
            )
        for character in self.world.characters.characters:
            for idx, secret in enumerate(character.secrets):
                fact_id = f"{character.id}_secret_{idx + 1}"
                state.world.fact_exposure.setdefault(
                    fact_id,
                    FactExposureEntry(
                        fact_id=fact_id,
                        truth=secret,
                        known_by=[character.id],
                        source="character_secret",
                        reveal_stage="hidden_fact",
                        created_tick=state.tick,
                    ),
                )

    def mark_known(
        self,
        state: WorldState,
        fact_id: str,
        character_id: str,
        source: str = "",
        truth: Optional[str] = None,
    ) -> None:
        entry = self._entry_for(state, fact_id, truth or fact_id, source)
        if character_id not in entry.known_by:
            entry.known_by.append(character_id)
        runtime = state.characters.get(character_id)
        if runtime and entry.truth not in runtime.known_facts:
            runtime.known_facts.append(entry.truth)

    def mark_suspected(
        self,
        state: WorldState,
        fact: str,
        character_id: str,
        confidence: float = 0.5,
        source: str = "",
    ) -> None:
        fact_id = self._find_fact_id(state, fact) or self._synthetic_fact_id(fact)
        entry = self._entry_for(state, fact_id, fact, source)
        entry.suspected_by[character_id] = max(
            confidence, entry.suspected_by.get(character_id, 0.0)
        )
        runtime = state.characters.get(character_id)
        if runtime and fact not in runtime.suspicions:
            runtime.suspicions.append(fact)

    def allowed_facts_for(self, state: WorldState, character_id: str) -> List[str]:
        return [
            entry.truth
            for entry in state.world.fact_exposure.values()
            if character_id in entry.known_by
        ]

    def forbidden_facts_for(self, state: WorldState, character_id: str) -> List[str]:
        return [
            entry.truth
            for entry in state.world.fact_exposure.values()
            if character_id not in entry.known_by
        ]

    def can_reveal(self, fact_id: str, plot_arc_service=None) -> bool:
        if plot_arc_service is None:
            return True
        try:
            clue = self.world.clues.get_clue(fact_id)
        except KeyError:
            return True
        return bool(plot_arc_service.can_discover_clue(clue.model_dump()))

    def apply_interaction_result(self, state: WorldState, result: InteractionResult) -> None:
        for fact in result.revealed_facts:
            fact_id = self._find_fact_id(state, fact) or self._synthetic_fact_id(fact)
            for character_id in result.visible_to:
                self.mark_known(state, fact_id, character_id, "interaction", fact)
        for fact, suspected_by in result.suspected_facts.items():
            for character_id, confidence in suspected_by.items():
                self.mark_suspected(state, fact, character_id, confidence, "interaction")

    def _entry_for(
        self, state: WorldState, fact_id: str, truth: str, source: str
    ) -> FactExposureEntry:
        if fact_id not in state.world.fact_exposure:
            state.world.fact_exposure[fact_id] = FactExposureEntry(
                fact_id=fact_id,
                truth=truth,
                source=source,
                created_tick=state.tick,
            )
        return state.world.fact_exposure[fact_id]

    @staticmethod
    def _find_fact_id(state: WorldState, fact: str) -> Optional[str]:
        for fact_id, entry in state.world.fact_exposure.items():
            if fact == fact_id or fact == entry.truth:
                return fact_id
        return None

    @staticmethod
    def _synthetic_fact_id(fact: str) -> str:
        return "fact_" + str(abs(hash(fact)))
