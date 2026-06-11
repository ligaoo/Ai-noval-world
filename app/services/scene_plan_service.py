from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

from app.models.chapter_brief import ChapterBrief
from app.models.event import EventLog
from app.models.scene_plan import ChapterHook, ScenePlan, SceneRevealBudget, SceneSpec, SelectedEventsReport
from app.models.world import WorldConfig


class ScenePlanService:
    def __init__(self, world: WorldConfig):
        self.world = world

    def build(
        self,
        selected_events: SelectedEventsReport,
        chapter_brief: ChapterBrief,
        events: List[EventLog],
        reveal_budget=None,
        quality_controls=None,
    ) -> ScenePlan:
        event_map = {event.event_id: event for event in events}
        selected = self._dedupe_selected_events(selected_events.selected_events)
        groups = self._group_selected_events(selected)
        scenes: List[SceneSpec] = []

        for index, group in enumerate(groups, start=1):
            group_events = [event_map[event.event_id] for event in group if event.event_id in event_map]
            if not group_events:
                continue
            primary = group_events[0]
            scene_id = f"scene_{index:03d}"
            scene_role = self._dominant_role([event.scene_role for event in group])
            location_id = self._group_location_id(group, primary.location_id)
            scenes.append(
                SceneSpec(
                    scene_id=scene_id,
                    scene_goal=self._scene_goal(scene_role, chapter_brief),
                    location_id=location_id,
                    pov_state=self._pov_state(primary),
                    conflict=self._conflict_for(scene_role, group_events),
                    event_ids=[event.event_id for event in group_events],
                    scene_role=scene_role,
                    reveal_budget=SceneRevealBudget(
                        allowed=[item.fact for item in reveal_budget.allowed_reveals[:3]] if reveal_budget else chapter_brief.reveal_policy.allowed_facts[:3],
                        suspected=[item.fact for item in reveal_budget.suspected_only[:4]] if reveal_budget else chapter_brief.reveal_policy.suspected_facts[:4],
                        forbidden=[item.fact for item in reveal_budget.forbidden_reveals] if reveal_budget else chapter_brief.reveal_policy.forbidden_facts,
                    ),
                    emotional_turn=self._emotional_turn(scene_role),
                    ending_beat=self._ending_beat(group_events[-1], scene_role),
                    protagonist_goal=self._protagonist_goal(scene_role, chapter_brief),
                    obstacle_or_pressure=self._obstacle_or_pressure(scene_role, group_events),
                    choice_or_test=self._choice_or_test(group_events),
                    consequence_or_change=self._consequence_or_change(group_events),
                    information_action_pair=self._information_action_pair(group_events),
                )
            )

        hook_event_id = scenes[-1].event_ids[-1] if scenes and scenes[-1].event_ids else None
        return ScenePlan(
            chapter_title=chapter_brief.chapter_title_hint or "序章",
            pov=self.world.chapter_goal.pov,
            scenes=scenes,
            chapter_hook=ChapterHook(
                type=chapter_brief.ending_hook.type,
                event_id=hook_event_id,
                requirement=chapter_brief.ending_hook.requirement,
            ),
            source_notes={
                "selected_event_count": len(selected),
                "compressed_event_count": len(selected_events.compressed_events),
                "chapter_brief_version": chapter_brief.version,
                "location_policy": self._location_policy_dict(chapter_brief),
            },
        )

    def save(self, sim_dir: Path, scene_plan: ScenePlan) -> None:
        with open(sim_dir / "scene_plan.json", "w", encoding="utf-8") as f:
            json.dump(scene_plan.model_dump(), f, ensure_ascii=False, indent=2)

    @staticmethod
    def load(sim_dir: Path) -> Optional[ScenePlan]:
        path = sim_dir / "scene_plan.json"
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return ScenePlan.model_validate(json.load(f))
        except Exception:
            return None

    @classmethod
    def _dedupe_selected_events(cls, selected) -> List:
        result = []
        seen = set()
        for event in selected:
            key = cls._selected_semantic_key(event)
            if key in seen:
                continue
            seen.add(key)
            result.append(event)
        return result

    @staticmethod
    def _selected_semantic_key(event) -> str:
        reason = "".join(str(getattr(event, "reason", "") or "").split())[:80]
        threads = ",".join(getattr(event, "thread_ids", []) or [])
        return f"{getattr(event, 'scene_role', '')}|{threads}|{reason}"

    @staticmethod
    def _group_selected_events(selected) -> List[list]:
        if not selected:
            return []
        groups: List[list] = []
        current: List = []
        current_location = None
        for event in selected:
            location_id = getattr(event, "location_id", "") or "unknown"
            if current and location_id != current_location:
                groups.append(current)
                current = []
            current.append(event)
            current_location = location_id
        if current:
            groups.append(current)
        if len(groups) <= 4:
            return groups
        merged = groups[:3]
        tail = []
        for group in groups[3:]:
            tail.extend(group)
        merged.append(tail)
        return merged

    @staticmethod
    def _group_location_id(group, fallback: str = "") -> str:
        for event in group:
            location_id = getattr(event, "location_id", "") or ""
            if location_id:
                return location_id
        return fallback or ""

    @staticmethod
    def _location_policy_dict(chapter_brief: ChapterBrief) -> Dict[str, List[str]]:
        policy = getattr(chapter_brief, "location_policy", None)
        if not policy:
            return {}
        if hasattr(policy, "model_dump"):
            return policy.model_dump()
        return dict(policy) if isinstance(policy, dict) else {}

    @staticmethod
    def _dominant_role(roles: List[str]) -> str:
        priority = ["hook", "reversal", "reveal", "relationship_turn", "escalation", "misdirection", "setup"]
        for role in priority:
            if role in roles:
                return role
        return roles[0] if roles else "setup"

    @staticmethod
    def _scene_goal(scene_role: str, chapter_brief: ChapterBrief) -> str:
        mapping = {
            "setup": "建立本章核心异常与 POV 的行动目标。",
            "escalation": "提高风险或冲突，让角色无法停留在原判断。",
            "reveal": "推进一个可见线索，但不揭示隐藏真相。",
            "misdirection": "制造合理误读，让主问题变得更尖锐。",
            "relationship_turn": "让人物关系出现试探、压力或不信任。",
        }
        return mapping.get(scene_role, chapter_brief.chapter_goal)

    @staticmethod
    def _pov_state(event: EventLog) -> str:
        if event.plot_value.danger >= 5:
            return "警觉且感到风险逼近"
        if event.plot_value.mystery >= 5:
            return "不安，试图用常理解释异常"
        if event.plot_value.conflict >= 5:
            return "克制，但开始防备他人"
        return "观察中保持谨慎"

    @staticmethod
    def _conflict_for(scene_role: str, events: List[EventLog]) -> str:
        if scene_role == "relationship_turn":
            return "角色之间的信息差和动机不透明造成压力。"
        if scene_role == "reveal":
            return "新线索推进判断，但仍留下无法确认的缺口。"
        if scene_role == "escalation":
            return "环境反馈或角色选择让风险升高。"
        if scene_role == "misdirection":
            return "可见事实和主角判断之间出现矛盾。"
        return "现场表象与本章主问题之间存在冲突。"

    @staticmethod
    def _emotional_turn(scene_role: str) -> str:
        return {
            "setup": "观察 -> 不安",
            "escalation": "不安 -> 紧张",
            "reveal": "困惑 -> 推进",
            "misdirection": "观察 -> 怀疑",
            "relationship_turn": "克制 -> 施压",
        }.get(scene_role, "观察 -> 悬念")

    @staticmethod
    def _ending_beat(event: EventLog, scene_role: str) -> str:
        if scene_role == "reveal":
            return f"以线索缺口收束：{event.result[:80]}"
        if scene_role == "relationship_turn":
            return "以一次未说破的反应或回避动作收束。"
        if scene_role == "escalation":
            return "以风险继续逼近的具体动作或感官变化收束。"
        return f"以未解释的异常细节收束：{event.result[:80]}"

    @staticmethod
    def _protagonist_goal(scene_role: str, chapter_brief: ChapterBrief) -> str:
        if chapter_brief.chapter_goal:
            return chapter_brief.chapter_goal
        return {
            "setup": "明确当前处境，并找到下一步可执行目标。",
            "escalation": "在风险升高时保住当前目标。",
            "reveal": "验证新信息是否能改变下一步行动。",
            "misdirection": "判断可见事实中哪些部分不可靠。",
            "relationship_turn": "在信息差中争取主动。",
        }.get(scene_role, "推动本章主目标。")

    @staticmethod
    def _obstacle_or_pressure(scene_role: str, events: List[EventLog]) -> str:
        pressure_event = max(
            events,
            key=lambda event: event.plot_value.conflict + event.plot_value.danger + event.plot_value.relationship,
        )
        if pressure_event.plot_value.conflict > 0:
            return f"冲突压力来自：{pressure_event.result[:80]}"
        if pressure_event.plot_value.danger > 0:
            return f"风险压力来自：{pressure_event.result[:80]}"
        if pressure_event.plot_value.relationship > 0:
            return f"关系压力来自：{pressure_event.result[:80]}"
        return {
            "reveal": "新信息尚无法完全确认，角色必须在不确定中行动。",
            "misdirection": "可见事实可能误导判断。",
            "setup": "当前目标和现场表象之间仍有缺口。",
        }.get(scene_role, "场景需要形成可感知阻力。")

    @staticmethod
    def _choice_or_test(events: List[EventLog]) -> str:
        risky = [event for event in events if event.action and event.action.risk_level in {"medium", "high"}]
        if risky:
            event = risky[0]
            intent = event.action.intent or event.action.method or event.result
            return f"角色采取带风险的行动：{intent[:80]}"
        acted = [event for event in events if event.action and event.action.action_type not in {"observe", "wait"}]
        if acted:
            event = acted[0]
            intent = event.action.intent or event.action.method or event.result
            return f"角色通过行动推进判断：{intent[:80]}"
        return "把观察结果转化为一个明确判断、试探或下一步选择。"

    @staticmethod
    def _consequence_or_change(events: List[EventLog]) -> str:
        for event in events:
            if event.discovered_facts:
                return f"新增事实改变判断：{', '.join(event.discovered_facts[:3])}"
            if event.hidden_effects:
                return f"事件留下隐性后果：{'; '.join(event.hidden_effects[:2])}"
            if event.plot_value.relationship > 0:
                return f"人物关系压力发生变化：{event.result[:80]}"
            if event.plot_value.danger > 0:
                return f"风险状态发生变化：{event.result[:80]}"
            if event.plot_value.progress > 0:
                return f"剧情状态发生变化：{event.result[:80]}"
        return "本场景结束时应让目标、风险、关系或信息状态至少改变一项。"

    @staticmethod
    def _information_action_pair(events: List[EventLog]) -> str:
        info_event = next((event for event in events if event.discovered_facts or event.plot_value.progress > 0), None)
        action_event = next((event for event in events if event.action and event.action.action_type not in {"observe", "wait"}), None)
        if info_event and action_event:
            action_text = action_event.action.intent or action_event.action.method or action_event.result
            return f"信息“{info_event.result[:60]}”需要推动行动“{action_text[:60]}”。"
        if info_event:
            return f"信息“{info_event.result[:80]}”需要引发反应、判断变化或下一步行动。"
        if action_event:
            action_text = action_event.action.intent or action_event.action.method or action_event.result
            return f"行动“{action_text[:80]}”需要带来可见信息或局势变化。"
        return "避免只展示信息；让信息、行动和变化形成因果。"
