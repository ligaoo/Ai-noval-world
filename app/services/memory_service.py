from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Dict, List, Optional, Set

from app.models.event import EventLog
from app.models.memory import Memory, MemoryChunk, MemoryType
from app.models.state import WorldState
from app.models.world import Clue, WorldConfig


class MemoryService:
    """
    V2.3 角色记忆服务
    - 支持三类记忆：event_memory / fact_memory / belief_memory
    - 本地 JSONL 存储
    - 基于 tags 的检索（无向量库）
    """

    def __init__(self, sim_dir: Path, world: WorldConfig):
        self.sim_dir = sim_dir
        self.world = world
        self.memories_file = sim_dir / "memories.jsonl"
        self._memories: List[Memory] = []
        self._load_existing()

    def _load_existing(self) -> None:
        """加载已存在的记忆"""
        if not self.memories_file.exists():
            return
        with open(self.memories_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    mem = Memory.model_validate_json(line)
                    self._memories.append(mem)

    def _save_memory(self, memory: Memory) -> None:
        """持久化记忆"""
        with open(self.memories_file, "a", encoding="utf-8") as f:
            # Pydantic V2 model_dump_json 不支持 ensure_ascii，使用 json.dumps
            data = memory.model_dump()
            f.write(json.dumps(data, ensure_ascii=False) + "\n")
        self._memories.append(memory)

    # ==========================================
    # 写入策略（从 EventLog 生成记忆）
    # ==========================================

    def write_from_event(self, event: EventLog, state: WorldState) -> Optional[Memory]:
        """从事件自动写入记忆"""
        # 1. plot_event / soft_hint → event_memory
        if event.event_level == "plot" or event.event_type == "soft_hint":
            return self._write_event_memory(event)

        # 2. 线索发现 → fact_memory
        if event.action and event.action.action_type in ["inspect", "search", "ask", "talk"]:
            if "发现" in event.result or "线索" in event.result:
                return self._write_fact_memory_from_event(event, state)

        # 3. 对话失败/含糊 → belief_memory
        if event.event_type == "action_result" and event.action and event.action.action_type in ["ask", "talk"]:
            if "含糊" in event.result or "没有透露" in event.result or "回避" in event.result:
                return self._write_belief_memory_from_event(event, state)

        return None

    def _write_event_memory(self, event: EventLog) -> Memory:
        """写入事件记忆：记录经历过的事"""
        memory_id = f"mem_evt_{len(self._memories):04d}"
        tags = self._extract_tags_from_event(event)

        mem = Memory(
            memory_id=memory_id,
            agent_id=event.actors[0] if event.actors else "",
            type=MemoryType.EVENT,
            time=event.time,
            location_id=event.location_id,
            content=event.result,
            tags=tags,
            confidence=1.0,  # event 是确定发生的
            importance=self._calc_importance(event),
            source_event_id=event.event_id,
        )
        self._save_memory(mem)
        return mem

    def _write_fact_memory_from_event(self, event: EventLog, state: WorldState) -> Optional[Memory]:
        """写入事实记忆：确认的线索"""
        if not event.actors:
            return None

        # 从 discovered_facts 中找新发现的线索
        for clue_id, discovered in state.world.discovered_facts.items():
            if discovered:
                # 检查是否已有该 fact_memory
                existing = [
                    m for m in self._memories
                    if m.agent_id == event.actors[0]
                    and m.type == MemoryType.FACT
                    and clue_id in m.tags
                ]
                if existing:
                    continue

                clue = self._get_clue_by_id(clue_id)
                if not clue:
                    continue

                memory_id = f"mem_fact_{len(self._memories):04d}"
                tags = ["fact", clue_id] + self._extract_tags_from_event(event)

                mem = Memory(
                    memory_id=memory_id,
                    agent_id=event.actors[0],
                    type=MemoryType.FACT,
                    time=event.time,
                    location_id=event.location_id,
                    content=f"确认事实：{clue.content}",
                    tags=tags,
                    confidence=0.95,
                    importance=clue.importance,
                    source_event_id=event.event_id,
                )
                self._save_memory(mem)
                return mem

        return None

    def _write_belief_memory_from_event(self, event: EventLog, state: WorldState) -> Optional[Memory]:
        """写入信念/推测记忆：对话含糊时产生的怀疑"""
        if not event.actors:
            return None

        agent_id = event.actors[0]
        target = event.action.target if event.action else "unknown"

        # 检查是否已有类似 belief
        content_suffix = f"{target} 在隐瞒什么"
        existing = [
            m for m in self._memories
            if m.agent_id == agent_id
            and m.type == MemoryType.BELIEF
            and content_suffix in m.content
        ]
        if existing:
            return None

        memory_id = f"mem_belief_{len(self._memories):04d}"
        tags = ["belief", "suspicion", target]

        mem = Memory(
            memory_id=memory_id,
            agent_id=agent_id,
            type=MemoryType.BELIEF,
            time=event.time,
            location_id=event.location_id,
            content=f"推测：{target} 可能在隐瞒什么",
            tags=tags,
            confidence=0.6,  # belief 置信度较低
            importance=5,
            source_event_id=event.event_id,
        )
        self._save_memory(mem)
        return mem

    # ==========================================
    # 检索策略（基于 tags + importance + recency）
    # ==========================================

    def retrieve_relevant(
        self,
        agent_id: str,
        query_tags: List[str],
        top_n: int = 6,
        location_id: Optional[str] = None,
    ) -> List[MemoryChunk]:
        """
        检索相关记忆
        - 先按 tags 命中过滤
        - 再按 importance*0.7 + recency*0.3 排序
        """
        agent_memories = [m for m in self._memories if m.agent_id == agent_id]
        if not agent_memories:
            return []

        # 按地点过滤（如果指定）
        if location_id:
            agent_memories = [
                m for m in agent_memories
                if m.location_id == location_id
            ]

        # tags 命中过滤
        query_tag_set = set(query_tags)
        scored: List[MemoryChunk] = []

        for mem in agent_memories:
            mem_tag_set = set(mem.tags)
            overlap = len(query_tag_set & mem_tag_set)
            if overlap == 0:
                continue

            # recency: 越新的记忆分数越高
            # 简单实现：按索引计算，越往后越新
            recency_score = (self._memories.index(mem) + 1) / len(self._memories)

            # importance 归一化（1-10 → 0.1-1.0）
            importance_score = mem.importance / 10.0

            # 综合评分
            total_score = importance_score * 0.7 + recency_score * 0.3
            match_reason = f"tags命中 {overlap} 个: {', '.join(query_tag_set & mem_tag_set)}"

            scored.append(MemoryChunk(memory=mem, score=total_score, match_reason=match_reason))

        # 按分数降序排序，取 top_n
        scored.sort(key=lambda x: x.score, reverse=True)
        return scored[:top_n]

    # ==========================================
    # 辅助方法
    # ==========================================

    def get_known_facts(self, agent_id: str, limit: int = 6) -> List[str]:
        """获取 Agent 的已知事实（fact_memory）"""
        facts = [
            m.content for m in self._memories
            if m.agent_id == agent_id and m.type == MemoryType.FACT
        ]
        return facts[-limit:]

    def get_beliefs(self, agent_id: str, limit: int = 6) -> List[str]:
        """获取 Agent 的信念/推测（belief_memory）"""
        beliefs = [
            m.content for m in self._memories
            if m.agent_id == agent_id and m.type == MemoryType.BELIEF
        ]
        return beliefs[-limit:]

    def add_belief_memory(
        self, agent_id: str, content: str, confidence: float = 0.7
    ) -> Memory:
        """
        V3.5：添加一条信念记忆（从反思生成）
        """
        # 检查重复
        existing = [
            m for m in self._memories
            if m.agent_id == agent_id
            and m.type == MemoryType.BELIEF
            and content in m.content
        ]
        if existing:
            return existing[0]

        memory_id = f"mem_belief_{len(self._memories):04d}"
        tags = ["belief", "reflection", "from_v3_arc"]

        mem = Memory(
            memory_id=memory_id,
            agent_id=agent_id,
            type=MemoryType.BELIEF,
            time="",  # 从调用处获取 time
            location_id="",
            content=content,
            tags=tags,
            confidence=confidence,
            importance=6,
            source_event_id="",
        )
        self._save_memory(mem)
        return mem

    def get_all_tags_for_state(self, state: WorldState, agent_id: str) -> List[str]:
        """从当前状态提取检索用的 tags"""
        agent_state = state.characters[agent_id]
        loc = self.world.map.get_location(agent_state.location_id)

        tags: List[str] = []
        tags.append(agent_state.location_id)  # 当前地点
        tags.extend([o.id for o in loc.objects])  # 可见对象
        tags.extend(list(state.world.discovered_facts.keys()))  # 已发现线索
        tags.extend(list(agent_state.known_facts))  # 已知事实

        return list(set(tags))

    def _extract_tags_from_event(self, event: EventLog) -> List[str]:
        """从事件提取 tags"""
        tags = [event.location_id, event.event_type]
        if event.action:
            tags.append(event.action.action_type)
            if event.action.target:
                tags.append(event.action.target)
            if event.action.topic:
                tags.append(event.action.topic)
        if event.actors:
            tags.extend(event.actors)
        return list(set(tags))

    def _calc_importance(self, event: EventLog) -> int:
        """根据事件 plot_value 计算重要性"""
        total = event.plot_value.mystery + event.plot_value.conflict + event.plot_value.progress
        if total >= 15:
            return 9
        if total >= 10:
            return 7
        if total >= 5:
            return 5
        return 3

    def _get_clue_by_id(self, clue_id: str) -> Optional[Clue]:
        for clue in self.world.clues.clues:
            if clue.id == clue_id:
                return clue
        return None

    def get_summary(self) -> Dict[str, int]:
        """获取记忆统计"""
        summary = {
            "total": len(self._memories),
            "event_memory": 0,
            "fact_memory": 0,
            "belief_memory": 0,
        }
        for mem in self._memories:
            if mem.type == MemoryType.EVENT:
                summary["event_memory"] += 1
            elif mem.type == MemoryType.FACT:
                summary["fact_memory"] += 1
            elif mem.type == MemoryType.BELIEF:
                summary["belief_memory"] += 1
        return summary
