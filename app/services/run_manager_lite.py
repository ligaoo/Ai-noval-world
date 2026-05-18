from __future__ import annotations

import json
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from app.models.state import WorldState
from app.models.world import WorldConfig


class RunManagerLite:
    """
    V3.6 Patch：最小运行管理与可观测性产物。
    负责 run_manifest / run_status / run_index / snapshots / metrics / tuning_report / errors。
    """

    ENGINE_VERSION = "v3.6-patch"

    def __init__(self, sim_dir: Path, world: WorldConfig, seed: int, tick_limit: int):
        self.sim_dir = sim_dir
        self.world = world
        self.seed = seed
        self.tick_limit = tick_limit
        self.started_at = self._now()
        self.last_error: Optional[str] = None
        self.snapshot_dir = sim_dir / "state_snapshots"
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)

    def initialize(self) -> None:
        (self.sim_dir / "errors.jsonl").touch(exist_ok=True)
        self.write_manifest(finished_at=None)
        self.update_status(status="created", current_tick=0, current_chapter=1)
        self.write_index()

    def mark_running(self, state: WorldState) -> None:
        self.update_status(
            status="running",
            current_tick=state.tick,
            current_chapter=1,
            last_event_id=self._last_event_id(),
        )

    def save_snapshot(self, state: WorldState) -> None:
        path = self.snapshot_dir / f"tick_{state.tick:04d}.json"
        self._write_json(path, state.model_dump(mode="json"))

    def complete(self, state: WorldState, extra_metrics: Optional[Dict[str, Any]] = None) -> None:
        self.write_manifest(finished_at=self._now())
        self.update_status(
            status="completed",
            current_tick=state.tick,
            current_chapter=1,
            last_event_id=self._last_event_id(),
            progress={
                "ticks_done": state.tick,
                "tick_limit": self.tick_limit,
                "chapters_done": 1,
                "chapter_limit": 1,
            },
        )
        metrics = self.collect_metrics(state, extra_metrics or {})
        self._write_json(self.sim_dir / "metrics.json", metrics)
        self.write_tuning_report(metrics)
        self.write_index()

    def fail(self, error: BaseException, state: Optional[WorldState] = None) -> None:
        self.last_error = f"{type(error).__name__}: {error}"
        self.append_error(error, state)
        self.update_status(
            status="failed",
            current_tick=state.tick if state else 0,
            current_chapter=1,
            last_error=self.last_error,
            last_event_id=self._last_event_id(),
        )
        self.write_manifest(finished_at=self._now())
        self.write_index()

    def write_manifest(self, finished_at: Optional[str]) -> None:
        manifest = {
            "simulation_id": self.sim_dir.name,
            "world_id": self.world.world_id,
            "engine_version": self.ENGINE_VERSION,
            "started_at": self.started_at,
            "finished_at": finished_at,
            "seed": self.seed,
            "parent_simulation_id": None,
            "features": {
                "progress_monitor_enabled": True,
                "director_enabled": True,
                "plot_arc_enabled": True,
                "chapter_continuity_enabled": True,
                "character_arc_lite_enabled": True,
                "debug_snapshots_enabled": True,
            },
            "input_files": {
                "world_bible": f"worlds/{self.world.world_id}/world_bible.json",
                "map": f"worlds/{self.world.world_id}/map.json",
                "characters": f"worlds/{self.world.world_id}/characters.json",
                "clues": f"worlds/{self.world.world_id}/clues.json",
                "chapter_goal": f"worlds/{self.world.world_id}/chapter_goal.json",
                "plot_arcs": f"worlds/{self.world.world_id}/plot_arcs.json",
                "character_arcs": f"worlds/{self.world.world_id}/character_arcs.json",
            },
        }
        self._write_json(self.sim_dir / "run_manifest.json", manifest)

    def update_status(
        self,
        status: str,
        current_tick: int,
        current_chapter: int,
        last_event_id: Optional[str] = None,
        last_error: Optional[str] = None,
        progress: Optional[Dict[str, int]] = None,
    ) -> None:
        status_data = {
            "simulation_id": self.sim_dir.name,
            "status": status,
            "current_tick": current_tick,
            "current_chapter": current_chapter,
            "last_event_id": last_event_id,
            "last_error": last_error,
            "progress": progress
            or {
                "ticks_done": current_tick,
                "tick_limit": self.tick_limit,
                "chapters_done": 0,
                "chapter_limit": 1,
            },
        }
        self._write_json(self.sim_dir / "run_status.json", status_data)

    def write_index(self) -> None:
        artifacts = {}
        for name in [
            "run_manifest.json",
            "run_status.json",
            "state.json",
            "events.jsonl",
            "memories.jsonl",
            "plot_arc_state.json",
            "character_arcs_state.json",
            "chapter_plan.json",
            "chapter_draft.md",
            "consistency_report.json",
            "metrics.json",
            "tuning_report.md",
            "errors.jsonl",
            "llm_traces.jsonl",
            "llm_summary.json",
        ]:
            if (self.sim_dir / name).exists():
                artifacts[name] = name

        index = {
            "simulation_id": self.sim_dir.name,
            "engine_version": self.ENGINE_VERSION,
            "artifacts": artifacts,
            "directories": {
                "state_snapshots": "state_snapshots"
                if self.snapshot_dir.exists()
                else None,
            },
        }
        self._write_json(self.sim_dir / "run_index.json", index)

    def collect_metrics(self, state: WorldState, extra: Dict[str, Any]) -> Dict[str, Any]:
        events = self._read_jsonl(self.sim_dir / "events.jsonl")
        memories = self._read_jsonl(self.sim_dir / "memories.jsonl")
        interventions = self._read_jsonl(self.sim_dir / "intervention_history.jsonl")
        plot_events = [e for e in events if e.get("event_level") == "plot"]
        invalid_actions = [e for e in events if e.get("event_type") == "invalid_action"]
        discovered = [
            clue_id
            for clue_id, ok in state.world.discovered_facts.items()
            if ok
        ]
        repeat_action_count = sum(
            max(0, c.repeat_action_count) for c in state.characters.values()
        )

        llm_summary = self._read_json(self.sim_dir / "llm_summary.json") or {}

        return {
            "simulation_id": self.sim_dir.name,
            "runtime": {
                "total_ticks": state.tick,
                "tick_limit": self.tick_limit,
                "total_events": len(events),
                "plot_events": len(plot_events),
                "chapters": 1 if (self.sim_dir / "chapter_draft.md").exists() else 0,
                "failed_actions": len(invalid_actions),
                "fallback_actions": extra.get("fallback_actions", 0),
            },
            "agent": {
                "repeat_action_count": repeat_action_count,
                "invalid_action_rate": round(len(invalid_actions) / max(1, len(events)), 4),
            },
            "plot": {
                "chapter_goal_progress": state.chapter_goal_status.progress,
                "chapter_goal_completed": state.chapter_goal_status.completed,
            },
            "director": {
                "intervention_count": len(interventions),
            },
            "clues": {
                "total_clues": len(state.world.discovered_facts),
                "discovered_clues": len(discovered),
                "discovered_clue_ids": discovered,
            },
            "memory": {
                "total_memories": len(memories),
            },
            "llm": llm_summary,
        }

    def write_tuning_report(self, metrics: Dict[str, Any]) -> None:
        runtime = metrics["runtime"]
        clues = metrics["clues"]
        agent = metrics["agent"]
        director = metrics["director"]
        plot = metrics["plot"]

        issues = []
        suggestions = []
        if clues["discovered_clues"] == 0:
            issues.append("本次运行没有发现任何线索。")
            suggestions.append("检查 clues.json 的 discover_routes，或降低关键 route difficulty。")
        if agent["invalid_action_rate"] > 0.1:
            issues.append(f"非法动作率偏高：{agent['invalid_action_rate']:.2%}。")
            suggestions.append("增强 Agent prompt 中 available_targets/topics 约束，或降低 LLM temperature。")
        if director["intervention_count"] >= 5:
            issues.append("导演干预次数达到上限。")
            suggestions.append("检查 Agent 是否重复动作，或增加更多可触发的低难度线索入口。")
        if not plot["chapter_goal_completed"]:
            issues.append("章节目标未完成。")
            suggestions.append("调整 chapter_goal.target_progress，或提高关键线索 plot_value.progress。")

        if not issues:
            issues.append("未发现明显阻塞问题。")
            suggestions.append("可以继续观察多次运行的线索发现率和章节目标完成率。")

        lines = [
            "# Tuning Report",
            "",
            "## Summary",
            "",
            (
                f"本次运行 {runtime['total_ticks']}/{runtime['tick_limit']} ticks，"
                f"记录 {runtime['total_events']} 个事件，"
                f"发现 {clues['discovered_clues']}/{clues['total_clues']} 个线索。"
            ),
            "",
            "## Issues",
            "",
        ]
        lines.extend(f"{i + 1}. {issue}" for i, issue in enumerate(issues))
        lines.extend(["", "## Suggestions", ""])
        lines.extend(f"{i + 1}. {s}" for i, s in enumerate(suggestions))
        lines.append("")
        (self.sim_dir / "tuning_report.md").write_text("\n".join(lines), encoding="utf-8")

    def append_error(self, error: BaseException, state: Optional[WorldState] = None) -> None:
        payload = {
            "timestamp": self._now(),
            "simulation_id": self.sim_dir.name,
            "tick": state.tick if state else None,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "stack_trace": traceback.format_exc(),
        }
        with (self.sim_dir / "errors.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def _last_event_id(self) -> Optional[str]:
        events = self._read_jsonl(self.sim_dir / "events.jsonl")
        if not events:
            return None
        return events[-1].get("event_id")

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

    @staticmethod
    def _write_json(path: Path, data: Dict[str, Any]) -> None:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _read_json(path: Path) -> Optional[Dict[str, Any]]:
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _read_jsonl(path: Path) -> list[Dict[str, Any]]:
        if not path.exists():
            return []
        rows = []
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
        return rows
