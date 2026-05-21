from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple


class TimelineConsistencyChecker:
    """
    V1.1 时间线一致性检查器
    职责：
    1. 从 world_bible.timeline 读取标准时间
    2. 抽取章节中的时间表达（正则 + 关键词）
    3. 判断时间表达是否冲突
    4. 输出结构化违规项，供 RewriteOptimizer 生成 fix_continuity 任务
    """

    def __init__(self, world_bible: Dict[str, Any]):
        self.timeline = world_bible.get("timeline", {})
        self.timeline_explanations = world_bible.get("timeline_explanations", {})

        # 时间表达的正则模式
        self.time_patterns = [
            (r"(\d+)\s*年前", "years_ago"),
            (r"废弃了\s*(\d+)\s*年", "abandoned_years"),
            (r"关闭了\s*(\d+)\s*年", "closed_years"),
            (r"事故发生在\s*(\d+)\s*年前", "accident_years_ago"),
        ]

        # 关键词到标准字段的映射
        self.keyword_to_slot = {
            "官方关闭": "official_closed_years_ago",
            "官方停用": "official_closed_years_ago",
            "实际废弃": "actual_abandoned_years_ago",
            "没人进出": "actual_abandoned_years_ago",
            "事故": "hospital_accident_years_ago",
            "火灾": "hospital_accident_years_ago",
        }

    def check(self, chapter_content: str) -> Dict[str, Any]:
        """
        检查章节内容中的时间线一致性
        """
        issues: List[Dict[str, Any]] = []

        # 提取所有时间表达
        time_expressions = self._extract_time_expressions(chapter_content)

        # 检查每个时间表达是否与标准冲突
        for expr, value, slot_hint in time_expressions:
            slot = self._resolve_slot(expr, slot_hint)
            if slot and slot in self.timeline:
                expected_value = self.timeline[slot]
                if value != expected_value:
                    issues.append({
                        "type": "timeline_conflict",
                        "phrase": expr,
                        "detected_value": value,
                        "expected_slot": slot,
                        "expected_value": expected_value,
                        "explanation": self.timeline_explanations.get(slot, ""),
                        "severity": "high" if abs(value - expected_value) > 1 else "medium",
                    })

        # 检查是否有模糊的时间表达（没有明确归因的）
        ambiguous_exprs = [
            expr for expr, value, slot_hint in time_expressions
            if not self._resolve_slot(expr, slot_hint)
        ]
        for expr in ambiguous_exprs:
            issues.append({
                "type": "timeline_ambiguous_statement",
                "phrase": expr,
                "severity": "low",
                "suggestion": "请明确该时间表达对应的是官方关闭时间、实际废弃时间还是事故时间。"
            })

        return {
            "passed": len(issues) == 0,
            "issues": issues,
            "standard_timeline": self.timeline,
            "rewrite_suggestion": self._generate_rewrite_suggestion(issues),
        }

    def _extract_time_expressions(self, content: str) -> List[Tuple[str, int, Optional[str]]]:
        """
        从文本中提取时间表达
        返回列表：(匹配的短语, 数值, 槽位提示)
        """
        results: List[Tuple[str, int, Optional[str]]] = []

        for pattern, slot_hint in self.time_patterns:
            for match in re.finditer(pattern, content):
                phrase = match.group(0)
                value = int(match.group(1))
                results.append((phrase, value, slot_hint))

        return results

    def _resolve_slot(self, phrase: str, slot_hint: Optional[str]) -> Optional[str]:
        """
        根据短语内容解析应该对应哪个时间槽
        """
        # 首先根据关键词匹配
        for keyword, slot in self.keyword_to_slot.items():
            if keyword in phrase:
                return slot

        # 根据正则的槽位提示推断
        if slot_hint == "years_ago":
            # 默认可能是事故时间，但需要上下文
            # 这里简单处理，返回 None 表示模糊，由调用方判断
            return None
        elif slot_hint == "abandoned_years":
            return "actual_abandoned_years_ago"
        elif slot_hint == "closed_years":
            return "official_closed_years_ago"
        elif slot_hint == "accident_years_ago":
            return "hospital_accident_years_ago"

        return None

    def _generate_rewrite_suggestion(self, issues: List[Dict[str, Any]]) -> str:
        """
        生成统一的修稿建议
        """
        if not issues:
            return ""

        conflict_issues = [i for i in issues if i["type"] == "timeline_conflict"]

        if conflict_issues:
            lines = [
                "统一时间线：",
                f"- 十年前发生旧医院事故（{self.timeline.get('hospital_accident_years_ago', 10)}年前）",
                f"- 九年前起实际无人进出（{self.timeline.get('actual_abandoned_years_ago', 9)}年前）",
                f"- 两年前官方才正式登记停用（{self.timeline.get('official_closed_years_ago', 2)}年前）",
                "",
                "请在表述中明确区分这三个不同的时间节点，避免混淆。"
            ]
            return "\n".join(lines)

        return ""
