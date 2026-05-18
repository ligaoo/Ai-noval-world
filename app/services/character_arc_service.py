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

        for char_data in data.get("characters", []):
            arc = CharacterArc.model_validate(char_data)
            self.character_arcs[arc.character_id] = arc

    def _create_default_arcs(self) -> None:
        """创建默认的林舟人物弧光"""
        linzhou_stages = [
            ArcStage(
                stage_id="avoidance",
                name="回避阶段",
                description="回避过去，只想快速确认梦境来源",
                required_belief_changes=["医院可能与自己有关"],
            ),
            ArcStage(
                stage_id="doubt",
                name="怀疑阶段",
                description="开始怀疑自己的记忆",
                required_belief_changes=["自己的记忆可能被篡改过"],
            ),
            ArcStage(
                stage_id="confrontation",
                name="面对阶段",
                description="被迫面对过去",
                required_belief_changes=["必须面对当年发生的事情"],
            ),
            ArcStage(
                stage_id="acceptance",
                name="接纳阶段",
                description="承认真相并做出选择",
                required_belief_changes=["接受过去才能真正离开"],
            ),
        ]

        linzhou_arc = CharacterArc(
            character_id="char_linzho",
            starting_state="逃避过去，不愿相信自己的记忆有问题",
            wound="童年事故造成的记忆断裂",
            false_belief="只要不追究过去，就能正常生活",
            desire="摆脱噩梦",
            need="承认自己曾经逃避的真相",
            current_stage="avoidance",
            stages=linzhou_stages,
            completed_stages=[],
            progress=0,
        )

        self.character_arcs["char_linzho"] = linzhou_arc

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
            "avoidance": "想查清噩梦来源，但害怕发现自己和医院有关。",
            "doubt": "记忆的碎片越来越多，但你仍在抗拒承认这是真的。",
            "confrontation": "你知道真相就在眼前，但揭露它意味着承认多年的逃避是错的。",
            "acceptance": "真相可能摧毁你，但也可能让你真正解脱。",
        }
        return conflicts.get(arc.current_stage, "过去的阴影正在逼近。")

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

        # 基于事件类型
        for event in events:
            if "锁" in event and "换" in event:
                understanding.append("旧医院并非彻底废弃，近期仍有人出入。")
            if "门卫" in event or "看门人" in event:
                if "回避" in event or "隐瞒" in event:
                    understanding.append("看门人至少隐瞒了近期有人出入的事实。")
            if "档案" in event or "记录" in event:
                understanding.append("有人在刻意掩盖医院里发生过的事情。")

        # 如果还不够，补充默认
        if not understanding:
            understanding.append("这里发生的事情比表面上的复杂。")

        return understanding[:3]

    def _generate_belief_changes(
        self, events: List[str], facts: List[str], stage: ArcStage
    ) -> List[BeliefChange]:
        """生成信念变化"""
        changes = []

        # 从回避到怀疑的转变
        if stage.stage_id == "avoidance":
            if any("锁" in e for e in events):
                changes.append(
                    BeliefChange(
                        from_belief="医院只是噩梦里的地点",
                        to_belief="医院可能与自己的过去有关",
                    )
                )

        return changes

    def _generate_relationship_updates(
        self, events: List[str], character_id: str
    ) -> List[RelationshipUpdate]:
        """生成关系变化"""
        updates = []

        for event in events:
            if "看门人" in event and ("回避" in event or "隐瞒" in event):
                updates.append(
                    RelationshipUpdate(
                        target="char_guard",
                        attitude_delta=-15,
                        reason="看门人多次回避关键问题",
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
            intentions.append("寻找近期出入医院的证据")
            intentions.append("弄清看门人听命于谁")
        elif "lobby" in location or "大厅" in location:
            intentions.append("检查前台是否有近期记录")
            intentions.append("寻找通往档案室的路")
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
