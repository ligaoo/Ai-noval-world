from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.llm_client import OpenAICompatibleClient
from app.models.event import EventLog
from app.models.narrative import ChapterPlan
from app.services.trace_service import LLMTrace, TraceService


@dataclass
class Violation:
    type: str  # new_entity / leaked_info / speculation_as_fact / pov_violation
    severity: str  # high / medium / low
    text: str
    reason: str
    suggested_fix: str


class ConsistencyService:
    """
    V2.3 一致性检查服务
    两层检查：规则检查（RuleCheck）+ LLM 语义检查（LLMCheck）
    支持自动修订一次
    """

    def __init__(
        self,
        world: Any,  # 世界配置（WorldConfig），用 Any 避免循环导入
        sim_dir: Path,
        llm_client: Optional[OpenAICompatibleClient] = None,
        trace_service: Optional[TraceService] = None,
    ):
        self.world = world
        self.sim_dir = sim_dir
        self.llm_client = llm_client
        self.trace_service = trace_service

    def check_consistency(
        self,
        draft: str,
        plan: ChapterPlan,
        plot_events: List[EventLog],
    ) -> Dict[str, Any]:
        """一致性检查：规则 + LLM"""
        # 1. RuleCheck
        rule_violations = self._rule_check(draft, plot_events)

        # 2. LLMCheck（如果有 llm_client）
        llm_violations = []
        if self.llm_client:
            llm_violations = self._llm_check(draft, plan, plot_events)

        violations = rule_violations + llm_violations
        passed = len([v for v in violations if v.severity in ["high", "medium"]]) == 0

        report = {
            "passed": passed,
            "mode": "rule_only" if not self.llm_client else "rule + llm",
            "violations": [
                {
                    "type": v.type,
                    "severity": v.severity,
                    "text": v.text,
                    "reason": v.reason,
                    "suggested_fix": v.suggested_fix,
                }
                for v in violations
            ],
            "summary": {
                "total": len(violations),
                "high": len([v for v in violations if v.severity == "high"]),
                "medium": len([v for v in violations if v.severity == "medium"]),
                "low": len([v for v in violations if v.severity == "low"]),
            },
        }

        with open(self.sim_dir / "consistency_report.json", "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        return report

    # ==========================================
    # RuleCheck：程序检查
    # ==========================================

    def _rule_check(self, draft: str, plot_events: List[EventLog]) -> List[Violation]:
        violations: List[Violation] = []

        # 从世界配置中提取合法实体
        valid_locations = set()
        valid_objects = set()
        valid_characters = set()
        visited_location_ids = {e.location_id for e in plot_events if e.location_id}
        visited_location_names = set()
        discovered_fact_ids = set()

        for loc in self.world.map.locations:
            valid_locations.add(loc.id.lower())
            valid_locations.add(loc.name.lower())
            if loc.id in visited_location_ids:
                visited_location_names.add(loc.name)
            for obj in loc.objects:
                valid_objects.add(obj.id.lower())
                valid_objects.add(obj.name.lower())

        for char in self.world.characters.characters:
            valid_characters.add(char.id.lower())
            valid_characters.add(char.name.lower())

        for event in plot_events:
            discovered_fact_ids.update(getattr(event, "discovered_facts", []) or [])
            if event.action:
                # 旧 EventLog 没有 discovered_facts 字段，退回从结果与状态里做弱检查。
                pass

        # 1. 未访问地点出现在正文中：视为中等风险。
        for loc in self.world.map.locations:
            if loc.name and loc.name in draft and loc.id not in visited_location_ids:
                violations.append(
                    Violation(
                        type="unvisited_location",
                        severity="medium",
                        text=loc.name,
                        reason="正文出现了本章事件中未访问的地点。",
                        suggested_fix="删除该地点描写，或改为角色对该地点的猜测。",
                    )
                )

        # 2. 未发现 clue content 直接出现在正文中：高风险剧透。
        discovered_by_content = set()
        for event in plot_events:
            for clue in self.world.clues.clues:
                if clue.content and clue.content in event.result:
                    discovered_by_content.add(clue.id)

        allowed_clue_ids = discovered_fact_ids | discovered_by_content
        for clue in self.world.clues.clues:
            if clue.id in allowed_clue_ids:
                continue
            content = clue.content.strip()
            if len(content) >= 6 and content in draft:
                violations.append(
                    Violation(
                        type="leaked_info",
                        severity="high",
                        text=content,
                        reason=f"正文出现了未在本章事件中发现的线索内容：{clue.id}。",
                        suggested_fix="删除该线索内容，或改写成模糊感受，不要确认事实。",
                    )
                )

        # 3. 简单新实体风险：中文引号/书名号中的实体如果不在白名单且像地点或人物，给低风险提示。
        known_terms = valid_locations | valid_objects | valid_characters
        candidates = set(re.findall(r"[《“\"]([^《》“”\"]{2,20})[》”\"]", draft))
        for term in sorted(candidates):
            low = term.lower()
            if low in known_terms:
                continue
            if self._looks_like_new_entity(term):
                violations.append(
                    Violation(
                        type="new_entity",
                        severity="low",
                        text=term,
                        reason="正文中出现疑似新增地点/人物/物品，未在世界配置白名单中确认。",
                        suggested_fix="确认该实体来自世界配置或事件日志，否则删除或替换为已知实体。",
                    )
                )

        return violations

    @staticmethod
    def _looks_like_new_entity(term: str) -> bool:
        text = str(term or "").strip()
        if not text or text in {"人？", "什么人？", "没看到人。", "没看到人", "外面是不是有人？"}:
            return False
        if text.endswith(("室", "楼", "馆", "院", "房间", "办公室", "档案室")):
            return True
        if any(suffix in text for suffix in ["维修部", "医院", "车站", "路口"]):
            return True
        if any(role in text for role in ["医生", "警察"]):
            return len(text) >= 4
        return False

    # ==========================================
    # LLMCheck：语义检查
    # ==========================================

    def _llm_check(
        self,
        draft: str,
        plan: ChapterPlan,
        plot_events: List[EventLog],
    ) -> List[Violation]:
        """LLM 语义检查"""
        if not self.llm_client:
            return []

        # 构建 prompt
        system = self._build_check_system_prompt()
        user = self._build_check_user_prompt(draft, plan, plot_events)

        resp = self.llm_client.chat_json(system=system, user=user, temperature=0.0)

        # 记录 trace
        if self.trace_service:
            trace = LLMTrace(
                trace_id=resp.trace_id,
                simulation_id=self.world.world_id,
                tick=0,
                agent_id="consistency_check",
                purpose="consistency_check",
                model=self.llm_client.model,
                input_tokens=resp.cost.input_tokens,
                output_tokens=resp.cost.output_tokens,
                total_tokens=resp.cost.total_tokens,
                cost_usd=resp.cost.cost_usd,
                success=True,
                retry_count=0,
                from_cache=resp.from_cache,
                error="",
            )
            self.trace_service.record(trace)

        # 解析结果
        if not resp.parsed_json:
            return []

        violations = []
        try:
            for v in resp.parsed_json.get("violations", []):
                violations.append(Violation(
                    type=v.get("type", "unknown"),
                    severity=v.get("severity", "low"),
                    text=v.get("text", ""),
                    reason=v.get("reason", ""),
                    suggested_fix=v.get("suggested_fix", ""),
                ))
        except Exception:
            pass

        return violations

    @staticmethod
    def _build_check_system_prompt() -> str:
        return (
            "你是一位小说一致性审查员。你的任务是：检查小说草稿是否有不符合规则的问题。\n"
            "\n"
            "请严格按照以下规则审查：\n"
            "1. speculation_as_fact：将猜测写成事实的地方\n"
            "2. leaked_info：泄露了 POV 角色不知道的信息\n"
            "3. pov_violation：出现了 POV 角色不可能知道的其他角色内心活动\n"
            "4. new_entity：出现了世界设定中没有的新地点/物品/角色\n"
            "\n"
            "输出 JSON 格式：\n"
            "violations: [\n"
            "  {type: str, severity: high|medium|low, text: 违规内容, reason: 原因, suggested_fix: 修改建议}\n"
            "]\n"
            "如果没有违规，violations 为空数组。\n"
        )

    @staticmethod
    def _build_check_user_prompt(
        draft: str,
        plan: ChapterPlan,
        plot_events: List[EventLog],
    ) -> str:
        lines: List[str] = []
        lines.append("【POV 角色】" + plan.pov)
        lines.append("【章节目标】" + plan.chapter_goal)
        lines.append("")
        lines.append("【已发生的事件（仅这些是事实）】")
        for e in plot_events[:20]:  # 限制数量
            lines.append(f"- {e.result}")
        lines.append("")
        lines.append("【小说草稿】")
        lines.append(draft[:3000])  # 限制长度
        lines.append("")
        lines.append("请检查以上草稿，找出所有违规：")
        return "\n".join(lines)

    # ==========================================
    # Revise Once：自动修订一次
    # ==========================================

    def revise_once(
        self,
        draft: str,
        plan: ChapterPlan,
        plot_events: List[EventLog],
    ) -> str:
        """自动修订一次"""
        if not self.llm_client:
            return draft  # 无 LLM 时不修改

        # 读取之前的报告
        report_file = self.sim_dir / "consistency_report.json"
        if not report_file.exists():
            return draft

        with open(report_file, "r", encoding="utf-8") as f:
            report = json.load(f)

        if not report.get("violations"):
            return draft

        # 构建修订 prompt
        system = self._build_revise_system_prompt()
        user = self._build_revise_user_prompt(draft, plan, plot_events, report)

        # 调用 LLM
        resp = self.llm_client.chat(system=system, user=user, temperature=0.2)

        # 记录 trace
        if self.trace_service:
            trace = LLMTrace(
                trace_id=resp.trace_id,
                simulation_id=self.world.world_id,
                tick=0,
                agent_id="consistency_revise",
                purpose="revise_once",
                model=self.llm_client.model,
                input_tokens=resp.cost.input_tokens,
                output_tokens=resp.cost.output_tokens,
                total_tokens=resp.cost.total_tokens,
                cost_usd=resp.cost.cost_usd,
                success=True,
                retry_count=0,
                from_cache=resp.from_cache,
                error="",
            )
            self.trace_service.record(trace)

        return resp.text

    @staticmethod
    def _build_revise_system_prompt() -> str:
        return (
            "你是小说修订编辑。你的任务是根据一致性报告，修改小说草稿中的违规。\n"
            "\n"
            "【核心规则】\n"
            "1. 只修改违规的部分，不要改其他内容\n"
            "2. 不能添加新的地点、物品、角色\n"
            "3. 将写成事实的猜测改成怀疑/似乎/好像等推测语气\n"
            "4. 删掉泄露的信息，改成 POV 角色的怀疑或不知道\n"
            "5. 保持原文的风格、氛围和叙事节奏\n"
        )

    @staticmethod
    def _build_revise_user_prompt(
        draft: str,
        plan: ChapterPlan,
        plot_events: List[EventLog],
        report: Dict,
    ) -> str:
        lines: List[str] = []
        lines.append("【POV 角色】" + plan.pov)
        lines.append("")
        lines.append("【已发现的违规】")
        for i, v in enumerate(report.get("violations", [])[:5]):  # 最多前5个
            lines.append(f"{i + 1}. [{v['type']}] {v['text']}")
            lines.append(f"   原因：{v['reason']}")
            lines.append(f"   建议：{v['suggested_fix']}")
        lines.append("")
        lines.append("【小说草稿】")
        lines.append(draft)
        lines.append("")
        lines.append("请根据以上违规，输出修订后的完整正文：")
        return "\n".join(lines)
