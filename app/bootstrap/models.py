from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ========== 5. SeedInterpreter：模糊设定解析输出 ==========
class ParsedSeed(BaseModel):
    genre: str = "horror"
    sub_genre: str = "suspense_supernatural"
    core_location: str = ""
    supernatural_element: str = ""
    protagonist_goal: str = ""
    missing_person: str = ""
    story_type: str = ""
    bootstrap_template: str = ""
    cast_mode: str = "solo_investigation"
    ensemble_size: int = 1
    group_goal: str = ""
    survival_stakes: str = ""
    opening_mode: str = "solo_arrival"
    core_motif: str = ""
    motif_keywords: List[str] = Field(default_factory=list)


# ========== 7. MinimumCastGenerator：角色配置 + active_agent ==========
class DisclosurePolicy(BaseModel):
    style: str = "reluctant"
    max_new_facts_per_dialogue: int = 1
    avoid_exposition: bool = True


class CharacterWithAgent(BaseModel):
    character_id: str
    name: str
    role: str
    active_agent: bool = True
    location_id: str = ""
    goal: str = ""
    personal_stakes: str = ""
    public_motive: str = ""
    private_motive: str = ""
    withheld_information: str = ""
    suspicious_micro_actions: List[str] = Field(default_factory=list)
    private_hook: str = ""
    emotional_core: str = ""
    known_facts: List[str] = Field(default_factory=list)
    suspicions: List[str] = Field(default_factory=list)
    inventory: List[str] = Field(default_factory=list)
    personality_traits: List[str] = Field(default_factory=list)
    fears: List[str] = Field(default_factory=list)
    secrets: List[str] = Field(default_factory=list)
    background: str = ""
    narrative_function: List[str] = Field(default_factory=list)
    visibility: str = "visible"
    disclosure_policy: Optional[DisclosurePolicy] = None
    llm_temperature: Optional[float] = None
    skills: Dict[str, int] = Field(default_factory=dict)


# ========== 8. BootstrapMapGenerator：地图配置 ==========
class BootstrapLocationObject(BaseModel):
    object_id: str
    object_type: str = "inspectable_trace"
    description: str = ""
    allowed_actions: List[str] = Field(default_factory=list)


class BootstrapLocation(BaseModel):
    location_id: str
    name: str
    type: str = "interior"
    connected_to: List[str] = Field(default_factory=list)
    available_actions: List[str] = Field(default_factory=lambda: ["observe", "inspect", "move"])
    public_description: str = ""
    objects: List[BootstrapLocationObject] = Field(default_factory=list)
    danger_level: int = 0
    reveal_stage: str = "surface"
    recommended_chapter_range: List[int] = Field(default_factory=list)
    narrative_function: str = ""
    unlock_condition: str = ""
    associated_threads: List[str] = Field(default_factory=list)


# ========== 9. TruthChainGenerator：真相链 ==========
class TruthRevealStage(BaseModel):
    stage: str
    chapter_range: List[int]
    allowed_information: List[str]
    forbidden_information: List[str] = Field(default_factory=list)


class TruthChain(BaseModel):
    truth_id: str
    final_truth: str
    reveal_steps: List[TruthRevealStage]


# ========== 10. EvidenceGraphGenerator：证据链 ==========
class EvidenceItem(BaseModel):
    evidence_id: str
    title: str
    type: str
    truth_relevance: str
    purpose: str
    related_thread: str
    can_mislead: bool = False
    real_meaning: str = ""
    allowed_reveal_chapters: List[int] = Field(default_factory=list)


# ========== 11. ClueRouteGenerator：线索 + 可发现入口 ==========
class DiscoverRoute(BaseModel):
    location_id: str
    object_id: Optional[str] = None
    target: Optional[str] = None
    action: str
    difficulty: int = 1
    required_skill: Optional[str] = None
    topic: Optional[str] = None


class OnDiscovered(BaseModel):
    add_known_fact: Optional[str] = None
    add_inventory_item: Optional[str] = None
    trigger_event: Optional[str] = None
    plot_progress: int = 0


class BootstrapClue(BaseModel):
    clue_id: str
    title: str
    content: str = ""
    level: str = "surface"
    related_event: str = ""
    related_thread: str = ""
    discover_routes: List[DiscoverRoute] = Field(default_factory=list)
    on_discovered: OnDiscovered = Field(default_factory=OnDiscovered)
    planned_chapters: List[int] = Field(default_factory=list)
    evidence_ids: List[str] = Field(default_factory=list)
    related_truth: str = ""
    reveal_role: str = "introduce"


