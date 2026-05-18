from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class StyleBible:
    style_id: str
    tone: str = "克制、压抑、现实中透出诡异"
    sentence_style: str = "中短句为主，避免过度华丽"
    description_level: str = "适度环境描写，避免堆砌形容词"
    dialogue_style: str = "含蓄、留白、带潜台词"
    pacing_style: str = "慢热，但每章必须有实质推进"
    horror_style: str = "现实细节中透出异常，避免直接惊吓"
    forbidden_styles: List[str] = field(default_factory=lambda: [
        "热血爽文",
        "过度解释",
        "网络段子化",
        "直接恐怖喊叫",
        "过度华丽辞藻",
    ])
    preferred_devices: List[str] = field(default_factory=lambda: [
        "细节反常",
        "短暂停顿",
        "未说完的话",
        "旧物件带出的记忆",
    ])
    reference_keywords: List[str] = field(default_factory=lambda: [
        "潮湿",
        "昏暗",
        "迟疑",
        "锈迹",
        "旧灯",
    ])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "style_id": self.style_id,
            "tone": self.tone,
            "sentence_style": self.sentence_style,
            "description_level": self.description_level,
            "dialogue_style": self.dialogue_style,
            "pacing_style": self.pacing_style,
            "horror_style": self.horror_style,
            "forbidden_styles": self.forbidden_styles,
            "preferred_devices": self.preferred_devices,
            "reference_keywords": self.reference_keywords,
        }


@dataclass
class CharacterVoiceProfile:
    character_id: str
    speech_style: str = "克制、短句、不轻易暴露情绪"
    inner_monologue: str = "怀疑自己，但习惯压下恐惧"
    vocabulary: List[str] = field(default_factory=lambda: ["确认", "不对", "可能", "等等"])
    forbidden: List[str] = field(default_factory=lambda: [
        "突然热血宣言",
        "过度自我解释",
        "轻浮玩笑",
    ])
    sample_lines: List[str] = field(default_factory=lambda: [
        "我只是想确认一件事。",
        "这把锁，不像是放了十年。",
    ])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "character_id": self.character_id,
            "speech_style": self.speech_style,
            "inner_monologue": self.inner_monologue,
            "vocabulary": self.vocabulary,
            "forbidden": self.forbidden,
            "sample_lines": self.sample_lines,
        }


@dataclass
class StyleViolation:
    type: str
    message: str
    severity: str = "medium"
    location: Optional[str] = None
    suggested_fix: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "message": self.message,
            "severity": self.severity,
            "location": self.location,
            "suggested_fix": self.suggested_fix,
        }


@dataclass
class StyleCheckReport:
    chapter_id: str
    style_consistency_score: float
    voice_consistency: Dict[str, float] = field(default_factory=dict)
    violations: List[StyleViolation] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chapter_id": self.chapter_id,
            "style_consistency_score": self.style_consistency_score,
            "voice_consistency": self.voice_consistency,
            "violations": [v.to_dict() for v in self.violations],
            "suggestions": self.suggestions,
        }


@dataclass
class StyleDriftMetrics:
    chapter_id: str
    drift_from_style_bible: float = 0.0
    drift_from_recent_average: float = 0.0
    high_risk: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chapter_id": self.chapter_id,
            "drift_from_style_bible": self.drift_from_style_bible,
            "drift_from_recent_average": self.drift_from_recent_average,
            "high_risk": self.high_risk,
        }
