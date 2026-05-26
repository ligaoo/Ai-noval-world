from __future__ import annotations

import re
from typing import Iterable, List


class SandboxGuardrailService:
    BACKEND_TERMS = {
        "系统",
        "后台",
        "Agent",
        "agent",
        "sandbox",
        "沙盘",
        "fact_exposure",
        "Director",
        "director",
        "tick",
        "state",
        "prompt",
        "LLM",
        "矩阵",
        "剧情弧",
    }
    TRUTH_SUMMARY_PATTERNS = (
        re.compile(r"真相是"),
        re.compile(r"其实一切都是"),
        re.compile(r"幕后原因是"),
        re.compile(r"the truth is", re.IGNORECASE),
        re.compile(r"what really happened", re.IGNORECASE),
    )
    FALLBACKS = (
        "gives a guarded response",
        "hesitates under pressure",
        "offers an inconsistent explanation",
    )

    def sanitize_lines(self, lines: Iterable[str], pressure_level: int = 0) -> List[str]:
        sanitized: List[str] = []
        for line in lines:
            clean = self.sanitize_line(line, pressure_level)
            if clean:
                sanitized.append(clean)
        return sanitized

    def sanitize_line(self, line: str, pressure_level: int = 0) -> str:
        text = (line or "").strip()
        if not text:
            return ""
        if self.is_unsafe(text):
            return self._fallback(pressure_level)
        return text

    def is_unsafe(self, text: str) -> bool:
        return any(term in text for term in self.BACKEND_TERMS) or any(
            pattern.search(text) for pattern in self.TRUTH_SUMMARY_PATTERNS
        )

    def _fallback(self, pressure_level: int) -> str:
        if pressure_level >= 3:
            return self.FALLBACKS[1]
        if pressure_level >= 2:
            return self.FALLBACKS[2]
        return self.FALLBACKS[0]
