from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from app.models.production import (
    ClosureCheckItem,
    FinalClosureReport,
    FullNovelConsistencyReport,
    LongRunReport,
    LongRunTestConfig,
)
from app.services.trace_service import TraceService


class LongRunTestRunner:
    """
    V5.7 LongRunTestRunner 长篇稳定性测试运行器
    验证系统能否独自完成约 10 万字悬疑灵异长篇
    """

    def __init__(
        self,
        project_dir: Path,
        config: LongRunTestConfig,
        trace_service: Optional[TraceService] = None,
    ):
        self.project_dir = project_dir
        self.config = config
        self.trace_service = trace_service

        self.longrun_dir = project_dir / "longrun_reports"
        self.longrun_dir.mkdir(exist_ok=True)

    def run_test(
        self,
        production_orchestrator: Callable,
        final_closure_check: Callable,
        full_novel_consistency_check: Callable,
    ) -> LongRunReport:
        """
        运行长篇测试
        """
        start_time = datetime.now()
        report = LongRunReport(
            test_id=self.config.test_id,
            final_status="running",
        )

        try:
            # 启动生产
            production_result = production_orchestrator()

            # 收集结果
            report.chapters_generated = production_result.get("total_chapters", 0)
            report.total_words = production_result.get("total_words", 0)
            report.average_quality_score = production_result.get("average_quality_score", 0.0)
            report.consistency_pass_rate = production_result.get("consistency_pass_rate", 1.0)
            report.genre_consistency_pass_rate = production_result.get("genre_consistency_pass_rate", 1.0)
            report.thread_resolution_rate = production_result.get("thread_resolution_rate", 0.0)
            report.main_arc_closed = production_result.get("main_arc_closed", False)
            report.truth_chain_closed = production_result.get("truth_chain_closed", False)
            report.style_drift_score = production_result.get("style_drift_score", 0.0)
            report.npc_growth_rate_per_chapter = production_result.get("npc_growth_rate_per_chapter", 0.0)

            # 检查阈值
            passed, issues = self._check_thresholds(report)

            if passed:
                # 运行终局收束检查
                closure_report = final_closure_check()
                if not closure_report.passed:
                    report.major_issues.extend([
                        f"终局收束失败: {item.get('message', '')}"
                        for item in closure_report.unresolved_items
                    ])

                # 运行全书一致性检查
                consistency_report = full_novel_consistency_check()
                if not consistency_report.checks_passed:
                    report.major_issues.extend([
                        f"全书一致性检查失败: {issue.get('message', '')}"
                        for issue in consistency_report.issues
                    ])

            if not report.major_issues:
                report.final_status = "passed"
            else:
                report.final_status = "failed"

        except Exception as e:
            report.final_status = "failed"
            report.major_issues.append(f"测试异常: {str(e)}")
            if self.trace_service:
                self.trace_service.add_error("longrun_test", str(e))

        finally:
            self._save_report(report)

        return report

    def _check_thresholds(self, report: LongRunReport) -> tuple[bool, List[str]]:
        """检查是否达到阈值要求"""
        thresholds = self.config.thresholds
        issues = []

        if report.average_quality_score < thresholds.get("average_quality_score_min", 7.0):
            issues.append(f"平均质量分 {report.average_quality_score:.1f} 低于阈值")

        if report.consistency_pass_rate < thresholds.get("consistency_pass_rate_min", 0.95):
            issues.append(f"一致性通过率 {report.consistency_pass_rate:.0%} 低于阈值")

        if report.thread_resolution_rate < thresholds.get("thread_resolution_rate_min", 0.7):
            issues.append(f"悬念回收率 {report.thread_resolution_rate:.0%} 低于阈值")

        if thresholds.get("main_thread_resolution_required") and not report.main_arc_closed:
            issues.append("主线未闭合")

        if report.style_drift_score > thresholds.get("style_drift_max", 0.25):
            issues.append(f"文风漂移 {report.style_drift_score:.2f} 超过阈值")

        return len(issues) == 0, issues


