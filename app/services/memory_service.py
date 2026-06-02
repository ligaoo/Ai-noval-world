from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

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
        """从事件自动写入记忆，兼容旧入口：返回第一条写入的记忆。"""
        memories = self.write_many_from_event(event, state)
        return memories[0] if memories else None

    def write_many_from_event(self, event: EventLog, state: WorldState) -> List[Memory]:
        """从事件自动写入多角色隔离记忆。"""
        memories: List[Memory] = []

        fact_ids = self._fact_ids_from_event(event)
        if fact_ids:
            memories.extend(self._write_fact_memories_from_event(event, state))

        if event.event_level == "plot" or event.event_type == "soft_hint":
            memories.extend(self._write_event_memories(event))

        if event.action and event.action.action_type in ["inspect", "search", "ask", "talk"]:
            if "发现" in event.result or "线索" in event.result:
                memories.extend(self._write_fact_memories_from_event(event, state))

        memories.extend(self._write_belief_memories_from_event(event, state))
        return memories

    def _write_event_memories(self, event: EventLog) -> List[Memory]:
        """写入事件记忆：给实际感知事件的角色各写一条。"""
        memories: List[Memory] = []
        for agent_id in self._event_memory_recipients(event):
            if self._memory_exists(agent_id=agent_id, memory_type=MemoryType.EVENT, source_event_id=event.event_id):
                continue
            mem = Memory(
                memory_id=self._build_memory_id("evt"),
                agent_id=agent_id,
                type=MemoryType.EVENT,
                time=event.time,
                location_id=event.location_id,
                content=event.result,
                tags=self._extract_tags_from_event(event),
                confidence=1.0,
                importance=self._calc_importance(event),
                source_event_id=event.event_id,
            )
            self._save_memory(mem)
            memories.append(mem)
        return memories

    def _event_memory_recipients(self, event: EventLog) -> List[str]:
        if event.perceived_by:
            return self._valid_agent_ids(event.perceived_by)
        if event.visible_to:
            return self._valid_agent_ids(event.visible_to)
        return self._valid_agent_ids(event.actors)

    def _write_fact_memories_from_event(self, event: EventLog, state: WorldState) -> List[Memory]:
        """写入事实记忆：只给真正知道该事实的角色。"""
        memories: List[Memory] = []
        for fact_id in self._fact_ids_from_event(event):
            clue = self._get_clue_by_id(fact_id)
            entry = state.world.fact_exposure.get(fact_id)
            if not clue and not entry:
                continue

            recipients = self._known_fact_recipients(state, fact_id, event)
            for agent_id in recipients:
                if self._memory_exists(agent_id=agent_id, memory_type=MemoryType.FACT, tag=fact_id):
                    continue
                content_source = entry.truth if entry else clue.content
                importance = clue.importance if clue else self._calc_importance(event)
                tags = ["fact", fact_id] + self._extract_tags_from_event(event)
                mem = Memory(
                    memory_id=self._build_memory_id("fact"),
                    agent_id=agent_id,
                    type=MemoryType.FACT,
                    time=event.time,
                    location_id=event.location_id,
                    content=f"确认事实：{content_source}",
                    tags=list(dict.fromkeys(tags)),
                    confidence=0.95,
                    importance=importance,
                    source_event_id=event.event_id,
                )
                self._save_memory(mem)
                memories.append(mem)
        return memories

    def _write_belief_memories_from_event(self, event: EventLog, state: WorldState) -> List[Memory]:
        """写入信念/推测记忆：只给真正产生怀疑的角色。"""
        memories: List[Memory] = []
        for fact_id in self._suspected_fact_ids_from_event(event, state):
            entry = state.world.fact_exposure.get(fact_id)
            label = (entry.public_label if entry else "") or fact_id
            known_by = set(entry.known_by if entry else [])
            suspected_by = self._suspected_fact_recipients(state, fact_id, event)
            for agent_id, confidence in suspected_by.items():
                if agent_id in known_by:
                    continue
                if self._memory_exists(agent_id=agent_id, memory_type=MemoryType.BELIEF, tag=fact_id):
                    continue
                tags = ["belief", "suspicion", fact_id, label] + self._extract_tags_from_event(event)
                mem = Memory(
                    memory_id=self._build_memory_id("belief"),
                    agent_id=agent_id,
                    type=MemoryType.BELIEF,
                    time=event.time,
                    location_id=event.location_id,
                    content=f"推测：{label} 可能与当前事件有关",
                    tags=list(dict.fromkeys(tags)),
                    confidence=confidence,
                    importance=5,
                    source_event_id=event.event_id,
                )
                self._save_memory(mem)
                memories.append(mem)

        if self._is_legacy_ambiguous_dialogue(event):
            target = event.action.target if event.action else "unknown"
            content_suffix = f"{target} 可能在隐瞒什么"
            for agent_id in self._legacy_belief_recipients(event):
                if self._memory_exists(agent_id=agent_id, memory_type=MemoryType.BELIEF, content_contains=content_suffix):
                    continue
                mem = Memory(
                    memory_id=self._build_memory_id("belief"),
                    agent_id=agent_id,
                    type=MemoryType.BELIEF,
                    time=event.time,
                    location_id=event.location_id,
                    content=f"推测：{content_suffix}",
                    tags=["belief", "suspicion", target],
                    confidence=0.6,
                    importance=5,
                    source_event_id=event.event_id,
                )
                self._save_memory(mem)
                memories.append(mem)
        return memories

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

        mem = Memory(
            memory_id=self._build_memory_id("belief"),
            agent_id=agent_id,
            type=MemoryType.BELIEF,
            time="",  # 从调用处获取 time
            location_id="",
            content=content,
            tags=["belief", "reflection", "from_v3_arc"],
            confidence=confidence,
            importance=6,
            source_event_id="",
        )
        self._save_memory(mem)
        return mem

    def get_all_tags_for_state(self, state: WorldState, agent_id: str) -> List[str]:
        """从当前状态提取检索用的 tags，限定为角色视角。"""
        agent_state = state.characters[agent_id]
        loc = self.world.map.get_location(agent_state.location_id)

        tags: List[str] = []
        tags.append(agent_state.location_id)
        tags.extend([o.id for o in loc.objects])
        tags.extend(list(agent_state.known_facts))
        for fact_id, entry in state.world.fact_exposure.items():
            if agent_id in entry.known_by:
                tags.append(fact_id)
            if agent_id in entry.suspected_by:
                tags.append(fact_id)
                if entry.public_label:
                    tags.append(entry.public_label)

        return list(dict.fromkeys(tag for tag in tags if tag))

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
        return list(dict.fromkeys(tag for tag in tags if tag))

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

    def _valid_agent_ids(self, agent_ids: List[str]) -> List[str]:
        valid_ids = set(self.world.characters.ids())
        result: List[str] = []
        for agent_id in agent_ids:
            if not agent_id or agent_id not in valid_ids or agent_id in result:
                continue
            result.append(agent_id)
        return result

    def _memory_exists(
        self,
        agent_id: str,
        memory_type: MemoryType,
        source_event_id: Optional[str] = None,
        tag: Optional[str] = None,
        content_contains: Optional[str] = None,
    ) -> bool:
        for memory in self._memories:
            if memory.agent_id != agent_id or memory.type != memory_type:
                continue
            if source_event_id is not None and memory.source_event_id != source_event_id:
                continue
            if tag is not None and tag not in memory.tags:
                continue
            if content_contains is not None and content_contains not in memory.content:
                continue
            return True
        return False

    def _build_memory_id(self, prefix: str) -> str:
        return f"mem_{prefix}_{len(self._memories):04d}"

    def _fact_ids_from_event(self, event: EventLog) -> List[str]:
        fact_ids: List[str] = []
        fact_ids.extend(str(fact_id) for fact_id in event.discovered_facts if fact_id)
        revealed = event.fact_exposure_delta.get("revealed_fact_ids", []) or []
        if isinstance(revealed, list):
            fact_ids.extend(str(fact_id) for fact_id in revealed if fact_id)
        return list(dict.fromkeys(fact_ids))

    def _known_fact_recipients(self, state: WorldState, fact_id: str, event: EventLog) -> List[str]:
        entry = state.world.fact_exposure.get(fact_id)
        if entry and entry.known_by:
            return self._valid_agent_ids(list(entry.known_by))

        delta_known_by = event.fact_exposure_delta.get("known_by", {}) or {}
        if isinstance(delta_known_by, dict):
            recipients = delta_known_by.get(fact_id, []) or []
            if isinstance(recipients, list) and recipients:
                return self._valid_agent_ids([str(agent_id) for agent_id in recipients])

        clue = self._get_clue_by_id(fact_id)
        clue_content = clue.content if clue else ""
        recipients: List[str] = []
        for agent_id, runtime in state.characters.items():
            known_facts = set(runtime.known_facts)
            if fact_id in known_facts or (clue_content and clue_content in known_facts):
                recipients.append(agent_id)
        if recipients:
            return self._valid_agent_ids(recipients)

        fallback = event.action.agent_id if event.action else None
        if fallback:
            return self._valid_agent_ids([fallback])
        return self._valid_agent_ids(event.actors[:1])

    def _suspected_fact_ids_from_event(self, event: EventLog, state: WorldState) -> List[str]:
        fact_ids: List[str] = []
        suspected = event.fact_exposure_delta.get("suspected_fact_ids", []) or []
        if isinstance(suspected, list):
            fact_ids.extend(str(fact_id) for fact_id in suspected if fact_id)
        suspected_by = event.fact_exposure_delta.get("suspected_by", {}) or {}
        if isinstance(suspected_by, dict):
            fact_ids.extend(str(fact_id) for fact_id in suspected_by.keys() if fact_id)
        fact_ids.extend(self._fact_ids_from_event(event))

        if not fact_ids:
            fact_ids.extend(
                fact_id
                for fact_id, entry in state.world.fact_exposure.items()
                if entry.suspected_by
            )
        return list(dict.fromkeys(fact_ids))

    def _suspected_fact_recipients(self, state: WorldState, fact_id: str, event: EventLog) -> Dict[str, float]:
        entry = state.world.fact_exposure.get(fact_id)
        recipients: Dict[str, float] = {}
        if entry:
            recipients.update({agent_id: float(confidence) for agent_id, confidence in entry.suspected_by.items()})
        delta_suspected_by = event.fact_exposure_delta.get("suspected_by", {}) or {}
        if isinstance(delta_suspected_by, dict):
            fact_recipients = delta_suspected_by.get(fact_id, {}) or {}
            if isinstance(fact_recipients, dict):
                for agent_id, confidence in fact_recipients.items():
                    recipients[str(agent_id)] = float(confidence)
            elif isinstance(fact_recipients, list):
                for agent_id in fact_recipients:
                    recipients[str(agent_id)] = 0.5
        return {
            agent_id: confidence
            for agent_id, confidence in recipients.items()
            if agent_id in self._valid_agent_ids([agent_id])
        }

    def _is_legacy_ambiguous_dialogue(self, event: EventLog) -> bool:
        if event.event_type != "action_result" or not event.action:
            return False
        if event.action.action_type not in ["ask", "talk"]:
            return False
        return "含糊" in event.result or "没有透露" in event.result or "回避" in event.result

    def _legacy_belief_recipients(self, event: EventLog) -> List[str]:
        if event.perceived_by:
            return self._valid_agent_ids(event.perceived_by)
        if event.visible_to:
            return self._valid_agent_ids(event.visible_to)
        if event.action and event.action.agent_id:
            return self._valid_agent_ids([event.action.agent_id])
        return self._valid_agent_ids(event.actors[:1])

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
