from __future__ import annotations

from typing import List

from app.models.event import EventLog
from app.models.interaction import AgentPerception, ScenePresence
from app.models.state import WorldState
from app.services.fact_exposure_matrix import FactExposureMatrix
from app.services.scene_presence_tracker import ScenePresenceTracker


class AgentPerceptionService:
    def __init__(
        self,
        presence_tracker: ScenePresenceTracker,
        fact_matrix: FactExposureMatrix,
    ):
        self.presence_tracker = presence_tracker
        self.fact_matrix = fact_matrix

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
        return AgentPerception(
            agent_id=agent_id,
            scene_id=scene.scene_id,
            location_id=runtime.location_id,
            visible_agents=self.presence_tracker.visible_agents_for(scene, agent_id),
            audible_agents=self.presence_tracker.audible_agents_for(scene, agent_id),
            visible_objects=list(scene.visible_objects),
            known_facts=self.fact_matrix.allowed_facts_for(state, agent_id) or list(runtime.known_facts),
            suspicions=list(runtime.suspicions),
            beliefs=beliefs,
            recent_visible_events=visible_event_text,
            unavailable_information=[
                "unseen_locations",
                "other_characters_private_intentions",
                "unexposed_facts",
            ],
        )
