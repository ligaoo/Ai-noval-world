from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class RewriteSuggestion:
    """修稿建议"""
    suggestion_id: str
    type: str
    message: str
    rewrite_task: str
    target_sections: List[str] = field(default_factory=list)
    priority: int = 7
    constraints: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "suggestion_id": self.suggestion_id,
            "type": self.type,
            "message": self.message,
            "rewrite_task": self.rewrite_task,
            "target_sections": self.target_sections,
            "priority": self.priority,
            "constraints": self.constraints,
        }


class RewriteSuggestionGenerator:
    """
    V5.1 修稿建议生成器
    根据质量问题生成具体的修稿建议，为 V5.2 自动修稿提供输入
    """

    PROBLEM_TO_SUGGESTION_MAPPING = {
        "weak_conflict": {
            "type": "increase_conflict",
            "rewrite_task": "increase_conflict",
            "message_template": "可以增强角色之间的目标冲突或外部阻碍，增加紧张感。",
            "constraints": [
                "只能强化已有事件的表达，不能新增冲突事件",
                "不能改变事件结果",
            ],
        },
        "slow_middle": {
            "type": "tighten_pacing",
            "rewrite_task": "tighten_pacing",
            "message_template": "压缩拖沓的段落，合并重复的场景描写，加快节奏。",
            "constraints": [
                "不能删除关键线索或伏笔",
                "保持必要的信息传递",
            ],
        },
        "weak_hook": {
            "type": "improve_hook",
            "rewrite_task": "improve_hook",
            "message_template": "强化章节结尾的钩子，增加读者的期待感。",
            "constraints": [
                "只能基于已有事件强化表达",
                "不能提前透露后续章节的内容",
            ],
        },
        "flat_emotional_curve": {
            "type": "deepen_character",
            "rewrite_task": "deepen_character",
            "message_template": "增加角色的内心活动或情绪变化描写，丰富情绪曲线。",
            "constraints": [
                "心理活动必须符合角色性格",
                "不能添加新的事实信息",
            ],
        },
        "low_plot_progress": {
            "type": "enhance_suspense",
            "rewrite_task": "enhance_suspense",
            "message_template": "强化已有线索的重要性暗示，突出悬念感。",
            "constraints": [
                "不能添加新的线索",
                "不能泄露未发现的事实",
            ],
        },
        "thin_character_motivation": {
            "type": "deepen_character",
            "rewrite_task": "deepen_character",
            "message_template": "通过细节描写强化角色的动机，让行动更有说服力。",
            "constraints": [
                "不能改变角色的行动序列",
                "不能添加新的背景故事",
            ],
        },
        "dialogue_too_expository": {
            "type": "improve_dialogue",
            "rewrite_task": "improve_dialogue",
            "message_template": "将过于直白的解释性对话改为含蓄的潜台词，增加对话张力。",
            "constraints": [
                "关键信息必须保留",
                "对话必须符合角色性格",
            ],
        },
        "style_drift": {
            "type": "polish_style",
            "rewrite_task": "polish_style",
            "message_template": "调整文风，使其与项目整体风格保持一致。",
            "constraints": [
                "保持所有事实信息不变",
            ],
        },
        "voice_drift": {
            "type": "improve_dialogue",
            "rewrite_task": "improve_dialogue",
            "message_template": "调整角色对白，使其符合角色的声音设定。",
            "constraints": [
                "关键信息必须保留",
                "不能改变对话内容",
            ],
        },
        "over_explanation": {
            "type": "reduce_exposition",
            "rewrite_task": "reduce_exposition",
            "message_template": "减少直白的解释，改为通过细节或动作暗示。",
            "constraints": [
                "关键信息必须保留",
            ],
        },
        "scene_repetition": {
            "type": "tighten_pacing",
            "rewrite_task": "tighten_pacing",
            "message_template": "合并重复的场景描写，避免读者疲劳。",
            "constraints": [
                "不能删除关键的环境信息",
            ],
        },
        "suspense_without_payoff": {
            "type": "strengthen_payoff",
            "rewrite_task": "strengthen_payoff",
            "message_template": "强化伏笔回收的力度，让揭晓时刻更有冲击力。",
            "constraints": [
                "不能改变伏笔回收的顺序",
                "不能添加新的回收内容",
            ],
        },
        "too_many_threads_opened": {
            "type": "enhance_suspense",
            "rewrite_task": "enhance_suspense",
            "message_template": "整合多条悬念线的描写，突出主线，弱化次要线索。",
            "constraints": [
                "不能删除任何悬念线",
            ],
        },
        "no_thread_progress": {
            "type": "enhance_suspense",
            "rewrite_task": "enhance_suspense",
            "message_template": "强调已有悬念的重要性，增加对后续推进的期待感。",
            "constraints": [
                "不能添加新的悬念",
            ],
        },
        "payoff_too_abrupt": {
            "type": "strengthen_payoff",
            "rewrite_task": "strengthen_payoff",
            "message_template": "增加伏笔回收的铺垫，让揭晓过程更自然。",
            "constraints": [
                "不能改变揭晓的时机",
            ],
        },
        "low_scene_vividness": {
            "type": "enhance_scene",
            "rewrite_task": "enhance_scene",
            "message_template": "增加感官描写，提升场景的画面感。",
            "constraints": [
                "不能添加不符合世界设定的元素",
            ],
        },
        "unclear_character_goal": {
            "type": "deepen_character",
            "rewrite_task": "deepen_character",
            "message_template": "通过细节强调角色的当前目标，让读者更清晰地理解角色行动的意义。",
            "constraints": [
                "不能改变角色的目标",
            ],
        },
        "poor_dialogue_voice": {
            "type": "improve_dialogue",
            "rewrite_task": "improve_dialogue",
            "message_template": "调整对白的措辞和语气，使其更符合角色的声音设定。",
            "constraints": [
                "对话内容必须保持不变",
            ],
        },
        # V1.1 新增问题类型到修稿建议的映射
        "clue_overload": {
            "type": "reduce_clue_density",
            "rewrite_task": "reduce_clue_density",
            "message_template": "线索密度过高，将部分线索后移或改为更含蓄的暗示，避免第一章像线索清单。",
            "constraints": [
                "不能删除必须包含的线索",
                "线索的核心信息必须保留",
            ],
        },
        "missing_required_character_beat": {
            "type": "deepen_character",
            "rewrite_task": "deepen_character",
            "message_template": "缺少必须的角色情感节拍，需要补充主角的内心活动或回忆，展示其行动背后的情感动机。",
            "constraints": [
                "情感描写必须符合角色性格",
                "不能添加新的事实信息",
            ],
        },
        "thin_emotional_motivation": {
            "type": "deepen_character",
            "rewrite_task": "deepen_character",
            "message_template": "主角的情感动机薄弱，需要通过细节描写强化其行动的情感驱动力。",
            "constraints": [
                "不能改变角色的行动序列",
                "不能添加新的背景故事",
            ],
        },
        "metaphor_overload": {
            "type": "reduce_overwriting",
            "rewrite_task": "reduce_overwriting",
            "message_template": "比喻堆砌过多，删除重复或不必要的修辞，保持文风克制。",
            "constraints": [
                "保留必要的信息性环境描写",
                "不能改变场景的氛围基调",
            ],
        },
        "decorative_description": {
            "type": "reduce_overwriting",
            "rewrite_task": "reduce_overwriting",
            "message_template": "装饰性描写过多，压缩过度修辞的段落，让描写服务于情节和氛围。",
            "constraints": [
                "保留关键的环境信息",
                "不能删除对氛围有重要作用的描写",
            ],
        },
        "weak_horror_hook": {
            "type": "improve_horror_hook",
            "rewrite_task": "improve_hook",
            "message_template": "第一章的恐怖钩子薄弱，需要在结尾增加轻微的异常感，制造不安氛围。",
            "constraints": [
                "只能使用轻微异常，不能出现直接的鬼怪攻击",
                "不能解释灵异规则",
            ],
        },
    }

    def generate_suggestions(
        self,
        classified_problems: List[Any],
        scores: Dict[str, int],
        pre_analysis: Dict[str, Any],
    ) -> List[RewriteSuggestion]:
        """生成修稿建议"""
        suggestions: List[RewriteSuggestion] = []
        suggestion_count = 0

        for problem in classified_problems:
            if not problem.can_be_rewritten:
                continue

            problem_type = problem.type
            mapping = self.PROBLEM_TO_SUGGESTION_MAPPING.get(problem_type)

            if not mapping:
                continue

            suggestion_id = f"sug_{suggestion_count:03d}"
            suggestion_count += 1

            target_sections = self._determine_target_sections(problem, pre_analysis)
            adjusted_priority = self._adjust_priority(problem, scores)

            suggestion = RewriteSuggestion(
                suggestion_id=suggestion_id,
                type=mapping["type"],
                message=mapping["message_template"],
                rewrite_task=mapping["rewrite_task"],
                target_sections=target_sections,
                priority=adjusted_priority,
                constraints=mapping["constraints"].copy(),
            )

            suggestions.append(suggestion)

        suggestions.sort(key=lambda s: s.priority, reverse=True)

        return suggestions

    def _determine_target_sections(
        self,
        problem: Any,
        pre_analysis: Dict[str, Any],
    ) -> List[str]:
        """确定需要修改的段落"""
        target_sections = []

        paragraph_count = pre_analysis.get("paragraph_count", 0)

        if paragraph_count <= 3:
            target_sections = ["sec_001", "sec_002", "sec_003"][:paragraph_count]
        else:
            problem_type = problem.type

            if problem_type in {"weak_hook", "payoff_too_abrupt"}:
                last_section = f"sec_{paragraph_count:03d}"
                second_last = f"sec_{paragraph_count - 1:03d}"
                target_sections = [second_last, last_section]
            elif problem_type in {"slow_middle", "scene_repetition"}:
                mid_start = max(1, paragraph_count // 3)
                mid_end = mid_start + max(1, paragraph_count // 3)
                for i in range(mid_start, min(mid_end + 1, paragraph_count)):
                    target_sections.append(f"sec_{i:03d}")
            else:
                for i in range(1, min(4, paragraph_count + 1)):
                    target_sections.append(f"sec_{i:03d}")

        return target_sections

    def _adjust_priority(
        self,
        problem: Any,
        scores: Dict[str, int],
    ) -> int:
        """调整建议优先级"""
        base_priority = problem.priority

        dimension = problem.score_dimension
        if dimension and dimension in scores:
            score = scores[dimension]
            if score < 5:
                base_priority += 2
            elif score < 6:
                base_priority += 1

        if problem.severity == "high":
            base_priority += 1
        elif problem.severity == "low":
            base_priority -= 1

        return max(1, min(10, base_priority))

    def group_suggestions_by_task(
        self,
        suggestions: List[RewriteSuggestion],
    ) -> Dict[str, List[RewriteSuggestion]]:
        """按修稿任务分组"""
        groups: Dict[str, List[RewriteSuggestion]] = {}

        for suggestion in suggestions:
            task = suggestion.rewrite_task
            if task not in groups:
                groups[task] = []
            groups[task].append(suggestion)

        return groups

    def get_top_priority_suggestions(
        self,
        suggestions: List[RewriteSuggestion],
        max_count: int = 3,
    ) -> List[RewriteSuggestion]:
        """获取最高优先级的建议"""
        sorted_suggestions = sorted(suggestions, key=lambda s: s.priority, reverse=True)
        return sorted_suggestions[:max_count]

    def should_rewrite(
        self,
        suggestions: List[RewriteSuggestion],
        overall_score: float,
        scores: Dict[str, int],
        thresholds: Dict[str, Any],
    ) -> tuple[bool, str, List[str]]:
        """判断是否建议修稿"""
        rewrite_recommended = False
        rewrite_priority = "low"
        rewrite_reasons: List[str] = []

        min_score = thresholds.get("overall_min", 7.0)
        if overall_score < min_score:
            rewrite_recommended = True
            rewrite_priority = "medium"
            rewrite_reasons.append(f"overall_score {overall_score:.1f} 低于阈值 {min_score}")

        for dimension, threshold in thresholds.get("dimension_thresholds", {}).items():
            if dimension in scores and scores[dimension] < threshold:
                rewrite_recommended = True
                rewrite_reasons.append(f"{dimension} {scores[dimension]} 低于阈值 {threshold}")

        high_priority_suggestions = [s for s in suggestions if s.priority >= 8]
        if len(high_priority_suggestions) > 0:
            rewrite_recommended = True
            if len(high_priority_suggestions) >= 2:
                rewrite_priority = "high"

        if rewrite_recommended and rewrite_priority == "low":
            if any(s.priority >= 7 for s in suggestions):
                rewrite_priority = "medium"

        return rewrite_recommended, rewrite_priority, rewrite_reasons
