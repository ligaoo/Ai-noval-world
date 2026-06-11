from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.models.character_arc import (
    ArcContext,
    ArcStage,
    BeliefChange,
    CharacterArc,
    ReflectionResult,
    RelationshipUpdate,
)


class CharacterArcService:
    """
    V3.4：人物弧光服务
    管理角色的信念、目标、关系、心理阶段的渐进变化。
    """

    def __init__(self, world_config_dir: Path, world_id: str):
        self.world_config_dir = world_config_dir
        self.world_id = world_id
        self.character_arcs: Dict[str, CharacterArc] = {}
        self.recent_reflections: Dict[str, List[ReflectionResult]] = {}
        self.event_since_last_reflection: Dict[str, int] = {}
        self.reflection_threshold: int = 3  # 每 3 个重要事件触发一次反思

        self._load_character_arcs()

    def _load_character_arcs(self) -> None:
        """加载人物弧光配置"""
        arcs_file = self.world_config_dir / self.world_id / "character_arcs.json"

        # 如果配置文件不存在，使用默认配置
        if not arcs_file.exists():
            self._create_default_arcs()
            return

        with open(arcs_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        character_items = data.get("characters") or data.get("arcs") or []
        for char_data in character_items:
            arc = CharacterArc.model_validate(char_data)
            self.character_arcs[arc.character_id] = arc

    def _create_default_arcs(self) -> None:
        """创建基于角色配置的默认人物弧光"""
        protagonist = self._load_protagonist_profile()
        character_id = protagonist.get("id") or "char_protagonist"
        goals = protagonist.get("goals") or {}
        desire = goals.get("long_term") or goals.get("short_term") or "完成当前目标"
        background = protagonist.get("background") or "进入未知处境后被迫重新评估自己的判断"
        stakes = protagonist.get("personal_stakes") or "错误选择会带来不可逆代价"

        stages = [
            ArcStage(
                stage_id="avoidance",
                name="回避阶段",
                description="倾向用旧有判断解释当前处境",
                required_belief_changes=["当前处境无法只靠旧经验解释"],
            ),
            ArcStage(
                stage_id="doubt",
                name="怀疑阶段",
                description="开始怀疑自己掌握的信息并不完整",
                required_belief_changes=["必须重新审视已有线索"],
            ),
            ArcStage(
                stage_id="confrontation",
                name="面对阶段",
                description="被迫面对目标背后的真实代价",
                required_belief_changes=["继续推进意味着承担个人代价"],
            ),
            ArcStage(
                stage_id="acceptance",
                name="选择阶段",
                description="在真相和代价之间做出主动选择",
                required_belief_changes=["必须主动选择而不是被处境推着走"],
            ),
        ]

        arc = CharacterArc(
            character_id=character_id,
            starting_state=background,
            wound=stakes,
            false_belief="只要按原计划行动就能控制局面",
            desire=desire,
            need="理解线索背后的代价，并为自己的选择负责",
            current_stage="avoidance",
            stages=stages,
            completed_stages=[],
            progress=0,
        )

        self.character_arcs[character_id] = arc

    def _load_protagonist_profile(self) -> Dict[str, Any]:
        characters_file = self.world_config_dir / self.world_id / "characters.json"
        try:
            if characters_file.exists():
                data = json.loads(characters_file.read_text(encoding="utf-8"))
                characters = data.get("characters", []) if isinstance(data, dict) else data
                return next((c for c in characters if c.get("role") == "protagonist"), characters[0] if characters else {})
        except Exception:
            return {}
        return {}

    def get_arc_context(self, character_id: str) -> Optional[ArcContext]:
        """获取人物弧光上下文"""
        arc = self.character_arcs.get(character_id)
        if not arc:
            return None

        current_stage_obj = self._get_current_stage(arc)
        if not current_stage_obj:
            return None

        # 生成内心冲突描述
        internal_conflict = self._generate_internal_conflict(arc, current_stage_obj)

        # 最近的反思
        recent = self.recent_reflections.get(character_id, [])
        recent_texts = [r.new_understanding[0] for r in recent[-2:] if r.new_understanding]

        return ArcContext(
            current_stage=arc.current_stage,
            stage_name=current_stage_obj.name,
            internal_conflict=internal_conflict,
            wound=arc.wound,
            false_belief=arc.false_belief,
            desire=arc.desire,
            need=arc.need,
            recent_reflections=recent_texts,
            progress_percent=arc.progress,
        )

    def _get_current_stage(self, arc: CharacterArc) -> Optional[ArcStage]:
        """获取当前阶段"""
        for stage in arc.stages:
            if stage.stage_id == arc.current_stage:
                return stage
        return None

    def _generate_internal_conflict(self, arc: CharacterArc, stage: ArcStage) -> str:
        """生成角色当前的内心冲突描述"""
        conflicts = {
            "avoidance": f"想继续按原计划推进，但{arc.wound}让每一步都变得更沉重。",
            "doubt": "线索之间的矛盾越来越多，角色开始怀疑自己最初的判断。",
            "confrontation": "真相已经逼近，但承认它意味着必须改变接下来的选择。",
            "acceptance": "继续前进需要主动承担代价，而不是等待局势替自己决定。",
        }
        return conflicts.get(arc.current_stage, "未解决的内心冲突正在逼近。")

    def record_plot_event_for_character(self, character_id: str) -> None:
        """记录角色经历了一个重要事件，检查是否触发反思"""
        if character_id not in self.event_since_last_reflection:
            self.event_since_last_reflection[character_id] = 0

        self.event_since_last_reflection[character_id] += 1

    def should_trigger_reflection(self, character_id: str) -> bool:
        """检查是否应该触发反思"""
        count = self.event_since_last_reflection.get(character_id, 0)
        return count >= self.reflection_threshold

    def generate_reflection(
        self,
        character_id: str,
        recent_events: List[str],
        known_facts: List[str],
        current_location: str,
    ) -> Optional[ReflectionResult]:
        """生成一次反思"""
        if character_id not in self.character_arcs:
            return None

        arc = self.character_arcs[character_id]
        stage = self._get_current_stage(arc)
        if not stage:
            return None

        # 重置计数
        self.event_since_last_reflection[character_id] = 0

        # 基于事件和事实生成新认知
        new_understanding = self._generate_new_understanding(recent_events, known_facts, stage)

        # 生成信念变化
        changed_beliefs = self._generate_belief_changes(recent_events, known_facts, stage)

        # 生成关系变化
        relationship_updates = self._generate_relationship_updates(recent_events, character_id)

        # 生成下一步意图
        next_intentions = self._generate_next_intentions(stage, known_facts, current_location)

        result = ReflectionResult(
            agent_id=character_id,
            new_understanding=new_understanding,
            changed_beliefs=changed_beliefs,
            relationship_updates=relationship_updates,
            next_intentions=next_intentions,
        )

        # 记录反思
        if character_id not in self.recent_reflections:
            self.recent_reflections[character_id] = []
        self.recent_reflections[character_id].append(result)

        # 检查是否可以推进阶段
        self._try_advance_stage(character_id)

        return result

    def _generate_new_understanding(
        self, events: List[str], facts: List[str], stage: ArcStage
    ) -> List[str]:
        """生成新认知"""
        understanding = []

        for event in events:
            if any(key in event for key in ["边界", "入口", "变化", "痕迹"]):
                understanding.append("当前地点的表面状态与实际变化不一致，近期可能发生过未说明的干预。")
            if any(key in event for key in ["回避", "隐瞒", "矛盾"]):
                understanding.append("可见角色或环境反馈中存在回避信息，说明事实链仍不完整。")
            if any(key in event for key in ["记录", "缺口", "错位"]):
                understanding.append("已有记录无法单独解释事件，需要和现场线索交叉验证。")

        if not understanding:
            understanding.append("这里发生的事情比表面上的复杂。")

        return understanding[:3]

    def _generate_belief_changes(
        self, events: List[str], facts: List[str], stage: ArcStage
    ) -> List[BeliefChange]:
        """生成信念变化"""
        changes = []

        if stage.stage_id == "avoidance":
            if any(any(key in e for key in ["边界", "痕迹", "记录", "矛盾"]) for e in events):
                changes.append(
                    BeliefChange(
                        from_belief="只要按原计划行动就能控制局面",
                        to_belief="当前处境必须依靠可验证线索重新判断",
                    )
                )

        return changes

    def _generate_relationship_updates(
        self, events: List[str], character_id: str
    ) -> List[RelationshipUpdate]:
        """生成关系变化"""
        updates = []

        for event in events:
            if "target=" in event and ("回避" in event or "隐瞒" in event):
                target = event.split("target=", 1)[1].split()[0]
                updates.append(
                    RelationshipUpdate(
                        target=target,
                        attitude_delta=-10,
                        reason="对方在关键信息上表现出回避或隐瞒",
                    )
                )
                break

        return updates

    def _generate_next_intentions(
        self, stage: ArcStage, facts: List[str], location: str
    ) -> List[str]:
        """生成下一步意图"""
        intentions = []

        if "entrance" in location or "入口" in location:
            intentions.append("验证边界状态为何发生变化")
            intentions.append("确认近期是谁或什么力量影响了入口")
        elif "lobby" in location or "大厅" in location or "front" in location:
            intentions.append("检查公共区域是否留下近期接触记录")
            intentions.append("寻找通往记录区或更深区域的路径")
        else:
            intentions.append("继续深入调查")
            intentions.append("寻找更多线索")

        return intentions[:2]

    def _try_advance_stage(self, character_id: str) -> Optional[str]:
        """尝试推进人物弧光阶段"""
        arc = self.character_arcs.get(character_id)
        if not arc:
            return None

        current_idx = -1
        for i, stage in enumerate(arc.stages):
            if stage.stage_id == arc.current_stage:
                current_idx = i
                break

        if current_idx < 0 or current_idx + 1 >= len(arc.stages):
            return None

        # 检查是否有足够的反思来推进
        reflections = self.recent_reflections.get(character_id, [])
        if len(reflections) >= 2:  # 经历 2 次反思后可推进
            next_stage = arc.stages[current_idx + 1]
            arc.completed_stages.append(arc.current_stage)
            arc.current_stage = next_stage.stage_id
            arc.progress = min(100, arc.progress + 25)
            return next_stage.stage_id

        return None

    def apply_relationship_changes(self, character_id: str, state: Any) -> None:
        """将关系变化应用到世界状态"""
        # 这里可以扩展为状态对象
        pass

    def save_state(self, output_dir: Path) -> None:
        """保存人物弧光状态"""
        state_file = output_dir / "character_arcs_state.json"
        arcs_data = []
        for cid, arc in self.character_arcs.items():
            arcs_data.append(arc.model_dump())

        with open(state_file, "w", encoding="utf-8") as f:
            json.dump({"characters": arcs_data}, f, ensure_ascii=False, indent=2)

    def get_all_arcs(self) -> List[str]:
        """获取所有角色 ID"""
        return list(self.character_arcs.keys())
