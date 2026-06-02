from pathlib import Path

from app.models.action import ActionCommand
from app.models.event import EventLog, PlotValue
from app.models.memory import Memory, MemoryType
from app.models.state import (
    ChapterGoalStatus,
    CharacterRuntimeState,
    FactExposureEntry,
    WorldState,
)
from app.models.world import (
    ChapterGoal,
    CharactersConfig,
    CharacterProfile,
    Clue,
    CluesConfig,
    Location,
    MapConfig,
    WorldBible,
    WorldConfig,
)
from app.services.memory_service import MemoryService


def make_world() -> WorldConfig:
    return WorldConfig(
        bible=WorldBible(world_id="test_world"),
        map=MapConfig(
            locations=[
                Location(
                    id="hall",
                    name="Hall",
                    public_description="A hall.",
                    objects=[],
                )
            ]
        ),
        characters=CharactersConfig(
            characters=[
                CharacterProfile(id="a", name="A"),
                CharacterProfile(id="b", name="B"),
                CharacterProfile(id="c", name="C"),
            ]
        ),
        clues=CluesConfig(
            clues=[
                Clue(id="fact_1", content="隐藏真相", importance=8),
            ]
        ),
        chapter_goal=ChapterGoal(goal="test", pov="a"),
    )


def make_state() -> WorldState:
    return WorldState(
        simulation_id="sim_test",
        chapter_goal_status=ChapterGoalStatus(goal="test"),
        characters={
            "a": CharacterRuntimeState(location_id="hall"),
            "b": CharacterRuntimeState(location_id="hall"),
            "c": CharacterRuntimeState(location_id="hall"),
        },
    )


def make_service(tmp_path: Path) -> MemoryService:
    return MemoryService(tmp_path, make_world())


def make_event(**kwargs) -> EventLog:
    data = {
        "event_id": "evt_1",
        "event_level": "plot",
        "time": "day1_20:00",
        "location_id": "hall",
        "actors": ["a"],
        "event_type": "interaction",
        "result": "事件发生",
        "visible_to": [],
        "perceived_by": [],
        "discovered_facts": [],
        "plot_value": PlotValue(progress=1),
    }
    data.update(kwargs)
    return EventLog(**data)


def memories_by_type(service: MemoryService, memory_type: MemoryType) -> list[Memory]:
    return [memory for memory in service._memories if memory.type == memory_type]


def test_event_memory_writes_to_perceived_by(tmp_path):
    service = make_service(tmp_path)
    state = make_state()
    event = make_event(actors=["a"], visible_to=["a", "b", "c"], perceived_by=["a", "b"])

    service.write_many_from_event(event, state)

    event_memories = memories_by_type(service, MemoryType.EVENT)
    assert {memory.agent_id for memory in event_memories} == {"a", "b"}


def test_event_memory_falls_back_to_visible_to(tmp_path):
    service = make_service(tmp_path)
    state = make_state()
    event = make_event(visible_to=["a", "b"])

    service.write_many_from_event(event, state)

    event_memories = memories_by_type(service, MemoryType.EVENT)
    assert {memory.agent_id for memory in event_memories} == {"a", "b"}


def test_event_memory_falls_back_to_actors(tmp_path):
    service = make_service(tmp_path)
    state = make_state()
    event = make_event(actors=["a", "b"])

    service.write_many_from_event(event, state)

    event_memories = memories_by_type(service, MemoryType.EVENT)
    assert {memory.agent_id for memory in event_memories} == {"a", "b"}


def test_fact_memory_writes_only_to_known_by(tmp_path):
    service = make_service(tmp_path)
    state = make_state()
    state.world.fact_exposure["fact_1"] = FactExposureEntry(
        fact_id="fact_1",
        truth="隐藏真相",
        known_by=["a"],
        public_label="可疑脚印",
    )
    event = make_event(
        visible_to=["a", "b", "c"],
        perceived_by=["a", "b", "c"],
        discovered_facts=["fact_1"],
    )

    service.write_many_from_event(event, state)

    fact_memories = memories_by_type(service, MemoryType.FACT)
    assert {memory.agent_id for memory in fact_memories} == {"a"}
    assert all("隐藏真相" not in memory.content for memory in service._memories if memory.agent_id in {"b", "c"})


