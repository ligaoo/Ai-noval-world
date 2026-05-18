from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List

from app.models.event import EventLog


class EventLogService:
    """事件日志本地文件存储（JSONL）。"""

    EVENTS_FILE = "events.jsonl"

    def append(self, sim_dir: Path, event: EventLog) -> None:
        path = sim_dir / self.EVENTS_FILE
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event.model_dump(mode="json"), ensure_ascii=False) + "\n")

    def read_all(self, sim_dir: Path) -> List[EventLog]:
        path = sim_dir / self.EVENTS_FILE
        if not path.exists():
            return []
        events: List[EventLog] = []
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                events.append(EventLog.model_validate(json.loads(line)))
        return events

    def read_plot_events(self, sim_dir: Path) -> List[EventLog]:
        return [e for e in self.read_all(sim_dir) if e.event_level == "plot"]

