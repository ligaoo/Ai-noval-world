from __future__ import annotations

import uuid
from typing import List

from app.models.interaction import (
    AgentReaction,
    GroupDecisionResult,
    InteractionProposal,
    PrivateTendencyTrigger,
    RelationshipImpactUpdate,
)
from app.models.state import WorldState
from app.models.world import WorldConfig


class RelationshipImpactEvaluator:
    """
    关系影响评估器。
    根据 Agent 的反应、决策、私人倾向，计算关系的信任、怀疑、敌意、亲和度变化。
    不绑定任何固定剧情逻辑。
    """

    def __init__(self, world: WorldConfig):
        self.world = world

    def evaluate_impacts(
        self,
        proposal: InteractionProposal,
        reactions: List[AgentReaction],
        triggers: List[PrivateTendencyTrigger],
        group_decision: GroupDecisionResult | None,
        state: WorldState,
    ) -> List[RelationshipImpactUpdate]:
        """
        评估所有关系影响。
        """
        updates: List[RelationshipImpactUpdate] = []

        updates.extend(self._evaluate_reaction_impacts(reactions, state))

        if group_decision:
            updates.extend(self._evaluate_group_decision_impacts(group_decision, state))

        updates.extend(self._evaluate_trigger_impacts(triggers, state))

        updates.extend(self._evaluate_witness_effects(updates, proposal, state))
        updates.extend(self._ensure_clue_discovery_relationship_update(proposal, reactions, updates))

        return updates

    def _evaluate_reaction_impacts(
        self,
        reactions: List[AgentReaction],
        state: WorldState,
    ) -> List[RelationshipImpactUpdate]:
        updates: List[RelationshipImpactUpdate] = []

        for reaction in reactions:
            if not reaction.target_agent:
                continue

            source = reaction.agent_id
            target = reaction.target_agent

            impact = self._reaction_to_impact(reaction, source, target, state)
            if impact:
                updates.append(impact)

        return updates

    def _reaction_to_impact(
        self,
        reaction: AgentReaction,
        source: str,
        target: str,
        state: WorldState,
    ) -> RelationshipImpactUpdate | None:
        impact_type, delta = self._classify_reaction_impact(reaction)
        if not impact_type or delta == 0:
            return None

        evidence_strength = reaction.confidence

        witnessed_by = [
            r.agent_id
            for r in reaction.related_fact_ids
            if r != source and r != target
        ] if reaction.related_fact_ids else []

        return RelationshipImpactUpdate(
            impact_id=f"impact_{uuid.uuid4().hex[:8]}",
            source_agent=source,
            target_agent=target,
            impact_type=impact_type,
            delta_value=delta,
            cause=reaction.reasoning or f"{reaction.reaction_type} reaction",
            evidence_strength=evidence_strength,
            is_public=reaction.will_express,
            witnessed_by=witnessed_by,
            related_reaction_id=reaction.reaction_id,
        )

    def _classify_reaction_impact(self, reaction: AgentReaction) -> tuple[str | None, int]:
        impact_map = {
            "support": ("trust_gain", 2),
            "agree": ("trust_gain", 1),
            "protect": ("affinity_gain", 2),
            "challenge": ("hostility_rise", 1),
            "doubt": ("suspicion_rise", 1),
            "accuse": ("suspicion_rise", 3),
            "deny": ("suspicion_rise", 1),
            "disagree": ("trust_loss", 1),
            "deflect": ("trust_loss", 1),
            "withhold": ("suspicion_rise", 1),
            "request_share": ("trust_gain", 1),
        }
        return impact_map.get(reaction.reaction_type, (None, 0))

    def _evaluate_group_decision_impacts(
        self,
        group_decision: GroupDecisionResult,
        state: WorldState,
    ) -> List[RelationshipImpactUpdate]:
        updates: List[RelationshipImpactUpdate] = []

        for opt in group_decision.options:
            for supporter in opt.supporters:
                for other_supporter in opt.supporters:
                    if supporter != other_supporter:
                        update = RelationshipImpactUpdate(
                            impact_id=f"impact_{uuid.uuid4().hex[:8]}",
                            source_agent=supporter,
                            target_agent=other_supporter,
                            impact_type="affinity_gain",
                            delta_value=1,
                            cause=f"Aligned on decision option",
                            evidence_strength=0.5,
                            is_public=True,
                        )
                        updates.append(update)

            for supporter in opt.supporters:
                for opposer in opt.opposers:
                    update = RelationshipImpactUpdate(
                        impact_id=f"impact_{uuid.uuid4().hex[:8]}",
                        source_agent=supporter,
                        target_agent=opposer,
                        impact_type="suspicion_rise",
                        delta_value=1,
                        cause=f"Opposing views on decision",
                        evidence_strength=0.5,
                        is_public=True,
                    )
                    updates.append(update)

        if group_decision.winning_option_id:
            winner_opt = next(
                (o for o in group_decision.options if o.option_id == group_decision.winning_option_id),
                None,
            )
            if winner_opt:
                for supporter in winner_opt.supporters:
                    update = RelationshipImpactUpdate(
                        impact_id=f"impact_{uuid.uuid4().hex[:8]}",
                        source_agent=winner_opt.proposer,
                        target_agent=supporter,
                        impact_type="respect_gained",
                        delta_value=1,
                        cause="Supported the winning proposal",
                        evidence_strength=0.6,
                        is_public=True,
                    )
                    updates.append(update)

        return updates

    def _evaluate_trigger_impacts(
        self,
        triggers: List[PrivateTendencyTrigger],
        state: WorldState,
    ) -> List[RelationshipImpactUpdate]:
        updates: List[RelationshipImpactUpdate] = []

        for trigger in triggers:
            if trigger.trigger_type == "loyalty_override":
                pass
            elif trigger.trigger_type == "personal_grudge":
                pass

        return updates

    def _ensure_clue_discovery_relationship_update(
        self,
        proposal: InteractionProposal,
        reactions: List[AgentReaction],
        current_updates: List[RelationshipImpactUpdate],
    ) -> List[RelationshipImpactUpdate]:
        if not self._is_clue_discovery(proposal, reactions):
            return []
        if any(update.impact_type in {"trust_gain", "trust_loss", "suspicion_rise", "suspicion_fall"} for update in current_updates):
            return []
        discoverer = proposal.participants[0] if proposal.participants else ""
        source = next((agent_id for agent_id in proposal.observers + proposal.participants if agent_id != discoverer), "")
        if not source or not discoverer:
            return []
        return [
            RelationshipImpactUpdate(
                impact_id=f"impact_{uuid.uuid4().hex[:8]}",
                source_agent=source,
                target_agent=discoverer,
                impact_type="suspicion_rise",
                delta_value=1,
                cause="key clue discovered / clue discovery changed relationship stance",
                evidence_strength=0.5,
                is_public=False,
                witnessed_by=[agent_id for agent_id in proposal.observers if agent_id != source],
            )
        ]

    @staticmethod
    def _is_clue_discovery(proposal: InteractionProposal, reactions: List[AgentReaction]) -> bool:
        text = " ".join(
            value
            for value in [proposal.topic or "", str(proposal.primary_conflict or "")]
            if value
        ).lower()
        if any(keyword in text for keyword in ["clue", "discover", "found", "线索", "发现"]):
            return True
        return any(reaction.trigger_event_type == "clue_discovered" for reaction in reactions)

    def _evaluate_witness_effects(
        self,
        current_updates: List[RelationshipImpactUpdate],
        proposal: InteractionProposal,
        state: WorldState,
    ) -> List[RelationshipImpactUpdate]:
        updates: List[RelationshipImpactUpdate] = []

        for update in current_updates:
            if not update.is_public:
                continue
            for witness in proposal.observers:
                if witness == update.source_agent or witness == update.target_agent:
                    continue

                witness_runtime = state.characters.get(witness)
                if not witness_runtime:
                    continue

                if "hostility" in update.impact_type or "suspicion" in update.impact_type:
                    to_source = witness_runtime.relationships.get(update.source_agent)
                    if to_source and to_source.trust < 0:
                        side_update = RelationshipImpactUpdate(
                            impact_id=f"impact_{uuid.uuid4().hex[:8]}",
                            source_agent=witness,
                            target_agent=update.source_agent,
                            impact_type="suspicion_rise",
                            delta_value=1,
                            cause=f"Witnessed hostile behavior",
                            evidence_strength=0.7,
                            is_public=False,
                        )
                        updates.append(side_update)

        return updates
