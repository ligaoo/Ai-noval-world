from __future__ import annotations

from typing import Dict, List

from app.models.interaction import (
    InteractionProposal,
    InteractionResult,
    InteractionRound,
    ScenePresence,
)
from app.models.state import WorldState
from app.services.fact_exposure_matrix import FactExposureMatrix
from app.services.perception_resolver import PerceptionResolver


class MultiRoundInteractionResolver:
    def __init__(
        self,
        fact_matrix: FactExposureMatrix,
        perception_resolver: PerceptionResolver,
        max_rounds: int = 5,
    ):
        self.fact_matrix = fact_matrix
        self.perception_resolver = perception_resolver
        self.max_rounds = max_rounds

    def resolve(
        self,
        state: WorldState,
        scene: ScenePresence,
        proposal: InteractionProposal,
    ) -> InteractionResult:
        rounds: List[InteractionRound] = []
        revealed: List[str] = []
        still_hidden: List[str] = []
        suspected: Dict[str, Dict[str, float]] = {}
        relationship_changes: List[dict] = []
        pressure = max((intent.pressure_level for intent in proposal.intents), default=0)
        visible_to = sorted(set(proposal.participants + proposal.observers))

        for idx, intent in enumerate(proposal.intents[: self.max_rounds], start=1):
            says = self._safe_say(state, intent.agent_id, intent.will_say)
            hidden = list(intent.will_hide)
            if intent.action_type in {"share_info", "answer"}:
                revealed.extend(says)
            elif intent.action_type in {"withhold", "lie", "refuse"}:
                revealed.extend(says[:1])
                still_hidden.extend(hidden)
                pressure += 1
            elif intent.action_type in {"ask", "challenge", "accuse"}:
                pressure += max(1, intent.pressure_level)

            observers = [cid for cid in visible_to if cid != intent.agent_id]
            notices = self.perception_resolver.resolve_notices(
                state,
                scene,
                intent,
                observers,
                proposal.interaction_id,
                pressure,
            )
            for notice in notices:
                for fact, confidence in notice.suspected_facts.items():
                    suspected.setdefault(fact, {})[notice.observer] = confidence
                for target_id, delta in notice.relationship_deltas.items():
                    relationship_changes.append(
                        {
                            "from": notice.observer,
                            "to": target_id,
                            "trust_delta": delta,
                            "suspicion_delta": abs(delta),
                        }
                    )
            rounds.append(
                InteractionRound(
                    round=idx,
                    speaker=intent.agent_id,
                    action=intent.action_type,
                    says_summary="; ".join(says),
                    hides=hidden,
                    pressure_level=pressure,
                    notices=notices,
                )
            )
            if idx >= self.max_rounds:
                break

        revealed = self._dedupe(revealed)
        still_hidden = self._dedupe(still_hidden)
        revealed = [fact for fact in revealed if fact not in still_hidden]
        agent_goal_results = self._goal_results(proposal, revealed, still_hidden, suspected)
        return InteractionResult(
            interaction_id=proposal.interaction_id,
            interaction_type=proposal.interaction_type,
            scene_id=proposal.scene_id,
            location_id=proposal.location_id,
            participants=proposal.participants,
            observers=proposal.observers,
            topic=proposal.topic,
            rounds=rounds,
            agent_goal_results=agent_goal_results,
            revealed_facts=revealed,
            still_hidden_facts=still_hidden,
            suspected_facts=suspected,
            relationship_changes=relationship_changes,
            plot_changes={
                "progress_delta": min(6, len(revealed) + len(suspected) + len(rounds)),
                "opened_threads": [],
            },
            visible_to=visible_to,
            hidden_effects=still_hidden,
        )

    def _safe_say(self, state: WorldState, agent_id: str, facts: List[str]) -> List[str]:
        allowed = set(self.fact_matrix.allowed_facts_for(state, agent_id))
        return [fact for fact in facts if fact in allowed]

    @staticmethod
    def _dedupe(values: List[str]) -> List[str]:
        result: List[str] = []
        for value in values:
            if value and value not in result:
                result.append(value)
        return result

    @staticmethod
    def _goal_results(
        proposal: InteractionProposal,
        revealed: List[str],
        still_hidden: List[str],
        suspected: Dict[str, Dict[str, float]],
    ) -> Dict[str, Dict[str, str]]:
        results: Dict[str, Dict[str, str]] = {}
        for intent in proposal.intents:
            if intent.action_type in {"withhold", "lie", "refuse"}:
                results[intent.agent_id] = {
                    "preserve_hidden_information": "success" if still_hidden else "failed",
                    "avoid_suspicion": "failed" if suspected else "success",
                }
            elif intent.action_type in {"ask", "challenge", "accuse"}:
                results[intent.agent_id] = {
                    "increase_pressure": "success",
                    "get_confirmed_information": "success" if revealed else "failed",
                }
            else:
                results[intent.agent_id] = {"perform_intent": "success"}
        return results
