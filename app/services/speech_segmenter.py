from __future__ import annotations

import re
from typing import List

from app.models.interaction import AgentIntent, SpeechPlan, SpeechSegment
from app.models.state import WorldState


class SpeechSegmenter:
    def build_plan(self, state: WorldState, intent: AgentIntent, max_segments: int = 5) -> SpeechPlan:
        if intent.speech_plan:
            return intent.speech_plan
        source = "agent_mind" if intent.intent_source != "director_intervention" else "director_intervention"
        fact_ids = self._ordered_fact_ids(state, intent)
        segments: List[SpeechSegment] = []
        withheld_fact_ids: List[str] = []
        withheld_summaries = list(intent.will_hide)
        lines = list(intent.will_say[:max_segments])
        if not lines and intent.action_type in {"ask", "answer", "refuse", "lie", "withhold", "suggest", "challenge", "share_info", "trade_info", "accuse", "call_out", "block", "protect", "force_check"}:
            lines = [intent.intention]
        for idx, line in enumerate(lines, start=1):
            fact_id = self._fact_id_for_text(state, line)
            if not fact_id and idx - 1 < len(fact_ids):
                candidate = fact_ids[idx - 1]
                if self._line_mentions_fact(state, line, candidate):
                    fact_id = candidate
            exposes: list[str] = []
            segment_withheld_fact_ids: list[str] = []
            segment_withheld_summaries: list[str] = []
            spoken_text = line
            content_summary = line
            if fact_id:
                if self._can_expose_fact(state, intent, fact_id, idx):
                    exposes = [fact_id]
                else:
                    spoken_text = self._safe_spoken_text_for_blocked_fact(state, intent, fact_id)
                    content_summary = spoken_text
                    withheld_fact_ids.append(fact_id)
                    withheld_summaries.append(spoken_text)
                    segment_withheld_fact_ids.append(fact_id)
                    segment_withheld_summaries.append(spoken_text)
            segments.append(
                SpeechSegment(
                    segment_id=f"{intent.intent_id}_seg_{idx:02d}",
                    speaker=intent.agent_id,
                    content_summary=content_summary,
                    spoken_text=spoken_text,
                    exposes_fact_ids=exposes,
                    withheld_fact_ids=segment_withheld_fact_ids,
                    withheld_summaries=segment_withheld_summaries,
                    exposure_level=self._exposure_level(state, fact_id if exposes else None),
                    interruptible=True,
                    trigger_keywords=self._trigger_keywords(spoken_text, state, fact_id),
                    intent_source=source,
                )
            )
        withheld_fact_ids.extend(self._fact_ids_for_texts(state, intent.will_hide))
        plan = SpeechPlan(
            speech_plan_id=f"plan_{intent.intent_id}",
            speaker=intent.agent_id,
            topic=intent.topic,
            speech_goal=intent.intention,
            segments=segments,
            withheld_fact_ids=list(dict.fromkeys(withheld_fact_ids)),
            withheld_summaries=list(dict.fromkeys(withheld_summaries)),
            source_intent_id=intent.intent_id,
            intent_source="agent_mind",
        )
        intent.speech_plan = plan
        return plan

    def _ordered_fact_ids(self, state: WorldState, intent: AgentIntent) -> List[str]:
        fact_ids: List[str] = []
        for fact_id in list(intent.claimed_fact_ids) + list(intent.referenced_fact_ids):
            if fact_id and fact_id not in fact_ids:
                fact_ids.append(fact_id)
        for fact_id in self._fact_ids_for_texts(state, intent.claimed_facts + intent.will_say):
            if fact_id not in fact_ids:
                fact_ids.append(fact_id)
        return fact_ids

    def _can_expose_fact(self, state: WorldState, intent: AgentIntent, fact_id: str, segment_index: int) -> bool:
        entry = state.world.fact_exposure.get(fact_id)
        if not entry:
            return False
        if intent.agent_id not in entry.known_by:
            return False
        if intent.pressure_level < entry.min_pressure_to_reveal:
            return False
        if segment_index < entry.min_rounds_to_reveal:
            return False
        if intent.action_type not in {"answer", "share_info", "trade_info"} and intent.pressure_level < 4:
            return False
        if entry.reveal_stage in {"forbidden", "secret"} and intent.pressure_level < 4:
            return False
        return True

    def _safe_spoken_text_for_blocked_fact(self, state: WorldState, intent: AgentIntent, fact_id: str) -> str:
        entry = state.world.fact_exposure.get(fact_id)
        label = entry.public_label if entry and entry.public_label else fact_id
        if intent.action_type in {"ask", "challenge", "accuse", "call_out"}:
            return f"There is something off about {label}."
        if intent.action_type in {"withhold", "refuse", "lie"}:
            return "I am not ready to spell that out."
        if intent.topic:
            return f"We should be careful about {intent.topic}."
        return f"Something about {label} does not add up."

    @staticmethod
    def _fact_ids_for_texts(state: WorldState, texts: List[str]) -> List[str]:
        fact_ids: List[str] = []
        for text in texts:
            for fact_id, entry in state.world.fact_exposure.items():
                if text == fact_id or text == entry.truth or text == entry.public_label:
                    if fact_id not in fact_ids:
                        fact_ids.append(fact_id)
        return fact_ids

    @staticmethod
    def _fact_id_for_text(state: WorldState, text: str) -> str | None:
        for fact_id, entry in state.world.fact_exposure.items():
            if text == fact_id or text == entry.truth or text == entry.public_label:
                return fact_id
        return None

    @staticmethod
    def _line_mentions_fact(state: WorldState, text: str, fact_id: str) -> bool:
        entry = state.world.fact_exposure.get(fact_id)
        if not entry:
            return False
        return text in {fact_id, entry.truth, entry.public_label}

    @staticmethod
    def _exposure_level(state: WorldState, fact_id: str | None) -> str:
        if not fact_id:
            return "safe"
        entry = state.world.fact_exposure.get(fact_id)
        if not entry:
            return "medium"
        if entry.reveal_stage in {"hidden_fact", "secret", "forbidden"}:
            return "high"
        return "medium"

    @staticmethod
    def _trigger_keywords(text: str, state: WorldState | None = None, fact_id: str | None = None) -> List[str]:
        keywords: List[str] = []
        if fact_id:
            keywords.append(fact_id)
            if state and fact_id in state.world.fact_exposure:
                label = state.world.fact_exposure[fact_id].public_label
                if label:
                    keywords.append(label)
        tokens = [token.strip().lower() for token in re.split(r"[\s，。！？；：、,.!?;:\"'（）()]+", text) if token.strip()]
        for token in tokens:
            if len(token) > 1 and token not in keywords:
                keywords.append(token)
        return keywords[:5]
