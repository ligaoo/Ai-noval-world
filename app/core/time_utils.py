from __future__ import annotations

import re


_TIME_RE = re.compile(r"^(day\d+)_(\d{2}):(\d{2})$")


def add_minutes(world_time: str, minutes: int) -> str:
    """
    V1 简化时间：格式 dayX_HH:MM；只处理同一天内加分钟（溢出就进位到小时）。
    """
    m = _TIME_RE.match(world_time)
    if not m:
        return world_time
    day, hh, mm = m.group(1), int(m.group(2)), int(m.group(3))
    total = hh * 60 + mm + minutes
    hh2 = (total // 60) % 24
    mm2 = total % 60
    return f"{day}_{hh2:02d}:{mm2:02d}"