class FinalClosureChecker:
    """
    V5.7 FinalClosureChecker 终局收束检查器
    检查全书是否完整收束
    """

    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        self.closure_dir = project_dir / "closure"
        self.closure_dir.mkdir(exist_ok=True)

    def check_closure(
        self,
        novel_id: str,
        blueprint: Dict[str, Any],
        thread_manager_state: Dict[str, Any],
        truth_chain_state: Dict[str, Any],
        character_arcs_state: Dict[str, Any],
        genre_state: Dict[str, Any],
    ) -> FinalClosureReport:
        """
        检查终局收束
        """
        closure_report_id = f"closure_{novel_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        checks = {
            "main_arc_closed": self._check_main_arc(blueprint, thread_manager_state),
            "truth_chain_closed": self._check_truth_chain(truth_chain_state),
            "high_priority_threads_resolved": self._check_high_priority_threads(thread_manager_state),
            "character_arcs_closed": self._check_character_arcs(character_arcs_state),
            "supernatural_rules_resolved": self._check_supernatural_rules(genre_state),
            "no_new_major_thread_in_ending": self._check_no_new_threads(thread_manager_state),
        }

        unresolved_items = []
        for check_name, passed in checks.items():
            if not passed:
                unresolved_items.append({
                    "type": check_name,
                    "priority": 8 if "high_priority" in check_name else 5,
                    "message": f"{check_name} 未满足",
                })

        recommendations = self._generate_recommendations(checks, thread_manager_state)

        report = FinalClosureReport(
            closure_report_id=closure_report_id,
            novel_id=novel_id,
            passed=all(checks.values()),
            checks=checks,
            unresolved_items=unresolved_items,
            recommendations=recommendations,
        )

        self._save_report(report)
        return report

    def _check_main_arc(self, blueprint: Dict[str, Any], thread_state: Dict[str, Any]) -> bool:
        """检查主线是否闭合"""
        main_threads = thread_state.get("main_threads", [])
        return all(t.get("status") in ["resolved", "abandoned"] for t in main_threads)

    def _check_truth_chain(self, truth_state: Dict[str, Any]) -> bool:
        """检查真相链是否闭合"""
        chains = truth_state.get("truth_chains", [])
        return all(chain.get("is_closed", False) for chain in chains)

    def _check_high_priority_threads(self, thread_state: Dict[str, Any]) -> bool:
        """检查高优先级悬念是否解决"""
        threads = thread_state.get("threads", [])
        high_priority = [t for t in threads if t.get("priority", 0) >= 7]
        return all(t.get("status") in ["resolved", "abandoned"] for t in high_priority)

    def _check_character_arcs(self, arcs_state: Dict[str, Any]) -> bool:
        """检查人物弧是否完成"""
        arcs = arcs_state.get("character_arcs", [])
        return all(arc.get("completed", False) for arc in arcs)

    def _check_supernatural_rules(self, genre_state: Dict[str, Any]) -> bool:
        """检查灵异规则是否解释"""
        rules = genre_state.get("supernatural_rules", [])
        return all(r.get("explained", False) for r in rules)

    def _check_no_new_threads(self, thread_state: Dict[str, Any]) -> bool:
        """检查结尾是否新增大坑"""
        recent_threads = thread_state.get("recent_threads", [])
        return len(recent_threads) == 0

    def _generate_recommendations(
        self,
        checks: Dict[str, bool],
        thread_state: Dict[str, Any],
    ) -> List[str]:
        """生成修复建议"""
        recommendations = []

        if not checks.get("high_priority_threads_resolved"):
            recommendations.append("在终章前增加对高优先级悬念的收束")

        if not checks.get("truth_chain_closed"):
            recommendations.append("确保真相链在最后几章完整揭示")

        if not checks.get("supernatural_rules_resolved"):
            recommendations.append("灵异规则应解释到应解释的程度")

        return recommendations

    def _save_report(self, report: FinalClosureReport) -> None:
        """保存收束报告"""
        report_file = self.closure_dir / f"{report.closure_report_id}.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report.to_dict(), f, ensure_ascii=False, indent=2)


