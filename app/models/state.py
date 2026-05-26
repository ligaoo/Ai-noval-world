from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class ChapterGoalStatus(BaseModel):
    goal: str
    completed: bool = False
    progress: int = 0  # 0..100


class BeliefState(BaseModel):
    content: str
    confidence: float = 0.5
    source: str = ""
    related_fact_id: Optional[str] = None
    updated_tick: int = 0


class RelationshipRuntimeState(BaseModel):
    trust: int = 0
    suspicion: int = 0
    hostility: int = 0
    affinity: int = 0
    last_changed_tick: int = 0


class FactExposureEntry(BaseModel):
    fact_id: str
    truth: str
    known_by: List[str] = Field(default_factory=list)
    suspected_by: Dict[str, float] = Field(default_factory=dict)
    misunderstood_by: Dict[str, str] = Field(default_factory=dict)
    source: str = ""
    reveal_stage: str = ""
    created_tick: int = 0
    public_label: str = ""
    min_pressure_to_reveal: int = 2
    min_rounds_to_reveal: int = 2
    revealed_tick: Optional[int] = None


class CharacterRuntimeState(BaseModel):
    location_id: str
    mental_state: str = ""
    known_facts: List[str] = Field(default_factory=list)
    suspicions: List[str] = Field(default_factory=list)
    inventory: List[str] = Field(default_factory=list)
    last_action: Optional[str] = None
    repeat_action_count: int = 0
    attitude_to: Dict[str, int] = Field(default_factory=dict)
    beliefs: List[BeliefState] = Field(default_factory=list)
    relationships: Dict[str, RelationshipRuntimeState] = Field(default_factory=dict)
    current_intention: str = ""
    emotional_state: str = ""
    hidden_status: str = "visible"
    last_intent_signature: Optional[str] = None


class WorldRuntimeState(BaseModel):
    discovered_facts: Dict[str, bool] = Field(default_factory=dict)
    objects: Dict[str, dict] = Field(default_factory=dict)
    soft_hints: List[str] = Field(default_factory=list)
    fact_exposure: Dict[str, FactExposureEntry] = Field(default_factory=dict)
    open_threads: List[str] = Field(default_factory=list)
    interaction_history: List[str] = Field(default_factory=list)


class WorldState(BaseModel):
    simulation_id: str
    tick: int = 0
    world_time: str = "day1_20:00"
    random_seed: int = 0
    chapter_goal_status: ChapterGoalStatus
    no_progress_ticks: int = 0
    characters: Dict[str, CharacterRuntimeState] = Field(default_factory=dict)
    world: WorldRuntimeState = Field(default_factory=WorldRuntimeState)

