from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ThreadType(str, Enum):
    """悬念类型"""
    MAIN_MYSTERY = "main_mystery"  # 主线谜团
    SUB_MYSTERY = "sub_mystery"  # 支线谜团
    CHARACTER_SECRET = "character_secret"  # 人物秘密
    SUPERNATURAL_RULE = "supernatural_rule"  # 灵异规则
    RELATIONSHIP_TENSION = "relationship_tension"  # 关系张力
    RED_HERRING = "red_herring"  # 误导线
    DANGER_THREAD = "danger_thread"  # 威胁线
    PAYOFF_THREAD = "payoff_thread"  # 伏笔回收线


class ThreadStatus(str, Enum):
    """悬念状态"""
    OPEN = "open"  # 已开启
    ACTIVE = "active"  # 当前章节正在推进
    IN_PROGRESS = "in_progress"  # 近期有推进
    BLOCKED = "blocked"  # 暂时无法推进
    PAYOFF_READY = "payoff_ready"  # 可以回收
    RESOLVED = "resolved"  # 已解决
    ABANDONED = "abandoned"  # 有意放弃
    EXPIRED = "expired"  # 过期
    REOPENED = "reopened"  # 重新打开，需要强校验


@dataclass
class Thread:
    """悬念线程"""
    thread_id: str
    question: str
    thread_type: ThreadType = ThreadType.SUB_MYSTERY
    arc_id: Optional[str] = None
    priority: int = 5
    status: ThreadStatus = ThreadStatus.OPEN
    
    # 开启信息
    opened_at_chapter: int = 0
    opened_at_event: Optional[str] = None
    
    # 推进信息
    last_progress_chapter: Optional[int] = None
    expected_progress_chapter_range: List[int] = field(default_factory=list)
    expected_payoff_chapter_range: List[int] = field(default_factory=list)
    
    # 关联信息
    related_clues: List[str] = field(default_factory=list)
    related_evidence: List[str] = field(default_factory=list)
    related_characters: List[str] = field(default_factory=list)
    related_locations: List[str] = field(default_factory=list)
    
    # 状态评估
    staleness: int = 0  # 停滞章节数
    payoff_readiness: float = 0.0  # 回收准备度 0-1
    
    # 推荐动作
    recommended_action: Optional[str] = None
    forbidden_actions: List[str] = field(default_factory=list)
    
    # 解决信息
    resolution: Optional[str] = None
    resolved_at_chapter: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "thread_id": self.thread_id,
            "question": self.question,
            "thread_type": self.thread_type.value if isinstance(self.thread_type, Enum) else self.thread_type,
            "arc_id": self.arc_id,
            "priority": self.priority,
            "status": self.status.value if isinstance(self.status, Enum) else self.status,
            "opened_at_chapter": self.opened_at_chapter,
            "opened_at_event": self.opened_at_event,
            "last_progress_chapter": self.last_progress_chapter,
            "expected_progress_chapter_range": self.expected_progress_chapter_range,
            "expected_payoff_chapter_range": self.expected_payoff_chapter_range,
            "related_clues": self.related_clues,
            "related_evidence": self.related_evidence,
            "related_characters": self.related_characters,
            "related_locations": self.related_locations,
            "staleness": self.staleness,
            "payoff_readiness": self.payoff_readiness,
            "recommended_action": self.recommended_action,
            "forbidden_actions": self.forbidden_actions,
            "resolution": self.resolution,
            "resolved_at_chapter": self.resolved_at_chapter,
        }


@dataclass
class NarrativeDebtReport:
    """叙事债务报告"""
    simulation_id: str
    chapter_id: str
    
    # 统计信息
    open_thread_count: int = 0
    high_priority_open_count: int = 0
    stale_thread_count: int = 0
    payoff_ready_count: int = 0
    
    # 高优先级停滞悬念
    high_priority_stale_threads: List[Dict[str, Any]] = field(default_factory=list)
    
    # 重新打开的悬念
    resolved_thread_reopened: List[Dict[str, Any]] = field(default_factory=list)
    
    # 债务等级
    debt_level: str = "low"  # low / medium / high / critical
    
    # 警告和建议
    warnings: List[str] = field(default_factory=list)
    recommendations: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "simulation_id": self.simulation_id,
            "chapter_id": self.chapter_id,
            "open_thread_count": self.open_thread_count,
            "high_priority_open_count": self.high_priority_open_count,
            "stale_thread_count": self.stale_thread_count,
            "payoff_ready_count": self.payoff_ready_count,
            "high_priority_stale_threads": self.high_priority_stale_threads,
            "resolved_thread_reopened": self.resolved_thread_reopened,
            "debt_level": self.debt_level,
            "warnings": self.warnings,
            "recommendations": self.recommendations,
        }


@dataclass
class ThreadPolicy:
    """悬念管理策略"""
    enabled: bool = True
    max_open_threads: int = 12
    max_new_threads_per_chapter: int = 2
    stale_chapter_threshold: int = 2
    high_priority_threshold: int = 7
    prevent_resolved_thread_reopen: bool = True
    endgame_new_thread_limit: int = 0  # 终局阶段新增悬念限制
    payoff_ready_threshold: float = 0.75  # 回收准备度阈值

    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "max_open_threads": self.max_open_threads,
            "max_new_threads_per_chapter": self.max_new_threads_per_chapter,
            "stale_chapter_threshold": self.stale_chapter_threshold,
            "high_priority_threshold": self.high_priority_threshold,
            "prevent_resolved_thread_reopen": self.prevent_resolved_thread_reopen,
            "endgame_new_thread_limit": self.endgame_new_thread_limit,
            "payoff_ready_threshold": self.payoff_ready_threshold,
        }
