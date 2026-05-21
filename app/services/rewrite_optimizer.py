from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.llm_client import OpenAICompatibleClient
from app.models.event import EventLog
from app.models.rewrite import (
    ChangedSection,
    RewriteAcceptancePolicy,
    RewriteGoal,
    RewriteMode,
    RewritePlan,
    RewriteResult,
    RewriteTaskType,
)
from app.services.trace_service import TraceService


@dataclass
class RewriteContext:
    """修稿上下文"""
    chapter_plan: Dict[str, Any]
    chapter_draft: str
    selected_events: List[EventLog]
    quality_report: Dict[str, Any]
    genre_context: Optional[Dict[str, Any]] = None
    style_bible: Optional[Dict[str, Any]] = None
    character_voice_profiles: Optional[Dict[str, Any]] = None
    consistency_report: Optional[Dict[str, Any]] = None


class RewriteOptimizerService:
    """
    V5.3 RewriteOptimizer 自动修稿器
    根据质量报告自动生成修稿计划并执行修稿
    核心原则：优化表达，不改变事实
    """

    REWRITE_TASK_PROMPTS = {
        RewriteTaskType.TIGHTEN_PACING: {
            "instruction": "压缩拖沓的段落，合并重复描写，加快节奏。",
            "constraints": ["不能删除关键线索", "保持必要信息传递"],
        },
        RewriteTaskType.INCREASE_CONFLICT: {
            "instruction": "增强角色之间的目标冲突或外部阻碍，增加紧张感。",
            "constraints": ["只能强化已有事件", "不能改变事件结果"],
        },
        RewriteTaskType.DEEPEN_CHARACTER: {
            "instruction": "增加角色的内心活动或情绪描写，丰富人物深度。",
            "constraints": ["心理活动必须符合角色性格", "不能添加新的事实信息"],
        },
        RewriteTaskType.IMPROVE_HOOK: {
            "instruction": "强化章节结尾的钩子，增加读者的期待感。",
            "constraints": ["只能基于已有事件强化", "不能提前透露后续章节内容"],
        },
        RewriteTaskType.POLISH_STYLE: {
            "instruction": "调整文风，使其与项目整体风格保持一致。",
            "constraints": ["保持所有事实信息不变"],
        },
        RewriteTaskType.REDUCE_EXPOSITION: {
            "instruction": "减少直白的解释，改为通过细节或动作暗示。",
            "constraints": ["关键信息必须保留"],
        },
        RewriteTaskType.IMPROVE_DIALOGUE: {
            "instruction": "优化对白，增加潜台词，减少过度解释。",
            "constraints": ["关键信息必须保留", "对话必须符合角色性格"],
        },
        RewriteTaskType.ENHANCE_SUSPENSE: {
            "instruction": "强化已有线索的重要性暗示，突出悬念感。",
            "constraints": ["不能添加新的线索", "不能泄露未发现的事实"],
        },
        RewriteTaskType.ENHANCE_HORROR_ATMOSPHERE: {
            "instruction": "增强恐怖氛围，使用允许的恐怖手法。",
            "constraints": ["只能使用当前阶段允许的 horror devices", "禁止正面鬼怪攻击"],
        },
        RewriteTaskType.RESTORE_GENRE_CONSTRAINTS: {
            "instruction": "修复题材约束偏移，恢复正确的类型表现。",
            "constraints": ["必须遵守 GenreContext", "不能违反 HorrorRule"],
        },
        RewriteTaskType.RESTORE_CHARACTER_VOICE: {
            "instruction": "修复角色声音漂移，使对白符合角色设定。",
            "constraints": ["关键信息必须保留", "不能改变对话内容"],
        },
        # V1.1 新增任务类型
        RewriteTaskType.REDUCE_CLUE_DENSITY: {
            "instruction": "降低线索密度，将部分线索后移或改为更含蓄的暗示。不要删除必须包含的线索。",
            "constraints": ["不能删除 must_include 的线索", "保留所有必须的信息", "可以将部分线索改为伏笔形式"],
        },
        RewriteTaskType.REDUCE_OVERWRITING: {
            "instruction": "减少过度修辞，删除重复或不必要的比喻和装饰性描写，保持文风克制。",
            "constraints": ["保留必要的信息性环境描写", "不能改变场景的氛围基调"],
        },
        RewriteTaskType.FIX_CONTINUITY: {
            "instruction": "修复时间线或连续性矛盾。统一时间表述，确保与世界设定一致。",
            "constraints": ["不能改变事件本身，只修改表述", "必须与 world_bible.timeline 保持一致"],
        },
    }

    def __init__(
        self,
        sim_dir: Path,
        llm_client: Optional[OpenAICompatibleClient] = None,
        trace_service: Optional[TraceService] = None,
        acceptance_policy: Optional[RewriteAcceptancePolicy] = None,
    ):
        self.sim_dir = sim_dir
        self.llm_client = llm_client
        self.trace_service = trace_service
        self.acceptance_policy = acceptance_policy or RewriteAcceptancePolicy()

        self.rewrite_reports_dir = sim_dir / "rewrite_reports"
        self.rewrite_reports_dir.mkdir(exist_ok=True)

    def generate_rewrite_plan(self, rewrite_context: RewriteContext) -> RewritePlan:
        """
        根据质量报告生成修稿计划
        规则：
        1. severity = high 的问题优先
        2. 分数低于阈值的维度优先
        3. 不可修复的问题只记录，不进入 rewrite_task
        4. 恐怖氛围不足时读取 Horror Genre Pack 允许手法
        """
        quality_report = rewrite_context.quality_report
        simulation_id = self.sim_dir.name
        chapter_id = quality_report.get("chapter_id", "ch_unknown")

        rewrite_plan_id = f"rp_{chapter_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        rewrite_goals = self._generate_rewrite_goals(quality_report, rewrite_context)

        rewrite_mode = self._determine_rewrite_mode(quality_report, rewrite_goals)

        global_constraints = self._build_global_constraints(rewrite_context)

        return RewritePlan(
            rewrite_plan_id=rewrite_plan_id,
            simulation_id=simulation_id,
            chapter_id=chapter_id,
            source_quality_report_id=quality_report.get("report_id", ""),
            rewrite_mode=rewrite_mode,
            rewrite_goals=rewrite_goals,
            global_constraints=global_constraints,
            max_rewrite_attempts=1,
        )

    def _generate_rewrite_goals(
        self,
        quality_report: Dict[str, Any],
        rewrite_context: RewriteContext,
    ) -> List[RewriteGoal]:
        """生成修稿目标列表"""
        goals: List[RewriteGoal] = []
        task_counter = 0

        problems = quality_report.get("problems", [])
        genre_problems = quality_report.get("genre_problems", [])

        all_problems = problems + genre_problems

        high_priority_problems = [p for p in all_problems if p.get("severity") == "high"]
        medium_priority_problems = [p for p in all_problems if p.get("severity") == "medium"]

        sorted_problems = high_priority_problems + medium_priority_problems

        for problem in sorted_problems:
            problem_type = problem.get("type", "")
            rewrite_task_type = self._problem_to_rewrite_task(problem_type)

            if not rewrite_task_type:
                continue

            priority = self._calculate_task_priority(problem, quality_report)

            constraints = self.REWRITE_TASK_PROMPTS.get(rewrite_task_type, {}).get("constraints", [])

            genre_constraints = []
            if rewrite_context.genre_context:
                genre_constraints = self._build_genre_constraints(rewrite_context.genre_context)
                constraints.extend(genre_constraints)

            goal = RewriteGoal(
                task_id=f"task_{task_counter:03d}",
                type=rewrite_task_type,
                priority=priority,
                reason=problem.get("message", ""),
                target_sections=problem.get("target_sections", []),
                constraints=constraints,
            )
            goals.append(goal)
            task_counter += 1

        goals.sort(key=lambda g: g.priority, reverse=True)

        return goals

    def _problem_to_rewrite_task(self, problem_type: str) -> Optional[RewriteTaskType]:
        """将问题类型转换为修稿任务类型"""
        mapping = {
            "weak_conflict": RewriteTaskType.INCREASE_CONFLICT,
            "slow_middle": RewriteTaskType.TIGHTEN_PACING,
            "weak_hook": RewriteTaskType.IMPROVE_HOOK,
            "flat_emotional_curve": RewriteTaskType.DEEPEN_CHARACTER,
            "low_plot_progress": RewriteTaskType.ENHANCE_SUSPENSE,
            "thin_character_motivation": RewriteTaskType.DEEPEN_CHARACTER,
            "dialogue_too_expository": RewriteTaskType.IMPROVE_DIALOGUE,
            "style_drift": RewriteTaskType.POLISH_STYLE,
            "voice_drift": RewriteTaskType.RESTORE_CHARACTER_VOICE,
            "over_explanation": RewriteTaskType.REDUCE_EXPOSITION,
            "scene_repetition": RewriteTaskType.TIGHTEN_PACING,
            "suspense_without_payoff": RewriteTaskType.ENHANCE_SUSPENSE,
            "too_many_threads_opened": RewriteTaskType.ENHANCE_SUSPENSE,
            "no_thread_progress": RewriteTaskType.ENHANCE_SUSPENSE,
            "payoff_too_abrupt": RewriteTaskType.DEEPEN_CHARACTER,
            "horror_atmosphere_weak": RewriteTaskType.ENHANCE_HORROR_ATMOSPHERE,
            "fear_escalation_flat": RewriteTaskType.ENHANCE_HORROR_ATMOSPHERE,
            "over_explained_supernatural": RewriteTaskType.REDUCE_EXPOSITION,
            "forbidden_horror_device": RewriteTaskType.RESTORE_GENRE_CONSTRAINTS,
            # V1.1 新增映射
            "clue_overload": RewriteTaskType.REDUCE_CLUE_DENSITY,
            "missing_required_character_beat": RewriteTaskType.DEEPEN_CHARACTER,
            "thin_emotional_motivation": RewriteTaskType.DEEPEN_CHARACTER,
            "metaphor_overload": RewriteTaskType.REDUCE_OVERWRITING,
            "decorative_description": RewriteTaskType.REDUCE_OVERWRITING,
            "weak_horror_hook": RewriteTaskType.IMPROVE_HOOK,
            "timeline_conflict": RewriteTaskType.FIX_CONTINUITY,
            "timeline_ambiguous_statement": RewriteTaskType.FIX_CONTINUITY,
        }
        return mapping.get(problem_type)

    def _calculate_task_priority(
        self,
        problem: Dict[str, Any],
        quality_report: Dict[str, Any],
    ) -> int:
        """计算任务优先级"""
        base_priority = 5

        severity = problem.get("severity", "medium")
        if severity == "high":
            base_priority += 3
        elif severity == "medium":
            base_priority += 1

        dimension = problem.get("score_dimension", "")
        scores = quality_report.get("scores", {})
        dimension_score = scores.get(dimension, 7)

        if dimension_score < 5:
            base_priority += 2
        elif dimension_score < 6:
            base_priority += 1

        return min(10, max(1, base_priority))

    def _determine_rewrite_mode(
        self,
        quality_report: Dict[str, Any],
        rewrite_goals: List[RewriteGoal],
    ) -> RewriteMode:
        """确定修稿模式"""
        overall_score = quality_report.get("overall_score", 7.0)

        if overall_score < 6.0:
            return RewriteMode.FULL_CHAPTER_REWRITE

        high_severity_goals = [g for g in rewrite_goals if g.priority >= 8]
        if len(high_severity_goals) >= 3:
            return RewriteMode.FULL_CHAPTER_REWRITE

        if len(rewrite_goals) >= 5:
            return RewriteMode.FULL_CHAPTER_REWRITE

        return RewriteMode.SECTION_REWRITE

    def _build_global_constraints(self, rewrite_context: RewriteContext) -> List[str]:
        """构建全局修稿约束"""
        constraints = [
            "不能新增 EventLog 中没有的事实",
            "不能新增未出现的角色",
            "不能新增未配置的地点",
            "不能新增未发现的线索",
            "不能改变角色行动结果",
            "不能改变 PlotArc 当前阶段",
            "不能提前暴露 forbidden_revelations",
        ]

        if rewrite_context.genre_context:
            forbidden_devices = rewrite_context.genre_context.get("genre_forbidden_devices", [])
            if forbidden_devices:
                constraints.append(f"禁止使用的恐怖手法：{', '.join(forbidden_devices)}")

        return constraints

    def _build_genre_constraints(self, genre_context: Dict[str, Any]) -> List[str]:
        """构建题材约束"""
        constraints = []

        genre_stage = genre_context.get("genre_stage", "")
        if genre_stage:
            constraints.append(f"当前题材阶段：{genre_stage}")

        allowed_devices = genre_context.get("genre_allowed_devices", [])
        if allowed_devices:
            constraints.append(f"允许的恐怖手法：{', '.join(allowed_devices)}")

        return constraints

    def execute_rewrite(self, rewrite_plan: RewritePlan, rewrite_context: RewriteContext) -> RewriteResult:
        """
        执行修稿
        流程：
        1. 根据 rewrite_mode 执行修稿
        2. 生成 rewrite_diff
        3. 重新评估质量（如果可能）
        4. 决定是否接受修稿结果
        """
        original_draft = rewrite_context.chapter_draft
        rewritten_draft = original_draft

        try:
            if rewrite_plan.rewrite_mode == RewriteMode.FULL_CHAPTER_REWRITE:
                rewritten_draft = self._full_chapter_rewrite(rewrite_plan, rewrite_context)
            elif rewrite_plan.rewrite_mode == RewriteMode.SECTION_REWRITE:
                rewritten_draft = self._section_rewrite(rewrite_plan, rewrite_context)
            else:
                rewritten_draft = original_draft

            changed_sections = self._generate_changed_sections(original_draft, rewritten_draft, rewrite_plan)

            quality_before = rewrite_context.quality_report.get("overall_score", 0.0)
            quality_after = quality_before

            rewrite_result_id = f"rr_{rewrite_plan.chapter_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            accepted, accept_reason = self._decide_acceptance(
                quality_before, quality_after, changed_sections, rewrite_context
            )

            result = RewriteResult(
                rewrite_result_id=rewrite_result_id,
                rewrite_plan_id=rewrite_plan.rewrite_plan_id,
                chapter_id=rewrite_plan.chapter_id,
                status="success",
                rewritten_draft_file=str(self.rewrite_reports_dir / f"{rewrite_plan.chapter_id}_rewritten_draft.md"),
                changed_sections=changed_sections,
                consistency_check={},
                quality_before=quality_before,
                quality_after=quality_after,
                accepted=accepted,
                accept_reason=accept_reason,
            )

            self._save_rewrite_result(result)
            self._save_rewritten_draft(rewritten_draft, rewrite_plan.chapter_id)

            return result

        except Exception as e:
            if self.trace_service:
                self.trace_service.add_error("rewrite_execution", str(e))

            if self.acceptance_policy.fallback_to_original_if_failed:
                return RewriteResult(
                    rewrite_result_id=f"rr_{rewrite_plan.chapter_id}_failed",
                    rewrite_plan_id=rewrite_plan.rewrite_plan_id,
                    chapter_id=rewrite_plan.chapter_id,
                    status="failed",
                    rewritten_draft_file="",
                    changed_sections=[],
                    consistency_check={},
                    quality_before=rewrite_context.quality_report.get("overall_score", 0.0),
                    quality_after=0.0,
                    accepted=False,
                    accept_reason=f"修稿失败：{str(e)}，保留原稿",
                )
            raise

    def _full_chapter_rewrite(
        self,
        rewrite_plan: RewritePlan,
        rewrite_context: RewriteContext,
    ) -> str:
        """整章重写"""
        if not self.llm_client:
            return rewrite_context.chapter_draft

        prompt = self._build_full_rewrite_prompt(rewrite_plan, rewrite_context)

        try:
            response = self.llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
            )
            return response.choices[0].message.content or rewrite_context.chapter_draft
        except Exception as e:
            if self.trace_service:
                self.trace_service.add_error("full_chapter_rewrite", str(e))
            return rewrite_context.chapter_draft

    def _section_rewrite(
        self,
        rewrite_plan: RewritePlan,
        rewrite_context: RewriteContext,
    ) -> str:
        """分段重写"""
        if not self.llm_client:
            return rewrite_context.chapter_draft

        sections = self._split_into_sections(rewrite_context.chapter_draft)

        for goal in rewrite_plan.rewrite_goals:
            for section_id in goal.target_sections:
                if section_id in sections:
                    prompt = self._build_section_rewrite_prompt(
                        section_id, sections[section_id], goal, rewrite_plan, rewrite_context
                    )
                    try:
                        response = self.llm_client.chat_completion(
                            messages=[{"role": "user", "content": prompt}],
                            temperature=0.5,
                        )
                        new_content = response.choices[0].message.content
                        if new_content:
                            sections[section_id] = new_content
                    except Exception as e:
                        if self.trace_service:
                            self.trace_service.add_error(f"section_rewrite_{section_id}", str(e))

        return "\n\n".join(sections.values())

    def _split_into_sections(self, draft: str) -> Dict[str, str]:
        """将草稿拆分为段落"""
        paragraphs = [p.strip() for p in draft.split("\n\n") if p.strip()]
        sections = {}
        for i, para in enumerate(paragraphs):
            section_id = f"sec_{i+1:03d}"
            sections[section_id] = para
        return sections

    def _build_full_rewrite_prompt(
        self,
        rewrite_plan: RewritePlan,
        rewrite_context: RewriteContext,
    ) -> str:
        """构建整章重写提示词"""
        goals_description = "\n".join([
            f"- {g.type.value}: {g.reason}" for g in rewrite_plan.rewrite_goals
        ])

        event_summaries = "\n".join([
            f"- {e.event_type}: {e.result[:80]}..." for e in rewrite_context.selected_events[:10]
        ])

        style_section = ""
        if rewrite_context.style_bible:
            style_section = f"\n文风要求：\n{json.dumps(rewrite_context.style_bible, ensure_ascii=False, indent=2)}"

        voice_section = ""
        if rewrite_context.character_voice_profiles:
            voice_section = f"\n角色声音要求：\n{json.dumps(rewrite_context.character_voice_profiles, ensure_ascii=False, indent=2)}"

        genre_section = ""
        if rewrite_context.genre_context:
            genre_section = f"\n题材约束：\n{json.dumps(rewrite_context.genre_context, ensure_ascii=False, indent=2)}"

        constraints_text = "\n".join([f"- {c}" for c in rewrite_plan.global_constraints])

        return f"""你是小说修稿器，不是剧情创造者。

你只能根据 RewritePlan 修改表达、节奏、对白、心理描写和氛围。
你不能新增事实。
你不能新增角色。
你不能新增地点。
你不能新增线索。
你不能改变 EventLog 中的事件结果。
你不能泄露 forbidden_revelations。
你必须遵守 GenreContext。

修稿目标：
{goals_description}

本章必须保留的事件：
{event_summaries}
{style_section}
{voice_section}
{genre_section}

重要约束：
{constraints_text}

章节计划：
{json.dumps(rewrite_context.chapter_plan, ensure_ascii=False, indent=2)}

原始章节：
{rewrite_context.chapter_draft}

请输出修订后的完整章节。只输出正文内容，不要输出任何解释或标记。
"""

    def _build_section_rewrite_prompt(
        self,
        section_id: str,
        section_content: str,
        rewrite_goal: RewriteGoal,
        rewrite_plan: RewritePlan,
        rewrite_context: RewriteContext,
    ) -> str:
        """构建分段重写提示词"""
        event_summaries = "\n".join([
            f"- {e.event_type}: {e.result[:80]}..." for e in rewrite_context.selected_events[:5]
        ])

        constraints_text = "\n".join([f"- {c}" for c in rewrite_goal.constraints])

        task_info = self.REWRITE_TASK_PROMPTS.get(rewrite_goal.type, {})
        instruction = task_info.get("instruction", rewrite_goal.reason)

        return f"""你是专业的小说修稿编辑。请对以下段落进行重写优化。

修稿目标：
- {rewrite_goal.type.value}: {instruction}
- 原因: {rewrite_goal.reason}

重要约束：
{constraints_text}

本章关键事件背景：
{event_summaries}

原始段落：
{section_content}

请输出修订后的段落。只输出正文内容，不要输出任何解释或标记。
"""

    def _generate_changed_sections(
        self,
        original_draft: str,
        rewritten_draft: str,
        rewrite_plan: RewritePlan,
    ) -> List[ChangedSection]:
        """生成变更的段落"""
        original_sections = self._split_into_sections(original_draft)
        rewritten_sections = self._split_into_sections(rewritten_draft)

        changed_sections = []
        max_sections = max(len(original_sections), len(rewritten_sections))

        for i in range(max_sections):
            section_id = f"sec_{i+1:03d}"
            orig = original_sections.get(section_id, "")
            rew = rewritten_sections.get(section_id, "")

            if orig != rew:
                changed_sections.append(
                    ChangedSection(
                        section_id=section_id,
                        change_type="modified",
                        summary="内容已修订",
                        before_content=orig,
                        after_content=rew,
                    )
                )

        return changed_sections

    def _decide_acceptance(
        self,
        quality_before: float,
        quality_after: float,
        changed_sections: List[ChangedSection],
        rewrite_context: RewriteContext,
    ) -> tuple[bool, str]:
        """决定是否接受修稿结果"""
        policy = self.acceptance_policy

        if not changed_sections:
            return False, "没有实际变更"

        quality_improvement = quality_after - quality_before

        if quality_improvement >= policy.min_quality_improvement:
            return True, f"质量提升 {quality_improvement:.1f}，超过阈值 {policy.min_quality_improvement}"

        return False, f"质量提升 {quality_improvement:.1f}，未达到阈值 {policy.min_quality_improvement}"

    def _save_rewrite_result(self, result: RewriteResult) -> None:
        """保存修稿结果"""
        result_file = self.rewrite_reports_dir / f"{result.chapter_id}_rewrite_result.json"
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)

    def _save_rewritten_draft(self, draft: str, chapter_id: str) -> None:
        """保存修稿后的草稿"""
        draft_file = self.rewrite_reports_dir / f"{chapter_id}_rewritten_draft.md"
        with open(draft_file, "w", encoding="utf-8") as f:
            f.write(draft)

    def load_rewrite_result(self, chapter_id: str) -> Optional[RewriteResult]:
        """加载修稿结果"""
        result_file = self.rewrite_reports_dir / f"{chapter_id}_rewrite_result.json"
        if not result_file.exists():
            return None
        with open(result_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return RewriteResult(**data)

    def load_rewritten_draft(self, chapter_id: str) -> Optional[str]:
        """加载修稿后的草稿"""
        draft_file = self.rewrite_reports_dir / f"{chapter_id}_rewritten_draft.md"
        if not draft_file.exists():
            return None
        with open(draft_file, "r", encoding="utf-8") as f:
            return f.read()