# ========== 12. OpenThreadSeedGenerator：悬念池 ==========
class OpenThread(BaseModel):
    thread_id: str
    question: str
    priority: int = 5
    status: str = "open"
    opened_at_chapter: int = 1
    related_evidence_ids: List[str] = Field(default_factory=list)
    thread_type: str = "mystery"
    motif: str = ""
    thematic_keyword: str = ""
    payoff_hint: str = ""


# ========== 13. OpeningChapterGoalGenerator：第一章目标 ==========
class Obstacle(BaseModel):
    type: str = "reluctant_witness"
    character_id: str = ""


class EndingHook(BaseModel):
    type: str = "personalized_clue"
    content: str = ""


class OpeningChapterPlan(BaseModel):
    chapter_no: int = 1
    chapter_function: str = ""
    protagonist_goal: str = ""
    personal_stakes: str = ""
    must_events: List[str] = Field(default_factory=list)
    selected_clues: List[str] = Field(default_factory=list)
    obstacle: Optional[Obstacle] = None
    ending_hook: Optional[EndingHook] = None
    protagonist_private_hook: str = ""
    required_conflict_beat: str = ""
    concrete_ending_hook: str = ""
    forbidden_reveals: List[str] = Field(default_factory=list)
    initial_location: str = ""


# ========== 20. WriterStoryAnchorGenerator：叙事锚点 ==========
class WriterStoryAnchor(BaseModel):
    title: str = ""
    protagonist_name: str = ""
    protagonist_goal: str = ""
    personal_stakes: str = ""
    current_chapter_goal: str = ""
    main_question: str = ""
    required_emotional_beat: str = ""
    protagonist_private_hook: str = ""
    required_interpersonal_conflict: str = ""
    core_motif: str = ""
    concrete_ending_hook: str = ""
    forbidden_summary_sentences: List[str] = Field(default_factory=list)
    forbidden_generic_phrases: List[str] = Field(default_factory=lambda: [
        "神秘之地", "发现真相", "重要的东西", "说不清的直觉",
        "有些问题只有走进去才能找到答案", "我已经做好继续走下去的准备",
        "Mysterious Place", "the truth will be revealed"
    ])
    world_tone: str = "压抑、克制"


# ========== 21. BootstrapValidator：校验结果 ==========
class ValidationIssue(BaseModel):
    type: str
    message: str
    severity: str = "error"


class ValidationResult(BaseModel):
    passed: bool = False
    issues: List[ValidationIssue] = Field(default_factory=list)
    warnings: List[ValidationIssue] = Field(default_factory=list)


# ========== 最终 Bootstrap 输出 ==========
class BootstrapSeed(BaseModel):
    user_seed: str
    target_genre: str = "horror_suspense"
    target_words: int = 100000
    target_chapters: int = 30
    auto_confirm: bool = False


class BootstrapResult(BaseModel):
    bootstrap_id: str
    world_id: str
    status: str = "candidate_generated"
    title: str = ""
    target_words: int = 100000
    target_chapters: int = 30

    world_bible: Dict[str, Any] = Field(default_factory=dict)
    characters: List[CharacterWithAgent] = Field(default_factory=list)
    map: List[BootstrapLocation] = Field(default_factory=list)
    clues: List[BootstrapClue] = Field(default_factory=list)
    plot_arcs: List[Dict[str, Any]] = Field(default_factory=list)
    character_arcs: List[Dict[str, Any]] = Field(default_factory=list)

    truth_chain: Optional[TruthChain] = None
    evidence_graph: List[EvidenceItem] = Field(default_factory=list)
    open_threads: List[OpenThread] = Field(default_factory=list)
    opening_chapter_plan: Optional[OpeningChapterPlan] = None
    writer_story_anchors: Optional[WriterStoryAnchor] = None
    chapter_goal: Dict[str, Any] = Field(default_factory=dict)

    parsed_seed: Optional[ParsedSeed] = None
    validation: Optional[ValidationResult] = None
    created_at: str = ""
    fusion_report: Dict[str, Any] = Field(default_factory=dict)

    def summary_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "characters": len(self.characters),
            "locations": len(self.map),
            "clues": len(self.clues),
            "open_threads": len(self.open_threads),
        }
