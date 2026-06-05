from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.models.chapter_continuity import ChapterContext, ChapterSummary, CharacterChange
from app.models.state import WorldState


class ChapterContinuityService:
    """
    V3.4：章节连续性服务
    支持多章连续，让下一章继承上一章的未解决问题、人物状态和伏笔状态。
    """

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.chapter_summaries: List[ChapterSummary] = []
        self.current_chapter_index: int = 0

    def generate_chapter_summary(
        self,
        chapter_id: str,
        chapter_title: str,
        final_state: WorldState,
        events: List[Dict[str, Any]],
        plot_events: List[Dict[str, Any]],
    ) -> ChapterSummary:
        """生成章节摘要"""
        self.current_chapter_index += 1

        # 提取新发现的事实（从 discovered_facts）
        new_facts: List[str] = []
        for char_id, char_state in final_state.characters.items():
            if hasattr(char_state, "known_facts"):
                facts = char_state.known_facts or []
                for f in facts:
                    if f not in new_facts:
                        new_facts.append(f)

        # 提取 beliefs
        new_beliefs: Dict[str, List[str]] = {}

        # 提取 open threads （从未解决的问题 + 情节中产生的疑问）
        open_threads = self._extract_open_threads(events, final_state)

        # 已解决的悬念
        resolved_threads: List[str] = []

        # 人物状态变化
        character_changes: Dict[str, CharacterChange] = {}
        for char_id, char_state in final_state.characters.items():
            character_changes[char_id] = CharacterChange(
                mental_state=getattr(char_state, "mental_state", "正常"),
                goal_updated="继续调查医院异常",
                new_beliefs=new_beliefs.get(char_id, []),
            )

        # 下一章的探索方向种子
        next_chapter_seeds = self._generate_next_seeds(final_state, plot_events)

        # 生成正文摘要
        summary = self._generate_natural_summary(
            chapter_title, events, new_facts, open_threads
        )

        chapter_summary = ChapterSummary(
            chapter_id=chapter_id,
            chapter_title=chapter_title,
            summary=summary,
            tick_count=final_state.tick,
            event_count=len(events),
            new_facts=new_facts,
            new_beliefs=new_beliefs,
            open_threads=open_threads,
            resolved_threads=resolved_threads,
            character_changes=character_changes,
            next_chapter_seeds=next_chapter_seeds,
            final_character_states={
                cid: {
                    "mental_state": getattr(cs, "mental_state", ""),
                    "location_id": getattr(cs, "location_id", ""),
                    "known_facts": getattr(cs, "known_facts", []),
                }
                for cid, cs in final_state.characters.items()
            },
            discovered_clues=[],
        )

        self.chapter_summaries.append(chapter_summary)
        return chapter_summary

    def _extract_open_threads(
        self, events: List[Dict[str, Any]], state: WorldState
    ) -> List[str]:
        """从事件中提取未解决的悬念"""
        threads = [
            "谁换了医院的锁？",
            "看门人为什么隐瞒？",
            "医院是否与林舟的噩梦有关？",
        ]

        # 根据实际事件添加
        for evt in events:
            result = evt.get("result", "")
            if "锁" in result and "换" in result:
                if "谁换了锁？" not in threads:
                    threads.append("谁换了锁？")
            if "档案" in result or "记录" in result:
                if "记录里写了什么？" not in threads:
                    threads.append("记录里写了什么？")

        return threads[:5]  # 最多保留 5 个主线悬念

    def _generate_next_seeds(
        self, state: WorldState, plot_events: List[Dict[str, Any]]
    ) -> List[str]:
        """生成下一章的探索方向种子"""
        seeds = [
            "调查大厅前台区域",
            "追问看门人关于锁的来源",
            "寻找旧医院档案",
            "检查是否有其他出入口",
        ]
        return seeds[:3]  # 给 3 个方向

    def _generate_natural_summary(
        self,
        title: str,
        events: List[Dict[str, Any]],
        facts: List[str],
        threads: List[str],
    ) -> str:
        """生成自然语言的章节摘要"""
        if not events:
            return f"{title}：调查开始。"

        # 提取关键事件
        key_events = []
        for e in events[:8]:
            result = e.get("result", "")
            if result and len(result) < 60:
                key_events.append(result)

        event_text = "；".join(key_events[:3]) if key_events else "调查过程中发现了一些线索。"

        if facts:
            fact_text = "、".join(facts[:2])
            return f"{title}：{event_text}发现的关键事实包括：{fact_text}。仍有多个疑问待解。"
        else:
            return f"{title}：{event_text}调查仍在进行中。"

    def build_next_chapter_context(self) -> ChapterContext:
        """构建下一章的上下文"""
        if not self.chapter_summaries:
            # 第一章
            return ChapterContext(
                chapter_number=1,
                previous_chapter_summary="调查开始，林舟进入旧医院。",
                open_threads=["旧医院是否真的废弃？"],
                next_chapter_seeds=["检查入口区域", "与看门人交谈"],
                inherited_facts=[],
                inherited_beliefs={},
            )

        # 基于上一章
        last_summary = self.chapter_summaries[-1]

        # 过滤掉已解决的悬念
        active_threads = [
            t for t in last_summary.open_threads
            if t not in last_summary.resolved_threads
        ]

        # 继承未解决的事实
        inherited_facts = last_summary.new_facts[:]
        inherited_beliefs = {}
        for cid, beliefs in last_summary.new_beliefs.items():
            inherited_beliefs[cid] = beliefs[:]

        # Soft Director Pressure
        soft_pressure = self._generate_soft_pressure(active_threads)

        return ChapterContext(
            chapter_number=len(self.chapter_summaries) + 1,
            previous_chapter_summary=last_summary.summary,
            open_threads=active_threads,
            next_chapter_seeds=last_summary.next_chapter_seeds,
            inherited_facts=inherited_facts,
            inherited_beliefs=inherited_beliefs,
            soft_director_pressure=soft_pressure,
        )

    def _generate_soft_pressure(self, open_threads: List[str]) -> List[str]:
        """生成软导演压力提示"""
        if not open_threads:
            return []

        pressures = []
        for t in open_threads[:2]:
            if "锁" in t:
                pressures.append("林舟觉得那把新锁背后一定有文章，不能就这么放过。")
            elif "隐瞒" in t or "为什么" in t:
                pressures.append("看门人的闪烁其词让你更加确信有什么被掩盖了。")
            elif "噩梦" in t or "记忆" in t:
                pressures.append("这个地方似乎在唤醒你不想记起的东西。")

        return pressures[:2]

    def save_summary(self, summary: ChapterSummary) -> None:
        """保存章节摘要到文件"""
        summary_file = self.output_dir / f"{summary.chapter_id}_summary.json"
        with open(summary_file, "w", encoding="utf-8") as f:
            # Pydantic V2 model_dump_json 不支持 ensure_ascii，使用 json.dumps
            data = summary.model_dump()
            f.write(json.dumps(data, indent=2, ensure_ascii=False))

    def load_previous_chapter_context(self, sim_dir: Path) -> Optional[ChapterContext]:
        """从之前的模拟目录加载章节上下文"""
        summary_files = list(sim_dir.glob("*_summary.json"))
        if not summary_files:
            return None

        # 加载最新的摘要
        latest = sorted(summary_files)[-1]
        with open(latest, "r", encoding="utf-8") as f:
            summary_data = json.load(f)

        summary = ChapterSummary.model_validate(summary_data)
        self.chapter_summaries.append(summary)

        return self.build_next_chapter_context()
