from __future__ import annotations

import hashlib
from typing import List

from app.models.interaction import AgentIntent, PerceptionNotice, ScenePresence
from app.models.state import WorldState
from app.models.world import WorldConfig


class PerceptionResolver:
    def __init__(self, world: WorldConfig):
        self.world = world

    def resolve_notices(
        self,
        state: WorldState,
        scene: ScenePresence,
        target_intent: AgentIntent,
        observers: List[str],
        interaction_id: str,
        pressure_level: int,
    ) -> List[PerceptionNotice]:
        notices: List[PerceptionNotice] = []
        if target_intent.action_type not in {"withhold", "lie", "refuse"}:
            return notices
        for observer in observers:
            if observer == target_intent.agent_id:
                continue
            if not self._can_observe(scene, observer):
                continue
            score = self._observer_score(observer) + pressure_level
            difficulty = self._target_difficulty(target_intent.agent_id) + len(target_intent.will_hide)
            if self._roll(state, interaction_id, observer, target_intent.agent_id) + score >= difficulty:
                suspected = target_intent.will_hide[0] if target_intent.will_hide else "withheld_information"
                notices.append(
                    PerceptionNotice(
                        observer=observer,
                        target=target_intent.agent_id,
                        noticed=list(target_intent.behavioral_leak_risk) or ["inconsistent_or_guarded_response"],
                        suspected_facts={suspected: min(0.9, 0.4 + score / 10)},
                        belief_updates=[f"{target_intent.agent_id} may be withholding information"],
                        relationship_deltas={target_intent.agent_id: -1},
                    )
                )
        return notices

    def _can_observe(self, scene: ScenePresence, observer: str) -> bool:
        if observer in scene.present_agents:
            return True
        return any(
            nearby.character_id == observer and (nearby.can_hear or nearby.can_see)
            for nearby in scene.nearby_agents
        )

    def _observer_score(self, character_id: str) -> int:
        profile = self.world.characters.get_character(character_id)
        return int(profile.skills.get("observation", 2))

    def _target_difficulty(self, character_id: str) -> int:
        profile = self.world.characters.get_character(character_id)
        return int(profile.skills.get("deception", 2)) + 2

    @staticmethod
    def _roll(
        state: WorldState,
        interaction_id: str,
        observer: str,
        target: str,
    ) -> int:
        raw = f"{state.random_seed}:{state.tick}:{interaction_id}:{observer}:{target}"
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        return int(digest[:8], 16) % 6
