from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


ActionType = Literal["move", "observe", "inspect", "search", "talk", "ask", "wait"]
RiskLevel = Literal["low", "medium", "high"]


class ActionCommand(BaseModel):
    agent_id: str
    intent: str
    action_type: ActionType
    target: str
    topic: Optional[str] = None
    method: str = ""
    dialogue: Optional[str] = None
    expected_gain: str = ""
    risk_level: RiskLevel = "low"


class StateChange(BaseModel):
    op: Literal["set", "inc", "append"]
    path: str
    value: Any


class RelationshipChange(BaseModel):
    from_id: str
    to_id: str
    delta: int


class ActionResult(BaseModel):
    valid: bool
    success: bool
    result: str
    discovered_facts: List[str] = Field(default_factory=list)
    state_changes: List[StateChange] = Field(default_factory=list)
    relationship_changes: List[RelationshipChange] = Field(default_factory=list)
    triggered_events: List[str] = Field(default_factory=list)
    reason_for_judgement: str = ""

