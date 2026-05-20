from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

from app.models.state import WorldState
from app.models.tension import InterventionProposal, PlotValue, TensionReport


class DirectorService:
    """
    V3.1：导演服务
    根据张力报告，决定是否干预、如何干预。
    只改变环境机会，不直接替角色做决定。
    """

    def __init__(self, world_config_dir: Path):
        self.world_config_dir = world_config_dir
        self.intervention_history: List[InterventionProposal] = []
        self.intervention_count = 0
        self.last_intervention_tick: int = 0
        self.cooldown_ticks: int = 3  # 干预冷却间隔

    def propose_intervention(
        self,
        state: WorldState,
        tension_report: TensionReport,
        chapter_goal: str,
    ) -> Optional[InterventionProposal]:
        """根据当前状态提出干预建议"""

        if not tension_report.need_intervention:
            return None

        # 冷却机制：避免频繁干预
        if state.tick - self.last_intervention_tick < self.cooldown_ticks:
            return None

        # 总干预数限制（避免过度干预
        if self.intervention_count >= 5:
            return None

        diagnosis = tension_report.diagnosis
        recommendations = tension_report.recommended_intervention_types

        # 选择干预类型（优先解决主线问题）
        intervention_type = self._select_best_intervention(recommendations, diagnosis)

        if not intervention_type:
            return None

        # 生成具体干预内容
        proposal = self._generate_intervention(
            intervention_type, state, chapter_goal, diagnosis
        )

        if proposal:
            self.intervention_history.append(proposal)
            self.intervention_count += 1

        return proposal

    def _select_best_intervention(
        self, recommendations: List[str], diagnosis: List[str]
    ) -> Optional[str]:
        """选择最合适的干预类型"""

        # 优先级：主线推进 > 悬念 > 冲突 > 危险
        priority_order = [
            "environment_hint",   # 最高优先级：解决停滞
            "npc_pressure",       # 冲突/互动
            "danger_signal",      # 增加紧张感
            "relationship_trigger",  # 关系变化
        ]

        for t in priority_order:
            if t in recommendations:
                return t

        return recommendations[0] if recommendations else None

    def _generate_intervention(
        self,
        intervention_type: str,
        state: WorldState,
        chapter_goal: str,
        diagnosis: List[str],
    ) -> Optional[InterventionProposal]:
        """生成具体干预内容"""

        # 确定主角所在地点（作为默认目标）
        pov_char = next(iter(state.characters.keys()), None)
        if not pov_char:
            return None
        target_location = state.characters[pov_char].location_id

        # 根据类型生成内容
        if intervention_type == "environment_hint":
            return self._make_environment_hint(target_location, diagnosis)
        elif intervention_type == "npc_pressure":
            return self._make_npc_pressure(target_location, diagnosis)
        elif intervention_type == "danger_signal":
            return self._make_danger_signal(target_location, diagnosis)
        elif intervention_type == "time_pressure":
            return self._make_time_pressure(diagnosis)
        else:
            return None

    def _make_environment_hint(
        self, location: str, diagnosis: List[str]
    ) -> InterventionProposal:
        """环境暗示：开放新的探索机会"""

        hints = {
            "old_hospital_entrance": [
                "看门人的值班室里传来纸张翻动的声音。",
                "铁锁在风中微微晃动，发出单调的金属声响。",
                "医院深处传来一阵轻微的、不自然的回声。",
            ],
            "hospital_lobby": [
                "前台后方有一只抽屉微微敞开，像是刚被人翻过。",
                "地面上有几道新鲜的脚印，一直延伸到走廊深处。",
                "墙壁上有一扇不起眼的小门，门把手上没有积灰。",
            ],
            "archive_room": [
                "某个文件柜的抽屉虚掩着，里面似乎还留着东西。",
                "角落里掉着一张皱巴巴的便签纸，看不清字迹。",
                "窗户缝里漏进一丝冷风，带着淡淡的消毒水味。",
            ],
        }

        hint_list = hints.get(location, hints["hospital_lobby"])
        content = hint_list[self.intervention_count % len(hint_list)]

        return InterventionProposal(
            need_intervention=True,
            reason="主线推进不足，提供新的探索机会",
            intervention_type="environment_hint",
            target_location=location,
            content=content,
            allowed_followup_actions=["observe", "inspect", "search", "move"],
            forbidden_effects=[
                "不能直接暴露核心真相",
                "不能让角色凭空知道线索内容",
            ],
            plot_value=PlotValue(
                progress=2,
                mystery=4,
                conflict=0,
                danger=1,
                relationship=0,
                novelty=3,
                emotion=2,
            ),
        )

    def _make_npc_pressure(
        self, location: str, diagnosis: List[str]
    ) -> InterventionProposal:
        """NPC 压力：增加冲突，推进对话"""

        pressure_content = {
            "old_hospital_entrance": [
                "老周忽然挡在入口处，手按在门把手上。",
                "看门人语气明显紧张，手在微微发抖。",
            ],
            "hospital_lobby": [
                "身后传来脚步声，有人正在靠近。",
                "走廊尽头闪过一个人影，又迅速消失。",
            ],
        }

        content = pressure_content.get(
            location, pressure_content["hospital_lobby"]
        )[0]

        return InterventionProposal(
            need_intervention=True,
            reason="冲突强度偏低，增加 NPC 压力",
            intervention_type="npc_pressure",
            target_location=location,
            content=content,
            allowed_followup_actions=["ask", "talk", "observe", "inspect"],
            forbidden_effects=[
                "不能直接暴露 NPC 知道的全部真相",
                "不能让 NPC 做出不符合设定的行为",
            ],
            plot_value=PlotValue(
                progress=1,
                mystery=3,
                conflict=5,
                danger=2,
                relationship=3,
                novelty=2,
                emotion=4,
            ),
        )

    def _make_danger_signal(
        self, location: str, diagnosis: List[str]
    ) -> InterventionProposal:
        """危险信号：增加紧张气氛"""

        danger_content = [
            "灯光忽明忽暗，电流发出滋滋的声响。",
            "某个房间里传来东西碎裂的声音。",
            "空气中开始弥漫一股奇怪的气味。",
            "手机信号忽然完全消失了。",
        ]

        content = danger_content[self.intervention_count % len(danger_content)]

        return InterventionProposal(
            need_intervention=True,
            reason="危险感不足，增加紧张气氛",
            intervention_type="danger_signal",
            target_location=location,
            content=content,
            allowed_followup_actions=["observe", "inspect", "move"],
            forbidden_effects=[
                "不能直接造成角色伤害",
                "不能暴露超自然元素的核心真相",
            ],
            plot_value=PlotValue(
                progress=0,
                mystery=5,
                conflict=1,
                danger=6,
                relationship=0,
                novelty=4,
                emotion=5,
            ),
        )

    def _make_time_pressure(self, diagnosis: List[str]) -> InterventionProposal:
        """时间压力：压缩行动窗口"""

        time_hints = [
            "远处传来警车巡逻的声音，时间不多了。",
            "墙上的老钟开始报时，每一声都像是在倒数。",
            "天色暗得比想象中更快，医院里越来越黑。",
        ]

        content = time_hints[self.intervention_count % len(time_hints)]

        return InterventionProposal(
            need_intervention=True,
            reason="节奏拖沓，增加时间压力",
            intervention_type="time_pressure",
            target_location="global",
            content=content,
            allowed_followup_actions=["inspect", "search", "move", "ask"],
            forbidden_effects=[
                "不能直接结束游戏",
                "不能让时间突然跳到不可挽回的地步",
            ],
            plot_value=PlotValue(
                progress=1,
                mystery=2,
                conflict=2,
                danger=4,
                relationship=0,
                novelty=1,
                emotion=3,
            ),
        )

    def save_history(self, output_dir: Path) -> None:
        """保存干预历史"""
        history_file = output_dir / "director_history.jsonl"
        with open(history_file, "w", encoding="utf-8") as f:
            for proposal in self.intervention_history:
                # Pydantic V2 model_dump_json 不支持 ensure_ascii，使用 json.dumps
                data = proposal.model_dump()
                f.write(json.dumps(data, ensure_ascii=False) + "\n")
