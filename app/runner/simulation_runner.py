from __future__ import annotations

import os
import sys
import time
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional

# Windows 编码修复：强制使用 UTF-8，避免替换 stdout/stderr 导致 logging 持有已关闭 stream
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    os.environ["PYTHONIOENCODING"] = "utf-8"

from rich.console import Console

from app.core.time_utils import add_minutes
from app.models.event import EventLog, PlotValue
from app.models.quality_controls import QualityControls
from app.models.world import WorldConfig
from app.services.chapter_brief_service import ChapterBriefService
from app.services.character_agent_service import CharacterAgentService
from app.services.director_service import DirectorService
from app.services.environment_engine import EnvironmentEngine
from app.services.event_log_service import EventLogService
from app.services.event_selection_service import EventSelectionService
from app.services.intervention_service import InterventionService
from app.services.memory_service import MemoryService
from app.services.narrative_service import NarrativeService
from app.services.plot_arc_service import PlotArcService
from app.services.progress_monitor import ProgressMonitor
from app.services.reveal_budget_service import RevealBudgetService
from app.services.run_manager_lite import RunManagerLite
from app.services.scene_plan_service import ScenePlanService
from app.services.tension_monitor import TensionMonitor
from app.services.trace_service import TraceService
from app.services.world_state_service import WorldStateService


