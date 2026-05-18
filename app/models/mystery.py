from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class EvidenceType(str, Enum):
    """证据类型"""
    WITNESS_STATEMENT = "witness_statement"
    PHYSICAL_EVIDENCE = "physical_evidence"
    DOCUMENT = "document"
    RECORDING = "recording"
    EXPERT_OPINION = "expert_opinion"
    CIRCUMSTANTIAL = "circumstantial"


class TruthRelevance(str, Enum):
    """真相相关度"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class Evidence:
    """证据"""
    evidence_id: str
    content: str
    evidence_type: EvidenceType = EvidenceType.PHYSICAL_EVIDENCE
    truth_relevance: TruthRelevance = TruthRelevance.MEDIUM
    reliability: float = 0.7  # 0-1
    can_mislead: bool = False
    points_to: List[str] = field(default_factory=list)  # 指向的嫌疑人
    real_meaning: str = ""
    allowed_reveal_chapters: List[int] = field(default_factory=list)  # 允许揭示的章节范围
    related_threads: List[str] = field(default_factory=list)
    related_clues: List[str] = field(default_factory=list)
    discovered_at_chapter: int = 0
    discovered_by: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "content": self.content,
            "evidence_type": self.evidence_type.value if isinstance(self.evidence_type, Enum) else self.evidence_type,
            "truth_relevance": self.truth_relevance.value if isinstance(self.truth_relevance, Enum) else self.truth_relevance,
            "reliability": self.reliability,
            "can_mislead": self.can_mislead,
            "points_to": self.points_to,
            "real_meaning": self.real_meaning,
            "allowed_reveal_chapters": self.allowed_reveal_chapters,
            "related_threads": self.related_threads,
            "related_clues": self.related_clues,
            "discovered_at_chapter": self.discovered_at_chapter,
            "discovered_by": self.discovered_by,
        }


@dataclass
class Suspect:
    """嫌疑人"""
    suspect_id: str
    character_id: str
    suspicion_level: float = 0.5  # 0-1
    apparent_motive: str = ""
    real_role: str = ""
    evidence_against: List[str] = field(default_factory=list)
    evidence_clearing: List[str] = field(default_factory=list)
    can_be_red_herring: bool = False
    cleared_at_chapter: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "suspect_id": self.suspect_id,
            "character_id": self.character_id,
            "suspicion_level": self.suspicion_level,
            "apparent_motive": self.apparent_motive,
            "real_role": self.real_role,
            "evidence_against": self.evidence_against,
            "evidence_clearing": self.evidence_clearing,
            "can_be_red_herring": self.can_be_red_herring,
            "cleared_at_chapter": self.cleared_at_chapter,
        }


@dataclass
class RedHerring:
    """误导线索"""
    red_herring_id: str
    points_to: str  # 指向的嫌疑人
    introduced_at_chapter: int = 0
    expected_clear_chapter_range: List[int] = field(default_factory=list)  # [start, end]
    supporting_evidence: List[str] = field(default_factory=list)
    clearing_evidence: List[str] = field(default_factory=list)
    status: str = "active"  # active / clearing / cleared
    risk: str = ""
    cleared_at_chapter: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "red_herring_id": self.red_herring_id,
            "points_to": self.points_to,
            "introduced_at_chapter": self.introduced_at_chapter,
            "expected_clear_chapter_range": self.expected_clear_chapter_range,
            "supporting_evidence": self.supporting_evidence,
            "clearing_evidence": self.clearing_evidence,
            "status": self.status,
            "risk": self.risk,
            "cleared_at_chapter": self.cleared_at_chapter,
        }


@dataclass
class TruthChainStep:
    """真相链步骤"""
    step_id: str
    chapter_range: List[int]  # [start, end]
    reveal_level: str  # surface / partial / major / truth
    allowed_information: str = ""
    required_evidence: List[str] = field(default_factory=list)
    revealed_at_chapter: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "chapter_range": self.chapter_range,
            "reveal_level": self.reveal_level,
            "allowed_information": self.allowed_information,
            "required_evidence": self.required_evidence,
            "revealed_at_chapter": self.revealed_at_chapter,
        }


@dataclass
class TruthChain:
    """真相链"""
    truth_id: str
    final_truth: str
    reveal_steps: List[TruthChainStep] = field(default_factory=list)
    is_closed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "truth_id": self.truth_id,
            "final_truth": self.final_truth,
            "reveal_steps": [step.to_dict() for step in self.reveal_steps],
            "is_closed": self.is_closed,
        }


@dataclass
class DeductionFairnessViolation:
    """推理公平性违规"""
    type: str
    message: str
    severity: str = "high"
    related_evidence: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "message": self.message,
            "severity": self.severity,
            "related_evidence": self.related_evidence,
        }


@dataclass
class DeductionFairnessReport:
    """推理公平性报告"""
    passed: bool = True
    violations: List[DeductionFairnessViolation] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "violations": [v.to_dict() for v in self.violations],
        }


@dataclass
class MysteryLogicReport:
    """悬疑逻辑报告"""
    evidence_count: int = 0
    suspect_count: int = 0
    red_herring_count: int = 0
    truth_chain_count: int = 0
    fairness_passed: bool = True
    issues: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evidence_count": self.evidence_count,
            "suspect_count": self.suspect_count,
            "red_herring_count": self.red_herring_count,
            "truth_chain_count": self.truth_chain_count,
            "fairness_passed": self.fairness_passed,
            "issues": self.issues,
        }
