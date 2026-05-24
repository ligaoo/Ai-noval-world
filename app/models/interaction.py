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
    behavioral_leak_risk: List[str] = Field(default_factory=list)
    risk_level: Literal["low", "medium", "high"] = "low"
    pressure_level: int = 0
    raw_confidence: float = 1.0


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
    state_changes: List[Dict[str, Any]] = Field(default_factory=list)
    plot_changes: Dict[str, Any] = Field(default_factory=dict)
    visible_to: List[str] = Field(default_factory=list)
    hidden_effects: List[str] = Field(default_factory=list)
    director_intervention: Optional[Dict[str, Any]] = None


class SandboxTickResult(BaseModel):
    tick: int
    scenes: List[ScenePresence] = Field(default_factory=list)
    perceptions: Dict[str, AgentPerception] = Field(default_factory=dict)
    intents: List[AgentIntent] = Field(default_factory=list)
    interactions: List[InteractionResult] = Field(default_factory=list)
    event_ids: List[str] = Field(default_factory=list)
