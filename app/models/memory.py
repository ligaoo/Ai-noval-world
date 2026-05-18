from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class MemoryType(str, Enum):
    EVENT = "event_memory"
    FACT = "fact_memory"
    BELIEF = "belief_memory"


class Memory(BaseModel):
    """角色记忆基类"""
    memory_id: str
    agent_id: str
    type: MemoryType
    time: str  # game time, e.g. "day1_20:20"
    location_id: str
    content: str
    tags: List[str] = Field(default_factory=list)
    confidence: float = 1.0  # 0.0~1.0: fact 0.8~1.0, belief 0.3~0.7
    importance: int = 5  # 1~10
    source_event_id: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class MemoryChunk(BaseModel):
    """检索返回的记忆块"""
    memory: Memory
    score: float  # 综合评分：importance * 0.7 + recency * 0.3
    match_reason: str = ""
