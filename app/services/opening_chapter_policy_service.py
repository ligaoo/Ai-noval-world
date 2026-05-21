from __future__ import annotations

from typing import Any, Dict, List


class OpeningChapterPolicyService:
    """
    V1.1 第一章策略服务
    职责：
    1. 检测 chapter_no == 1
    2. 注入第一章约束（线索上限、必须元素、禁用元素、轻异常钩子）
    3. 生成/补齐 chapter_plan.clue_budget、required_character_beats、ending_hook
    """

    def __init__(self, quality_policy: Dict[str, Any], characters: List[Dict[str, Any]]):
        self.quality_policy = quality_policy
        self.characters = characters
        self.v11_constraints = quality_policy.get("v11_constraints", {})
        self.opening_config = self.v11_constraints.get("opening_chapter", {})

    def apply(self, chapter_plan: Dict[str, Any], world_bible: Dict[str, Any]) -> Dict[str, Any]:
        """
        应用第一章策略
        """
        chapter_no = chapter_plan.get("chapter_no", 1)

        # 只对第一章应用
        if chapter_no != 1:
            chapter_plan["opening_policy_applied"] = False
            return chapter_plan

        # 1. 设置第一章线索预算
        clue_budget = self.v11_constraints.get("clue_budget", {})
        chapter_plan["clue_budget"] = {
            "max_clues": clue_budget.get("chapter_1_max_clues", 3),
            "must_include_only": False,
            "allow_foreshadowing": True,
        }

        # 2. 注入第一章必须的角色 beats
        required_beats = self._extract_required_character_beats()
        chapter_plan["required_character_beats"] = required_beats

        # 3. 注入第一章结尾钩子（轻异常）
        chapter_plan["ending_hook"] = self._generate_ending_hook_spec()

        # 4. 设置第一章禁用元素
        chapter_plan["opening_policy_applied"] = True
        chapter_plan["must_not_reveal"] = chapter_plan.get("must_not_reveal", []) + [
            "不能出现强灵异/直接攻击",
            "不能解释完整的灵异规则",
            "不能揭露核心真相",
        ]

        return chapter_plan

    def _extract_required_character_beats(self) -> List[Dict[str, Any]]:
        """
        从角色配置中提取第一章必须的情感 beat
        """
        beats: List[Dict[str, Any]] = []

        for char in self.characters:
            if char.get("role") == "主角":
                # 从 required_early_beats 中提取第一章需要的
                for beat in char.get("required_early_beats", []):
                    if beat.get("target_chapter") == 1:
                        beats.append({
                            "beat_id": beat.get("beat_id", ""),
                            "character_id": char.get("id", ""),
                            "function": beat.get("function", ""),
                            "must_include": beat.get("must_include", True),
                            "suggested_location": "early",
                            "max_length_words": 150,  # 限制情感 beat 的长度
                        })

                # 如果没有配置，添加默认的情感 beat
                if not beats and char.get("emotional_core"):
                    emotional_core = char["emotional_core"]
                    beats.append({
                        "beat_id": "beat_default_guilt",
                        "character_id": char.get("id", ""),
                        "function": "展示主角的愧疚动机",
                        "must_include": True,
                        "suggested_location": "early",
                        "max_length_words": 150,
                        "content_hint": f"{emotional_core.get('guilt_source', '')} - {emotional_core.get('current_drive', '')}",
                    })

        return beats

    def _generate_ending_hook_spec(self) -> Dict[str, Any]:
        """
        生成第一章结尾钩子规范
        """
        return {
            "type": "subtle_anomaly",
            "intensity": "low",
            "allowed_devices": [
                "轻微的声音异常",
                "物品位置的细微变化",
                "温度的不正常变化",
                "似曾相识的感觉",
                "模糊的影子/视线错觉",
            ],
            "forbidden_devices": [
                "直接的鬼怪攻击",
                "明确的超自然现象解释",
                "血腥/暴力场景",
                "完整的规则说明",
            ],
            "purpose": "让读者感到不安，但还不知道具体发生了什么",
            "max_length_words": 100,
        }

    def validate_opening_chapter(self, chapter_content: str) -> Dict[str, Any]:
        """
        验证第一章是否符合策略要求
        供质量评估使用
        """
        issues: List[Dict[str, Any]] = []
        passed_checks: List[str] = []

        # 检查是否有情感 beat（简单关键词匹配）
        guilt_keywords = ["愧疚", "后悔", "抱歉", "对不起", "当初", "如果"]
        has_emotional_beat = any(keyword in chapter_content for keyword in guilt_keywords)

        if self.opening_config.get("require_character_beat", True):
            if has_emotional_beat:
                passed_checks.append("required_character_beat_present")
            else:
                issues.append({
                    "type": "missing_required_character_beat",
                    "severity": "medium",
                    "reason": "第一章缺少主角的情感 beat，动机展示不足",
                })

        # 检查是否有轻异常钩子（在末尾部分）
        content_end = chapter_content[-500:] if len(chapter_content) > 500 else chapter_content
        anomaly_keywords = ["声音", "位置", "温度", "影子", "错觉", "不对劲", "奇怪"]
        has_subtle_hook = any(keyword in content_end for keyword in anomaly_keywords)

        if self.opening_config.get("require_subtle_anomaly_hook", True):
            if has_subtle_hook:
                passed_checks.append("subtle_anomaly_hook_present")
            else:
                issues.append({
                    "type": "weak_horror_hook",
                    "severity": "medium",
                    "reason": "第一章结尾缺少轻异常钩子",
                })

        # 检查是否有禁用元素
        if self.opening_config.get("forbid_direct_supernatural_attack", True):
            attack_keywords = ["攻击", "扑来", "抓住", "掐住", "袭击"]
            has_direct_attack = any(keyword in chapter_content for keyword in attack_keywords)
            if has_direct_attack:
                issues.append({
                    "type": "forbidden_supernatural_content",
                    "severity": "high",
                    "reason": "第一章出现了直接的灵异攻击，这会过早破坏悬念",
                })

        if self.opening_config.get("forbid_complete_rule_explanation", True):
            rule_keywords = ["规则是", "原来如此", "因为", "所以"]
            has_rule_explanation = any(keyword in chapter_content for keyword in rule_keywords)
            if has_rule_explanation and len(chapter_content) < 3000:  # 只在短文本中检查
                issues.append({
                    "type": "premature_rule_explanation",
                    "severity": "medium",
                    "reason": "第一章过早解释了灵异规则，破坏了悬念",
                })

        return {
            "passed": len(issues) == 0,
            "issues": issues,
            "passed_checks": passed_checks,
        }
