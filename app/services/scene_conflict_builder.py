from __future__ import annotations

from typing import Any, Dict, List

from app.models.interaction import AgentIntent, ScenePresence
from app.models.state import WorldState
from app.models.world import WorldConfig


class SceneConflictBuilder:
    def __init__(self, world: WorldConfig):
        self.world = world

    def build_for_scene(
        self,
        state: WorldState,
        scene: ScenePresence,
        intents: List[AgentIntent] | None = None,
    ) -> List[Dict[str, Any]]:
        conflicts: List[Dict[str, Any]] = []
        active_agents = [
            cid
            for cid in scene.present_agents
            if self.world.characters.get_character(cid).active_agent
        ]
        intents = intents or []

        if any(intent.action_type in {"withhold", "lie", "refuse", "ask", "challenge", "accuse"} for intent in intents):
            conflicts.append(
                {
                    "type": "information_control",
                    "agents": active_agents,
                    "pressure_required": 2,
                }
            )

        goal_agents = [cid for cid in active_agents if self.world.characters.get_character(cid).goals]
        if len(goal_agents) >= 2:
            conflicts.append(
                {
                    "type": "goal_obstruction",
                    "agents": goal_agents,
                    "pressure_required": 2,
                }
            )

        if scene.danger_level not in {"", "low", "0", 0}:
            conflicts.append(
                {
                    "type": "danger_response",
                    "agents": active_agents,
                    "pressure_required": 1,
                }
            )

        if len(scene.visible_objects) == 1 and len(active_agents) >= 2:
            conflicts.append(
                {
                    "type": "resource_competition",
                    "agents": active_agents,
                    "object_id": scene.visible_objects[0],
                    "pressure_required": 1,
                }
            )

        if len(active_agents) >= 2 and not conflicts:
            conflicts.append(
                {
                    "type": "social_tension",
                    "agents": active_agents,
                    "pressure_required": 1,
                }
            )

        return conflicts
