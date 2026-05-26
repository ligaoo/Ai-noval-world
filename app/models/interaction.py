from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


IntentActionType = Literal[
    "observe",
    "inspect",
    "search",
    "move",
    "ask",
    "answer",
    "refuse",
    "hide",
    "lie",
    "withhold",
    "follow",
    "block",
    "suggest",
    "challenge",
    "share_info",
    "trade_info",
    "take_item",
    "mark_location",
    "listen",
    "wait",
    "retreat",
    "call_out",
    "test_rule",
    "accuse",
    "force_check",
    "protect",
    "attack",
    "escape",
]

InteractionType = Literal[
    "information_pressure",
    "information_trade",
    "trust_test",
    "contested_item_control",
    "route_conflict",
    "danger_response",
    "accusation",
    "cooperation",
    "deception",
    "stealth_observation",
    "physical_block",
    "solo_action",
]


class NearbyAgentPresence(BaseModel):
    character_id: str
    location_id: str
    can_hear: bool = False
    can_see: bool = False
    hidden: bool = False
    detection_difficulty: int = 0


class ScenePresence(BaseModel):
    scene_id: str
    tick: int
    location_id: str
    present_agents: List[str] = Field(default_factory=list)
    nearby_agents: List[NearbyAgentPresence] = Field(default_factory=list)
    hidden_agents: List[str] = Field(default_factory=list)
    visible_objects: List[str] = Field(default_factory=list)
    audible_events: List[str] = Field(default_factory=list)
    visibility_rules: Dict[str, Any] = Field(default_factory=dict)
    danger_level: str = "low"
    goal_conflicts: List[Dict[str, Any]] = Field(default_factory=list)


class AgentPerception(BaseModel):
    agent_id: str
    scene_id: str
    location_id: str
    visible_agents: List[str] = Field(default_factory=list)
    audible_agents: List[str] = Field(default_factory=list)
    visible_objects: List[str] = Field(default_factory=list)
    known_facts: List[str] = Field(default_factory=list)
    suspicions: List[str] = Field(default_factory=list)
    beliefs: List[str] = Field(default_factory=list)
    recent_visible_events: List[str] = Field(default_factory=list)
    unavailable_information: List[str] = Field(default_factory=list)


class SpeechSegment(BaseModel):
    segment_id: str
    speaker: str
    content_summary: str = ""
    spoken_text: str = ""
    exposes_fact_ids: List[str] = Field(default_factory=list)
    withheld_fact_ids: List[str] = Field(default_factory=list)
    withheld_summaries: List[str] = Field(default_factory=list)
    exposure_level: Literal["safe", "medium", "high", "forbidden"] = "safe"
    interruptible: bool = True
    trigger_keywords: List[str] = Field(default_factory=list)
    intent_source: Literal["agent_mind", "director_intervention", "system_arbitration"] = "agent_mind"


class SpeechPlan(BaseModel):
    speech_plan_id: str
    speaker: str
    topic: Optional[str] = None
    speech_goal: str = ""
    segments: List[SpeechSegment] = Field(default_factory=list)
    withheld_fact_ids: List[str] = Field(default_factory=list)
    withheld_summaries: List[str] = Field(default_factory=list)
    source_intent_id: str = ""
    intent_source: Literal["agent_mind"] = "agent_mind"


class ReactionIntent(BaseModel):
    reaction_id: str
    agent_id: str
    reaction_type: Literal[
        "interrupt",
        "observe",
        "hold",
        "challenge",
        "clarify",
        "probe",
        "block_disclosure",
        "support",
        "redirect",
        "leave",
        "deflect",
        "continue_speaking",
    ] = "hold"
    trigger_segment_id: Optional[str] = None
    target_speaker: Optional[str] = None
    spoken_text: str = ""
    reason: str = ""
    urgency: int = 0
    pressure_delta: int = 0
    focus: str = ""
    intent_source: Literal["agent_mind"] = "agent_mind"


