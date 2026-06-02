from __future__ import annotations

from typing import List, Optional

from app.models.event import EventLog
from app.models.interaction import AgentPerception, ScenePresence
from app.models.state import WorldState
from app.services.fact_exposure_matrix import FactExposureMatrix
from app.services.memory_service import MemoryService
from app.services.scene_presence_tracker import ScenePresenceTracker


class AgentPerceptionService:
    def __init__(
        self,
        presence_tracker: ScenePresenceTracker,
        fact_matrix: FactExposureMatrix,
        memory_service: Optional[MemoryService] = None,
    ):
        self.presence_tracker = presence_tracker
        self.fact_matrix = fact_matrix
        self.memory_service = memory_service

    def build_perception(
        self,
        state: WorldState,
        scene: ScenePresence,
        agent_id: str,
        recent_events: List[EventLog],
    ) -> AgentPerception:
        runtime = state.characters[agent_id]
        visible_event_text = [
            f"{event.time} {event.event_type}: {event.result}"
            for event in recent_events[-12:]
            if agent_id in (event.visible_to or [])
        ]
        beliefs = [belief.content for belief in runtime.beliefs]
        visible_agents = self.presence_tracker.visible_agents_for(scene, agent_id)
        known_facts = self.fact_matrix.allowed_facts_for(state, agent_id) or list(runtime.known_facts)
        query_tags = self._query_tags(runtime.location_id, visible_agents, known_facts, runtime.suspicions)
        relevant_memories = self._relevant_memories(agent_id, query_tags, runtime.location_id)
        relationship_context = {}
        for other_id in visible_agents:
            relationship = runtime.relationships.get(other_id)
            if relationship:
                relationship_context[other_id] = {
                    "trust": relationship.trust,
                    "suspicion": relationship.suspicion,
                    "hostility": relationship.hostility,
                    "affinity": relationship.affinity,
                }
        active_goals = [
            goal.description
            for goal in sorted(runtime.goals.values(), key=lambda item: item.priority, reverse=True)
            if goal.status == "active"
        ]
        stance_summary = [f"{target}: {stance}" for target, stance in runtime.stance.items()]
        return AgentPerception(
            agent_id=agent_id,
            scene_id=scene.scene_id,
            location_id=runtime.location_id,
            visible_agents=visible_agents,
            audible_agents=self.presence_tracker.audible_agents_for(scene, agent_id),
            visible_objects=list(scene.visible_objects),
            known_facts=known_facts,
            suspicions=list(runtime.suspicions),
            beliefs=beliefs,
            recent_visible_events=visible_event_text,
            unavailable_information=[
                "unseen_locations",
                "other_characters_private_intentions",
                "unexposed_facts",
            ],
            relevant_memories=relevant_memories,
            relationship_context=relationship_context,
            active_goals=active_goals,
            stance_summary=stance_summary,
        )

    @staticmethod
    def _query_tags(location_id: str, visible_agents: List[str], known_facts: List[str], suspicions: List[str]) -> List[str]:
        tags = [location_id]
        tags.extend(visible_agents)
        tags.extend(known_facts)
        tags.extend(suspicions)
        return list(dict.fromkeys(str(tag) for tag in tags if tag))

    def _relevant_memories(self, agent_id: str, query_tags: List[str], location_id: str) -> List[str]:
        if not self.memory_service:
            return []
        chunks = self.memory_service.retrieve_relevant(
            agent_id=agent_id,
            query_tags=query_tags,
            top_n=6,
            location_id=location_id,
        )
        return [chunk.memory.content for chunk in chunks[:6]]
