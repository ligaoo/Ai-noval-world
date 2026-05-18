from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.models.mystery import (
    DeductionFairnessReport,
    DeductionFairnessViolation,
    Evidence,
    EvidenceType,
    MysteryLogicReport,
    RedHerring,
    Suspect,
    TruthChain,
    TruthChainStep,
    TruthRelevance,
)
from app.services.trace_service import TraceService


@dataclass
class MysteryLogicConfig:
    """悬疑逻辑配置"""
    enabled: bool = True
    max_active_red_herrings: int = 3
    require_evidence_before_major_reveal: bool = True
    forbid_final_truth_without_prior_evidence: bool = True
    red_herring_clear_required: bool = True
    deduction_fairness_check_enabled: bool = True


class EvidenceGraphManager:
    """证据图管理器"""

    def __init__(self):
        self.evidence: Dict[str, Evidence] = {}

    def add_evidence(self, evidence: Evidence) -> None:
        self.evidence[evidence.evidence_id] = evidence

    def get_evidence(self, evidence_id: str) -> Optional[Evidence]:
        return self.evidence.get(evidence_id)

    def get_evidence_by_thread(self, thread_id: str) -> List[Evidence]:
        return [e for e in self.evidence.values() if thread_id in e.related_threads]

    def get_discovered_evidence(self, chapter_no: int) -> List[Evidence]:
        return [e for e in self.evidence.values() if e.discovered_at_chapter <= chapter_no]

    def get_evidence_for_reveal(self, chapter_no: int) -> List[Evidence]:
        """获取允许在当前章节揭示的证据"""
        result = []
        for e in self.evidence.values():
            if e.allowed_reveal_chapters:
                min_ch, max_ch = e.allowed_reveal_chapters[0], e.allowed_reveal_chapters[-1]
                if min_ch <= chapter_no <= max_ch:
                    result.append(e)
        return result


class SuspectTracker:
    """嫌疑人追踪器"""

    def __init__(self):
        self.suspects: Dict[str, Suspect] = {}

    def add_suspect(self, suspect: Suspect) -> None:
        self.suspects[suspect.suspect_id] = suspect

    def update_suspicion(self, suspect_id: str, new_level: float) -> None:
        if suspect_id in self.suspects:
            self.suspects[suspect_id].suspicion_level = max(0.0, min(1.0, new_level))

    def clear_suspect(self, suspect_id: str, chapter_no: int) -> None:
        if suspect_id in self.suspects:
            self.suspects[suspect_id].suspicion_level = 0.0
            self.suspects[suspect_id].cleared_at_chapter = chapter_no

    def get_active_suspects(self) -> List[Suspect]:
        return [s for s in self.suspects.values() if s.suspicion_level > 0.2]

    def get_most_suspected(self) -> Optional[Suspect]:
        active = self.get_active_suspects()
        if not active:
            return None
        return max(active, key=lambda s: s.suspicion_level)


class RedHerringManager:
    """误导线索管理器"""

    def __init__(self, max_active: int = 3):
        self.red_herrings: Dict[str, RedHerring] = {}
        self.max_active = max_active

    def add_red_herring(self, red_herring: RedHerring) -> bool:
        active_count = sum(1 for rh in self.red_herrings.values() if rh.status == "active")
        if active_count >= self.max_active:
            return False
        self.red_herrings[red_herring.red_herring_id] = red_herring
        return True

    def clear_red_herring(self, red_herring_id: str, chapter_no: int) -> None:
        if red_herring_id in self.red_herrings:
            self.red_herrings[red_herring_id].status = "cleared"
            self.red_herrings[red_herring_id].cleared_at_chapter = chapter_no

    def get_active_red_herrings(self) -> List[RedHerring]:
        return [rh for rh in self.red_herrings.values() if rh.status == "active"]

    def get_red_herrings_due_for_clearing(self, chapter_no: int) -> List[RedHerring]:
        result = []
        for rh in self.red_herrings.values():
            if rh.status == "active" and rh.expected_clear_chapter_range:
                if chapter_no >= rh.expected_clear_chapter_range[-1]:
                    result.append(rh)
        return result