class FullNovelConsistencyChecker:
    """
    V5.7 FullNovelConsistencyChecker 全书一致性检查器
    """

    def __init__(self, project_dir: Path):
        self.project_dir = project_dir

    def check_consistency(
        self,
        chapters: List[Dict[str, Any]],
        characters: Dict[str, Any],
        locations: Dict[str, Any],
        timeline: Dict[str, Any],
    ) -> FullNovelConsistencyReport:
        """
        检查全书一致性
        """
        issues = []

        # 检查角色名字一致性
        issues.extend(self._check_character_names(chapters, characters))

        # 检查地点状态一致性
        issues.extend(self._check_location_states(chapters, locations))

        # 检查时间线一致性
        issues.extend(self._check_timeline(chapters, timeline))

        # 检查已死亡/离开角色是否错误出现
        issues.extend(self._check_dead_characters(chapters, characters))

        # 检查灵异规则一致性
        issues.extend(self._check_supernatural_rules(chapters))

        return FullNovelConsistencyReport(
            novel_id="novel_unknown",
            checks_passed=len(issues) == 0,
            issues=issues,
        )

    def _check_character_names(self, chapters: List[Dict], characters: Dict) -> List[Dict]:
        """检查角色名字一致性"""
        issues = []
        valid_ids = set(characters.keys())
        valid_names = {
            str(v.get("name", "")).strip()
            for v in characters.values()
            if isinstance(v, dict) and v.get("name")
        }

        for idx, chapter in enumerate(chapters, start=1):
            chapter_no = chapter.get("chapter_no", idx)
            present = chapter.get("characters_present", []) or []
            for cid in present:
                if cid not in valid_ids:
                    issues.append({
                        "type": "unknown_character_id",
                        "chapter_no": chapter_no,
                        "severity": "high",
                        "message": f"章节 {chapter_no} 出现未注册角色ID: {cid}",
                    })

            aliases = chapter.get("character_names_used", []) or []
            for name in aliases:
                if valid_names and name not in valid_names:
                    issues.append({
                        "type": "unknown_character_name",
                        "chapter_no": chapter_no,
                        "severity": "medium",
                        "message": f"章节 {chapter_no} 出现未注册角色名: {name}",
                    })
        return issues

    def _check_location_states(self, chapters: List[Dict], locations: Dict) -> List[Dict]:
        """检查地点状态一致性"""
        issues = []
        valid_location_ids = set(locations.keys())
        known_state = {}

        for idx, chapter in enumerate(chapters, start=1):
            chapter_no = chapter.get("chapter_no", idx)
            location_changes = chapter.get("location_state_changes", {}) or {}
            for loc_id, state_patch in location_changes.items():
                if loc_id not in valid_location_ids:
                    issues.append({
                        "type": "unknown_location",
                        "chapter_no": chapter_no,
                        "severity": "high",
                        "message": f"章节 {chapter_no} 修改了未注册地点: {loc_id}",
                    })
                    continue

                if not isinstance(state_patch, dict):
                    issues.append({
                        "type": "invalid_location_state_patch",
                        "chapter_no": chapter_no,
                        "severity": "medium",
                        "message": f"章节 {chapter_no} 的地点状态变更格式非法: {loc_id}",
                    })
                    continue

                previous = known_state.get(loc_id, {})
                if previous.get("destroyed") is True and state_patch.get("destroyed") is False:
                    issues.append({
                        "type": "location_state_regression",
                        "chapter_no": chapter_no,
                        "severity": "high",
                        "message": f"章节 {chapter_no} 将已摧毁地点 {loc_id} 回滚为未摧毁",
                    })
                merged = dict(previous)
                merged.update(state_patch)
                known_state[loc_id] = merged

            active_locations = chapter.get("locations_present", []) or []
            for loc_id in active_locations:
                if loc_id not in valid_location_ids:
                    issues.append({
                        "type": "unknown_location_presence",
                        "chapter_no": chapter_no,
                        "severity": "medium",
                        "message": f"章节 {chapter_no} 出现未注册地点: {loc_id}",
                    })
        return issues

    def _check_timeline(self, chapters: List[Dict], timeline: Dict) -> List[Dict]:
        """检查时间线一致性"""
        issues = []
        chapter_nos = [ch.get("chapter_no") for ch in chapters if ch.get("chapter_no") is not None]
        if chapter_nos and chapter_nos != sorted(chapter_nos):
            issues.append({
                "type": "chapter_order_invalid",
                "severity": "high",
                "message": "章节编号不是单调递增，时间线可能紊乱",
            })

        previous_time = None
        for idx, chapter in enumerate(chapters, start=1):
            chapter_no = chapter.get("chapter_no", idx)
            chapter_time = chapter.get("chapter_time")
            if chapter_time is None:
                continue

            if previous_time is not None and str(chapter_time) < str(previous_time):
                issues.append({
                    "type": "timeline_regression",
                    "chapter_no": chapter_no,
                    "severity": "high",
                    "message": f"章节 {chapter_no} 的时间早于上一章",
                })
            previous_time = chapter_time

        required_milestones = timeline.get("required_milestones", []) if isinstance(timeline, dict) else []
        completed = set()
        for chapter in chapters:
            for m in chapter.get("milestones_completed", []) or []:
                completed.add(m)
        for m in required_milestones:
            if m not in completed:
                issues.append({
                    "type": "missing_milestone",
                    "severity": "medium",
                    "message": f"关键里程碑未完成: {m}",
                })
        return issues

    def _check_dead_characters(self, chapters: List[Dict], characters: Dict) -> List[Dict]:
        """检查已死亡角色是否错误出现"""
        issues = []
        dead_character_ids = set()
        dead_character_names = set()
        for cid, profile in characters.items():
            if not isinstance(profile, dict):
                continue
            if str(profile.get("status", "")).lower() == "dead":
                dead_character_ids.add(cid)
                if profile.get("name"):
                    dead_character_names.add(str(profile["name"]))

        for idx, chapter in enumerate(chapters, start=1):
            chapter_no = chapter.get("chapter_no", idx)
            present = set(chapter.get("characters_present", []) or [])
            wrong_ids = present.intersection(dead_character_ids)
            for cid in wrong_ids:
                issues.append({
                    "type": "dead_character_appeared",
                    "chapter_no": chapter_no,
                    "severity": "high",
                    "message": f"章节 {chapter_no} 中已死亡角色再次出现: {cid}",
                })

            draft = chapter.get("draft", "") or ""
            for name in dead_character_names:
                if name and name in draft and chapter.get("allow_flashback", False) is not True:
                    issues.append({
                        "type": "dead_character_text_appeared",
                        "chapter_no": chapter_no,
                        "severity": "medium",
                        "message": f"章节 {chapter_no} 文本出现已死亡角色姓名: {name}",
                    })
        return issues

    def _check_supernatural_rules(self, chapters: List[Dict]) -> List[Dict]:
        """检查灵异规则一致性"""
        issues = []
        for idx, chapter in enumerate(chapters, start=1):
            chapter_no = chapter.get("chapter_no", idx)
            stage = str(chapter.get("horror_stage", "setup")).lower()
            draft = chapter.get("draft", "") or ""
            forbidden = chapter.get("forbidden_revelations", []) or []

            for token in forbidden:
                if token and token in draft:
                    issues.append({
                        "type": "forbidden_reveal_leak",
                        "chapter_no": chapter_no,
                        "severity": "high",
                        "message": f"章节 {chapter_no} 泄露了禁止揭示信息: {token}",
                    })

            if stage in {"setup", "investigation"}:
                hard_truth_keywords = chapter.get("hard_truth_keywords", ["真相是", "幕后黑手", "最终答案"])
                for kw in hard_truth_keywords:
                    if kw and kw in draft:
                        issues.append({
                            "type": "premature_truth_reveal",
                            "chapter_no": chapter_no,
                            "severity": "high",
                            "message": f"章节 {chapter_no} 在 {stage} 阶段出现过早真相揭示: {kw}",
                        })
        return issues


