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

    def generate_chapter(self, sim_dir: Path, world: WorldConfig, chapter_plan: Dict = None) -> None:
        state = self.state_svc.load(sim_dir)
        plot_events = self.event_svc.read_plot_events(sim_dir)
        if not plot_events:
            # fallback：取最后几条 raw 事件避免空稿
            plot_events = self.event_svc.read_all(sim_dir)[-8:]

        plan = self._build_plan(state, world, plot_events, chapter_plan)
        (sim_dir / self.CHAPTER_PLAN_FILE).write_text(
            json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        draft = self._write_draft(state, world, plot_events, plan)
        (sim_dir / self.CHAPTER_DRAFT_FILE).write_text(draft, encoding="utf-8")

    def _build_plan(self, state: WorldState, world: WorldConfig, events: List[EventLog], chapter_plan: Dict = None) -> Dict:
        title = "入口区的回声"
        for e in events:
            if "锁" in e.result:
                title = "生锈的新锁"
                break

        plan = {
            "chapter": 1,
            "title": title,
            "pov": world.chapter_goal.pov,
            "chapter_goal": state.chapter_goal_status.goal,
            "core_events": [e.event_id for e in events],
            "ending_hook": "他忽然意识到：这里一定有人还在进出。",
        }

        # V1.1 合并传入的 chapter_plan 中的新字段
        if chapter_plan:
            plan["clue_budget"] = chapter_plan.get("clue_budget", {})
            plan["selected_clues"] = chapter_plan.get("selected_clues", [])
            plan["reserved_clues"] = chapter_plan.get("reserved_clues", [])
            plan["required_character_beats"] = chapter_plan.get("required_character_beats", [])
            plan["opening_policy_applied"] = chapter_plan.get("opening_policy_applied", False)

            # 使用 opening policy 生成的 ending_hook（如果有）
            if chapter_plan.get("ending_hook"):
                hook_spec = chapter_plan["ending_hook"]
                if isinstance(hook_spec, dict) and hook_spec.get("type") == "subtle_anomaly":
                    allowed_devices = hook_spec.get("allowed_devices", [])
                    if allowed_devices:
                        plan["ending_hook"] = allowed_devices[0]  # 使用第一个作为钩子
                elif isinstance(hook_spec, str):
                    plan["ending_hook"] = hook_spec

        return plan

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

        # V1.1 1) Required Character Beats - 主角情感动机展示
        required_beats = plan.get("required_character_beats", [])
        if required_beats:
            for beat in required_beats:
                beat_text = self._character_beat_to_text(pov_name, beat)
                if beat_text:
                    lines.append(beat_text)
                    lines.append("")

        lines.append(f"{loc.public_description}")
        lines.append("")

        for e in events:
            lines.append(self._event_to_paragraph(pov_name, e))
            lines.append("")

        # 收束
        lines.append("他把那点不安压回喉咙里，像把一枚硬币塞进旧口袋。")
        lines.append("如果这里真的早已废弃，就不该留下这么多“新”的痕迹。")

        # V1.1 3) Ending Hook - 结尾轻异常钩子
        ending_hook = plan.get("ending_hook", "")
        if ending_hook:
            if isinstance(ending_hook, str):
                lines.append(ending_hook)
            elif isinstance(ending_hook, dict) and ending_hook.get("type") == "subtle_anomaly":
                devices = ending_hook.get("allowed_devices", [])
                if devices:
                    lines.append(f"空气中忽然传来{devices[0]}——")
        lines.append("")
        return "\n".join([l for l in lines if l is not None])

    def _character_beat_to_text(self, pov_name: str, beat: Dict) -> str:
        """
        V1.1 将角色情感 beat 转换为自然文本
        """
        beat_id = beat.get("beat_id", "")
        content_hint = beat.get("content_hint", "")

        if content_hint:
            return f"{pov_name}想起了{content_hint}。"
        if beat_id == "beat_last_call_memory":
            return f"{pov_name}想起某个被自己忽略过的求助瞬间，那段记忆正在改变此刻的判断。"
        return ""

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
