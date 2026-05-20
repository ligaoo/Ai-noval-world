from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.models.plot_arc import PlotArc, PlotArcState, StageConfig


class PlotArcService:
    """
    V3.3：剧情阶段管理服务
    管理剧情阶段推进，防止核心真相过早暴露。
    """

    def __init__(self, world_config_dir: Path, world_id: str):
        self.world_config_dir = world_config_dir
        self.world_id = world_id
        self.plot_arc_state: Optional[PlotArcState] = None

        # 加载 plot_arcs.json
        self._load_plot_arcs()

    def _load_plot_arcs(self) -> None:
        """加载剧情弧配置"""
        arcs_file = self.world_config_dir / self.world_id / "plot_arcs.json"

        # 如果配置文件不存在，使用默认配置
        if not arcs_file.exists():
            self._create_default_arc()
            return

        with open(arcs_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        arcs_data = data.get("arcs", [])
        if not arcs_data:
            self._create_default_arc()
            return

        # 激活第一个剧情弧
        active_arc = PlotArc.model_validate(arcs_data[0])
        self.plot_arc_state = PlotArcState(active_arc=active_arc)

    def _create_default_arc(self) -> None:
        """创建默认的医院真相剧情弧"""
        default_stages = [
            StageConfig(
                stage_id="setup",
                name="建立异常",
                purpose="建立医院并非完全废弃的认知",
                required_events=["发现医院锁被更换过"],
                allowed_clue_levels=["surface", "minor"],
                forbidden_revelations=["ten_years_truth", "real_killer_identity"],
            ),
            StageConfig(
                stage_id="investigation",
                name="调查线索",
                purpose="收集旧案相关证据",
                required_events=["发现旧档案记录", "看门人露出破绽"],
                allowed_clue_levels=["surface", "minor", "medium"],
                forbidden_revelations=["real_killer_identity"],
            ),
            StageConfig(
                stage_id="confrontation",
                name="冲突阶段",
                purpose="与隐瞒者产生正面冲突",
                required_events=["看门人承认有人让他封锁医院"],
                allowed_clue_levels=["surface", "minor", "medium", "major"],
                forbidden_revelations=[],
            ),
            StageConfig(
                stage_id="revelation",
                name="真相揭露",
                purpose="揭露部分真相",
                required_events=["主角发现自己十年前来过医院"],
                allowed_clue_levels=["surface", "minor", "medium", "major", "truth"],
                forbidden_revelations=[],
            ),
        ]

        default_arc = PlotArc(
            arc_id="arc_hospital_truth",
            name="旧医院真相篇",
            status="active",
            current_stage="setup",
            progress=0,
            stages=default_stages,
            completed_stages=[],
        )

        self.plot_arc_state = PlotArcState(active_arc=default_arc)

    def get_current_stage(self) -> Optional[StageConfig]:
        """获取当前阶段"""
        if not self.plot_arc_state:
            return None
        return self.plot_arc_state.get_current_stage()

    def can_discover_clue(self, clue: Dict[str, Any]) -> bool:
        """检查线索是否可以在当前阶段发现"""
        if not self.plot_arc_state:
            return True
        return self.plot_arc_state.is_clue_allowed(clue)

    def get_blocked_clue_message(self, clue: Dict[str, Any]) -> str:
        """返回线索被阶段锁定时的模糊提示"""
        level_messages = {
            "medium": [
                "你注意到档案袋上似乎有熟悉的痕迹，但灰尘和光线让你无法确认。",
                "这份文件内容有些模糊，你觉得需要更仔细的条件才能辨认。",
            ],
            "major": [
                "这里藏着什么重要的东西，但现在你的状态让你无法集中注意力。",
                "档案的内容太沉重了，现在还不是面对它的时候。",
            ],
            "truth": [
                "有一个真相就在眼前，但你的潜意识在抗拒它。",
                "这份记录牵扯到你不想触碰的过去，你下意识把它放回去了。",
            ],
        }

        clue_level = clue.get("level", "surface")
        messages = level_messages.get(clue_level, level_messages["medium"])
        return messages[0]

    def record_discovered_clue(self, clue_id: str) -> None:
        """记录已发现的线索"""
        if self.plot_arc_state and clue_id not in self.plot_arc_state.discovered_clue_ids:
            self.plot_arc_state.discovered_clue_ids.append(clue_id)

    def record_triggered_event(self, event_desc: str) -> None:
        """记录已触发的关键事件"""
        if self.plot_arc_state and event_desc not in self.plot_arc_state.triggered_events:
            self.plot_arc_state.triggered_events.append(event_desc)

    def record_question(self, question: str) -> None:
        """记录未解决的问题"""
        if self.plot_arc_state and question not in self.plot_arc_state.unresolved_questions:
            self.plot_arc_state.unresolved_questions.append(question)

    def resolve_question(self, question: str) -> None:
        """标记问题已解决"""
        if self.plot_arc_state:
            if question in self.plot_arc_state.unresolved_questions:
                self.plot_arc_state.unresolved_questions.remove(question)
            if question not in self.plot_arc_state.resolved_questions:
                self.plot_arc_state.resolved_questions.append(question)

    def try_advance_stage(self) -> Optional[str]:
        """尝试推进到下一阶段"""
        if not self.plot_arc_state:
            return None

        if self.plot_arc_state.can_advance_stage():
            next_stage = self.plot_arc_state.advance_to_next_stage()
            if next_stage:
                self.plot_arc_state.active_arc.progress += 25
                return next_stage
        return None

    def get_forbidden_revelations(self) -> List[str]:
        """获取当前阶段禁止揭露的真相"""
        stage = self.get_current_stage()
        if not stage:
            return []
        return stage.forbidden_revelations

    def get_stage_purpose(self) -> str:
        """获取当前阶段目的"""
        stage = self.get_current_stage()
        if not stage:
            return "调查真相"
        return stage.purpose

    def to_context_dict(self) -> Dict[str, Any]:
        """转换为 AgentContext 可用的字典"""
        stage = self.get_current_stage()
        if not stage:
            return {
                "current_arc": "未知",
                "arc_stage": "unknown",
                "chapter_goal": "调查真相",
                "forbidden_revelations": [],
            }

        return {
            "current_arc": self.plot_arc_state.active_arc.name if self.plot_arc_state else "未知",
            "arc_stage": stage.stage_id,
            "chapter_goal": stage.purpose,
            "forbidden_revelations": stage.forbidden_revelations,
            "progress": self.plot_arc_state.active_arc.progress if self.plot_arc_state else 0,
        }

    def save_state(self, output_dir: Path) -> None:
        """保存剧情弧状态"""
        if not self.plot_arc_state:
            return

        state_file = output_dir / "plot_arc_state.json"
        with open(state_file, "w", encoding="utf-8") as f:
            # Pydantic V2 model_dump_json 不支持 ensure_ascii，使用 json.dumps
            data = self.plot_arc_state.model_dump()
            f.write(json.dumps(data, indent=2, ensure_ascii=False))
