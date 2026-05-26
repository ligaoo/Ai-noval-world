from __future__ import annotations

import uuid
from typing import List, Optional

from app.models.interaction import (
    AgentReaction,
    GroupDecisionOption,
    GroupDecisionResult,
    InteractionProposal,
)
from app.models.state import WorldState
from app.models.world import WorldConfig


class GroupDecisionFlow:
    """
    群体决策流程。
    收集各 Agent 的提议和态度，通过共识、多数或领导者方式形成决策。
    不绑定任何固定剧情逻辑。
    """

    def __init__(self, world: WorldConfig):
        self.world = world

    def resolve_group_decision(
        self,
        proposal: InteractionProposal,
        reactions: List[AgentReaction],
        state: WorldState,
    ) -> Optional[GroupDecisionResult]:
        """
        解析群体决策结果。
        仅当存在明确的决策话题和多个参与者时触发。
        """
        participants = proposal.participants
        if len(participants) < 2:
            return None

        topic = proposal.topic or self._infer_topic(proposal, reactions)
        if not topic:
            return None

        options = self._extract_options(proposal, reactions, state)
        if not options:
            return None

        self._tally_votes(options, participants, reactions, state)

        winning_id = self._determine_winner(options, state)

        decision_type = self._classify_decision_type(participants, state)

        unresolved = self._find_unresolved_tensions(reactions, state)

        return GroupDecisionResult(
            decision_id=f"decision_{uuid.uuid4().hex[:8]}",
            participants=list(participants),
            topic=topic,
            options=options,
            winning_option_id=winning_id,
            decision_type=decision_type,
            pressure_level=self._calculate_pressure_level(reactions),
            unresolved_tensions=unresolved,
            side_effect_relationship_changes=self._infer_relationship_side_effects(reactions, options),
        )

    def _extract_options(
        self,
        proposal: InteractionProposal,
        reactions: List[AgentReaction],
        state: WorldState,
    ) -> List[GroupDecisionOption]:
        options: List[GroupDecisionOption] = []

        for intent in proposal.intents:
            if intent.action_type in ("suggest", "call_out", "propose") or "proposal" in intent.intention.lower():
                option = GroupDecisionOption(
                    option_id=f"opt_{uuid.uuid4().hex[:8]}",
                    proposer=intent.agent_id,
                    proposal_text=intent.intention[:200],
                    related_fact_ids=list(intent.claimed_fact_ids or intent.referenced_fact_ids),
                )
                options.append(option)

        for reaction in reactions:
            if reaction.reaction_type in ("action_proposal", "suggest_alternative") and reaction.will_express:
                option = GroupDecisionOption(
                    option_id=f"opt_{uuid.uuid4().hex[:8]}",
                    proposer=reaction.agent_id,
                    proposal_text=reaction.spoken_text or reaction.reasoning[:200],
                    related_fact_ids=list(reaction.related_fact_ids),
                )
                options.append(option)

        if not options and proposal.intents:
            primary_intent = proposal.intents[0]
            option = GroupDecisionOption(
                option_id=f"opt_{uuid.uuid4().hex[:8]}",
                proposer=primary_intent.agent_id,
                proposal_text=f"Accept the proposal from {primary_intent.agent_id}",
            )
            options.append(option)

        return options[:5]

    def _tally_votes(
        self,
        options: List[GroupDecisionOption],
        participants: List[str],
        reactions: List[AgentReaction],
        state: WorldState,
    ) -> None:
        agent_reactions = {r.agent_id: r for r in reactions if r.agent_id in participants}

        for agent_id in participants:
            runtime = state.characters.get(agent_id)
            if not runtime:
                continue

            reaction = agent_reactions.get(agent_id)
            relations = runtime.relationships

            chosen_idx = self._agent_choose_option(agent_id, options, reaction, relations, state)
            chosen_option = options[chosen_idx] if 0 <= chosen_idx < len(options) else None

            if not reaction:
                if chosen_option:
                    chosen_option.abstainers.append(agent_id)
                continue

            if reaction.reaction_type in ("support", "agree"):
                if chosen_option:
                    chosen_option.supporters.append(agent_id)
            elif reaction.reaction_type in ("deny", "disagree", "challenge", "doubt"):
                if chosen_option and chosen_option.proposer != agent_id:
                    chosen_option.opposers.append(agent_id)
            elif reaction.reaction_type in ("suggest_alternative", "action_proposal"):
                if reaction.agent_id == chosen_option.proposer if chosen_option else False:
                    chosen_option.supporters.append(agent_id)
                elif chosen_option:
                    chosen_option.opposers.append(agent_id)
            elif chosen_option:
                chosen_option.abstainers.append(agent_id)

    def _agent_choose_option(
        self,
        agent_id: str,
        options: List[GroupDecisionOption],
        reaction: Optional[AgentReaction],
        relations: dict,
        state: WorldState,
    ) -> int:
        if not options:
            return -1

        if reaction and reaction.target_agent:
            for idx, opt in enumerate(options):
                if opt.proposer == reaction.target_agent:
                    if reaction.reaction_type in ("support", "agree"):
                        return idx
                    elif reaction.reaction_type in ("deny", "disagree", "challenge", "doubt"):
                        return (idx + 1) % len(options)

        for idx, opt in enumerate(options):
            rel = relations.get(opt.proposer)
            if rel and rel.trust > 3:
                return idx

        for idx, opt in enumerate(options):
            if opt.proposer == agent_id:
                return idx

        return 0

    def _determine_winner(
        self,
        options: List[GroupDecisionOption],
        state: WorldState,
    ) -> Optional[str]:
        if not options:
            return None

        scores = []
        for opt in options:
            support_score = len(opt.supporters) * 2
            oppose_score = len(opt.opposers)
            abstain_score = len(opt.abstainers) * 0.5

            proposer_runtime = state.characters.get(opt.proposer)
            if proposer_runtime:
                trust_sum = sum(
                    r.trust
                    for r in proposer_runtime.relationships.values()
                )
                support_score += max(0, trust_sum)

            total = support_score - oppose_score + abstain_score
            scores.append((opt.option_id, total))

        scores.sort(key=lambda x: -x[1])
        best_id, best_score = scores[0]

        if len(scores) > 1 and best_score == scores[1][1]:
            return None

        return best_id

    def _classify_decision_type(
        self,
        participants: List[str],
        state: WorldState,
    ) -> str:
        trust_scores = []
        for agent_id in participants:
            runtime = state.characters.get(agent_id)
            if runtime:
                for other_id in participants:
                    if other_id != agent_id:
                        rel = runtime.relationships.get(other_id)
                        if rel:
                            trust_scores.append(rel.trust)

        avg_trust = sum(trust_scores) / len(trust_scores) if trust_scores else 0

        if avg_trust > 3:
            return "consensus"
        if avg_trust < -2:
            return "deadlocked"
        return "majority"

    def _find_unresolved_tensions(
        self,
        reactions: List[AgentReaction],
        state: WorldState,
    ) -> List[str]:
        tensions = []
        for reaction in reactions:
            if reaction.reaction_type in ("challenge", "doubt", "deny", "accuse"):
                tensions.append(f"{reaction.agent_id} vs {reaction.target_agent or 'group'}: {reaction.reasoning[:50]}")
        return tensions[:5]

    def _calculate_pressure_level(self, reactions: List[AgentReaction]) -> int:
        return sum(r.pressure_delta for r in reactions)

    def _infer_relationship_side_effects(
        self,
        reactions: List[AgentReaction],
        options: List[GroupDecisionOption],
    ) -> List[dict]:
        changes = []
        for opt in options:
            for supporter in opt.supporters:
                for opposer in opt.opposers:
                    changes.append({
                        "source": supporter,
                        "target": opposer,
                        "relationship_impact": "suspicion_rise",
                        "delta": 1,
                        "cause": "Opposing views in group decision",
                    })
        return changes[:10]

    @staticmethod
    def _infer_topic(proposal: InteractionProposal, reactions: List[AgentReaction]) -> str:
        if proposal.topic:
            return proposal.topic
        for reaction in reactions:
            if reaction.target_fact:
                return reaction.target_fact
        return "general discussion"