class InterruptionResult(BaseModel):
    interruption_id: str
    trigger_segment_id: Optional[str] = None
    interrupter: Optional[str] = None
    interrupted_speaker: Optional[str] = None
    success: bool = False
    winning_reaction_id: Optional[str] = None
    result: Literal["interrupt_success", "interrupt_failed", "no_interrupt"] = "no_interrupt"
    intent_source: str = "agent_mind"
    arbitrated_by: Literal["interrupt_arbitrator"] = "interrupt_arbitrator"
    spoken_text: str = ""
    remaining_segments_suspended: bool = False
    prevented_fact_ids: List[str] = Field(default_factory=list)
    turn_owner: Optional[str] = None
    non_winning_reactions: List[ReactionIntent] = Field(default_factory=list)
    reason: str = ""


class TurnState(BaseModel):
    interaction_id: str
    current_speaker: Optional[str] = None
    previous_speaker: Optional[str] = None
    speech_state: Literal["in_progress", "interrupted", "completed", "suspended"] = "in_progress"
    current_segment_id: Optional[str] = None
    turn_shift_reason: str = ""
    pressure: int = 0
    others_can_interrupt: bool = True


class ExposureUpdate(BaseModel):
    revealed_facts: List[Dict[str, Any]] = Field(default_factory=list)
    prevented_facts: List[Dict[str, Any]] = Field(default_factory=list)
    suspected_facts: List[Dict[str, Any]] = Field(default_factory=list)
    spoken_segment_ids: List[str] = Field(default_factory=list)
    prevented_segment_ids: List[str] = Field(default_factory=list)


class AgentIntent(BaseModel):
    agent_id: str
    intent_id: str
    scene_id: str
    intention: str
    action_type: IntentActionType
    target_agents: List[str] = Field(default_factory=list)
    target_object: Optional[str] = None
    target_location: Optional[str] = None
    topic: Optional[str] = None
    will_say: List[str] = Field(default_factory=list)
    will_hide: List[str] = Field(default_factory=list)
    claimed_facts: List[str] = Field(default_factory=list)
    referenced_fact_ids: List[str] = Field(default_factory=list)
    private_interest: str = ""
    conflict_buttons: List[str] = Field(default_factory=list)
    claimed_fact_ids: List[str] = Field(default_factory=list)
    claim_mode: Literal["known", "suspected", "misdirect", "unknown"] = "unknown"
    behavioral_leak_risk: List[str] = Field(default_factory=list)
    risk_level: Literal["low", "medium", "high"] = "low"
    pressure_level: int = 0
    raw_confidence: float = 1.0
    intent_source: Literal["agent_mind", "director_intervention", "system_seed"] = "agent_mind"
    speech_plan: Optional[SpeechPlan] = None


class PerceptionNotice(BaseModel):
    observer: str
    target: str
    noticed: List[str] = Field(default_factory=list)
    suspected_facts: Dict[str, float] = Field(default_factory=dict)
    belief_updates: List[str] = Field(default_factory=list)
    relationship_deltas: Dict[str, int] = Field(default_factory=dict)


class InteractionRound(BaseModel):
    round: int
    speaker: str
    action: str
    says_summary: str = ""
    hides: List[str] = Field(default_factory=list)
    pressure_level: int = 0
    notices: List[PerceptionNotice] = Field(default_factory=list)
    round_type: Literal["speech_segment", "reaction", "interruption", "post_interruption_reaction", "legacy"] = "legacy"
    segment_id: Optional[str] = None
    intent_source: Optional[str] = None
    interrupted_by: Optional[str] = None
    turn_owner_after: Optional[str] = None


class InteractionProposal(BaseModel):
    interaction_id: str
    interaction_type: InteractionType
    scene_id: str
    location_id: str
    participants: List[str] = Field(default_factory=list)
    observers: List[str] = Field(default_factory=list)
    topic: Optional[str] = None
    primary_conflict: Dict[str, Any] = Field(default_factory=dict)
    intents: List[AgentIntent] = Field(default_factory=list)


