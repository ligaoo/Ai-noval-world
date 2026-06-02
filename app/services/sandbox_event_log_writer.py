from __future__ import annotations

import json
from typing import List

from app.models.event import EventLog, PlotValue
from app.models.interaction import InteractionResult
from app.models.state import WorldState
from app.models.world import WorldConfig


class SandboxEventLogWriter:
    def __init__(self, world: WorldConfig | None = None):
        self.world = world

    def events_from_interaction(
        self,
        state: WorldState,
        result: InteractionResult,
    ) -> List[EventLog]:
        summary = self._visible_summary(result)
        plot_value = PlotValue(
            progress=int(result.plot_changes.get("progress_delta", 0)),
            mystery=len(result.suspected_facts),
            conflict=len(result.relationship_changes),
            relationship=len(result.relationship_changes),
        )
        return [
            EventLog(
                event_id=f"evt_{result.interaction_id}",
                event_level="plot",
                time=state.world_time,
                location_id=result.location_id,
                actors=result.participants,
                event_type="interaction",
                action=None,
                result=summary,
                visible_to=list(result.visible_to),
                hidden_effects=[],
                discovered_facts=self._revealed_fact_ids(state, result),
                plot_value=plot_value,
                interaction_id=result.interaction_id,
                scene_id=result.scene_id,
                perceived_by=list(result.visible_to),
                fact_exposure_delta={
                    "revealed_fact_ids": self._revealed_fact_ids(state, result),
                    "suspected_fact_ids": self._suspected_fact_ids(state, result),
                    "known_by": self._known_by_by_fact(state, result),
                    "suspected_by": self._suspected_by_by_fact(state, result),
                    "revealed_count": len(result.revealed_facts),
                    "suspected_count": sum(len(v) for v in result.suspected_facts.values()),
                },
                source_interaction=self._source_summary(result),
            )
        ]

    def _character_name(self, character_id: str | None) -> str:
        if not character_id:
            return "unknown"
        if self.world:
            try:
                return self.world.characters.get_character(character_id).name or character_id
            except KeyError:
                pass
        return character_id

    def _character_ref(self, character_id: str | None) -> dict:
        return {"id": character_id, "name": self._character_name(character_id)}

    def _location_name(self, location_id: str | None) -> str:
        if not location_id:
            return "unknown"
        if self.world:
            try:
                return self.world.map.get_location(location_id).name or location_id
            except KeyError:
                pass
        return location_id

    def _visible_summary(self, result: InteractionResult) -> str:
        parts = []
        if result.spoken_segments or result.interruption_results:
            for segment in result.spoken_segments:
                parts.append(f"{self._character_name(segment.speaker)}: {segment.spoken_text or segment.content_summary}")
            for interruption in result.interruption_results:
                if interruption.success:
                    parts.append(
                        f"{self._character_name(interruption.interrupter)} interrupted "
                        f"{self._character_name(interruption.interrupted_speaker)}: {interruption.spoken_text}"
                    )
            for reaction in result.post_interruption_reactions:
                if reaction.spoken_text:
                    parts.append(f"{self._character_name(reaction.agent_id)}: {reaction.spoken_text}")
            observers = [
                self._character_name(reaction.agent_id)
                for reaction in result.reaction_intents
                if reaction.reaction_type == "observe"
            ]
            if observers:
                parts.append(f"{', '.join(sorted(set(observers)))} noticed something unusual.")
        else:
            for round_item in result.rounds:
                speaker = self._character_name(round_item.speaker)
                if round_item.says_summary:
                    parts.append(f"{speaker}: {round_item.says_summary}")
                else:
                    parts.append(f"{speaker}: {round_item.action}")
        if result.suspected_facts:
            parts.append("New suspicions emerged among participants.")
        return " | ".join(parts) if parts else json.dumps(result.agent_goal_results, ensure_ascii=False)

    @staticmethod
    def _revealed_fact_ids(state: WorldState, result: InteractionResult) -> List[str]:
        fact_ids: List[str] = []
        if result.exposure_update:
            for item in result.exposure_update.revealed_facts:
                fact_id = str(item.get("fact_id") or "")
                if fact_id:
                    fact_ids.append(fact_id)
        for fact in result.revealed_facts:
            for fact_id, entry in state.world.fact_exposure.items():
                if fact == fact_id or fact == entry.truth:
                    fact_ids.append(fact_id)
                    break
        return list(dict.fromkeys(fact_ids))

    @staticmethod
    def _suspected_fact_ids(state: WorldState, result: InteractionResult) -> List[str]:
        fact_ids: List[str] = []
        if result.exposure_update:
            for item in result.exposure_update.suspected_facts:
                if item.get("status", "suspected") != "suspected":
                    continue
                fact_id = str(item.get("fact_id") or item.get("label") or "")
                if fact_id:
                    fact_ids.append(fact_id)
        for fact in result.suspected_facts:
            matched = None
            for fact_id, entry in state.world.fact_exposure.items():
                if fact == fact_id or fact == entry.public_label or fact == entry.truth:
                    matched = fact_id
                    break
            fact_ids.append(matched or fact)
        return list(dict.fromkeys(fact_ids))

    @staticmethod
    def _known_by_by_fact(state: WorldState, result: InteractionResult) -> dict:
        known_by: dict[str, List[str]] = {}
        if result.exposure_update:
            for item in result.exposure_update.revealed_facts:
                fact_id = str(item.get("fact_id") or "")
                if fact_id:
                    known_by[fact_id] = [str(agent_id) for agent_id in item.get("known_by", [])]
        for fact_id in SandboxEventLogWriter._revealed_fact_ids(state, result):
            known_by.setdefault(fact_id, list(result.visible_to))
        return known_by

    @staticmethod
    def _suspected_by_by_fact(state: WorldState, result: InteractionResult) -> dict:
        suspected_by: dict[str, dict[str, float]] = {}
        if result.exposure_update:
            for item in result.exposure_update.suspected_facts:
                if item.get("status", "suspected") != "suspected":
                    continue
                fact_id = str(item.get("fact_id") or item.get("label") or "")
                if not fact_id:
                    continue
                confidence = float(item.get("confidence", 0.5))
                suspected_by.setdefault(fact_id, {})
                for agent_id in item.get("suspected_by", []):
                    suspected_by[fact_id][str(agent_id)] = confidence
        for fact, agents in result.suspected_facts.items():
            matched = None
            for fact_id, entry in state.world.fact_exposure.items():
                if fact == fact_id or fact == entry.public_label or fact == entry.truth:
                    matched = fact_id
                    break
            fact_id = matched or fact
            suspected_by.setdefault(fact_id, {})
            for agent_id, confidence in agents.items():
                suspected_by[fact_id][str(agent_id)] = float(confidence)
        return suspected_by

    def _source_summary(self, result: InteractionResult) -> dict:
        character_ids = sorted(set(result.participants + result.observers + result.visible_to))
        for segment in result.spoken_segments + result.prevented_segments:
            character_ids.append(segment.speaker)
        for reaction in result.reaction_intents + result.post_interruption_reactions:
            character_ids.append(reaction.agent_id)
            if reaction.target_speaker:
                character_ids.append(reaction.target_speaker)
        for interruption in result.interruption_results:
            if interruption.interrupter:
                character_ids.append(interruption.interrupter)
            if interruption.interrupted_speaker:
                character_ids.append(interruption.interrupted_speaker)
            if interruption.turn_owner:
                character_ids.append(interruption.turn_owner)
        character_display_map = {
            character_id: self._character_name(character_id)
            for character_id in sorted(set(character_ids))
            if character_id
        }
        summary = {
            "interaction_id": result.interaction_id,
            "interaction_type": result.interaction_type,
            "location_id": result.location_id,
            "location_name": self._location_name(result.location_id),
            "participants": list(result.participants),
            "participants_display": [self._character_ref(cid) for cid in result.participants],
            "observers": list(result.observers),
            "observers_display": [self._character_ref(cid) for cid in result.observers],
            "character_display_map": character_display_map,
            "rounds": [
                {
                    "round": round_item.round,
                    "speaker": round_item.speaker,
                    "speaker_name": self._character_name(round_item.speaker),
                    "action": round_item.action,
                    "says_summary": round_item.says_summary,
                    "pressure_level": round_item.pressure_level,
                    "round_type": round_item.round_type,
                    "segment_id": round_item.segment_id,
                    "intent_source": round_item.intent_source,
                    "interrupted_by": round_item.interrupted_by,
                    "interrupted_by_name": self._character_name(round_item.interrupted_by) if round_item.interrupted_by else None,
                    "turn_owner_after": round_item.turn_owner_after,
                    "turn_owner_after_name": self._character_name(round_item.turn_owner_after) if round_item.turn_owner_after else None,
                }
                for round_item in result.rounds
            ],
            "revealed_count": len(result.revealed_facts),
            "suspected_count": sum(len(v) for v in result.suspected_facts.values()),
            "primary_conflict": result.plot_changes.get("primary_conflict", {}),
            "agent_debug_metrics": dict(result.agent_debug_metrics),
            "agent_reactions": [reaction.model_dump(mode="json") for reaction in result.agent_reactions],
            "group_decision": result.group_decision.model_dump(mode="json") if result.group_decision else None,
            "private_tendency_triggers": [
                trigger.model_dump(mode="json") for trigger in result.private_tendency_triggers
            ],
            "relationship_updates": [
                update.model_dump(mode="json") for update in result.relationship_impact_candidates
            ],
            "interaction_events": [
                item.model_dump(mode="json") for item in result.interaction_events
            ],
        }
        if result.spoken_segments or result.interruption_results:
            summary.update(
                {
                    "spoken_segments": [
                        {
                            "segment_id": segment.segment_id,
                            "speaker": segment.speaker,
                            "speaker_name": self._character_name(segment.speaker),
                            "content_summary": segment.content_summary,
                            "spoken_text": segment.spoken_text,
                            "exposes_fact_ids": list(segment.exposes_fact_ids),
                            "intent_source": segment.intent_source,
                        }
                        for segment in result.spoken_segments
                    ],
                    "prevented_segments": [
                        {
                            "segment_id": segment.segment_id,
                            "speaker": segment.speaker,
                            "speaker_name": self._character_name(segment.speaker),
                            "content_summary": segment.content_summary,
                            "spoken_text": segment.spoken_text,
                            "exposes_fact_ids": list(segment.exposes_fact_ids),
                            "intent_source": segment.intent_source,
                        }
                        for segment in result.prevented_segments
                    ],
                    "interruption_results": [
                        self._interruption_summary(item) for item in result.interruption_results
                    ],
                    "post_interruption_reactions": [
                        self._reaction_summary(item) for item in result.post_interruption_reactions
                    ],
                    "reaction_intents": [
                        self._reaction_summary(reaction) for reaction in result.reaction_intents
                    ],
                    "exposure_update": result.exposure_update.model_dump(mode="json") if result.exposure_update else None,
                    "turn_transfers": [
                        state.model_dump(mode="json") for state in result.turn_states if state.turn_shift_reason
                    ],
                    "intent_source": "agent_mind",
                    "arbitrated_by": "interrupt_arbitrator",
                }
            )
        return summary

    def _reaction_summary(self, reaction) -> dict:
        data = reaction.model_dump(mode="json")
        data["agent_name"] = self._character_name(reaction.agent_id)
        data["target_speaker_name"] = self._character_name(reaction.target_speaker) if reaction.target_speaker else None
        return data

    def _interruption_summary(self, interruption) -> dict:
        data = interruption.model_dump(mode="json")
        data["interrupter_name"] = self._character_name(interruption.interrupter) if interruption.interrupter else None
        data["interrupted_speaker_name"] = self._character_name(interruption.interrupted_speaker) if interruption.interrupted_speaker else None
        data["turn_owner_name"] = self._character_name(interruption.turn_owner) if interruption.turn_owner else None
        return data
