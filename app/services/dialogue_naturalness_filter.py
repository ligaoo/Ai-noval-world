from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class FilterResult:
    """过滤器结果"""
    original_dialogue: str
    filtered_dialogue: str
    issues_found: List[str]
    modifications_applied: List[str]
    passed: bool = True


class DialogueNaturalnessFilter:
    """
    V1.1 NPC对话自然度过滤器
    职责：
    1. 检查单轮新事实数量
    2. 检查是否"背景说明整段输出"
    3. 改写为不情愿、碎片化回答
    """

    DEFAULT_MAX_FACTS_PER_TURN = 1
    DEFAULT_DISCLOSURE_POLICY = {
        "style": "reluctant",
        "max_new_facts": 1,
        "requires_pressure": True,
        "avoid_exposition": True,
    }

    # 检测说明性对话的关键词
    EXPOSITION_PATTERNS = [
        r"其实", r"原来", r"事实是", r"情况是", r"你知道吗",
        r"我告诉你", r"事情是这样", r"那是因为", r"原因是",
        r"简单来说", r"总的来说", r"那就是", r"就是说",
    ]

    # NPC不情愿表达的模板
    RELUCTANT_TEMPLATES = {
        "hesitation_prefix": [
            "...",
            "嗯...",
            "这个...",
            "我不太确定...",
            "可能...",
            "好像是...",
        ],
        "fragment_markers": [
            "至少我是这么觉得",
            "就我所知...",
            "只记得这些了",
            "其他的我不清楚",
        ],
        "deflection_responses": [
            "你怎么突然问起这个？",
            "这些对你很重要吗？",
            "问这个做什么？",
            "别打听太多，对你没好处。",
        ],
    }

    def __init__(self, npc_config: Dict[str, Any] = None):
        """
        初始化过滤器
        :param npc_config: NPC配置，包含 disclosure_policy
        """
        self.npc_config = npc_config or {}
        self.disclosure_policy = self.npc_config.get(
            "disclosure_policy", self.DEFAULT_DISCLOSURE_POLICY
        )

    def filter(self, npc_dialogue: str, character_name: str = "NPC") -> FilterResult:
        """
        过滤NPC对话，使其更自然
        :param npc_dialogue: 原始NPC对话
        :param character_name: NPC角色名称
        :return: 过滤结果
        """
        issues_found: List[str] = []
        modifications: List[str] = []
        filtered_text = npc_dialogue

        # 1. 检查事实数量
        fact_count = self._count_facts(npc_dialogue)
        max_facts = self.disclosure_policy.get("max_new_facts", self.DEFAULT_MAX_FACTS_PER_TURN)

        if fact_count > max_facts:
            issues_found.append(
                f"单轮对话包含 {fact_count} 个新事实，超过阈值 {max_facts}"
            )
            filtered_text = self._reduce_fact_density(filtered_text, fact_count, max_facts)
            modifications.append(f"减少事实密度，从 {fact_count} 个降至约 {max_facts} 个")

        # 2. 检查说明性文字
        exposition_score = self._detect_exposition(npc_dialogue)
        if exposition_score > 0.3:
            issues_found.append(f"说明性文字比例过高（{int(exposition_score * 100)}%）")
            filtered_text = self._remove_exposition(filtered_text)
            modifications.append("移除直白的说明性表达")

        # 3. 应用不情愿风格（如果配置要求）
        if self.disclosure_policy.get("style") == "reluctant":
            filtered_text = self._apply_reluctant_style(filtered_text, character_name)
            modifications.append("应用不情愿对话风格")

        # 4. 检查是否有整段背景说明
        if self._is_block_exposition(npc_dialogue):
            issues_found.append("检测到整段背景说明")
            filtered_text = self._break_down_exposition(filtered_text)
            modifications.append("将整段说明拆分为碎片化回答")

        passed = len(issues_found) == 0

        return FilterResult(
            original_dialogue=npc_dialogue,
            filtered_dialogue=filtered_text,
            issues_found=issues_found,
            modifications_applied=modifications,
            passed=passed,
        )

    def _count_facts(self, text: str) -> int:
        """
        估算文本中的事实数量
        基于句子数量和确定性标记来估算
        """
        sentences = re.split(r'[。！？；]', text)
        sentences = [s.strip() for s in sentences if s.strip()]

        # 每个句子可能包含0-2个事实
        fact_count = 0
        for s in sentences:
            # 确定性标记越多，事实数量越高
            certainty_markers = ["是", "有", "在", "知道", "记得", "确实", "的确"]
            markers_found = sum(1 for m in certainty_markers if m in s)
            fact_count += min(markers_found, 2)

        return max(fact_count, len(sentences) // 2)

    def _detect_exposition(self, text: str) -> float:
        """
        检测说明性文字的比例
        返回0-1的分数，越高说明说明性越强
        """
        exposition_count = 0
        for pattern in self.EXPOSITION_PATTERNS:
            if re.search(pattern, text):
                exposition_count += 1

        char_count = len(text)
        if char_count == 0:
            return 0.0

        # 说明性标记数量 + 文本长度作为因素
        length_factor = min(char_count / 100, 1.0)
        pattern_factor = min(exposition_count / 3, 1.0)

        return (length_factor + pattern_factor) / 2

    def _is_block_exposition(self, text: str) -> bool:
        """
        检测是否为整段背景说明
        """
        # 如果文本过长且包含多个说明性标记，则认为是整段说明
        if len(text) > 150:
            exposition_markers = sum(1 for p in self.EXPOSITION_PATTERNS if re.search(p, text))
            if exposition_markers >= 2:
                return True

        # 检查是否是连续的陈述句
        sentences = re.split(r'[。！？；]', text)
        statements = [s for s in sentences if s.strip() and not s.strip().endswith("？")]
        if len(statements) >= 4:
            return True

        return False

    def _reduce_fact_density(self, text: str, current_facts: int, max_facts: int) -> str:
        """
        降低事实密度，将部分事实改为不确定的表达或延迟透露
        """
        sentences = re.split(r'([。！？；])', text)
        result = []

        # 保留前 max_facts 个句子，将后面的改为不确定表达
        kept_count = 0
        for i in range(0, len(sentences) - 1, 2):
            sentence = sentences[i].strip()
            punctuation = sentences[i + 1] if i + 1 < len(sentences) else ""

            if not sentence:
                continue

            if kept_count < max_facts:
                result.append(f"{sentence}{punctuation}")
                kept_count += 1
            else:
                # 将后面的句子改为不确定的表达
                modified = f"不过{sentence}...我也不太确定"
                result.append(f"{modified}{punctuation}")
                break  # 只保留部分信息

        return "".join(result)

    def _remove_exposition(self, text: str) -> str:
        """
        移除直白的说明性表达
        """
        result = text

        # 移除说明性开头标记
        for pattern in self.EXPOSITION_PATTERNS:
            result = re.sub(f"^{pattern}[，, ]*", "", result)
            result = re.sub(f"[。]{pattern}[，, ]*", "。", result)

        return result

    def _apply_reluctant_style(self, text: str, character_name: str) -> str:
        """
        应用不情愿的对话风格
        """
        import random

        # 在开头添加犹豫
        prefix = random.choice(self.RELUCTANT_TEMPLATES["hesitation_prefix"])

        # 如果文本较长，在中间或末尾添加碎片化标记
        sentences = re.split(r'([。！？；])', text)

        if len(sentences) > 3:
            # 在中间插入"停顿"
            mid_point = len(sentences) // 2
            sentences.insert(mid_point, "...")

        result = prefix + "".join(sentences)

        # 在末尾添加碎片化标记
        if random.random() > 0.5:
            fragment_marker = random.choice(self.RELUCTANT_TEMPLATES["fragment_markers"])
            result = result.rstrip("。！？；") + f"。{fragment_marker}。"

        return result

    def _break_down_exposition(self, text: str) -> str:
        """
        将整段说明拆分为碎片化回答
        """
        sentences = [s.strip() for s in re.split(r'[。！？；]', text) if s.strip()]

        if len(sentences) <= 2:
            return text

        # 只保留最重要的2-3句，其余改为"不确定"
        import random

        kept_sentences = sentences[:2]
        result = "...".join(kept_sentences) + "。"

        # 添加碎片化标记
        fragment = random.choice(self.RELUCTANT_TEMPLATES["fragment_markers"])
        result += f"其他的我不太清楚了。{fragment}。"

        return result

    @staticmethod
    def for_character(characters: List[Dict[str, Any]], char_id: str) -> "DialogueNaturalnessFilter":
        """
        为指定角色创建过滤器
        """
        for char in characters:
            if char.get("id") == char_id:
                npc_config = char
                return DialogueNaturalnessFilter(npc_config)

        return DialogueNaturalnessFilter()
