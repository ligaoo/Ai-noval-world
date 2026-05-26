from __future__ import annotations

from app.models.interaction import InteractionResult
from app.models.state import BeliefState, RelationshipRuntimeState, WorldState
from app.services.fact_exposure_matrix import FactExposureMatrix


class WorldStateUpdater:
    def __init__(self, fact_matrix: FactExposureMatrix):
        self.fact_matrix = fact_matrix

    def apply_interaction_result(self, state: WorldState, result: InteractionResult) -> None:
        self.fact_matrix.apply_interaction_result(state, result)
        suspicion_items = []
        if result.exposure_update:
            for item in result.exposure_update.suspected_facts:
                if item.get("status", "suspected") != "suspected":
                    continue
                label = str(item.get("label") or item.get("fact_id") or "")
                related_fact_id = str(item.get("fact_id") or "")
                for character_id in item.get("suspected_by", []):
                    suspicion_items.append((label, str(character_id), float(item.get("confidence", 0.5)), related_fact_id))
        else:
            for fact, suspected_by in result.suspected_facts.items():
                for character_id, confidence in suspected_by.items():
                    suspicion_items.append((fact, character_id, confidence, None))
        for fact, character_id, confidence, related_fact_id in suspicion_items:
            runtime = state.characters.get(character_id)
            if not runtime:
                continue
            if fact not in runtime.suspicions:
                runtime.suspicions.append(fact)
            if not any(b.content == fact for b in runtime.beliefs):
                runtime.beliefs.append(
                    BeliefState(
                        content=fact,
                        confidence=confidence,
                        source=result.interaction_id,
                        related_fact_id=related_fact_id,
                        updated_tick=state.tick,
                    )
                )
        for change in result.relationship_changes:
            from_id = change.get("from")
            to_id = change.get("to")
            if not from_id or not to_id or from_id not in state.characters:
                continue
            runtime = state.characters[from_id]
            relationship = runtime.relationships.setdefault(
                to_id,
                RelationshipRuntimeState(),
            )
            relationship.trust += int(change.get("trust_delta", 0))
            relationship.suspicion += int(change.get("suspicion_delta", 0))
            relationship.last_changed_tick = state.tick
            runtime.attitude_to[to_id] = relationship.trust - relationship.suspicion
        progress = int(result.plot_changes.get("progress_delta", 0))
        if progress > 0:
            state.chapter_goal_status.progress = min(
                100,
                state.chapter_goal_status.progress + progress,
            )
            if state.chapter_goal_status.progress >= 100:
                state.chapter_goal_status.completed = True
        for thread in result.plot_changes.get("opened_threads", []):
            if thread not in state.world.open_threads:
                state.world.open_threads.append(thread)
        if result.interaction_id not in state.world.interaction_history:
            state.world.interaction_history.append(result.interaction_id)
