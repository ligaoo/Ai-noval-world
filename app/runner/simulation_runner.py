from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional

from rich.console import Console

from app.core.time_utils import add_minutes
from app.models.event import EventLog, PlotValue
from app.models.world import WorldConfig
from app.services.character_agent_service import CharacterAgentService
from app.services.director_service import DirectorService
from app.services.environment_engine import EnvironmentEngine
from app.services.event_log_service import EventLogService
from app.services.intervention_service import InterventionService
from app.services.memory_service import MemoryService
from app.services.narrative_service import NarrativeService
from app.services.plot_arc_service import PlotArcService
from app.services.progress_monitor import ProgressMonitor
from app.services.run_manager_lite import RunManagerLite
from app.services.tension_monitor import TensionMonitor
from app.services.trace_service import TraceService
from app.services.world_state_service import WorldStateService


AgentMode = Literal["scripted", "heuristic", "llm"]


@dataclass
class RunResult:
    sim_dir: Path
    simulation_id: str


class SimulationRunner:
    def __init__(self, project_root: Path, console: Optional[Console] = None):
        self.project_root = project_root
        self.console = console or Console()
        self.state_svc = WorldStateService()
        self.event_svc = EventLogService()

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
    ) -> RunResult:
        outputs_dir = self.project_root / "outputs"
        outputs_dir.mkdir(parents=True, exist_ok=True)
        sim_dir = self._new_simulation_dir(outputs_dir)
        simulation_id = sim_dir.name
        tick_limit = ticks if ticks is not None else world.chapter_goal.tick_limit

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
            memory_service = MemoryService(sim_dir, world)
            monitor = ProgressMonitor(no_progress_limit=world.chapter_goal.no_progress_limit)

            from app.llm_client import OpenAICompatibleClient

            llm_client = OpenAICompatibleClient() if mode == "llm" else None
            agent_svc = CharacterAgentService(
                world=world,
                mode=mode,
                memory_service=memory_service,
                llm_client=llm_client,
                trace_service=trace_service,
                temperature=temperature,
                max_retries=max_retries,
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

            self.console.print(f"[bold]Simulation[/bold] {simulation_id} started. mode={mode}, ticks={tick_limit}")
            self.console.print(f"[dim]Genre: {genre_id}[/dim]")

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
                    applied = env.apply_action(state, action)
                    for ev in applied.new_events:
                        self.event_svc.append(sim_dir, ev)
                        memory_service.write_from_event(ev, state)
                        tension_monitor.record_event(ev)

                tension_report = tension_monitor.generate_report(simulation_id, t)
                if tension_report.need_intervention:
                    self.console.print(f"[yellow]⚠️ Tick {t}: 剧情张力异常[/yellow]")
                    for issue in tension_report.diagnosis[:2]:
                        self.console.print(f"   - {issue}")

                    proposal = director_service.propose_intervention(
                        state=state,
                        tension_report=tension_report,
                        chapter_goal=world.chapter_goal.goal,
                    )
                    if proposal:
                        self.console.print(f"[blue]🎬 Director 干预[/blue]: {proposal.intervention_type}")
                        self.console.print(f"   → {proposal.content}")
                        director_service.last_intervention_tick = t
                        intervention_event = intervention_service.apply_intervention(proposal, state, pov_id)
                        if intervention_event:
                            ev = intervention_service.to_event_log(intervention_event)
                            ev.time = state.world_time
                            self.event_svc.append(sim_dir, ev)
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
                self.console.print(
                    f"[dim]LLM Stats: {summary['total_calls']} calls, "
                    f"{summary['failed_calls']} failed, "
                    f"${summary['cost_usd']:.6f} cost[/dim]"
                )

            mem_summary = memory_service.get_summary()
            self.console.print(
                f"[dim]Memory Stats: {mem_summary['total']} total, "
                f"{mem_summary['event_memory']} event, "
                f"{mem_summary['fact_memory']} fact, "
                f"{mem_summary['belief_memory']} belief[/dim]"
            )

            narrative_llm = agent_svc._llm if mode == "llm" else None
            narrative_service = NarrativeService(world, sim_dir, narrative_llm, trace_service)
            result = narrative_service.generate_chapter()

            self.console.print(
                f"[green]✓ Chapter generated:[/green] {len(result['draft'])} characters, "
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

                self.console.print(
                    f"[blue]✓ Quality evaluated:[/blue] score={quality_report.overall_score:.1f}, "
                    f"grade={quality_report.grade}, "
                    f"rewrite={'recommended' if quality_report.rewrite_recommended else 'not needed'}"
                )

                if quality_report.rewrite_recommended:
                    self.console.print(
                        f"[yellow]⚠️ Rewrite priority: {quality_report.rewrite_priority}, "
                        f"issues found: {len(quality_report.problems) + len(quality_report.genre_problems)}[/yellow]"
                    )

                    if quality_report.problems:
                        for problem in quality_report.problems[:3]:
                            severity = problem.get("severity", "unknown")
                            message = problem.get("message", "")[:60]
                            self.console.print(f"   - [{severity}] {message}")

                    if quality_report.genre_problems:
                        for problem in quality_report.genre_problems[:2]:
                            severity = problem.get("severity", "unknown")
                            message = problem.get("message", "")[:60]
                            self.console.print(f"   - [genre][{severity}] {message}")

            except ImportError as e:
                self.console.print(f"[dim]Quality evaluation skipped: {e}[/dim]")
            except Exception as e:
                self.console.print(f"[yellow]⚠️ Quality evaluation failed: {e}[/yellow]")

            run_manager.complete(state)
            self.console.print(f"[bold]Simulation[/bold] {simulation_id} finished at tick={state.tick}.")
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
