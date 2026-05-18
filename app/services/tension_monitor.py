from __future__ import annotations

from collections import deque
from typing import Deque, List, Optional

from app.models.event import EventLog
from app.models.tension import PlotValue, TensionReport, TensionScores


class TensionMonitor:
    """
    V3.1：剧情张力监控器
    滚动窗口计算最近 N 个事件的剧情贡献，识别剧情停滞。
    """

    def __init__(self, window_size: int = 5):
        self.window_size = window_size
        self.recent_events: Deque[EventLog] = deque(maxlen=window_size)
        self.reports: List[TensionReport] = []

    def record_event(self, event: EventLog) -> None:
        """记录一个事件"""
        self.recent_events.append(event)

    def calculate_scores(self) -> TensionScores:
        """计算最近窗口内的张力评分"""
        if not self.recent_events:
            return TensionScores()

        # 取最近 N 个事件
        recent = list(self.recent_events)[-self.window_size:]

        # 累加各维度评分
        scores = PlotValue()
        for event in recent:
            if event.plot_value:
                scores.progress += event.plot_value.progress
                scores.mystery += event.plot_value.mystery
                scores.conflict += event.plot_value.conflict
                scores.danger += event.plot_value.danger
                scores.relationship += event.plot_value.relationship
                scores.novelty += event.plot_value.novelty
                scores.emotion += event.plot_value.emotion

        n = len(recent)
        return TensionScores(
            progress=scores.progress / n,
            mystery=scores.mystery / n,
            conflict=scores.conflict / n,
            danger=scores.danger / n,
            relationship=scores.relationship / n,
            novelty=scores.novelty / n,
            emotion=scores.emotion / n,
        )

    def diagnose(self, scores: TensionScores) -> List[str]:
        """根据评分生成诊断"""
        issues = []

        # 主线推进不足
        if scores.progress < 2.0:
            issues.append("主线推进不足，剧情有停滞风险")

        # 悬念不足
        if scores.mystery < 2.0:
            issues.append("悬念强度偏低，考虑增加未知元素")

        # 冲突不足
        if scores.conflict < 1.5:
            issues.append("冲突强度偏低，考虑增加角色互动压力")

        # 危险感不够
        if scores.danger < 1.0:
            issues.append("危险感不足，缺少紧张气氛")

        # 新鲜度下降（可能在重复）
        if scores.novelty < 1.5:
            issues.append("连续事件缺乏新信息，有重复风险")

        # 人物关系无变化
        if scores.relationship < 0.5:
            issues.append("人物关系无变化，角色互动偏弱")

        return issues

    def recommend_interventions(self, diagnosis: List[str]) -> List[str]:
        """根据诊断推荐干预类型"""
        recommendations = set()

        for issue in diagnosis:
            if "主线推进不足" in issue or "缺乏新信息" in issue:
                recommendations.add("environment_hint")
            if "悬念强度偏低" in issue or "危险感不足" in issue:
                recommendations.add("danger_signal")
            if "冲突强度偏低" in issue or "角色互动偏弱" in issue:
                recommendations.add("npc_pressure")
            if "人物关系无变化" in issue:
                recommendations.add("relationship_trigger")

        return list(recommendations)

    def generate_report(self, simulation_id: str, tick: int) -> TensionReport:
        """生成完整张力报告"""
        scores = self.calculate_scores()
        diagnosis = self.diagnose(scores)
        recommendations = self.recommend_interventions(diagnosis)

        need = len(diagnosis) >= 2 or any("主线" in d for d in diagnosis)

        report = TensionReport(
            simulation_id=simulation_id,
            tick=tick,
            window=f"last_{self.window_size}_events",
            scores=scores,
            window_event_count=len(self.recent_events),
            diagnosis=diagnosis,
            recommended_intervention_types=recommendations,
            need_intervention=need,
        )
        self.reports.append(report)
        return report

    def needs_intervention(self) -> bool:
        """是否需要干预"""
        if not self.reports:
            return False
        return self.reports[-1].need_intervention