class ManuscriptExporter:
    """
    V5.7 ManuscriptExporter 成稿导出器
    导出完整的小说稿件
    """

    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        self.exports_dir = project_dir / "exports"
        self.exports_dir.mkdir(exist_ok=True)

    def export_manuscript(
        self,
        novel_id: str,
        title: str,
        chapters: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, str]:
        """
        导出完整稿件
        返回导出文件路径
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_base = f"{novel_id}_{timestamp}"

        # 导出 Markdown
        md_path = self.exports_dir / f"{export_base}_manuscript.md"
        self._export_markdown(md_path, title, chapters, metadata)

        # 导出章节索引
        index_path = self.exports_dir / f"{export_base}_chapter_index.json"
        self._export_chapter_index(index_path, chapters)

        # 导出完整报告
        report_path = self.exports_dir / f"{export_base}_full_report.json"
        self._export_full_report(report_path, novel_id, chapters, metadata)

        return {
            "manuscript_md": str(md_path),
            "chapter_index": str(index_path),
            "full_report": str(report_path),
        }

    def _export_markdown(
        self,
        path: Path,
        title: str,
        chapters: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """导出 Markdown 格式"""
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"# {title}\n\n")

            if metadata:
                f.write("## 元数据\n\n")
                for key, value in metadata.items():
                    f.write(f"- **{key}**: {value}\n")
                f.write("\n---\n\n")

            for chapter in chapters:
                chapter_no = chapter.get("chapter_no", 0)
                chapter_title = chapter.get("title", f"第{chapter_no}章")
                draft = chapter.get("draft", "")

                f.write(f"## 第{chapter_no}章 {chapter_title}\n\n")
                f.write(f"{draft}\n\n")

    def _export_chapter_index(
        self,
        path: Path,
        chapters: List[Dict[str, Any]],
    ) -> None:
        """导出章节索引"""
        index = {
            "chapters": [
                {
                    "chapter_no": ch.get("chapter_no"),
                    "title": ch.get("title"),
                    "word_count": ch.get("word_count"),
                    "quality_score": ch.get("quality_score"),
                }
                for ch in chapters
            ],
            "total_chapters": len(chapters),
            "total_words": sum(ch.get("word_count", 0) for ch in chapters),
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=2)

    def _export_full_report(
        self,
        path: Path,
        novel_id: str,
        chapters: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """导出完整报告"""
        report = {
            "novel_id": novel_id,
            "total_chapters": len(chapters),
            "total_words": sum(ch.get("word_count", 0) for ch in chapters),
            "average_quality_score": self._calculate_average_quality(chapters),
            "chapters": [
                {
                    "chapter_no": ch.get("chapter_no"),
                    "title": ch.get("title"),
                    "word_count": ch.get("word_count"),
                    "quality_score": ch.get("quality_score"),
                }
                for ch in chapters
            ],
            "metadata": metadata or {},
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

    def _calculate_average_quality(self, chapters: List[Dict[str, Any]]) -> float:
        """计算平均质量分"""
        scores = [ch.get("quality_score", 0) for ch in chapters if ch.get("quality_score")]
        if not scores:
            return 0.0
        return sum(scores) / len(scores)