class TruthChainManager:
    """真相链管理器"""

    def __init__(self):
        self.truth_chains: Dict[str, TruthChain] = {}

    def add_truth_chain(self, truth_chain: TruthChain) -> None:
        self.truth_chains[truth_chain.truth_id] = truth_chain

    def reveal_step(self, truth_id: str, step_id: str, chapter_no: int) -> bool:
        """揭示真相链的某个步骤"""
        if truth_id not in self.truth_chains:
            return False

        chain = self.truth_chains[truth_id]
        for step in chain.reveal_steps:
            if step.step_id == step_id:
                # 检查是否在当前章节范围内
                min_ch, max_ch = step.chapter_range
                if min_ch <= chapter_no <= max_ch:
                    step.revealed_at_chapter = chapter_no
                    return True
                else:
                    return False
        return False

    def get_current_reveal_level(self, truth_id: str, chapter_no: int) -> str:
        """获取当前章节允许揭示的真相等级"""
        if truth_id not in self.truth_chains:
            return "none"

        chain = self.truth_chains[truth_id]
        current_level = "surface"
        for step in chain.reveal_steps:
            min_ch, max_ch = step.chapter_range
            if chapter_no >= min_ch:
                current_level = step.reveal_level
            else:
                break
        return current_level

    def is_truth_chain_closed(self, truth_id: str) -> bool:
        if truth_id not in self.truth_chains:
            return False
        chain = self.truth_chains[truth_id]
        return all(step.revealed_at_chapter > 0 for step in chain.reveal_steps)


class DeductionFairnessChecker:
    """推理公平性检查器"""

    def __init__(self, config: Optional[MysteryLogicConfig] = None):
        self.config = config or MysteryLogicConfig()

    def check_fairness(
        self,
        evidence_graph: EvidenceGraphManager,
        truth_chain: Optional[TruthChain],
        chapter_no: int,
        target_chapters: int = 30,
    ) -> DeductionFairnessReport:
        """检查推理公平性"""
        violations: List[DeductionFairnessViolation] = []

        if truth_chain and self.config.require_evidence_before_major_reveal:
            violations.extend(self._check_reveal_fairness(evidence_graph, truth_chain, chapter_no))

        if self.config.forbid_final_truth_without_prior_evidence:
            violations.extend(self._check_final_truth_fairness(evidence_graph, truth_chain, chapter_no, target_chapters))

        return DeductionFairnessReport(
            passed=len(violations) == 0,
            violations=violations,
        )

    def _check_reveal_fairness(
        self,
        evidence_graph: EvidenceGraphManager,
        truth_chain: TruthChain,
        chapter_no: int,
    ) -> List[DeductionFairnessViolation]:
        """检查揭示是否公平"""
        violations = []

        for step in truth_chain.reveal_steps:
            min_ch, max_ch = step.chapter_range
            if min_ch <= chapter_no <= max_ch:
                for ev_id in step.required_evidence:
                    evidence = evidence_graph.get_evidence(ev_id)
                    if not evidence or evidence.discovered_at_chapter > chapter_no:
                        violations.append(DeductionFairnessViolation(
                            type="unfair_reveal",
                            message=f"章节 {chapter_no} 揭示了 {step.reveal_level} 等级的真相，但缺少前置证据 {ev_id}",
                            severity="high",
                            related_evidence=ev_id,
                        ))

        return violations

    def _check_final_truth_fairness(
        self,
        evidence_graph: EvidenceGraphManager,
        truth_chain: Optional[TruthChain],
        chapter_no: int,
        target_chapters: int,
    ) -> List[DeductionFairnessViolation]:
        """检查终局真相公平性"""
        violations = []

        if chapter_no < target_chapters * 0.8:
            return violations

        if truth_chain:
            final_step = truth_chain.reveal_steps[-1] if truth_chain.reveal_steps else None
            if final_step and final_step.reveal_level == "truth":
                required_evidence = final_step.required_evidence
                discovered_count = sum(
                    1 for ev_id in required_evidence
                    if evidence_graph.get_evidence(ev_id)
                    and evidence_graph.get_evidence(ev_id).discovered_at_chapter <= chapter_no
                )
                if discovered_count < len(required_evidence) * 0.7:
                    violations.append(DeductionFairnessViolation(
                        type="final_truth_missing_evidence",
                        message="终局真相揭示前缺少足够的前置证据铺垫",
                        severity="high",
                    ))

        return violations