class InteractionResult(BaseModel):
    interaction_id: str
    interaction_type: InteractionType
    scene_id: str
    location_id: str
    participants: List[str] = Field(default_factory=list)
    observers: List[str] = Field(default_factory=list)
    topic: Optional[str] = None
    rounds: List[InteractionRound] = Field(default_factory=list)
    agent_goal_results: Dict[str, Dict[str, str]] = Field(default_factory=dict)
    revealed_facts: List[str] = Field(default_factory=list)
    still_hidden_facts: List[str] = Field(default_factory=list)
    suspected_facts: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    relationship_changes: List[Dict[str, Any]] = Field(default_factory=list)
    relationship_impact_candidates: List[RelationshipImpactUpdate] = Field(default_factory=list)
    naming_resolution: List[NamingResolutionItem] = Field(default_factory=list)
    agent_reactions: List[AgentReaction] = Field(default_factory=list)
    group_decision: Optional[GroupDecisionResult] = None
    private_tendency_triggers: List[PrivateTendencyTrigger] = Field(default_factory=list)
    interaction_events: List[InteractionEvent] = Field(default_factory=list)
    agent_debug_metrics: Dict[str, int] = Field(default_factory=dict)
    state_changes: List[Dict[str, Any]] = Field(default_factory=list)
    plot_changes: Dict[str, Any] = Field(default_factory=dict)
    visible_to: List[str] = Field(default_factory=list)
    hidden_effects: List[str] = Field(default_factory=list)
    director_intervention: Optional[Dict[str, Any]] = None
    speech_plans: List[SpeechPlan] = Field(default_factory=list)
    spoken_segments: List[SpeechSegment] = Field(default_factory=list)
    prevented_segments: List[SpeechSegment] = Field(default_factory=list)
    reaction_intents: List[ReactionIntent] = Field(default_factory=list)
    interruption_results: List[InterruptionResult] = Field(default_factory=list)
    post_interruption_reactions: List[ReactionIntent] = Field(default_factory=list)
    turn_states: List[TurnState] = Field(default_factory=list)
    exposure_update: Optional[ExposureUpdate] = None


class AgentReaction(BaseModel):
    reaction_id: str
    agent_id: str
    reaction_type: Literal[
        "question", "challenge", "observe", "request_share",
        "withhold", "silent_record", "action_proposal", "deny",
        "deflect", "support", "accuse", "protect", "doubt",
        "agree", "disagree", "suggest_alternative", "demand_verification"
    ]
    trigger_event_type: Literal["clue_discovered", "proposal_made", "accusation_made", "danger_sensed", "secret_at_risk", "trust_broken", "information_revealed", "conflict_observed"]
    target_agent: Optional[str] = None
    target_fact: Optional[str] = None
    urgency: int = 0
    confidence: float = 0.5
    reasoning: str = ""
    private_motivation: str = ""
    will_express: bool = True
    spoken_text: str = ""
    pressure_delta: int = 0
    related_fact_ids: List[str] = Field(default_factory=list)
    trigger_source: Literal["agent_mind", "private_tendency", "group_pressure", "relationship_change"] = "agent_mind"


class GroupDecisionOption(BaseModel):
    option_id: str
    proposer: str
    proposal_text: str
    supporters: List[str] = Field(default_factory=list)
    opposers: List[str] = Field(default_factory=list)
    abstainers: List[str] = Field(default_factory=list)
    related_fact_ids: List[str] = Field(default_factory=list)
    pressure_influence: int = 0
    trust_influence: int = 0


class GroupDecisionResult(BaseModel):
    decision_id: str
    participants: List[str] = Field(default_factory=list)
    topic: str
    options: List[GroupDecisionOption] = Field(default_factory=list)
    winning_option_id: Optional[str] = None
    decision_type: Literal["consensus", "majority", "leader_decides", "deadlocked"] = "consensus"
    pressure_level: int = 0
    unresolved_tensions: List[str] = Field(default_factory=list)
    side_effect_relationship_changes: List[Dict[str, Any]] = Field(default_factory=list)


