from __future__ import annotations

from typing import Dict, List

from app.models.interaction import NearbyAgentPresence, ScenePresence
from app.models.state import WorldState
from app.models.world import WorldConfig


class ScenePresenceTracker:
    def __init__(self, world: WorldConfig, policy: Dict | None = None):
        self.world = world
        self.policy = policy or {}

    def build_scenes(self, state: WorldState) -> List[ScenePresence]:
        occupied_locations = sorted(
            {runtime.location_id for runtime in state.characters.values()}
        )
        return [self.build_scene(state, location_id) for location_id in occupied_locations]

    def build_scene(self, state: WorldState, location_id: str) -> ScenePresence:
        loc = self.world.map.get_location(location_id)
        present_agents = [
            cid
            for cid, runtime in state.characters.items()
            if runtime.location_id == location_id and not self._is_absent(cid)
        ]
        hidden_agents = [
            cid
            for cid in present_agents
            if self._is_hidden(cid, state)
        ]
        nearby_agents: List[NearbyAgentPresence] = []
        for cid, runtime in state.characters.items():
            if runtime.location_id == location_id or self._is_absent(cid):
                continue
            if runtime.location_id in loc.connected_to:
                hidden = self._is_hidden(cid, state)
                nearby_agents.append(
                    NearbyAgentPresence(
                        character_id=cid,
                        location_id=runtime.location_id,
                        can_hear=self._adjacent_can_hear(runtime.location_id, location_id),
                        can_see=self._adjacent_can_see(runtime.location_id, location_id) and not hidden,
                        hidden=hidden,
                        detection_difficulty=self._detection_difficulty(cid),
                    )
                )
        visible_objects = [obj.id for obj in loc.objects if obj.visible]
        for obj_id, data in state.world.objects.items():
            if data.get("location_id") == location_id and data.get("visible", True):
                if obj_id not in visible_objects:
                    visible_objects.append(obj_id)
        return ScenePresence(
            scene_id=f"scene_{location_id}_{state.tick:04d}",
            tick=state.tick,
            location_id=location_id,
            present_agents=present_agents,
            nearby_agents=nearby_agents,
            hidden_agents=hidden_agents,
            visible_objects=visible_objects,
            visibility_rules={
                "same_location_can_see": self.policy.get("same_location_can_see", True),
                "same_location_can_hear": self.policy.get("same_location_can_hear", True),
                "adjacent_can_hear": self.policy.get("adjacent_can_hear", True),
                "hidden_agent_requires_detection_check": True,
            },
            danger_level=self._danger_level(loc.danger_level),
        )

    def visible_agents_for(self, scene: ScenePresence, agent_id: str) -> List[str]:
        visible = [
            cid
            for cid in scene.present_agents
            if cid != agent_id and cid not in scene.hidden_agents
        ]
        visible.extend(
            nearby.character_id
            for nearby in scene.nearby_agents
            if nearby.can_see and nearby.character_id != agent_id
        )
        return visible

    def audible_agents_for(self, scene: ScenePresence, agent_id: str) -> List[str]:
        audible = [cid for cid in scene.present_agents if cid != agent_id]
        audible.extend(
            nearby.character_id
            for nearby in scene.nearby_agents
            if nearby.can_hear and nearby.character_id != agent_id
        )
        return audible

    def _is_absent(self, character_id: str) -> bool:
        profile = self.world.characters.get_character(character_id)
        return profile.visibility == "absent"

    def _is_hidden(self, character_id: str, state: WorldState) -> bool:
        runtime = state.characters[character_id]
        profile = self.world.characters.get_character(character_id)
        return runtime.hidden_status == "hidden" or profile.visibility == "hidden"

    def _adjacent_can_hear(self, from_location: str, to_location: str) -> bool:
        return bool(self.policy.get("adjacent_can_hear", True))

    def _adjacent_can_see(self, from_location: str, to_location: str) -> bool:
        return bool(self.policy.get("adjacent_can_see", False))

    def _detection_difficulty(self, character_id: str) -> int:
        profile = self.world.characters.get_character(character_id)
        skills = profile.skills or {}
        return int(skills.get("stealth", skills.get("deception", 2)))

    @staticmethod
    def _danger_level(value: int) -> str:
        if value >= 7:
            return "high"
        if value >= 3:
            return "medium"
        return "low"
