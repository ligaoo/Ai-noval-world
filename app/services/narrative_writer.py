from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

from app.models.event import EventLog
from app.models.state import WorldState
from app.models.world import WorldConfig
from app.services.event_log_service import EventLogService
from app.services.world_state_service import WorldStateService


class NarrativeWriterService:
    """
    V1 小说生成：不依赖大模型也能跑通（模板改写）。
    后续可替换为 LLM 改写器，只要保持输入=事件、输出=正文即可。
    """

    CHAPTER_PLAN_FILE = "chapter_plan.json"
    CHAPTER_DRAFT_FILE = "chapter_draft.md"

    def __init__(self):
        self.event_svc = EventLogService()
        self.state_svc = WorldStateService()

    def generate_chapter(self, sim_dir: Path, world: WorldConfig) -> None:
        state = self.state_svc.load(sim_dir)
        plot_events = self.event_svc.read_plot_events(sim_dir)
        if not plot_events:
            # fallback：取最后几条 raw 事件避免空稿
            plot_events = self.event_svc.read_all(sim_dir)[-8:]

        plan = self._build_plan(state, world, plot_events)
        (sim_dir / self.CHAPTER_PLAN_FILE).write_text(
            json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        draft = self._write_draft(state, world, plot_events, plan)
        (sim_dir / self.CHAPTER_DRAFT_FILE).write_text(draft, encoding="utf-8")

    def _build_plan(self, state: WorldState, world: WorldConfig, events: List[EventLog]) -> Dict:
        title = "入口区的回声"
        for e in events:
            if "锁" in e.result:
                title = "生锈的新锁"
                break
        return {
            "chapter": 1,
            "title": title,
            "pov": world.chapter_goal.pov,
            "chapter_goal": state.chapter_goal_status.goal,
            "core_events": [e.event_id for e in events],
            "ending_hook": "他忽然意识到：这里一定有人还在进出。",
        }

    def _write_draft(self, state: WorldState, world: WorldConfig, events: List[EventLog], plan: Dict) -> str:
        pov_id = world.chapter_goal.pov
        pov_name = world.characters.get_character(pov_id).name
        loc = world.map.get_location(state.characters[pov_id].location_id)

        # 元数据（便于一致性检查）：本章允许出现的线索 id（已发现）
        discovered = [cid for cid, ok in state.world.discovered_facts.items() if ok]
        meta = f"<!-- POV:{pov_id} ALLOWED_CLUES:{','.join(discovered)} -->"

        lines: List[str] = []
        lines.append(meta)
        lines.append(f"# 第1章：{plan['title']}")
        lines.append("")
        lines.append(f"{loc.public_description}")
        lines.append("")

        for e in events:
            lines.append(self._event_to_paragraph(pov_name, e))
            lines.append("")

        # 收束
        lines.append("他把那点不安压回喉咙里，像把一枚硬币塞进旧口袋。")
        lines.append("如果这里真的早已废弃，就不该留下这么多“新”的痕迹。")
        lines.append(plan.get("ending_hook", ""))
        lines.append("")
        return "\n".join([l for l in lines if l is not None])

    @staticmethod
    def _event_to_paragraph(pov_name: str, e: EventLog) -> str:
        # V1：只基于 e.result 做有限第三人称改写，避免新增事实。
        if e.event_type == "soft_hint":
            return f"{pov_name}停住脚步。{e.result}"
        if e.action and e.action.action_type in ("ask", "talk"):
            topic = e.action.topic or "某个话题"
            # topic 可能是对象 id（如 hospital_gate_lock），这里做一次“更像人话”的降噪
            topic = {
                "hospital_gate_lock": "那把挂锁",
                "night_visitors": "夜里是否有人来过",
                "hospital_history": "旧医院的传闻",
            }.get(topic, topic)
            return f"{pov_name}把话题绕到“{topic}”上，试图从对方的反应里挤出一点缝隙。{e.result}"
        if e.action and e.action.action_type == "inspect":
            return f"{pov_name}俯下身，耐着性子去看。{e.result}"
        if e.action and e.action.action_type == "search":
            return f"{pov_name}伸手拨开灰尘，翻找可能留下的东西。{e.result}"
        if e.action and e.action.action_type == "observe":
            return f"{pov_name}抬眼打量四周，像是在为自己找一个更确定的解释。{e.result}"
        if e.action and e.action.action_type == "wait":
            return f"{pov_name}没有贸然推进，只让时间先走一步。{e.result}"
        return e.result
