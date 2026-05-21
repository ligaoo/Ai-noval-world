from __future__ import annotations

from typing import Any, Dict, List


class ChapterClueBudgetController:
    """
    V1.1 章节线索预算控制器
    职责：
    1. 读取 chapter_plan.clue_budget
    2. 从候选线索中筛出 selected_clues
    3. 其余放入 reserved_clues
    4. 保证 must_include_clues 不被移除
    """

    def __init__(self, quality_policy: Dict[str, Any]):
        self.v11_constraints = quality_policy.get("v11_constraints", {})
        clue_budget_config = self.v11_constraints.get("clue_budget", {})
        self.chapter_1_max_clues = clue_budget_config.get("chapter_1_max_clues", 3)
        self.default_max_clues_per_chapter = clue_budget_config.get("default_max_clues_per_chapter", 5)
        self.max_must_include_clues = clue_budget_config.get("max_must_include_clues", 2)

    def apply(self, chapter_plan: Dict[str, Any], available_clues: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        应用线索预算，筛选出本章节要展示的线索
        """
        chapter_no = chapter_plan.get("chapter_no", 1)
        clue_budget = chapter_plan.get("clue_budget", {})

        # 确定本章最大线索数
        if chapter_no == 1:
            max_clues = clue_budget.get("max_clues", self.chapter_1_max_clues)
        else:
            max_clues = clue_budget.get("max_clues", self.default_max_clues_per_chapter)

        # 分离 must_include 线索和普通线索
        must_include_clues: List[Dict[str, Any]] = []
        normal_clues: List[Dict[str, Any]] = []

        for clue in available_clues:
            if clue.get("must_include", False):
                must_include_clues.append(clue)
            else:
                normal_clues.append(clue)

        # 确保 must_include 线索不超过上限
        if len(must_include_clues) > self.max_must_include_clues:
            # 按优先级排序，只保留优先级最高的
            must_include_clues = sorted(
                must_include_clues,
                key=lambda c: c.get("priority", 5),
                reverse=True
            )[:self.max_must_include_clues]

        # 计算剩余可用名额
        remaining_slots = max_clues - len(must_include_clues)

        # 从普通线索中按优先级挑选
        if remaining_slots > 0:
            selected_normal_clues = sorted(
                normal_clues,
                key=lambda c: c.get("priority", 5),
                reverse=True
            )[:remaining_slots]
        else:
            selected_normal_clues = []

        # 未选中的普通线索放入 reserved
        reserved_clues = [
            clue for clue in normal_clues
            if clue not in selected_normal_clues
        ]

        # 合并最终选中的线索
        selected_clues = must_include_clues + selected_normal_clues

        # 更新 chapter_plan
        chapter_plan["clue_budget"] = {
            "max_clues": max_clues,
            "selected_count": len(selected_clues),
            "reserved_count": len(reserved_clues),
            "must_include_count": len(must_include_clues),
        }
        chapter_plan["selected_clues"] = selected_clues
        chapter_plan["reserved_clues"] = reserved_clues

        return chapter_plan

    def check_clue_density(self, chapter_content: str, selected_clues: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        检查章节实际线索密度（供质量评估使用）
        """
        detected_clue_count = 0
        clue_locations: List[Dict[str, Any]] = []

        for clue in selected_clues:
            clue_text = clue.get("text", "")
            if clue_text and clue_text in chapter_content:
                detected_clue_count += 1
                # 找到所有出现位置
                import re
                for match in re.finditer(re.escape(clue_text), chapter_content):
                    clue_locations.append({
                        "clue_id": clue.get("clue_id", ""),
                        "start_pos": match.start(),
                        "end_pos": match.end(),
                    })

        max_allowed = self.chapter_1_max_clues if selected_clues and len(selected_clues) > 0 else self.default_max_clues_per_chapter

        return {
            "detected_clue_count": detected_clue_count,
            "max_allowed": max_allowed,
            "clue_locations": clue_locations,
            "over_budget": detected_clue_count > max_allowed,
            "overage": max(0, detected_clue_count - max_allowed),
        }