class MysteryLogicManager:
    """
    V5.6 MysteryLogicManager 悬疑逻辑管理器
    管理证据、嫌疑人、误导线索和真相链
    """

    def __init__(
        self,
        sim_dir: Path,
        config: Optional[MysteryLogicConfig] = None,
        trace_service: Optional[TraceService] = None,
    ):
        self.sim_dir = sim_dir
        self.config = config or MysteryLogicConfig()
        self.trace_service = trace_service

        self.evidence_graph = EvidenceGraphManager()
        self.suspect_tracker = SuspectTracker()
        self.red_herring_manager = RedHerringManager(self.config.max_active_red_herrings)
        self.truth_chain_manager = TruthChainManager()
        self.fairness_checker = DeductionFairnessChecker(self.config)

        self.mystery_reports_dir = sim_dir / "mystery_reports"
        self.mystery_reports_dir.mkdir(exist_ok=True)

        self._load_mystery_data()

    def add_evidence(self, evidence: Evidence) -> None:
        self.evidence_graph.add_evidence(evidence)
        self._save_mystery_data()

    def add_suspect(self, suspect: Suspect) -> None:
        self.suspect_tracker.add_suspect(suspect)
        self._save_mystery_data()

    def add_red_herring(self, red_herring: RedHerring) -> bool:
        result = self.red_herring_manager.add_red_herring(red_herring)
        if result:
            self._save_mystery_data()
        return result

    def add_truth_chain(self, truth_chain: TruthChain) -> None:
        self.truth_chain_manager.add_truth_chain(truth_chain)
        self._save_mystery_data()

    def update_from_chapter(
        self,
        chapter_no: int,
        chapter_summary: Dict[str, Any],
        target_chapters: int = 30,
    ) -> MysteryLogicReport:
        """从章节更新悬疑逻辑状态"""
        # 检查是否需要清除误导线索
        due_for_clearing = self.red_herring_manager.get_red_herrings_due_for_clearing(chapter_no)
        for rh in due_for_clearing:
            if self.config.red_herring_clear_required:
                self.red_herring_manager.clear_red_herring(rh.red_herring_id, chapter_no)

        # 检查推理公平性
        fairness_report = DeductionFairnessReport(passed=True)
        if self.config.deduction_fairness_check_enabled:
            truth_chain = None
            if self.truth_chain_manager.truth_chains:
                truth_chain = list(self.truth_chain_manager.truth_chains.values())[0]
            fairness_report = self.fairness_checker.check_fairness(
                self.evidence_graph,
                truth_chain,
                chapter_no,
                target_chapters,
            )

        report = MysteryLogicReport(
            evidence_count=len(self.evidence_graph.evidence),
            suspect_count=len(self.suspect_tracker.suspects),
            red_herring_count=len(self.red_herring_manager.get_active_red_herrings()),
            truth_chain_count=len(self.truth_chain_manager.truth_chains),
            fairness_passed=fairness_report.passed,
            issues=[v.message for v in fairness_report.violations],
        )

        self._save_mystery_report(report, chapter_no)
        return report

    def get_mystery_recommendation(self, chapter_no: int, target_chapters: int) -> Dict[str, Any]:
        """获取悬疑逻辑推荐"""
        recommendation = {
            "should_introduce_evidence": False,
            "should_clear_red_herring": False,
            "can_reveal_truth_level": "none",
            "warnings": [],
        }

        # 检查是否需要引入新证据
        if len(self.evidence_graph.evidence) < (chapter_no // 3):
            recommendation["should_introduce_evidence"] = True

        # 检查是否需要清除误导线索
        due_for_clearing = self.red_herring_manager.get_red_herrings_due_for_clearing(chapter_no)
        if due_for_clearing:
            recommendation["should_clear_red_herring"] = True
            recommendation["warnings"].append(
                f"有 {len(due_for_clearing)} 条误导线索应该在本章清除"
            )

        # 检查可以揭示的真相等级
        for truth_id, chain in self.truth_chain_manager.truth_chains.items():
            level = self.truth_chain_manager.get_current_reveal_level(truth_id, chapter_no)
            if level != "none":
                recommendation["can_reveal_truth_level"] = level

        return recommendation

    def _save_mystery_data(self) -> None:
        """保存悬疑逻辑数据"""
        data_file = self.sim_dir / "mystery_data.json"
        data = {
            "evidence": {k: v.to_dict() for k, v in self.evidence_graph.evidence.items()},
            "suspects": {k: v.to_dict() for k, v in self.suspect_tracker.suspects.items()},
            "red_herrings": {k: v.to_dict() for k, v in self.red_herring_manager.red_herrings.items()},
            "truth_chains": {k: v.to_dict() for k, v in self.truth_chain_manager.truth_chains.items()},
        }
        with open(data_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _load_mystery_data(self) -> None:
        """加载悬疑逻辑数据"""
        data_file = self.sim_dir / "mystery_data.json"
        if not data_file.exists():
            return

        try:
            with open(data_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            for ev_data in data.get("evidence", {}).values():
                evidence = Evidence(**ev_data)
                self.evidence_graph.add_evidence(evidence)

            for s_data in data.get("suspects", {}).values():
                suspect = Suspect(**s_data)
                self.suspect_tracker.add_suspect(suspect)

            for rh_data in data.get("red_herrings", {}).values():
                red_herring = RedHerring(**rh_data)
                self.red_herring_manager.add_red_herring(red_herring)

            for tc_data in data.get("truth_chains", {}).values():
                truth_chain = TruthChain(**tc_data)
                self.truth_chain_manager.add_truth_chain(truth_chain)

        except Exception as e:
            if self.trace_service:
                self.trace_service.add_error("load_mystery_data", str(e))

    def _save_mystery_report(self, report: MysteryLogicReport, chapter_no: int) -> None:
        """保存悬疑逻辑报告"""
        report_file = self.mystery_reports_dir / f"ch_{chapter_no:03d}_mystery.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report.to_dict(), f, ensure_ascii=False, indent=2)
