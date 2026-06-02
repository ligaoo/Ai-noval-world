from __future__ import annotations

from typing import Optional

from app.models.interaction import (
    AgentDrivenInteractionResult,
    InteractionEvent,
    InteractionProposal,
    InteractionResult,
    RelationshipImpactUpdate,
)
from app.models.state import WorldState
from app.models.world import WorldConfig
from app.services.agent_reaction_check import AgentReactionCheck
from app.services.group_decision_flow import GroupDecisionFlow
from app.services.naming_resolution import NamingResolution
from app.services.private_tendency_trigger_check import PrivateTendencyTriggerCheck
from app.services.relationship_impact_evaluator import RelationshipImpactEvaluator


class AgentDrivenOrchestrator:
    """
    Agent 驱动交互的编排器。
    整合所有 Agent 驱动模块：
    - AgentReactionCheck (生成反应)
    - PrivateTendencyTriggerCheck (私人倾向修正)
    - GroupDecisionFlow (群体决策)
    - RelationshipImpactEvaluator (关系影响评估)
    - NamingResolution (命名解析)

    严格遵守 Writer 边界：
    Writer 只能消费结构化结果，不得自行决定谁反对、怀疑、打断、失去信任、隐瞒信息或变得害怕。

    不绑定任何固定剧情逻辑。
    """

    def __init__(self, world: WorldConfig):
        self.agent_reaction_check = AgentReactionCheck(world)
        self.group_decision_flow = GroupDecisionFlow(world)
        self.private_tendency_check = PrivateTendencyTriggerCheck(world)
        self.relationship_evaluator = RelationshipImpactEvaluator(world)
        self.naming_resolution = NamingResolution(world)

    def process_interaction(
        self,
        proposal: InteractionProposal,
        state: WorldState,
    ) -> AgentDrivenInteractionResult:
        """
        处理一次交互，生成完整的 Agent 驱动结构化结果。
        这是唯一应该被 Writer 消费的结构化数据。
        """
        trigger = self._detect_trigger(proposal)

        reactions = self.agent_reaction_check.generate_reactions_for_interaction(
            proposal,
            state,
            trigger,
        )

        triggers = self.private_tendency_check.check_triggers(
            proposal,
            reactions,
            state,
        )

        group_decision = self.group_decision_flow.resolve_group_decision(
            proposal,
            reactions,
            state,
        )

        relationship_updates = self.relationship_evaluator.evaluate_impacts(
            proposal,
            reactions,
            triggers,
            group_decision,
            state,
        )

        naming_resolution = self.naming_resolution.resolve_names(
            proposal,
            reactions,
            state,
        )

        active_agent_count = len(set(proposal.participants + proposal.observers))

        result = AgentDrivenInteractionResult(
            source_interaction_id=proposal.interaction_id,
            agent_reactions=reactions,
            group_decision=group_decision,
            private_tendency_triggers=triggers,
            relationship_updates=relationship_updates,
            naming_resolution=naming_resolution,
            interaction_events=self._build_interaction_events(
                proposal,
                reactions,
                group_decision,
                triggers,
                relationship_updates,
            ),
        )
        result.calculate_debug_metrics(active_agent_count)

        return result

    def apply_structured_results_to_interaction(
        self,
        agent_result: AgentDrivenInteractionResult,
        interaction: InteractionResult,
    ) -> None:
        """
        将结构化结果应用到 InteractionResult 中。
        这保证了 Writer 只能消费上游生成的结构化决策，而不能自行决定冲突。
        """
        interaction.relationship_impact_candidates.extend(agent_result.relationship_updates)
        interaction.naming_resolution.extend(agent_result.naming_resolution)
        interaction.agent_reactions.extend(agent_result.agent_reactions)
        interaction.group_decision = agent_result.group_decision
        interaction.private_tendency_triggers.extend(agent_result.private_tendency_triggers)
        interaction.interaction_events.extend(agent_result.interaction_events)
        interaction.agent_debug_metrics.update(agent_result.debug_metrics)
        interaction.relationship_changes.extend(
            change
            for update in agent_result.relationship_updates
            if (change := self._relationship_update_to_change(update)) is not None
        )

    @staticmethod
    def _relationship_update_to_change(update: RelationshipImpactUpdate) -> dict | None:
        trust_delta = 0
        suspicion_delta = 0
        hostility_delta = 0
        affinity_delta = 0
        if update.impact_type == "trust_gain":
            trust_delta = abs(update.delta_value)
        elif update.impact_type == "trust_loss":
            trust_delta = -abs(update.delta_value)
        elif update.impact_type == "suspicion_rise":
            suspicion_delta = abs(update.delta_value)
        elif update.impact_type == "suspicion_fall":
            suspicion_delta = -abs(update.delta_value)
        elif update.impact_type == "hostility_rise":
            hostility_delta = abs(update.delta_value)
        elif update.impact_type == "hostility_fall":
            hostility_delta = -abs(update.delta_value)
        elif update.impact_type == "affinity_gain":
            affinity_delta = abs(update.delta_value)
        elif update.impact_type == "affinity_loss":
            affinity_delta = -abs(update.delta_value)
        elif update.impact_type == "respect_gained":
            trust_delta = abs(update.delta_value)
        elif update.impact_type == "respect_lost":
            trust_delta = -abs(update.delta_value)
        else:
            return None
        return {
            "from": update.source_agent,
            "to": update.target_agent,
            "trust_delta": trust_delta,
            "suspicion_delta": suspicion_delta,
            "hostility_delta": hostility_delta,
            "affinity_delta": affinity_delta,
            "cause": update.cause,
            "impact_type": update.impact_type,
        }

    def _detect_trigger(self, proposal: InteractionProposal) -> str:
        """
        检测交互的触发类型。
        不绑定任何固定剧情。
        """
        if not proposal.intents:
            return "conflict_observed"

        primary_intent = proposal.intents[0]
        action = primary_intent.action_type

        trigger_map = {
            "accuse": "accusation_made",
            "force_check": "danger_sensed",
            "call_out": "information_revealed",
            "suggest": "proposal_made",
            "propose": "proposal_made",
            "challenge": "conflict_observed",
        }

        for key, value in trigger_map.items():
            if key in action:
                return value

        topic = proposal.topic or ""
        topic_lower = topic.lower()
        if "discover" in topic_lower or "found" in topic_lower or "clue" in topic_lower:
            return "clue_discovered"
        if "propose" in topic_lower or "suggest" in topic_lower or "plan" in topic_lower:
            return "proposal_made"

        return "information_revealed"

    def _build_interaction_events(
        self,
        proposal: InteractionProposal,
        reactions,
        group_decision,
        triggers,
        relationship_updates,
    ) -> list[InteractionEvent]:
        events: list[InteractionEvent] = []

        for reaction in reactions:
            events.append(
                InteractionEvent(
                    event_id=f"ie_{reaction.reaction_id}",
                    source_interaction_id=proposal.interaction_id,
                    event_type="agent_reaction",
                    source_agent=reaction.agent_id,
                    target_agent=reaction.target_agent,
                    source_ref_id=reaction.reaction_id,
                    summary=f"{reaction.agent_id} -> {reaction.reaction_type}: {reaction.reasoning or reaction.spoken_text or proposal.topic or 'no-topic'}",
                    payload=reaction.model_dump(mode="json"),
                )
            )

        if group_decision:
            events.append(
                InteractionEvent(
                    event_id=f"ie_{group_decision.decision_id}",
                    source_interaction_id=proposal.interaction_id,
                    event_type="group_decision",
                    source_ref_id=group_decision.decision_id,
                    summary=f"group decision on {group_decision.topic}: {group_decision.decision_type}",
                    payload=group_decision.model_dump(mode="json"),
                )
            )

        for trigger in triggers:
            events.append(
                InteractionEvent(
                    event_id=f"ie_{trigger.trigger_id}",
                    source_interaction_id=proposal.interaction_id,
                    event_type="private_tendency_trigger",
                    source_agent=trigger.agent_id,
                    source_ref_id=trigger.trigger_id,
                    summary=f"{trigger.agent_id} tendency {trigger.trigger_type}: {trigger.resulting_bias}",
                    payload=trigger.model_dump(mode="json"),
                )
            )

        for update in relationship_updates:
            events.append(
                InteractionEvent(
                    event_id=f"ie_{update.impact_id}",
                    source_interaction_id=proposal.interaction_id,
                    event_type="relationship_update",
                    source_agent=update.source_agent,
                    target_agent=update.target_agent,
                    source_ref_id=update.impact_id,
                    summary=f"{update.source_agent} -> {update.target_agent}: {update.impact_type} ({update.cause})",
                    payload=update.model_dump(mode="json"),
                )
            )

        return events
