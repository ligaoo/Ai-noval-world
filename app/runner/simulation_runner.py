from __future__ import annotations

import io
import os
import sys
import time
import json
from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from typing import Literal, Optional

# Windows 编码修复：强制使用 UTF-8
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    os.environ["PYTHONIOENCODING"] = "utf-8"

from rich.console import Console

from app.core.time_utils import add_minutes
from app.models.event import EventLog, PlotValue
from app.models.world import WorldConfig
from app.services.environment_engine import EnvironmentEngine
from app.services.event_log_service import EventLogService
from app.services.memory_service import MemoryService
from app.services.narrative_service import NarrativeService
from app.services.plot_arc_service import PlotArcService
from app.services.progress_monitor import ProgressMonitor
from app.services.run_manager_lite import RunManagerLite
from app.services.tension_monitor import TensionMonitor
from app.services.trace_service import TraceService
from app.services.world_state_service import WorldStateService


AgentMode = Literal["scripted", "heuristic", "llm"]
V2Phase = Literal["v2.4"]


@dataclass
class RunResult:
    sim_dir: Path
    simulation_id: str


class SimulationRunner:
    def __init__(self, project_root: Path, console=None):
        self.project_root = project_root
        self.state_svc = WorldStateService()
        self.event_svc = EventLogService()

    def _log(self, message: str) -> None:
        """安全的日志输出，避免 I/O 操作在后台线程报错"""
        # 只记录到 run_manager 的状态，不调用 print
        pass

    def run(
        self,
        world: WorldConfig,
        mode: AgentMode = "heuristic",
        ticks: Optional[int] = None,
        seed: int = 12345,
        temperature: float = 0.2,
        max_retries: int = 2,
        target_chapters: int = 10,
        chapter_no: int = 1,
        genre_id: str = "horror",
        v2_phase: Optional[V2Phase] = None,
        allow_incomplete_world: bool = False,
    ) -> RunResult:
        world_dir = self.project_root / "worlds" / world.world_id
        if not allow_incomplete_world:
            from app.services.world_runtime_validator import RuntimeWorldValidator
            validation = RuntimeWorldValidator().validate_for_formal_run(world, world_dir)
            if not validation.passed:
                raise ValueError(
                    "当前 world 未完成模型补全或不可正式运行：" + "；".join(validation.issues)
                )

        outputs_dir = self.project_root / "outputs"
        outputs_dir.mkdir(parents=True, exist_ok=True)
        sim_dir = self._new_simulation_dir(outputs_dir)
        simulation_id = sim_dir.name
        tick_limit = ticks if ticks is not None else world.chapter_goal.tick_limit

        if v2_phase not in (None, "v2.4"):
            raise ValueError("旧阶段 v2.1/v2.2/v2.3 已删除，SimulationRunner 仅支持 v2.4")
        v2_phase = "v2.4"
        feature_flags = self._resolve_feature_flags()

        run_manager = RunManagerLite(
            sim_dir=sim_dir,
            world=world,
            seed=seed,
            tick_limit=tick_limit,
        )
        run_manager.initialize()

        state = None
        try:
            trace_service = TraceService(sim_dir) if mode == "llm" else None
            memory_service = MemoryService(sim_dir, world) if feature_flags["enable_memory"] else None
            monitor = ProgressMonitor(no_progress_limit=world.chapter_goal.no_progress_limit)

            from app.llm_client import OpenAICompatibleClient

            llm_client = OpenAICompatibleClient.from_config(self.project_root) if mode == "llm" else None
            env = EnvironmentEngine(world=world, llm_client=llm_client)

            tension_monitor = TensionMonitor(window_size=5)
            plot_arc_service = PlotArcService(self.project_root / "worlds", world.world_id)
            from app.services.agent_sandbox_loop import AgentSandboxLoop
            sandbox_loop = AgentSandboxLoop(
                project_root=self.project_root,
                sim_dir=sim_dir,
                world=world,
                mode=mode,
                environment=env,
                event_service=self.event_svc,
                memory_service=memory_service,
                llm_client=llm_client,
                trace_service=trace_service,
                plot_arc_service=plot_arc_service,
                temperature=temperature,
            )

            state = self.state_svc.init_state(simulation_id=simulation_id, world=world, seed=seed)
            self.state_svc.save(sim_dir, state)
            run_manager.save_snapshot(state)
            run_manager.mark_running(state)

            self._log(f"Simulation {simulation_id} started. mode={mode}, ticks={tick_limit}")
            if v2_phase:
                self._log(f"V2 Phase: {v2_phase}")
            self._log(f"Genre: {genre_id}")

            env.plot_arc_service = plot_arc_service

            for t in range(1, tick_limit + 1):
                state.tick = t
                pov_id = world.chapter_goal.pov

                recent_events = self.event_svc.read_all(sim_dir)
                sandbox_result = sandbox_loop.run_tick(state, recent_events[-20:])
                for event_id in sandbox_result.event_ids:
                    matching = [e for e in self.event_svc.read_all(sim_dir) if e.event_id == event_id]
                    for ev in matching:
                        tension_monitor.record_event(ev)
                current_events = self.event_svc.read_all(sim_dir)
                hint = monitor.update_and_maybe_hint(state, current_events)
                if hint:
                    hint_event = EventLog(
                        event_id=f"evt_soft_hint_{t:04d}",
                        event_level="plot",
                        time=state.world_time,
                        event_type="soft_hint",
                        location_id=state.characters[pov_id].location_id,
                        actors=[pov_id],
                        action=None,
                        result=hint.text,
                        visible_to=[pov_id],
                        plot_value=PlotValue(mystery=1, novelty=1),
                    )
                    self.event_svc.append(sim_dir, hint_event)
                    if memory_service:
                        memory_service.write_from_event(hint_event, state)
                    tension_monitor.record_event(hint_event)
                state.world_time = add_minutes(state.world_time, 5)
                self.state_svc.save(sim_dir, state)
                run_manager.save_snapshot(state)
                run_manager.mark_running(state)
                if state.chapter_goal_status.completed:
                    break

            plot_arc_service.save_state(sim_dir) if hasattr(plot_arc_service, 'save_state') else None
            self.state_svc.save(sim_dir, state)

            if trace_service:
                trace_service.save_summary()
                summary = trace_service.get_summary()
                self._log(
                    f"LLM Stats: {summary['total_calls']} calls, "
                    f"{summary['failed_calls']} failed, "
                    f"${summary['cost_usd']:.6f} cost"
                )

            if memory_service:
                mem_summary = memory_service.get_summary()
                self._log(
                    f"Memory Stats: {mem_summary['total']} total, "
                    f"{mem_summary['event_memory']} event, "
                    f"{mem_summary['fact_memory']} fact, "
                    f"{mem_summary['belief_memory']} belief"
                )
            else:
                self._log("Memory Stats: disabled for this phase")

            narrative_llm = llm_client if mode == "llm" else None
            narrative_service = NarrativeService(
                world,
                sim_dir,
                narrative_llm,
                trace_service,
                force_rule_based=feature_flags["force_rule_narrative"],
                enable_consistency_check=feature_flags["enable_consistency_revise"],
                state=state,
            )
            result = narrative_service.generate_chapter()

            self._log(
                f"Chapter generated: {len(result['draft'])} characters, "
                f"{len(result['plan'].beats)} beats, "
                f"consistency check {'passed' if result['consistency_report']['passed'] else 'found issues'}"
            )

            final_events = self.event_svc.read_all(sim_dir)
            event_dicts = [e.model_dump() for e in final_events]
            plot_events = [e for e in event_dicts if e.get("event_level") == "plot"]

            try:
                from app.quality.story_quality_evaluator_service import StoryQualityEvaluatorService

                progress_ratio = chapter_no / max(target_chapters, 1)
                novel_progress = {
                    "chapter_no": chapter_no,
                    "target_chapters": target_chapters,
                    "current_progress_ratio": progress_ratio,
                }

                quality_evaluator = StoryQualityEvaluatorService(
                    sim_dir=sim_dir,
                    genre_id=genre_id,
                )

                plan_obj = result["plan"]
                if hasattr(plan_obj, "model_dump"):
                    chapter_plan_dict = plan_obj.model_dump()
                elif is_dataclass(plan_obj):
                    chapter_plan_dict = asdict(plan_obj)
                else:
                    chapter_plan_dict = dict(plan_obj) if isinstance(plan_obj, dict) else {}

                open_threads = self._load_open_threads(world.world_id)

                quality_report = quality_evaluator.evaluate(
                    chapter_plan=chapter_plan_dict,
                    chapter_draft=result["draft"],
                    selected_events=final_events,
                    chapter_no=chapter_no,
                    novel_progress=novel_progress,
                    open_threads=open_threads,
                    consistency_report=result.get("consistency_report"),
                    state=state,
                )

                quality_evaluator.save_report(quality_report)

                self._log(
                    f"Quality evaluated: score={quality_report.overall_score:.1f}, "
                    f"grade={quality_report.grade}, "
                    f"rewrite={'recommended' if quality_report.rewrite_recommended else 'not needed'}"
                )

                if quality_report.rewrite_recommended:
                    self._log(
                        f"[!] Rewrite priority: {quality_report.rewrite_priority}, "
                        f"issues found: {len(quality_report.problems) + len(quality_report.genre_problems)}"
                    )

                    if quality_report.problems:
                        for problem in quality_report.problems[:3]:
                            severity = problem.get("severity", "unknown")
                            message = problem.get("message", "")[:60]
                            self._log(f"   - [{severity}] {message}")

                    if quality_report.genre_problems:
                        for problem in quality_report.genre_problems[:2]:
                            severity = problem.get("severity", "unknown")
                            message = problem.get("message", "")[:60]
                            self._log(f"   - [genre][{severity}] {message}")

            except ImportError as e:
                self._log(f"Quality evaluation skipped: {e}")
            except Exception as e:
                self._log(f"[!] Quality evaluation failed: {e}")

            self._write_v2_report(sim_dir, v2_phase, feature_flags, mode, tick_limit, state.tick, state)

            run_manager.complete(state)
            self._log(f"Simulation {simulation_id} finished at tick={state.tick}.")
            return RunResult(sim_dir=sim_dir, simulation_id=simulation_id)

        except Exception as e:
            run_manager.fail(e, state)
            raise

    def _load_open_threads(self, world_id: str) -> list[dict]:
        thread_file = self.project_root / "worlds" / world_id / "open_threads.json"
        if not thread_file.exists():
            return []
        try:
            with open(thread_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except Exception:
            return []

    @staticmethod
    def _new_simulation_dir(outputs_dir: Path) -> Path:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        random_suffix = Path(__file__).stem[:4]
        sim_dir = outputs_dir / f"sim_{timestamp}_{random_suffix}"
        sim_dir.mkdir(parents=True, exist_ok=True)
        return sim_dir

    @staticmethod
    def _resolve_feature_flags() -> dict:
        return {
            "allow_move": True,
            "enable_memory": True,
            "force_rule_narrative": False,
            "enable_consistency_revise": True,
            "enable_agent_sandbox": True,
            "enable_fact_exposure_matrix": True,
            "enable_multi_round_interaction": True,
        }

    @staticmethod
    def _write_v2_report(
        sim_dir: Path,
        v2_phase: V2Phase,
        feature_flags: dict,
        mode: AgentMode,
        tick_limit: int,
        finished_tick: int,
        state=None,
    ) -> None:
        metrics = SimulationRunner._v2_sandbox_metrics(sim_dir, state)
        report = {
            "phase": "v2.4",
            "mode": mode,
            "tick_limit": tick_limit,
            "finished_tick": finished_tick,
            "feature_flags": feature_flags,
            "sandbox_metrics": metrics,
            "artifacts": {
                "events": "events.jsonl",
                "state": "state.json",
                "chapter_plan": "chapter_plan.json",
                "chapter_draft": "chapter_draft.md",
                "chapter_debug": "chapter_debug.json",
                "consistency_report": "consistency_report.json",
            },
        }
        with open(sim_dir / "v2_phase_report.json", "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

    @staticmethod
    def _v2_sandbox_metrics(sim_dir: Path, state) -> dict:
        fact_entries = list(getattr(getattr(state, "world", None), "fact_exposure", {}).values()) if state else []
        interaction_count = 0
        scene_conflict_count = 0
        agent_reaction_count = 0
        group_decision_count = 0
        private_tendency_trigger_count = 0
        relationship_update_count = 0
        interaction_event_count = 0
        events_file = sim_dir / "events.jsonl"
        if events_file.exists():
            try:
                with open(events_file, "r", encoding="utf-8") as f:
                    for line in f:
                        if not line.strip():
                            continue
                        event = json.loads(line)
                        if event.get("interaction_id"):
                            interaction_count += 1
                        source = event.get("source_interaction") or {}
                        metrics = source.get("agent_debug_metrics") or {}
                        agent_reaction_count += int(metrics.get("agent_reaction_count", 0))
                        group_decision_count += int(metrics.get("group_decision_count", 0))
                        private_tendency_trigger_count += int(metrics.get("private_tendency_trigger_count", 0))
                        relationship_update_count += int(metrics.get("relationship_update_count", 0))
                        interaction_event_count += int(metrics.get("interaction_event_count", 0))
                        primary_conflict = source.get("primary_conflict") or {}
                        if primary_conflict:
                            scene_conflict_count += 1
            except Exception:
                pass
        return {
            "fact_count": len(fact_entries),
            "known_edges": sum(len(entry.known_by) for entry in fact_entries),
            "suspected_edges": sum(len(entry.suspected_by) for entry in fact_entries),
            "misunderstood_edges": sum(len(entry.misunderstood_by) for entry in fact_entries),
            "interaction_count": interaction_count,
            "scene_conflict_count": scene_conflict_count,
            "agent_reaction_count": agent_reaction_count,
            "group_decision_count": group_decision_count,
            "private_tendency_trigger_count": private_tendency_trigger_count,
            "relationship_update_count": relationship_update_count,
            "interaction_event_count": interaction_event_count,
        }
