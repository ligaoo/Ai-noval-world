from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.llm_client import OpenAICompatibleClient
from app.models.style import (
    CharacterVoiceProfile,
    StyleBible,
    StyleCheckReport,
    StyleDriftMetrics,
    StyleViolation,
)
from app.services.trace_service import TraceService


class StyleConsistencyService:
    """
    V5.5 文风与角色声音一致性服务
    - 维护文风圣经
    - 维护角色声音档案
    - 检测文风漂移
    - 检测角色声音漂移
    - 生成风格检查报告
    """

    def __init__(
        self,
        sim_dir: Path,
        style_bible: Optional[StyleBible] = None,
        voice_profiles: Optional[Dict[str, CharacterVoiceProfile]] = None,
        llm_client: Optional[OpenAICompatibleClient] = None,
        trace_service: Optional[TraceService] = None,
    ):
        self.sim_dir = sim_dir
        self.style_bible = style_bible or StyleBible(style_id="default")
        self.voice_profiles = voice_profiles or {}
        self.llm_client = llm_client
        self.trace_service = trace_service
        self.style_reports_dir = sim_dir / "style_reports"
        self.style_reports_dir.mkdir(exist_ok=True)
        self.recent_chapter_styles: List[Dict[str, Any]] = []

    def check_style_consistency(
        self,
        draft: str,
        chapter_id: str,
        character_dialogues: Optional[Dict[str, List[str]]] = None,
    ) -> StyleCheckReport:
        """检查章节的风格一致性"""
        violations: List[StyleViolation] = []

        rule_based_violations = self._rule_based_style_check(draft)
        violations.extend(rule_based_violations)

        voice_consistency = {}
        if character_dialogues:
            for char_id, dialogues in character_dialogues.items():
                voice_score, voice_violations = self._check_voice_consistency(char_id, dialogues)
                voice_consistency[char_id] = voice_score
                violations.extend(voice_violations)

        llm_violations = []
        if self.llm_client:
            llm_violations = self._llm_style_check(draft)
            violations.extend(llm_violations)

        style_consistency_score = self._calculate_style_score(violations)

        suggestions = self._generate_style_suggestions(violations)

        report = StyleCheckReport(
            chapter_id=chapter_id,
            style_consistency_score=style_consistency_score,
            voice_consistency=voice_consistency,
            violations=violations,
            suggestions=suggestions,
        )

        self._save_style_report(report)
        self._record_chapter_style(report, chapter_id)

        return report

    def _rule_based_style_check(self, draft: str) -> List[StyleViolation]:
        """基于规则的风格检查"""
        violations: List[StyleViolation] = []

        over_explanation_patterns = [
            r"其实就是",
            r"也就是说",
            r"换句话说",
            r"这意味着",
        ]
        for pattern in over_explanation_patterns:
            if re.search(pattern, draft):
                violations.append(StyleViolation(
                    type="over_explanation",
                    message="发现过度解释的表达，可能削弱悬念感",
                    severity="low",
                    suggested_fix="将直接解释改为环境细节暗示",
                ))
                break

        exclamation_count = draft.count("!")
        if exclamation_count > 3:
            violations.append(StyleViolation(
                type="over_exclamation",
                message="感叹号使用过多，可能破坏克制的文风",
                severity="low",
                suggested_fix="减少感叹号的使用，用细节代替直接情绪表达",
            ))

        if len(draft) > 5000:
            sentences = re.split(r"[。！？]", draft)
            long_sentences = [s for s in sentences if len(s.strip()) > 100]
            if len(long_sentences) > 5:
                violations.append(StyleViolation(
                    type="too_many_long_sentences",
                    message="长句过多，可能影响阅读节奏",
                    severity="low",
                    suggested_fix="将部分长句拆分为中短句",
                ))

        forbidden_styles = ["热血", "加油", "奋斗", "无敌"]
        for word in forbidden_styles:
            if word in draft:
                violations.append(StyleViolation(
                    type="forbidden_style_word",
                    message=f"发现禁忌词汇 '{word}'，不符合文风要求",
                    severity="medium",
                    suggested_fix="替换为更符合克制文风的表达",
                ))
                break

        return violations

    def _check_voice_consistency(
        self,
        character_id: str,
        dialogues: List[str],
    ) -> tuple[float, List[StyleViolation]]:
        """检查角色声音一致性"""
        violations: List[StyleViolation] = []
        profile = self.voice_profiles.get(character_id)

        if not profile:
            return 8.0, violations

        issues = 0
        for dialogue in dialogues:
            for forbidden in profile.forbidden:
                if forbidden[:2] in dialogue:
                    violations.append(StyleViolation(
                        type="voice_drift",
                        character_id=character_id,
                        message=f"角色 {character_id} 的对白不符合其声音设定",
                        severity="medium",
                        suggested_fix=f"参考角色的典型对白风格: {profile.sample_lines[:2]}",
                    ))
                    issues += 1
                    break

        base_score = 10.0
        score = max(5.0, base_score - issues * 0.5)

        return score, violations

    def _llm_style_check(self, draft: str) -> List[StyleViolation]:
        """使用LLM进行风格检查"""
        prompt = self._build_style_check_prompt(draft)

        try:
            response = self.llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                response_format={"type": "json_object"},
            )

            result = json.loads(response.choices[0].message.content)
            violations_data = result.get("violations", [])

            return [
                StyleViolation(
                    type=v.get("type", "style_issue"),
                    message=v.get("message", ""),
                    severity=v.get("severity", "medium"),
                    location=v.get("location"),
                    suggested_fix=v.get("suggested_fix"),
                )
                for v in violations_data
            ]

        except Exception as e:
            if self.trace_service:
                self.trace_service.add_error("llm_style_check", str(e))
            return []

    def _build_style_check_prompt(self, draft: str) -> str:
        """构建风格检查提示词"""
        return f"""你是专业的文风编辑。请检查以下小说章节的风格是否符合要求。

文风要求：
{json.dumps(self.style_bible.to_dict(), ensure_ascii=False, indent=2)}

章节内容：
{draft[:3000]}

请输出严格JSON格式，包含以下字段：
- violations: 违规列表，每个违规包含type, message, severity, location, suggested_fix

严重级别可选值：high, medium, low
"""

    def _calculate_style_score(self, violations: List[StyleViolation]) -> float:
        """计算风格一致性分数"""
        base_score = 10.0

        high_count = sum(1 for v in violations if v.severity == "high")
        medium_count = sum(1 for v in violations if v.severity == "medium")
        low_count = sum(1 for v in violations if v.severity == "low")

        penalty = high_count * 1.0 + medium_count * 0.5 + low_count * 0.2
        score = max(0.0, base_score - penalty)

        return round(score, 1)

    def _generate_style_suggestions(self, violations: List[StyleViolation]) -> List[str]:
        """生成风格改进建议"""
        suggestions = []

        for violation in violations:
            if violation.suggested_fix:
                suggestions.append(violation.suggested_fix)

        return list(set(suggestions))

    def detect_style_drift(self, chapter_id: str) -> StyleDriftMetrics:
        """检测文风漂移"""
        drift_from_style_bible = 0.15
        drift_from_recent_average = 0.1

        if len(self.recent_chapter_styles) >= 3:
            recent_scores = [s.get("style_consistency_score", 8.0) for s in self.recent_chapter_styles[-3:]]
            avg_recent = sum(recent_scores) / len(recent_scores)
            current = self.recent_chapter_styles[-1].get("style_consistency_score", 8.0) if self.recent_chapter_styles else 8.0
            drift_from_recent_average = abs(current - avg_recent) / 10.0

        high_risk = drift_from_style_bible > 0.25 or drift_from_recent_average > 0.3

        return StyleDriftMetrics(
            chapter_id=chapter_id,
            drift_from_style_bible=round(drift_from_style_bible, 2),
            drift_from_recent_average=round(drift_from_recent_average, 2),
            high_risk=high_risk,
        )

    def _record_chapter_style(self, report: StyleCheckReport, chapter_id: str) -> None:
        """记录章节风格数据"""
        self.recent_chapter_styles.append({
            "chapter_id": chapter_id,
            "style_consistency_score": report.style_consistency_score,
            "voice_consistency": report.voice_consistency,
        })

        if len(self.recent_chapter_styles) > 10:
            self.recent_chapter_styles = self.recent_chapter_styles[-10:]

    def _save_style_report(self, report: StyleCheckReport) -> None:
        """保存风格报告"""
        report_file = self.style_reports_dir / f"{report.chapter_id}_style.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report.to_dict(), f, ensure_ascii=False, indent=2)

    def load_style_report(self, chapter_id: str) -> Optional[StyleCheckReport]:
        """加载风格报告"""
        report_file = self.style_reports_dir / f"{chapter_id}_style.json"
        if not report_file.exists():
            return None
        with open(report_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return StyleCheckReport(**data)

    @staticmethod
    def load_style_bible(world_dir: Path) -> StyleBible:
        """加载文风圣经"""
        bible_file = world_dir / "style_bible.json"
        if not bible_file.exists():
            return StyleBible(style_id="default")
        with open(bible_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return StyleBible(**data)

    @staticmethod
    def save_style_bible(style_bible: StyleBible, world_dir: Path) -> None:
        """保存文风圣经"""
        bible_file = world_dir / "style_bible.json"
        with open(bible_file, "w", encoding="utf-8") as f:
            json.dump(style_bible.to_dict(), f, ensure_ascii=False, indent=2)

    @staticmethod
    def load_voice_profiles(world_dir: Path) -> Dict[str, CharacterVoiceProfile]:
        """加载角色声音档案"""
        profiles_file = world_dir / "character_voice_profiles.json"
        if not profiles_file.exists():
            return {}
        with open(profiles_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {k: CharacterVoiceProfile(**v) for k, v in data.items()}

    @staticmethod
    def save_voice_profiles(profiles: Dict[str, CharacterVoiceProfile], world_dir: Path) -> None:
        """保存角色声音档案"""
        profiles_file = world_dir / "character_voice_profiles.json"
        data = {k: v.to_dict() for k, v in profiles.items()}
        with open(profiles_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