def test_belief_memory_writes_only_to_suspected_by_without_truth(tmp_path):
    service = make_service(tmp_path)
    state = make_state()
    state.world.fact_exposure["fact_1"] = FactExposureEntry(
        fact_id="fact_1",
        truth="隐藏真相",
        suspected_by={"b": 0.6},
        public_label="可疑脚印",
    )
    event = make_event(fact_exposure_delta={"suspected_fact_ids": ["fact_1"]})

    service.write_many_from_event(event, state)

    belief_memories = memories_by_type(service, MemoryType.BELIEF)
    assert {memory.agent_id for memory in belief_memories} == {"b"}
    assert "可疑脚印" in belief_memories[0].content
    assert "隐藏真相" not in belief_memories[0].content


def test_known_by_and_suspected_by_are_separated(tmp_path):
    service = make_service(tmp_path)
    state = make_state()
    state.world.fact_exposure["fact_1"] = FactExposureEntry(
        fact_id="fact_1",
        truth="隐藏真相",
        known_by=["a"],
        suspected_by={"b": 0.6},
        public_label="可疑脚印",
    )
    event = make_event(
        discovered_facts=["fact_1"],
        fact_exposure_delta={"suspected_fact_ids": ["fact_1"]},
    )

    service.write_many_from_event(event, state)

    assert {memory.agent_id for memory in memories_by_type(service, MemoryType.FACT)} == {"a"}
    belief_memories = memories_by_type(service, MemoryType.BELIEF)
    assert {memory.agent_id for memory in belief_memories} == {"b"}
    assert all("隐藏真相" not in memory.content for memory in belief_memories)


def test_duplicate_event_calls_are_deduped(tmp_path):
    service = make_service(tmp_path)
    state = make_state()
    state.world.fact_exposure["fact_1"] = FactExposureEntry(
        fact_id="fact_1",
        truth="隐藏真相",
        known_by=["a"],
        suspected_by={"b": 0.6},
        public_label="可疑脚印",
    )
    event = make_event(
        visible_to=["a", "b"],
        discovered_facts=["fact_1"],
        fact_exposure_delta={"suspected_fact_ids": ["fact_1"]},
    )

    service.write_many_from_event(event, state)
    service.write_many_from_event(event, state)

    assert len(memories_by_type(service, MemoryType.EVENT)) == 2
    assert len(memories_by_type(service, MemoryType.FACT)) == 1
    assert len(memories_by_type(service, MemoryType.BELIEF)) == 1


def test_write_from_event_returns_optional_memory(tmp_path):
    service = make_service(tmp_path)
    state = make_state()
    event = make_event(visible_to=["a", "b"])

    memory = service.write_from_event(event, state)

    assert isinstance(memory, Memory)


def test_retrieve_relevant_is_agent_scoped(tmp_path):
    service = make_service(tmp_path)
    service._save_memory(
        Memory(
            memory_id="mem_evt_a",
            agent_id="a",
            type=MemoryType.EVENT,
            time="day1_20:00",
            location_id="hall",
            content="a memory",
            tags=["shared_tag"],
        )
    )
    service._save_memory(
        Memory(
            memory_id="mem_evt_b",
            agent_id="b",
            type=MemoryType.EVENT,
            time="day1_20:00",
            location_id="hall",
            content="b memory",
            tags=["shared_tag"],
        )
    )

    chunks = service.retrieve_relevant("a", ["shared_tag"])

    assert [chunk.memory.agent_id for chunk in chunks] == ["a"]
    assert chunks[0].memory.content == "a memory"


def test_legacy_ambiguous_dialogue_uses_perception_scope(tmp_path):
    service = make_service(tmp_path)
    state = make_state()
    event = make_event(
        event_id="evt_legacy",
        event_level="raw",
        event_type="action_result",
        result="对方回答含糊，似乎回避了问题",
        visible_to=["a", "b", "c"],
        perceived_by=["a", "b"],
        action=ActionCommand(
            agent_id="a",
            intent="ask",
            action_type="ask",
            target="c",
            topic="fact_1",
        ),
    )

    service.write_many_from_event(event, state)

    belief_memories = memories_by_type(service, MemoryType.BELIEF)
    assert {memory.agent_id for memory in belief_memories} == {"a", "b"}
