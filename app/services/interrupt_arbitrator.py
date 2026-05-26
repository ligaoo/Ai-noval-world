from __future__ import annotations

from typing import Dict, List

from app.models.interaction import InterruptionResult, ReactionIntent, SpeechSegment, TurnState


class InterruptArbitrator:
    CLAIMING_REACTIONS = {"interrupt", "challenge", "clarify", "probe", "block_disclosure", "redirect"}

    def arbitrate(
        self,
        reactions: List[ReactionIntent],
        segment: SpeechSegment,
        turn_state: TurnState,
        agent_scores: Dict[str, Dict[str, int]] | None = None,
    ) -> InterruptionResult:
        eligible = [
            reaction
            for reaction in reactions
            if reaction.intent_source == "agent_mind"
            and reaction.reaction_type in self.CLAIMING_REACTIONS
        ]
        if not eligible:
            return InterruptionResult(
                interruption_id=f"intr_{segment.segment_id}",
                trigger_segment_id=segment.segment_id,
                interrupted_speaker=segment.speaker,
                result="no_interrupt",
                turn_owner=turn_state.current_speaker,
                non_winning_reactions=list(reactions),
                reason="no eligible interrupt reaction",
            )
        scores = {reaction.reaction_id: self._score(reaction, turn_state, agent_scores or {}) for reaction in eligible}
        winner = max(eligible, key=lambda reaction: scores[reaction.reaction_id])
        non_winning = [reaction for reaction in reactions if reaction.reaction_id != winner.reaction_id]
        if not segment.interruptible:
            return InterruptionResult(
                interruption_id=f"intr_{segment.segment_id}",
                trigger_segment_id=segment.segment_id,
                interrupter=winner.agent_id,
                interrupted_speaker=segment.speaker,
                success=False,
                winning_reaction_id=winner.reaction_id,
                result="interrupt_failed",
                intent_source=winner.intent_source,
                spoken_text=winner.spoken_text,
                turn_owner=turn_state.current_speaker,
                non_winning_reactions=non_winning,
                reason="segment is not interruptible",
            )
        return InterruptionResult(
            interruption_id=f"intr_{segment.segment_id}",
            trigger_segment_id=segment.segment_id,
            interrupter=winner.agent_id,
            interrupted_speaker=segment.speaker,
            success=True,
            winning_reaction_id=winner.reaction_id,
            result="interrupt_success",
            intent_source=winner.intent_source,
            spoken_text=winner.spoken_text,
            remaining_segments_suspended=True,
            turn_owner=winner.agent_id,
            non_winning_reactions=non_winning,
            reason=f"{winner.reaction_type} won arbitration",
        )

    @staticmethod
    def _score(
        reaction: ReactionIntent,
        turn_state: TurnState,
        agent_scores: Dict[str, Dict[str, int]],
    ) -> int:
        profile_scores = agent_scores.get(reaction.agent_id, {})
        current_scores = agent_scores.get(turn_state.current_speaker or "", {})
        dominance = int(profile_scores.get("dominance", 0))
        reaction_speed = int(profile_scores.get("reaction_speed", 0))
        scene_pressure_bonus = max(0, turn_state.pressure // 2)
        current_speaker_assertiveness = int(current_scores.get("assertiveness", 0))
        return (
            reaction.urgency
            + dominance
            + reaction_speed
            + reaction.pressure_delta
            + scene_pressure_bonus
            - current_speaker_assertiveness
        )
