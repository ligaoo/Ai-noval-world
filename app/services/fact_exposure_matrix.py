from __future__ import annotations

import hashlib
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
                public_label=clue.name or clue.id,
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
                        public_label=f"{character.id}_private_information_{idx + 1}",
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
        entry.revealed_tick = state.tick
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

    def mark_misunderstood(
        self,
        state: WorldState,
        fact: str,
        character_id: str,
        misunderstanding: str = "misdirected_claim",
        source: str = "",
    ) -> None:
        fact_id = self._find_fact_id(state, fact) or self._synthetic_fact_id(fact)
        entry = self._entry_for(state, fact_id, fact, source)
        entry.misunderstood_by[character_id] = misunderstanding or "misdirected_claim"
        runtime = state.characters.get(character_id)
        if runtime and misunderstanding and misunderstanding not in runtime.suspicions:
            runtime.suspicions.append(misunderstanding)

    def allowed_fact_ids_for(self, state: WorldState, character_id: str) -> List[str]:
        return [
            entry.fact_id
            for entry in state.world.fact_exposure.values()
            if character_id in entry.known_by
        ]

    def allowed_facts_for(self, state: WorldState, character_id: str) -> List[str]:
        return [
            entry.truth
            for entry in state.world.fact_exposure.values()
            if character_id in entry.known_by
        ]

    def forbidden_fact_ids_for(self, state: WorldState, character_id: str) -> List[str]:
        return [
            entry.fact_id
            for entry in state.world.fact_exposure.values()
            if character_id not in entry.known_by
        ]

    def forbidden_fact_labels_for(self, state: WorldState, character_id: str) -> List[str]:
        return [
            entry.public_label or entry.fact_id
            for entry in state.world.fact_exposure.values()
            if character_id not in entry.known_by
        ]

    def forbidden_facts_for(self, state: WorldState, character_id: str) -> List[str]:
        return self.forbidden_fact_labels_for(state, character_id)

    def can_reveal(self, fact_id: str, plot_arc_service=None) -> bool:
        if plot_arc_service is None:
            return True
        try:
            clue = self.world.clues.get_clue(fact_id)
        except KeyError:
            return True
        return bool(plot_arc_service.can_discover_clue(clue.model_dump()))

    def apply_interaction_result(self, state: WorldState, result: InteractionResult) -> None:
        if result.exposure_update:
            for item in result.exposure_update.revealed_facts:
                fact_id = str(item.get("fact_id") or "")
                if not fact_id:
                    continue
                entry = state.world.fact_exposure.get(fact_id)
                truth = entry.truth if entry else fact_id
                for character_id in item.get("known_by", []):
                    self.mark_known(state, fact_id, str(character_id), str(item.get("source") or "interaction"), truth)
            for item in result.exposure_update.suspected_facts:
                if item.get("status", "suspected") != "suspected":
                    continue
                fact_id = str(item.get("fact_id") or item.get("label") or "")
                if not fact_id:
                    continue
                entry = state.world.fact_exposure.get(fact_id)
                label = str(item.get("label") or (entry.public_label if entry else fact_id))
                confidence = float(item.get("confidence", 0.5))
                for character_id in item.get("suspected_by", []):
                    self.mark_suspected(state, label, str(character_id), confidence, str(item.get("source") or "interaction"))
        else:
            for fact in result.revealed_facts:
                fact_id = self._find_fact_id(state, fact) or self._synthetic_fact_id(fact)
                entry = state.world.fact_exposure.get(fact_id)
                truth = entry.truth if entry else fact
                for character_id in result.visible_to:
                    self.mark_known(state, fact_id, character_id, "interaction", truth)
            for fact, suspected_by in result.suspected_facts.items():
                for character_id, confidence in suspected_by.items():
                    self.mark_suspected(state, fact, character_id, confidence, "interaction")
        for change in result.state_changes:
            if change.get("type") != "misunderstood_fact":
                continue
            fact = str(change.get("fact") or change.get("fact_id") or "")
            character_id = str(change.get("character_id") or "")
            if fact and character_id:
                self.mark_misunderstood(
                    state,
                    fact,
                    character_id,
                    str(change.get("misunderstanding") or "misdirected_claim"),
                    "interaction",
                )

    def _entry_for(
        self, state: WorldState, fact_id: str, truth: str, source: str
    ) -> FactExposureEntry:
        if fact_id not in state.world.fact_exposure:
            state.world.fact_exposure[fact_id] = FactExposureEntry(
                fact_id=fact_id,
                truth=truth,
                source=source,
                created_tick=state.tick,
                public_label=fact_id,
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
        digest = hashlib.sha256(fact.encode("utf-8")).hexdigest()[:16]
        return f"fact_{digest}"