class PrivateTendencyTrigger(BaseModel):
    trigger_id: str
    agent_id: str
    trigger_type: Literal[
        "secret_protection", "personal_grudge", "hidden_agenda",
        "fear_response", "opportunism", "loyalty_override",
        "self_preservation", "revenge_urge", "curiosity_override",
        "moral_conflict"
    ]
    trigger_condition: str
    intensity: float = 0.5
    overrides_intent: bool = False
    resulting_bias: str = ""
    related_secret_index: Optional[int] = None
    suppressed_reaction_ids: List[str] = Field(default_factory=list)
    amplified_reaction_ids: List[str] = Field(default_factory=list)


class RelationshipImpactUpdate(BaseModel):
    impact_id: str
    source_agent: str
    target_agent: str
    impact_type: Literal[
        "trust_gain", "trust_loss", "suspicion_rise", "suspicion_fall",
        "hostility_rise", "hostility_fall", "affinity_gain", "affinity_loss",
        "alliance_formed", "alliance_broken", "respect_gained", "respect_lost"
    ]
    delta_value: int = 0
    cause: str
    evidence_strength: float = 0.5
    is_public: bool = False
    witnessed_by: List[str] = Field(default_factory=list)
    related_reaction_id: Optional[str] = None


class NamingResolutionItem(BaseModel):
    reference_id: str
    agent_id: str
    original_reference: str
    resolved_name: str
    resolution_type: Literal["public_label", "known_fact", "suspected_fact", "euphemism", "code_name", "avoided_topic"]
    confidence: float = 1.0
    exposure_risk: Literal["low", "medium", "high"] = "low"
    is_consensus: bool = False
    alternative_names: Dict[str, str] = Field(default_factory=dict)


class InteractionEvent(BaseModel):
    event_id: str
    source_interaction_id: str
    event_type: Literal[
        "agent_reaction",
        "group_decision",
        "private_tendency_trigger",
        "relationship_update",
    ]
    source_agent: Optional[str] = None
    target_agent: Optional[str] = None
    source_ref_id: Optional[str] = None
    summary: str
    payload: Dict[str, Any] = Field(default_factory=dict)


class AgentDrivenInteractionResult(BaseModel):
    source_interaction_id: str
    agent_reactions: List[AgentReaction] = Field(default_factory=list)
    group_decision: Optional[GroupDecisionResult] = None
    private_tendency_triggers: List[PrivateTendencyTrigger] = Field(default_factory=list)
    relationship_updates: List[RelationshipImpactUpdate] = Field(default_factory=list)
    naming_resolution: List[NamingResolutionItem] = Field(default_factory=list)
    interaction_events: List[InteractionEvent] = Field(default_factory=list)
    debug_metrics: Dict[str, int] = Field(default_factory=dict)

    def calculate_debug_metrics(self, active_agent_count: int) -> None:
        self.debug_metrics = {
            "agent_reaction_count": len(self.agent_reactions),
            "group_decision_count": 1 if self.group_decision else 0,
            "private_tendency_trigger_count": len(self.private_tendency_triggers),
            "relationship_update_count": len(self.relationship_updates),
            "interaction_event_count": len(self.interaction_events),
            "naming_resolved_count": len(self.naming_resolution),
            "naming_resolved": len(self.naming_resolution) > 0,
            "active_agent_count": active_agent_count,
            "tendency_per_agent_ratio": len(self.private_tendency_triggers) / max(1, active_agent_count),
        }


class SandboxTickResult(BaseModel):
    tick: int
    scenes: List[ScenePresence] = Field(default_factory=list)
    perceptions: Dict[str, AgentPerception] = Field(default_factory=dict)
    intents: List[AgentIntent] = Field(default_factory=list)
    interactions: List[InteractionResult] = Field(default_factory=list)
    event_ids: List[str] = Field(default_factory=list)
    agent_driven_results: List[AgentDrivenInteractionResult] = Field(default_factory=list)
