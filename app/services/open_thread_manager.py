from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.models.thread import (
    NarrativeDebtReport,
    Thread,
    ThreadPolicy,
    ThreadStatus,
    ThreadType,
)
from app.services.trace_service import TraceService


@dataclass
class ThreadRecommendation:
    """悬念推荐"""
    type: str  # prioritize_thread / payoff_thread / progress_thread / abandon_thread
    thread_id: str
    message: str
    priority: int = 5


class OpenThreadManager:
    """
    V5.4 OpenThreadManager 悬念债务管理器
    统一管理所有 open_threads，避免故事越写越散
    
    核心功能：
    1. 悬念注册和状态管理
    2. 停滞悬念检测
    3. 回收准备度评估
    4. 叙事债务报告
    5. 已解决悬念保护
    6. 终局阶段控制
    """

    def __init__(
        self,
        sim_dir: Path,
        policy: Optional[ThreadPolicy] = None,
        trace_service: Optional[TraceService] = None,
    ):
        self.sim_dir = sim_dir
        self.policy = policy or ThreadPolicy()
        self.trace_service = trace_service

        self.threads: Dict[str, Thread] = {}
        self.thread_reports_dir = sim_dir / "thread_reports"
        self.thread_reports_dir.mkdir(exist_ok=True)

        self._load_threads()

    def create_thread(
        self,
        question: str,
        chapter_no: int,
        event_id: Optional[str] = None,
        thread_type: ThreadType = ThreadType.SUB_MYSTERY,
        priority: int = 5,
        arc_id: Optional[str] = None,
        expected_payoff_range: Optional[List[int]] = None,
        related_clues: Optional[List[str]] = None,
        related_evidence: Optional[List[str]] = None,
        related_characters: Optional[List[str]] = None,
        related_locations: Optional[List[str]] = None,
        forbidden_actions: Optional[List[str]] = None,
    ) -> Optional[Thread]:
        """
        创建新悬念
        规则：
        1. 检查是否超过最大开放悬念数
        2. 检查当前章节新增悬念是否超过限制
        3. 终局阶段禁止新增主线级悬念
        """
        if not self.policy.enabled:
            return None

        if not self._can_create_new_thread(chapter_no, thread_type):
            return None

        thread_id = f"thread_{len(self.threads) + 1:03d}"

        thread = Thread(
            thread_id=thread_id,
            question=question,
            thread_type=thread_type,
            arc_id=arc_id,
            priority=priority,
            status=ThreadStatus.OPEN,
            opened_at_chapter=chapter_no,
            opened_at_event=event_id,
            expected_payoff_chapter_range=expected_payoff_range or [],
            related_clues=related_clues or [],
            related_evidence=related_evidence or [],
            related_characters=related_characters or [],
            related_locations=related_locations or [],
            last_progress_chapter=chapter_no,
            forbidden_actions=forbidden_actions or [],
        )

        self.threads[thread_id] = thread
        self._save_threads()

        return thread

    def _can_create_new_thread(self, chapter_no: int, thread_type: ThreadType) -> bool:
        """检查是否可以创建新悬念"""
        open_threads = [
            t for t in self.threads.values()
            if t.status in [ThreadStatus.OPEN, ThreadStatus.ACTIVE, ThreadStatus.IN_PROGRESS]
        ]

        if len(open_threads) >= self.policy.max_open_threads:
            return False

        new_threads_this_chapter = sum(
            1 for t in self.threads.values()
            if t.opened_at_chapter == chapter_no
        )
        if new_threads_this_chapter >= self.policy.max_new_threads_per_chapter:
            return False

        if thread_type == ThreadType.MAIN_MYSTERY:
            progress_ratio = self._calculate_progress_ratio(chapter_no)
            if progress_ratio > 0.7:
                return False

        return True

    def update_thread_progress(self, thread_id: str, chapter_no: int) -> None:
        """更新悬念推进"""
        if thread_id not in self.threads:
            return

        thread = self.threads[thread_id]
        
        if thread.status == ThreadStatus.RESOLVED:
            return

        thread.status = ThreadStatus.ACTIVE
        thread.last_progress_chapter = chapter_no
        thread.staleness = 0

        self._update_payoff_readiness(thread, chapter_no)
        self._save_threads()

    def resolve_thread(
        self,
        thread_id: str,
        chapter_no: int,
        resolution: str,
    ) -> bool:
        """回收悬念"""
        if thread_id not in self.threads:
            return False

        thread = self.threads[thread_id]
        thread.status = ThreadStatus.RESOLVED
        thread.resolved_at_chapter = chapter_no
        thread.resolution = resolution
        thread.staleness = 0

        self._save_threads()
        return True

    def abandon_thread(self, thread_id: str, reason: str) -> bool:
        """放弃悬念"""
        if thread_id not in self.threads:
            return False

        if self.policy.require_reason_for_abandon and not reason:
            return False

        self.threads[thread_id].status = ThreadStatus.ABANDONED
        self._save_threads()
        return True

    def expire_thread(self, thread_id: str) -> bool:
        """标记悬念过期"""
        if thread_id not in self.threads:
            return False

        self.threads[thread_id].status = ThreadStatus.EXPIRED
        self._save_threads()
        return True

    def reopen_thread(self, thread_id: str, reason: str) -> bool:
        """重新打开悬念（需要强校验）"""
        if thread_id not in self.threads:
            return False

        thread = self.threads[thread_id]
        
        if thread.status != ThreadStatus.RESOLVED:
            return False

        if self.policy.prevent_resolved_thread_reopen:
            if self.trace_service:
                self.trace_service.add_warning(
                    "thread_reopen_attempt",
                    f"尝试重新打开已解决的悬念: {thread_id}",
                )
            return False

        thread.status = ThreadStatus.REOPENED
        thread.staleness = 0
        self._save_threads()
        return True

    def mark_thread_blocked(self, thread_id: str) -> None:
        """标记悬念为阻塞"""
        if thread_id in self.threads:
            self.threads[thread_id].status = ThreadStatus.BLOCKED
            self._save_threads()

    def mark_thread_payoff_ready(self, thread_id: str) -> None:
        """标记悬念为可回收"""
        if thread_id in self.threads:
            self.threads[thread_id].status = ThreadStatus.PAYOFF_READY
            self.threads[thread_id].payoff_readiness = 1.0
            self._save_threads()

    def update_from_chapter_summary(
        self,
        chapter_no: int,
        chapter_summary: Dict[str, Any],
    ) -> NarrativeDebtReport:
        """
        从章节摘要更新悬念状态
        每章结束后调用
        """
        self._update_staleness(chapter_no)
        self._update_thread_statuses(chapter_no)
        
        return self.generate_debt_report(chapter_no)

    def _update_staleness(self, current_chapter: int) -> None:
        """更新所有悬念的停滞章节数"""
        for thread in self.threads.values():
            if thread.status in [ThreadStatus.OPEN, ThreadStatus.ACTIVE, ThreadStatus.IN_PROGRESS]:
                if thread.last_progress_chapter:
                    thread.staleness = current_chapter - thread.last_progress_chapter
                else:
                    thread.staleness = current_chapter - thread.opened_at_chapter

    def _update_thread_statuses(self, current_chapter: int) -> None:
        """更新悬念状态"""
        for thread in self.threads.values():
            if thread.status in [ThreadStatus.OPEN, ThreadStatus.ACTIVE, ThreadStatus.IN_PROGRESS]:
                if thread.staleness >= self.policy.stale_chapter_threshold:
                    if thread.status != ThreadStatus.BLOCKED:
                        thread.status = ThreadStatus.IN_PROGRESS

    def _update_payoff_readiness(self, thread: Thread, current_chapter: int) -> None:
        """评估悬念回收准备度"""
        if not thread.expected_payoff_chapter_range:
            return

        min_chapter, max_chapter = thread.expected_payoff_chapter_range

        if current_chapter >= max_chapter:
            thread.payoff_readiness = 1.0
        elif current_chapter >= min_chapter:
            progress = (current_chapter - min_chapter) / (max_chapter - min_chapter)
            thread.payoff_readiness = min(1.0, progress)
        else:
            thread.payoff_readiness = 0.0

    def generate_debt_report(self, chapter_no: int) -> NarrativeDebtReport:
        """生成叙事债务报告"""
        simulation_id = self.sim_dir.name
        chapter_id = f"ch_{chapter_no:03d}"

        open_threads = [
            t for t in self.threads.values()
            if t.status in [ThreadStatus.OPEN, ThreadStatus.ACTIVE, ThreadStatus.IN_PROGRESS]
        ]

        high_priority_open = [
            t for t in open_threads
            if t.priority >= self.policy.high_priority_threshold
        ]

        stale_threads = [
            t for t in open_threads
            if t.staleness >= self.policy.stale_chapter_threshold
        ]

        high_priority_stale = [
            t for t in stale_threads
            if t.priority >= self.policy.high_priority_threshold
        ]

        payoff_ready = [
            t for t in self.threads.values()
            if t.status == ThreadStatus.PAYOFF_READY or t.payoff_readiness >= self.policy.payoff_ready_threshold
        ]

        debt_level = self._calculate_debt_level(open_threads, high_priority_stale)
        warnings = self._generate_warnings(open_threads, high_priority_stale)
        recommendations = self._generate_recommendations(high_priority_stale, payoff_ready)

        report = NarrativeDebtReport(
            simulation_id=simulation_id,
            chapter_id=chapter_id,
            open_thread_count=len(open_threads),
            high_priority_open_count=len(high_priority_open),
            stale_thread_count=len(stale_threads),
            payoff_ready_count=len(payoff_ready),
            high_priority_stale_threads=[
                {
                    "thread_id": t.thread_id,
                    "question": t.question,
                    "priority": t.priority,
                    "staleness": t.staleness,
                    "recommended_action": "progress_or_payoff",
                }
                for t in high_priority_stale
            ],
            resolved_thread_reopened=[],
            debt_level=debt_level,
            warnings=warnings,
            recommendations=[r.__dict__ if hasattr(r, '__dict__') else r for r in recommendations],
        )

        self._save_debt_report(report, chapter_no)
        return report

    def _calculate_debt_level(
        self,
        open_threads: List[Thread],
        high_priority_stale: List[Thread],
    ) -> str:
        """计算债务等级"""
        if len(high_priority_stale) >= 3:
            return "critical"
        
        if len(open_threads) >= self.policy.max_open_threads * 0.9:
            return "high"
        
        if len(high_priority_stale) >= 1 or len(open_threads) >= self.policy.max_open_threads * 0.7:
            return "medium"
        
        return "low"

    def _generate_warnings(
        self,
        open_threads: List[Thread],
        high_priority_stale: List[Thread],
    ) -> List[str]:
        """生成警告"""
        warnings = []

        if high_priority_stale:
            warnings.append(
                f"有 {len(high_priority_stale)} 个高优先级悬念超过 "
                f"{self.policy.stale_chapter_threshold} 章未推进。"
            )

        if len(open_threads) >= self.policy.max_open_threads * 0.8:
            warnings.append(
                f"当前 open_threads 数量 ({len(open_threads)}) 接近上限 "
                f"({self.policy.max_open_threads})。"
            )

        main_mystery_stale = [
            t for t in high_priority_stale
            if t.thread_type == ThreadType.MAIN_MYSTERY
        ]
        if main_mystery_stale:
            warnings.append("主线谜团长期未推进，可能影响故事核心。")

        return warnings

    def _generate_recommendations(
        self,
        high_priority_stale: List[Thread],
        payoff_ready: List[Thread],
    ) -> List[ThreadRecommendation]:
        """生成推荐动作"""
        recommendations = []

        for thread in high_priority_stale:
            recommendations.append(ThreadRecommendation(
                type="prioritize_thread",
                thread_id=thread.thread_id,
                message=f"下一章应推进: {thread.question}",
                priority=thread.priority,
            ))

        for thread in payoff_ready:
            recommendations.append(ThreadRecommendation(
                type="payoff_thread",
                thread_id=thread.thread_id,
                message=f"可以回收: {thread.question} (准备度: {thread.payoff_readiness:.0%})",
                priority=8,
            ))

        recommendations.sort(key=lambda r: r.priority, reverse=True)
        return recommendations

    def get_threads_for_chapter_planning(self, chapter_no: int) -> Dict[str, List[Thread]]:
        """
        获取章节规划所需的悬念信息
        供 ChapterPlanner 使用
        """
        high_priority_stale = [
            t for t in self.threads.values()
            if t.staleness >= self.policy.stale_chapter_threshold
            and t.priority >= self.policy.high_priority_threshold
            and t.status in [ThreadStatus.OPEN, ThreadStatus.ACTIVE, ThreadStatus.IN_PROGRESS]
        ]

        payoff_ready = [
            t for t in self.threads.values()
            if t.status == ThreadStatus.PAYOFF_READY
            or t.payoff_readiness >= self.policy.payoff_ready_threshold
        ]

        active = [
            t for t in self.threads.values()
            if t.status == ThreadStatus.ACTIVE
        ]

        return {
            "high_priority_stale": high_priority_stale,
            "payoff_ready": payoff_ready,
            "active": active,
        }

    def get_all_threads(self) -> List[Thread]:
        """获取所有悬念"""
        return list(self.threads.values())

    def get_thread(self, thread_id: str) -> Optional[Thread]:
        """获取指定悬念"""
        return self.threads.get(thread_id)

    def get_thread_stats(self) -> Dict[str, Any]:
        """获取悬念统计"""
        stats = {
            "total": len(self.threads),
            "open": 0,
            "active": 0,
            "in_progress": 0,
            "blocked": 0,
            "payoff_ready": 0,
            "resolved": 0,
            "abandoned": 0,
            "expired": 0,
        }

        for thread in self.threads.values():
            status_key = thread.status.value if isinstance(thread.status, ThreadStatus) else thread.status
            if status_key in stats:
                stats[status_key] += 1

        return stats

    def _load_threads(self) -> None:
        """加载悬念数据"""
        threads_file = self.sim_dir / "threads.json"
        if not threads_file.exists():
            return

        try:
            with open(threads_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            for thread_data in data:
                thread = Thread(
                    thread_id=thread_data["thread_id"],
                    question=thread_data["question"],
                    thread_type=ThreadType(thread_data.get("thread_type", "sub_mystery")),
                    arc_id=thread_data.get("arc_id"),
                    priority=thread_data.get("priority", 5),
                    status=ThreadStatus(thread_data.get("status", "open")),
                    opened_at_chapter=thread_data.get("opened_at_chapter", 0),
                    opened_at_event=thread_data.get("opened_at_event"),
                    expected_payoff_chapter_range=thread_data.get("expected_payoff_chapter_range", []),
                    related_clues=thread_data.get("related_clues", []),
                    related_evidence=thread_data.get("related_evidence", []),
                    related_characters=thread_data.get("related_characters", []),
                    related_locations=thread_data.get("related_locations", []),
                    staleness=thread_data.get("staleness", 0),
                    payoff_readiness=thread_data.get("payoff_readiness", 0.0),
                    recommended_action=thread_data.get("recommended_action"),
                    forbidden_actions=thread_data.get("forbidden_actions", []),
                    resolution=thread_data.get("resolution"),
                    resolved_at_chapter=thread_data.get("resolved_at_chapter"),
                )
                self.threads[thread.thread_id] = thread

        except Exception as e:
            if self.trace_service:
                self.trace_service.add_error("load_threads", str(e))

    def _save_threads(self) -> None:
        """保存悬念数据"""
        threads_file = self.sim_dir / "threads.json"
        data = [thread.to_dict() for thread in self.threads.values()]
        with open(threads_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _save_debt_report(self, report: NarrativeDebtReport, chapter_no: int) -> None:
        """保存债务报告"""
        report_file = self.thread_reports_dir / f"ch_{chapter_no:03d}_debt.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report.to_dict(), f, ensure_ascii=False, indent=2)

    def _calculate_progress_ratio(self, chapter_no: int) -> float:
        """计算当前进度比例"""
        target_chapters = 30
        return min(1.0, chapter_no / target_chapters)
