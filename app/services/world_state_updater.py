from __future__ import annotations

from app.models.interaction import InteractionResult
from app.models.state import BeliefState, RelationshipRuntimeState, WorldState
from app.services.fact_exposure_matrix import FactExposureMatrix


class WorldStateUpdater:
    def __init__(self, fact_matrix: FactExposureMatrix):
        self.fact_matrix = fact_matrix

    @staticmethod
    def _clamp(value: int, lower: int = -10, upper: int = 10) -> int:
        return max(lower, min(upper, value))

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
            deltas = {
                "trust": int(change.get("trust_delta", 0)),
                "suspicion": int(change.get("suspicion_delta", 0)),
                "hostility": int(change.get("hostility_delta", 0)),
                "affinity": int(change.get("affinity_delta", 0)),
            }
            if not any(deltas.values()):
                continue
            relationship.trust = self._clamp(relationship.trust + deltas["trust"])
            relationship.suspicion = self._clamp(relationship.suspicion + deltas["suspicion"])
            relationship.hostility = self._clamp(relationship.hostility + deltas["hostility"])
            relationship.affinity = self._clamp(relationship.affinity + deltas["affinity"])
            relationship.last_changed_tick = state.tick
            relationship.last_cause = str(change.get("cause") or change.get("impact_type") or "")
            evidence = str(change.get("evidence") or change.get("impact_type") or "")
            if evidence and evidence not in relationship.evidence:
                relationship.evidence.append(evidence)
            runtime.attitude_to[to_id] = (
                relationship.trust
                + relationship.affinity
                - relationship.suspicion
                - relationship.hostility
            )
        self._apply_agent_goal_results(state, result)
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

    def _apply_agent_goal_results(self, state: WorldState, result: InteractionResult) -> None:
        for agent_id, goal_result in result.agent_goal_results.items():
            runtime = state.characters.get(agent_id)
            if not runtime or not runtime.goals:
                continue
            active_goals = [goal for goal in runtime.goals.values() if goal.status == "active"]
            if not active_goals:
                continue
            goal = sorted(active_goals, key=lambda item: item.priority, reverse=True)[0]
            status = str(goal_result.get("status") or goal_result.get("result") or "").lower()
            if status in {"blocked", "advanced", "completed", "abandoned"}:
                goal.status = status
            elif goal_result.get("blocked_by") or goal_result.get("blocker"):
                goal.status = "blocked"
            else:
                goal.status = "advanced"
            progress_delta = int(goal_result.get("progress_delta", goal_result.get("progress", 10 if goal.status == "advanced" else 0)) or 0)
            if goal.status == "completed":
                goal.progress = 100
            elif progress_delta:
                goal.progress = self._clamp(goal.progress + progress_delta, 0, 100)
            blocker = str(goal_result.get("blocked_by") or goal_result.get("blocker") or "")
            if blocker and blocker not in goal.blockers:
                goal.blockers.append(blocker)
            for fact_id in goal_result.get("related_fact_ids", []) or []:
                fact_id = str(fact_id)
                if fact_id and fact_id not in goal.related_fact_ids:
                    goal.related_fact_ids.append(fact_id)
            for target_id in goal_result.get("related_agent_ids", []) or []:
                target_id = str(target_id)
                if target_id and target_id not in goal.related_agent_ids:
                    goal.related_agent_ids.append(target_id)
            goal.last_updated_tick = state.tick
            for fact_id in result.still_hidden_facts:
                runtime.stance.setdefault(fact_id, "wants_to_verify")
            if result.exposure_update:
                for item in result.exposure_update.suspected_facts:
                    fact_id = str(item.get("fact_id") or item.get("label") or "")
                    if fact_id:
                        runtime.stance.setdefault(fact_id, "wants_to_verify")
