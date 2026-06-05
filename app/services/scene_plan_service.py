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
        selected = selected_events.selected_events
        groups = self._group_selected_events(selected)
        scenes: List[SceneSpec] = []

        for index, group in enumerate(groups, start=1):
            group_events = [event_map[event.event_id] for event in group if event.event_id in event_map]
            if not group_events:
                continue
            primary = group_events[0]
            scene_id = f"scene_{index:03d}"
            scene_role = self._dominant_role([event.scene_role for event in group])
            scenes.append(
                SceneSpec(
                    scene_id=scene_id,
                    scene_goal=self._scene_goal(scene_role, chapter_brief),
                    location_id=primary.location_id,
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

    @staticmethod
    def _group_selected_events(selected) -> List[list]:
        if not selected:
            return []
        target_scene_count = 1
        if len(selected) >= 5:
            target_scene_count = 2
        if len(selected) >= 8:
            target_scene_count = 3
        target_scene_count = min(target_scene_count, 4)
        chunk_size = max(1, (len(selected) + target_scene_count - 1) // target_scene_count)
        return [selected[i:i + chunk_size] for i in range(0, len(selected), chunk_size)][:4]

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
