from __future__ import annotations

import uuid
from typing import Dict, List, Optional, Set

from app.models.interaction import (
    AgentReaction,
    InteractionProposal,
    NamingResolutionItem,
)
from app.models.state import FactExposureEntry, WorldState
from app.models.world import WorldConfig


class NamingResolution:
    """
    命名解析。
    处理 Agent 对敏感事实的公开称呼方式，避免直接暴露秘密。
    提供公开标签、已知事实、怀疑事实、委婉语、代号等多种称呼方式。
    不绑定任何固定剧情逻辑。
    """

    def __init__(self, world: WorldConfig):
        self.world = world
        self._euphemisms = [
            "that matter",
            "the incident",
            "what happened",
            "the situation",
            "the thing we discussed",
            "certain information",
            "the event",
            "the issue",
            "the subject",
            "the circumstances",
        ]
        self._code_names = [
            "Alpha",
            "Bravo",
            "Charlie",
            "Delta",
            "Echo",
            "Foxtrot",
        ]

    def resolve_names(
        self,
        proposal: InteractionProposal,
        reactions: List[AgentReaction],
        state: WorldState,
    ) -> List[NamingResolutionItem]:
        """
        为交互中涉及的事实解析合适的称呼方式。
        """
        items: List[NamingResolutionItem] = []
        all_agents = set(proposal.participants + proposal.observers)

        referenced_facts = self._collect_referenced_facts(proposal, reactions, state)

        for fact_id, entry in referenced_facts.items():
            for agent_id in all_agents:
                item = self._resolve_for_agent(
                    agent_id,
                    fact_id,
                    entry,
                    state,
                    all_agents,
                )
                if item:
                    items.append(item)

        self._mark_consensus(items, all_agents)

        return items

    def _collect_referenced_facts(
        self,
        proposal: InteractionProposal,
        reactions: List[AgentReaction],
        state: WorldState,
    ) -> Dict[str, FactExposureEntry]:
        facts: Dict[str, FactExposureEntry] = {}

        for intent in proposal.intents:
            for fid in intent.referenced_fact_ids or []:
                if fid in state.world.fact_exposure:
                    facts[fid] = state.world.fact_exposure[fid]

        for reaction in reactions:
            for fid in reaction.related_fact_ids:
                if fid in state.world.fact_exposure:
                    facts[fid] = state.world.fact_exposure[fid]

        if proposal.topic:
            for fid, entry in state.world.fact_exposure.items():
                if proposal.topic in entry.truth or fid in proposal.topic:
                    facts[fid] = entry

        return facts

    def _resolve_for_agent(
        self,
        agent_id: str,
        fact_id: str,
        entry: FactExposureEntry,
        state: WorldState,
        all_agents: Set[str],
    ) -> Optional[NamingResolutionItem]:
        known_by_agent = agent_id in entry.known_by
        known_by_all = all(aid in entry.known_by for aid in all_agents)
        suspected_by_agent = agent_id in entry.suspected_by
        is_sensitive = entry.min_pressure_to_reveal >= 2

        resolution_type: str = ""
        resolved_name: str = ""
        exposure_risk: str = "low"
        confidence = 1.0

        if known_by_all and not is_sensitive:
            resolution_type = "known_fact"
            resolved_name = entry.public_label or fact_id
            exposure_risk = "low"
        elif known_by_agent and not known_by_all:
            if is_sensitive:
                resolution_type = "euphemism"
                resolved_name = self._select_euphemism(fact_id)
                exposure_risk = "medium"
            else:
                resolution_type = "public_label"
                resolved_name = entry.public_label or fact_id
                exposure_risk = "low"
        elif suspected_by_agent:
            resolution_type = "suspected_fact"
            resolved_name = entry.public_label or fact_id
            exposure_risk = "medium"
            confidence = entry.suspected_by.get(agent_id, 0.5)
        elif is_sensitive:
            resolution_type = "avoided_topic"
            resolved_name = "that thing"
            exposure_risk = "high"
        else:
            resolution_type = "code_name"
            resolved_name = self._select_code_name(fact_id)
            exposure_risk = "medium"

        if not resolved_name:
            resolved_name = fact_id

        return NamingResolutionItem(
            reference_id=f"ref_{uuid.uuid4().hex[:8]}",
            agent_id=agent_id,
            original_reference=fact_id,
            resolved_name=resolved_name,
            resolution_type=resolution_type,
            confidence=confidence,
            exposure_risk=exposure_risk,
            is_consensus=False,
        )

    def _select_euphemism(self, fact_id: str) -> str:
        index = hash(fact_id) % len(self._euphemisms)
        return self._euphemisms[index]

    def _select_code_name(self, fact_id: str) -> str:
        index = hash(fact_id) % len(self._code_names)
        return self._code_names[index]

    def _mark_consensus(
        self,
        items: List[NamingResolutionItem],
        all_agents: Set[str],
    ) -> None:
        if not items:
            return

        fact_groups: Dict[str, List[NamingResolutionItem]] = {}
        for item in items:
            fact_groups.setdefault(item.original_reference, []).append(item)

        for fact_id, group in fact_groups.items():
            if len(group) >= len(all_agents):
                types = [i.resolution_type for i in group]
                if all(t == types[0] for t in types) and types[0] in ("known_fact", "public_label"):
                    for item in group:
                        item.is_consensus = True