AgentMode = Literal["scripted", "heuristic", "llm"]
RuntimeVersion = Literal["正式版V1"]


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
        version: Optional[RuntimeVersion] = None,
        quality_controls: Optional[QualityControls] = None,
    ) -> RunResult:
        outputs_dir = self.project_root / "outputs"
        outputs_dir.mkdir(parents=True, exist_ok=True)
        sim_dir = self._new_simulation_dir(outputs_dir)
        simulation_id = sim_dir.name
        tick_limit = ticks if ticks is not None else world.chapter_goal.tick_limit

        feature_flags = self._resolve_feature_flags(version)

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

            llm_client = OpenAICompatibleClient.from_config(self.project_root, max_retries=max_retries) if mode == "llm" else None
            quality_controls = quality_controls or QualityControls()
            with open(sim_dir / "quality_controls.json", "w", encoding="utf-8") as f:
                json.dump(quality_controls.model_dump(), f, ensure_ascii=False, indent=2)
            reveal_budget_service = RevealBudgetService(world)
            reveal_budget = reveal_budget_service.build(chapter_no=chapter_no, target_chapters=target_chapters)
            reveal_budget_service.save(sim_dir, reveal_budget)
            chapter_brief_service = ChapterBriefService(world)
            chapter_brief = chapter_brief_service.build(
                chapter_no=chapter_no,
                target_chapters=target_chapters,
                reveal_budget=reveal_budget,
                quality_controls=quality_controls,
            )
            chapter_brief_service.save(sim_dir, chapter_brief)
            agent_svc = CharacterAgentService(
                world=world,
                mode=mode,
                memory_service=memory_service,
                llm_client=llm_client,
                trace_service=trace_service,
                temperature=temperature,
                max_retries=max_retries,
                chapter_brief=chapter_brief,
            )
            env = EnvironmentEngine(world=world, llm_client=llm_client)

            tension_monitor = TensionMonitor(window_size=5)
            director_service = DirectorService(self.project_root / "worlds" / world.world_id)
            intervention_service = InterventionService(sim_dir)
            plot_arc_service = PlotArcService(self.project_root / "worlds", world.world_id)
            chapter_continuity_service = None

            try:
                from app.services.chapter_continuity_service import ChapterContinuityService
                chapter_continuity_service = ChapterContinuityService(sim_dir)
            except ImportError:
                pass

            state = self.state_svc.init_state(simulation_id=simulation_id, world=world, seed=seed)
            self.state_svc.save(sim_dir, state)
            run_manager.save_snapshot(state)
            run_manager.mark_running(state)

            self._log(f"Simulation {simulation_id} started. mode={mode}, ticks={tick_limit}")
            if version:
                self._log(f"运行版本: {version}")
            self._log(f"Genre: {genre_id}")

            env.plot_arc_service = plot_arc_service

            for t in range(1, tick_limit + 1):
                state.tick = t
                pov_id = world.chapter_goal.pov
                character_order = [pov_id] + [cid for cid in world.characters.ids() if cid != pov_id]

                for cid in character_order:
                    last_events = self.event_svc.read_all(sim_dir)
                    last_events_text = [f"{e.time} {e.event_type}: {e.result}" for e in last_events[-8:]]
                    ctx = agent_svc.build_context(state, cid, last_events_text=last_events_text)

                    plot_ctx = plot_arc_service.to_context_dict() if plot_arc_service else {}
                    ctx.plot_arc_stage = plot_ctx.get("arc_stage", "")
                    ctx.plot_arc_purpose = plot_ctx.get("chapter_goal", "")
                    ctx.forbidden_revelations = plot_ctx.get("forbidden_revelations", [])

                    if chapter_continuity_service:
                        ctx.previous_chapter_summary = ""
                        ctx.open_threads = []
                        ctx.next_chapter_seeds = []

                    action = agent_svc.decide_next_action(state, ctx)
                    if not feature_flags["allow_move"] and action.action_type == "move":
                        action.action_type = "wait"
                        action.target = ""
                        action.topic = None
                        action.intent = "当前阶段禁用 move，先观察现场"
                        action.expected_gain = "避免跨地点移动导致阶段偏差"
                    applied = env.apply_action(state, action)
                    for ev in applied.new_events:
                        self.event_svc.append(sim_dir, ev)
                        if memory_service:
                            memory_service.write_from_event(ev, state)
                        tension_monitor.record_event(ev)

                tension_report = tension_monitor.generate_report(simulation_id, t)
                if tension_report.need_intervention:
                    self._log(f"[!] Tick {t}: 剧情张力异常")
                    for issue in tension_report.diagnosis[:2]:
                        self._log(f"   - {issue}")

                    proposal = director_service.propose_intervention(
                        state=state,
                        tension_report=tension_report,
                        chapter_goal=world.chapter_goal.goal,
                    )
                    if proposal:
                        self._log(f"[Director] 干预: {proposal.intervention_type}")
                        self._log(f"   → {proposal.content}")
                        director_service.last_intervention_tick = t
                        intervention_event = intervention_service.apply_intervention(proposal, state, pov_id)
                        if intervention_event:
                            ev = intervention_service.to_event_log(intervention_event)
                            ev.time = state.world_time
                            self.event_svc.append(sim_dir, ev)
                            if memory_service:
                                memory_service.write_from_event(ev, state)
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

            director_service.save_history(sim_dir)
            intervention_service.save_history()
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

            events_for_planning = self.event_svc.read_all(sim_dir)
            event_selection_service = EventSelectionService(world)
            selected_events_report = event_selection_service.select(events_for_planning, chapter_brief)
            event_selection_service.save(sim_dir, selected_events_report)
            scene_plan_service = ScenePlanService(world)
            scene_plan = scene_plan_service.build(
                selected_events_report,
                chapter_brief,
                events_for_planning,
                reveal_budget=reveal_budget,
                quality_controls=quality_controls,
            )
            scene_plan_service.save(sim_dir, scene_plan)

            narrative_llm = agent_svc._llm if mode == "llm" else None
            narrative_service = NarrativeService(
                world,
                sim_dir,
                narrative_llm,
                trace_service,
                force_rule_based=feature_flags["force_rule_narrative"],
                enable_consistency_check=feature_flags["enable_consistency_revise"],
                chapter_brief=chapter_brief,
                scene_plan=scene_plan,
                reveal_budget=reveal_budget,
                quality_controls=quality_controls,
            )
            result = narrative_service.generate_chapter()
            self._write_chapter_continuity(sim_dir, chapter_no, reveal_budget, chapter_brief)

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

                quality_report = quality_evaluator.evaluate(
                    chapter_plan=result["plan"].model_dump() if hasattr(result["plan"], 'model_dump') else {},
                    chapter_draft=result["draft"],
                    selected_events=final_events,
                    chapter_no=chapter_no,
                    novel_progress=novel_progress,
                    open_threads=[],
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

            if version:
                self._write_version_report(sim_dir, version, feature_flags, mode, tick_limit, state.tick)

            run_manager.complete(
                state,
                extra_metrics={
                    "fallback_actions": getattr(agent_svc, "fallback_actions", 0),
                    "agent_decision_failures": getattr(agent_svc, "agent_decision_failures", 0),
                },
            )
            self._log(f"Simulation {simulation_id} finished at tick={state.tick}.")
            return RunResult(sim_dir=sim_dir, simulation_id=simulation_id)

        except Exception as e:
            run_manager.fail(e, state)
            raise

    @staticmethod
    def _new_simulation_dir(outputs_dir: Path) -> Path:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        random_suffix = Path(__file__).stem[:4]
        sim_dir = outputs_dir / f"sim_{timestamp}_{random_suffix}"
        sim_dir.mkdir(parents=True, exist_ok=True)
        return sim_dir

    @staticmethod
    def _resolve_feature_flags(version: Optional[RuntimeVersion]) -> dict:
        if not version:
            return {
                "allow_move": True,
                "enable_memory": True,
                "force_rule_narrative": False,
                "enable_consistency_revise": True,
            }
        return {
            "allow_move": True,
            "enable_memory": True,
            "force_rule_narrative": False,
            "enable_consistency_revise": True,
        }

    @staticmethod
    def _write_chapter_continuity(sim_dir: Path, chapter_no: int, reveal_budget, chapter_brief) -> None:
        report = {
            "version": "正式版V1.4",
            "chapter_no": chapter_no,
            "resolved_threads": [],
            "open_threads": list(chapter_brief.must_advance_threads) if chapter_brief else [],
            "new_questions": list(reveal_budget.required_questions) if reveal_budget else [],
            "character_memory_updates": [],
            "relationship_changes": [item.model_dump() for item in chapter_brief.relationship_focus] if chapter_brief else [],
            "next_chapter_seeds": [target.model_dump() for target in reveal_budget.payoff_targets] if reveal_budget else [],
        }
        with open(sim_dir / "chapter_continuity.json", "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

    @staticmethod
    def _write_version_report(
        sim_dir: Path,
        version: RuntimeVersion,
        feature_flags: dict,
        mode: AgentMode,
        tick_limit: int,
        finished_tick: int,
    ) -> None:
        report = {
            "version": "正式版V1",
            "phase": "正式版V1",
            "mode": mode,
            "tick_limit": tick_limit,
            "finished_tick": finished_tick,
            "feature_flags": feature_flags,
            "artifacts": {
                "events": "events.jsonl",
                "state": "state.json",
                "quality_controls": "quality_controls.json",
                "reveal_budget": "reveal_budget.json",
                "chapter_brief": "chapter_brief.json",
                "selected_events": "selected_events.json",
                "scene_plan": "scene_plan.json",
                "chapter_plan": "chapter_plan.json",
                "chapter_draft_raw": "chapter_draft_raw.md",
                "rewrite_plan": "rewrite_plan.json",
                "chapter_draft": "chapter_draft.md",
                "style_rewrite_report": "style_rewrite_report.json",
                "chapter_continuity": "chapter_continuity.json",
                "consistency_report": "consistency_report.json",
            },
        }
        with open(sim_dir / "version_report.json", "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
