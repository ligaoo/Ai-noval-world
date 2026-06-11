from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple

from app.models.chapter_brief import ChapterBrief
from app.models.event import EventLog
from app.models.scene_plan import CompressedEventGroup, DiscardedEvent, SelectedEvent, SelectedEventsReport
from app.models.world import WorldConfig


class EventSelectionService:
    def __init__(self, world: WorldConfig):
        self.world = world

    def select(self, events: List[EventLog], chapter_brief: ChapterBrief) -> SelectedEventsReport:
        plot_events = [event for event in events if event.event_level == "plot"] or events
        scored = [(event, self._score_event(event, chapter_brief)) for event in plot_events]
        scored.sort(key=lambda item: item[1], reverse=True)

        selected: List[SelectedEvent] = []
        discarded: List[DiscardedEvent] = []
        compressed_groups = self._compress_low_value_events(plot_events, scored)
        selected_ids = set()
        selected_semantic_keys = set()
        viable_scored = []
        blocked_scored = []
        for event, score in scored:
            blocked_reason = self._location_block_reason(event, chapter_brief)
            if blocked_reason:
                blocked_scored.append((event, score, blocked_reason))
                discarded.append(DiscardedEvent(event_id=event.event_id, reason=blocked_reason))
            else:
                viable_scored.append((event, score))

        selection_pool = viable_scored or [(event, score) for event, score, _ in blocked_scored[:1]]

        for event, score in selection_pool:
            if score < 3 and len(selected) >= 5:
                discarded.append(DiscardedEvent(event_id=event.event_id, reason="低价值事件：未明显推进线索、关系或风险。"))
                continue
            if event.event_id in selected_ids:
                continue
            semantic_key = self._semantic_key(event)
            if semantic_key in selected_semantic_keys:
                discarded.append(DiscardedEvent(event_id=event.event_id, reason="语义重复事件：已由同类结果进入章节骨架。"))
                continue
            selected.append(self._to_selected_event(event, score, chapter_brief))
            selected_ids.add(event.event_id)
            selected_semantic_keys.add(semantic_key)
            if len(selected) >= 8:
                break

        if len(selected) < min(5, len(selection_pool)):
            for event, score in selection_pool:
                if event.event_id in selected_ids:
                    continue
                semantic_key = self._semantic_key(event)
                if semantic_key in selected_semantic_keys:
                    continue
                selected.append(self._to_selected_event(event, score, chapter_brief))
                selected_ids.add(event.event_id)
                selected_semantic_keys.add(semantic_key)
                if len(selected) >= min(5, len(selection_pool)):
                    break

        selected.sort(key=lambda item: self._event_order(plot_events).get(item.event_id, 0))
        selected_ids = {item.event_id for item in selected}
        for event in plot_events:
            if event.event_id not in selected_ids and not any(event.event_id in group.source_event_ids for group in compressed_groups):
                discarded.append(DiscardedEvent(event_id=event.event_id, reason="未进入核心场景骨架。"))

        return SelectedEventsReport(
            selected_events=selected,
            compressed_events=compressed_groups,
            discarded_events=discarded,
        )

    def save(self, sim_dir: Path, report: SelectedEventsReport) -> None:
        with open(sim_dir / "selected_events.json", "w", encoding="utf-8") as f:
            json.dump(report.model_dump(), f, ensure_ascii=False, indent=2)

    @staticmethod
    def load(sim_dir: Path) -> SelectedEventsReport | None:
        path = sim_dir / "selected_events.json"
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return SelectedEventsReport.model_validate(json.load(f))
        except Exception:
            return None

    def _score_event(self, event: EventLog, chapter_brief: ChapterBrief) -> float:
        pv = event.plot_value
        score = (
            pv.progress * 2
            + pv.mystery * 1.5
            + pv.conflict * 1.5
            + pv.danger
            + pv.relationship * 1.5
            + pv.novelty
            + pv.emotion
        )
        if event.discovered_facts:
            score += 4
            if self._has_consequence(event):
                score += 2
        if event.hidden_effects:
            score += 2
        if event.source_interaction:
            score += 2
        if event.action and event.action.action_type not in {"observe", "wait"}:
            score += 1.5
        if event.action and event.action.risk_level in {"medium", "high"}:
            score += 1.5
        if event.event_type in {"wait", "idle"}:
            score -= 3
        if event.event_type in {"observe", "inspect", "search"}:
            score += 1
        if self._is_passive_information_event(event):
            score -= 1.5
        policy = getattr(chapter_brief, "location_policy", None)
        if policy:
            preferred = set(getattr(policy, "preferred_location_ids", []) or [])
            allowed = set(getattr(policy, "allowed_location_ids", []) or [])
            if event.location_id in preferred:
                score += 2
            if allowed and event.location_id not in allowed:
                score -= 6
        text = event.result or ""
        for clue_id in chapter_brief.must_include_clues:
            if clue_id and clue_id in text:
                score += 3
        return max(score, 0)

    def _to_selected_event(self, event: EventLog, score: float, chapter_brief: ChapterBrief) -> SelectedEvent:
        role = self._scene_role(event)
        thread_ids = self._related_threads(event, chapter_brief)
        return SelectedEvent(
            event_id=event.event_id,
            importance=round(score, 2),
            scene_role=role,
            reason=self._reason_for(event, role),
            location_id=event.location_id or "",
            thread_ids=thread_ids,
            character_impact=[{"character_id": actor, "impact": self._impact_for(event)} for actor in event.actors[:3]],
            reader_question=self._reader_question(event, thread_ids),
        )

    def _compress_low_value_events(
        self,
        events: List[EventLog],
        scored: List[Tuple[EventLog, float]],
    ) -> List[CompressedEventGroup]:
        low_scores: Dict[str, float] = {event.event_id: score for event, score in scored if score < 3}
        groups: List[CompressedEventGroup] = []
        current_key = ""
        current_ids: List[str] = []
        for event in events:
            if event.event_id not in low_scores or event.event_type not in {"observe", "wait"}:
                if len(current_ids) >= 2:
                    groups.append(CompressedEventGroup(source_event_ids=current_ids, summary=f"角色在 {current_key} 附近进行低强度观察或等待，未产生新的核心事实。"))
                current_key = ""
                current_ids = []
                continue
            key = event.location_id or "unknown"
            if current_key and key != current_key:
                if len(current_ids) >= 2:
                    groups.append(CompressedEventGroup(source_event_ids=current_ids, summary=f"角色在 {current_key} 附近进行低强度观察或等待，未产生新的核心事实。"))
                current_ids = []
            current_key = key
            current_ids.append(event.event_id)
        if len(current_ids) >= 2:
            groups.append(CompressedEventGroup(source_event_ids=current_ids, summary=f"角色在 {current_key} 附近进行低强度观察或等待，未产生新的核心事实。"))
        return groups

    @classmethod
    def _semantic_key(cls, event: EventLog) -> str:
        facts = ",".join(sorted(str(fact) for fact in event.discovered_facts))
        text = cls._normalize_text(event.result or "")[:80]
        return "|".join([
            event.event_type or "",
            event.location_id or "",
            facts,
            text,
        ])

    @staticmethod
    def _normalize_text(text: str) -> str:
        return "".join(str(text or "").split())

    @staticmethod
    def _scene_role(event: EventLog) -> str:
        pv = event.plot_value
        if event.discovered_facts or pv.progress >= 5:
            return "reveal"
        if pv.relationship >= 4:
            return "relationship_turn"
        if pv.conflict >= 5:
            return "escalation"
        if pv.danger >= 5:
            return "escalation"
        if pv.mystery >= 5:
            return "misdirection"
        return "setup"

    @staticmethod
    def _reason_for(event: EventLog, role: str) -> str:
        role_text = {
            "setup": "建立场景、目标或异常基础。",
            "escalation": "提高冲突、危险或行动压力。",
            "reveal": "推进线索或确认可见事实。",
            "misdirection": "制造不确定感或误导。",
            "relationship_turn": "改变角色之间的信任或压力。",
        }.get(role, "推进章节骨架。")
        return f"{role_text} 来源事件：{event.result[:80]}"

    @staticmethod
    def _impact_for(event: EventLog) -> str:
        if event.discovered_facts:
            return "获得新事实或线索，需要调整判断。"
        if event.plot_value.conflict > 0:
            return "承受关系或行动压力。"
        if event.plot_value.danger > 0:
            return "感受到风险上升。"
        return "对当前异常产生新的观察。"

    @staticmethod
    def _reader_question(event: EventLog, thread_ids: List[str]) -> str:
        if thread_ids:
            return f"这个事件如何推进悬念 {thread_ids[0]}？"
        if event.discovered_facts:
            return "这条线索真正指向什么？"
        return ""

    @staticmethod
    def _related_threads(event: EventLog, chapter_brief: ChapterBrief) -> List[str]:
        text = event.result or ""
        facts = " ".join(str(fact) for fact in event.discovered_facts)
        haystack = f"{text} {facts}"
        result = [thread for thread in chapter_brief.must_advance_threads if thread and thread in haystack]
        return result[:3]

    @staticmethod
    def _event_order(events: List[EventLog]) -> Dict[str, int]:
        return {event.event_id: index for index, event in enumerate(events)}

    @staticmethod
    def _location_block_reason(event: EventLog, chapter_brief: ChapterBrief) -> str:
        policy = getattr(chapter_brief, "location_policy", None)
        if not policy:
            return ""
        location_id = event.location_id or ""
        if location_id and location_id in set(getattr(policy, "forbidden_location_ids", []) or []):
            return f"章节地点边界禁止：{location_id}"
        allowed = set(getattr(policy, "allowed_location_ids", []) or [])
        if allowed and location_id and location_id not in allowed:
            return f"非本章允许地点：{location_id}"
        return ""

    @staticmethod
    def _has_consequence(event: EventLog) -> bool:
        action_result = getattr(event, "action_result", None)
        state_changes = getattr(action_result, "state_changes", None) if action_result else None
        relationship_changes = getattr(action_result, "relationship_changes", None) if action_result else None
        return bool(
            event.hidden_effects
            or state_changes
            or relationship_changes
            or event.plot_value.conflict > 0
            or event.plot_value.danger > 0
            or event.plot_value.relationship > 0
            or event.plot_value.emotion > 0
        )

    @classmethod
    def _is_passive_information_event(cls, event: EventLog) -> bool:
        action_type = event.action.action_type if event.action else event.event_type
        passive_action = action_type in {"observe", "inspect", "search", "ask", "talk", "wait"}
        return bool(event.discovered_facts and passive_action and not cls._has_consequence(event))
