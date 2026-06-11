from __future__ import annotations

import os
import sys
import time
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Optional

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
from app.services.narrative_readiness_guard import NarrativeReadinessError
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
        sim_dir: Optional[Path] = None,
        novel_run_dir: Optional[Path] = None,
        previous_chapter_dir: Optional[Path] = None,
        memory_file: Optional[Path] = None,
    ) -> RunResult:
        outputs_dir = self.project_root / "outputs"
        outputs_dir.mkdir(parents=True, exist_ok=True)
        if novel_run_dir is not None:
            novel_run_dir = Path(novel_run_dir)
            sim_dir = sim_dir or (novel_run_dir / f"ch_{chapter_no:03d}")
            memory_file = memory_file or (novel_run_dir / "memories.jsonl")
        if sim_dir is None:
            sim_dir = self._new_simulation_dir(outputs_dir)
        sim_dir = Path(sim_dir)
        sim_dir.mkdir(parents=True, exist_ok=True)
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
            memory_service = MemoryService(sim_dir, world, memory_file=memory_file) if feature_flags["enable_memory"] else None
            monitor = ProgressMonitor(no_progress_limit=world.chapter_goal.no_progress_limit)

            from app.llm_client import OpenAICompatibleClient

            llm_client = OpenAICompatibleClient.from_config(self.project_root, max_retries=max_retries) if mode == "llm" else None
            quality_controls = quality_controls or QualityControls()
            with open(sim_dir / "quality_controls.json", "w", encoding="utf-8") as f:
                json.dump(quality_controls.model_dump(), f, ensure_ascii=False, indent=2)
            previous_chapter_context = self._load_previous_chapter_continuity(previous_chapter_dir) if previous_chapter_dir else {}
            chapter_function = self._load_chapter_function(novel_run_dir, chapter_no)
            reveal_budget_service = RevealBudgetService(world)
            reveal_budget = reveal_budget_service.build(chapter_no=chapter_no, target_chapters=target_chapters, chapter_function=chapter_function)
            reveal_budget_service.save(sim_dir, reveal_budget)
            chapter_brief_service = ChapterBriefService(world)
            chapter_brief = chapter_brief_service.build(
                chapter_no=chapter_no,
                target_chapters=target_chapters,
                reveal_budget=reveal_budget,
                quality_controls=quality_controls,
                chapter_function=chapter_function,
                previous_chapter_context=previous_chapter_context,
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
            env.current_chapter = chapter_no

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

            previous_state = None
            if chapter_no > 1 and previous_chapter_dir and (Path(previous_chapter_dir) / "state.json").exists():
                previous_state = self.state_svc.load(Path(previous_chapter_dir))
            if previous_state:
                state = self.state_svc.continue_state(
                    previous_state=previous_state,
                    simulation_id=simulation_id,
                    world=world,
                    seed=seed,
                    chapter_goal_text=getattr(chapter_brief, "chapter_goal", "") or world.chapter_goal.goal,
                )
            else:
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
                playable_character_ids = []
                for cid in world.characters.ids():
                    profile = world.characters.get_character(cid)
                    if profile and profile.active_agent:
                        playable_character_ids.append(cid)
                character_order = ([pov_id] if pov_id in playable_character_ids else []) + [cid for cid in playable_character_ids if cid != pov_id]

                for cid in character_order:
                    last_events = self.event_svc.read_all(sim_dir)
                    last_events_text = [f"{e.time} {e.event_type}: {e.result}" for e in last_events[-8:]]
                    ctx = agent_svc.build_context(state, cid, last_events_text=last_events_text)

                    plot_ctx = plot_arc_service.to_context_dict() if plot_arc_service else {}
                    ctx.plot_arc_stage = plot_ctx.get("arc_stage", "")
                    ctx.plot_arc_purpose = plot_ctx.get("chapter_goal", "")
                    ctx.forbidden_revelations = plot_ctx.get("forbidden_revelations", [])

                    if previous_chapter_context:
                        ctx.previous_chapter_summary = previous_chapter_context.get("previous_chapter_summary", "")
                        ctx.open_threads = previous_chapter_context.get("open_threads", [])
                        ctx.next_chapter_seeds = previous_chapter_context.get("next_chapter_seeds", [])

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
            quality_report = None
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
                    open_threads=self._quality_open_threads(previous_chapter_context, chapter_brief, selected_events_report, chapter_no),
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

            self._write_chapter_continuity(
                sim_dir,
                chapter_no,
                reveal_budget,
                chapter_brief,
                selected_events_report=selected_events_report,
                scene_plan=scene_plan,
                chapter_function=chapter_function,
            )
            validation_status = self._aggregate_validation_status(
                result.get("consistency_report"),
                result.get("draft_faithfulness_report"),
                quality_report,
            )
            validation_errors = self._validation_errors_from_reports(
                result.get("consistency_report"),
                result.get("draft_faithfulness_report"),
                quality_report,
            )
            run_manager.complete_with_validation(
                state=state,
                validation_status=validation_status,
                validation_errors=validation_errors,
                extra_metrics={
                    "fallback_actions": getattr(agent_svc, "fallback_actions", 0),
                    "agent_decision_failures": getattr(agent_svc, "agent_decision_failures", 0),
                },
            )
            self._log(f"Simulation {simulation_id} finished at tick={state.tick}.")
            return RunResult(sim_dir=sim_dir, simulation_id=simulation_id)

        except NarrativeReadinessError as e:
            self._log(f"[!] Narrative readiness failed: {e}")
            errors = [
                {
                    "source": "narrative_readiness_report",
                    "type": error.get("code", "narrative_readiness_failed"),
                    "severity": "high",
                    "message": error.get("message", "Narrative readiness failed."),
                    "details": error.get("details") or error,
                }
                for error in e.report.get("errors", [])
            ]
            run_manager.complete_with_validation(
                state=state,
                validation_status="failed",
                validation_errors=errors,
                extra_metrics={
                    "fallback_actions": getattr(agent_svc, "fallback_actions", 0),
                    "agent_decision_failures": getattr(agent_svc, "agent_decision_failures", 0),
                },
            )
            self._log(f"Simulation {simulation_id} stopped before narrative draft at tick={state.tick}.")
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
    def _load_previous_chapter_continuity(previous_chapter_dir: Path) -> dict[str, Any]:
        path = Path(previous_chapter_dir) / "chapter_continuity.json"
        if not path.exists():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}

        def text_list(value: Any) -> list[str]:
            if not isinstance(value, list):
                return []
            result: list[str] = []
            for item in value:
                if isinstance(item, dict):
                    text = item.get("question") or item.get("thread_id") or item.get("effect") or item.get("summary") or json.dumps(item, ensure_ascii=False)
                else:
                    text = str(item)
                text = str(text or "").strip()
                if text and text not in result:
                    result.append(text)
            return result

        open_threads = text_list(data.get("open_threads"))
        for item in text_list(data.get("active_reader_promises")):
            if item not in open_threads:
                open_threads.append(item)
        next_chapter_seeds = text_list(data.get("next_chapter_seeds"))
        for item in text_list(data.get("new_questions")):
            if item not in next_chapter_seeds:
                next_chapter_seeds.append(item)
        return {
            "previous_chapter_summary": str(data.get("chapter_delta_summary") or "").strip(),
            "open_threads": open_threads[:12],
            "next_chapter_seeds": next_chapter_seeds[:12],
        }

    @staticmethod
    def _load_chapter_function(novel_run_dir: Optional[Path], chapter_no: int) -> dict[str, Any]:
        if not novel_run_dir:
            return {}
        path = Path(novel_run_dir) / "novel_plan.json"
        if not path.exists():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
        chapter_functions = data.get("chapter_functions")
        if not isinstance(chapter_functions, list):
            return {}
        for item in chapter_functions:
            if isinstance(item, dict) and item.get("chapter_no") == chapter_no:
                return item
        index = chapter_no - 1
        if 0 <= index < len(chapter_functions) and isinstance(chapter_functions[index], dict):
            return chapter_functions[index]
        return {}

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
    def _quality_open_threads(previous_chapter_context: dict, chapter_brief, selected_events_report, chapter_no: int):
        threads = []
        seen = set()

        def add_thread(thread_id: str, summary: str = "", progressed: bool = False):
            text = str(thread_id or summary or "").strip()
            if not text or text in seen:
                return
            seen.add(text)
            threads.append({
                "thread_id": text,
                "summary": summary or text,
                "status": "open",
                "last_progress_chapter": chapter_no if progressed else 0,
            })

        for item in (previous_chapter_context or {}).get("open_threads") or []:
            if isinstance(item, dict):
                add_thread(item.get("thread_id") or item.get("question") or item.get("summary"), item.get("summary") or item.get("question") or "", bool(item.get("last_progress_chapter")))
            else:
                add_thread(str(item), str(item), False)
        for thread in getattr(chapter_brief, "must_advance_threads", []) or []:
            add_thread(thread, thread, False)
        for event in getattr(selected_events_report, "selected_events", []) or []:
            for thread_id in getattr(event, "thread_ids", []) or []:
                add_thread(thread_id, thread_id, True)
            question = getattr(event, "reader_question", "") or ""
            if question and not self._is_generic_quality_thread(question):
                add_thread(question, question, True)
        return threads or None

    @staticmethod
    def _is_generic_quality_thread(text: str) -> bool:
        normalized = str(text or "").strip()
        if not normalized or len(normalized) < 6:
            return True
        return any(fragment in normalized for fragment in ["这个异常细节为什么会出现", "这条线索真正指向什么", "这个事件如何推进悬念"])

    @staticmethod
    def _write_chapter_continuity(
        sim_dir: Path,
        chapter_no: int,
        reveal_budget,
        chapter_brief,
        selected_events_report=None,
        scene_plan=None,
        chapter_function=None,
    ) -> None:
        open_threads = []
        new_questions = []
        next_chapter_seeds = []
        new_facts = []
        changed_character_states = []
        cause_effect_links = []
        active_reader_promises = []
        seen_seed_questions = set()
        generic_questions = {
            "这条线索真正指向什么？",
            "这个异常细节为什么会出现？",
            "本章异常真正指向什么？",
            "本章异常真正指向什么",
            "以线索钩子结束，不总结，不揭示隐藏真相。",
            "从表面合作转为轻微试探，保留信息差。",
        }

        def is_generic_question(value: Any) -> bool:
            text = str(value or "").strip()
            return not text or text in generic_questions

        def add_unique(target: list, value: Any) -> None:
            if value is None:
                return
            text = str(value).strip()
            if text and not is_generic_question(text) and text not in target:
                target.append(text)

        def add_seed_question(question: Any) -> None:
            text = str(question or "").strip()
            if is_generic_question(text) or text in seen_seed_questions:
                return
            seen_seed_questions.add(text)
            next_chapter_seeds.append({"type": "reader_question", "question": text})

        relationship_promises = []

        if chapter_brief:
            for thread in chapter_brief.must_advance_threads:
                add_unique(open_threads, thread)
            for focus in chapter_brief.relationship_focus:
                promise = str(getattr(focus, "expected_shift", "") or "").strip()
                if promise and not is_generic_question(promise):
                    relationship_promises.append(focus.model_dump())

        if reveal_budget:
            for question in reveal_budget.required_questions:
                add_unique(open_threads, question)
                add_unique(new_questions, question)
            for target in reveal_budget.payoff_targets:
                add_unique(open_threads, getattr(target, "thread_id", ""))
                next_chapter_seeds.append(target.model_dump())

        if selected_events_report:
            for event in selected_events_report.selected_events:
                for thread_id in getattr(event, "thread_ids", []) or []:
                    add_unique(open_threads, thread_id)
                    add_unique(active_reader_promises, thread_id)
                reader_question = getattr(event, "reader_question", "")
                add_unique(open_threads, reader_question)
                add_unique(new_questions, reader_question)
                add_unique(active_reader_promises, reader_question)
                add_seed_question(reader_question)
                for impact in getattr(event, "character_impact", []) or []:
                    if isinstance(impact, dict):
                        character_id = impact.get("character_id")
                        impact_text = impact.get("impact")
                        if character_id and impact_text:
                            changed_character_states.append({"character_id": character_id, "change": impact_text})
                reason = getattr(event, "reason", "")
                if reason:
                    cause_effect_links.append({"event_id": event.event_id, "effect": reason})

        if scene_plan and getattr(scene_plan, "scenes", None):
            for scene in scene_plan.scenes:
                for fact in getattr(getattr(scene, "reveal_budget", None), "allowed", []) or []:
                    add_unique(new_facts, fact)
                change = getattr(scene, "consequence_or_change", "")
                pair = getattr(scene, "information_action_pair", "")
                if change:
                    cause_effect_links.append({"scene_id": scene.scene_id, "effect": change})
                if pair:
                    add_unique(active_reader_promises, pair)

        if scene_plan and getattr(scene_plan, "chapter_hook", None):
            hook_requirement = getattr(scene_plan.chapter_hook, "requirement", "")
            add_unique(new_questions, hook_requirement)
            add_unique(active_reader_promises, hook_requirement)

        chapter_delta_parts = []
        if new_facts:
            chapter_delta_parts.append(f"新增事实 {len(new_facts)} 项")
        if changed_character_states:
            chapter_delta_parts.append(f"角色状态变化 {len(changed_character_states)} 项")
        if cause_effect_links:
            chapter_delta_parts.append(f"因果变化 {len(cause_effect_links)} 项")
        if new_questions:
            chapter_delta_parts.append(f"新增/延续读者问题 {len(new_questions)} 项")

        resolved_threads = [
            {"thread_id": str(thread_id), "resolved_at_chapter": chapter_no, "resolution_type": "planned_payoff"}
            for thread_id in ((chapter_function or {}).get("thread_payoffs") or [])
            if str(thread_id).strip()
        ]

        report = {
            "version": "正式版V1.4",
            "chapter_no": chapter_no,
            "resolved_threads": resolved_threads,
            "open_threads": open_threads,
            "new_questions": new_questions,
            "new_facts": new_facts,
            "changed_character_states": changed_character_states,
            "cause_effect_links": cause_effect_links,
            "chapter_delta_summary": "；".join(chapter_delta_parts) if chapter_delta_parts else "本章未记录到明确状态变化。",
            "active_reader_promises": active_reader_promises,
            "character_memory_updates": [],
            "relationship_changes": [item.model_dump() for item in chapter_brief.relationship_focus] if chapter_brief else [],
            "relationship_promises": relationship_promises,
            "next_chapter_seeds": next_chapter_seeds,
        }
        with open(sim_dir / "chapter_continuity.json", "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

    @staticmethod
    def _aggregate_validation_status(consistency_report, faithfulness_report, quality_report) -> str:
        reports = [report for report in [consistency_report, faithfulness_report] if isinstance(report, dict)]
        if any(report.get("status") == "failed" or report.get("passed") is False for report in reports):
            return "failed"
        if any(report.get("status") == "warning" for report in reports):
            return "warning"
        if quality_report and getattr(quality_report, "rewrite_recommended", False):
            return "warning"
        return "passed"

    @staticmethod
    def _validation_errors_from_reports(consistency_report, faithfulness_report, quality_report) -> list[dict[str, Any]]:
        errors: list[dict[str, Any]] = []
        if isinstance(consistency_report, dict):
            for violation in consistency_report.get("violations") or []:
                errors.append(
                    {
                        "source": "consistency_report",
                        "type": violation.get("type", "consistency_violation"),
                        "severity": violation.get("severity", "medium"),
                        "message": violation.get("reason") or violation.get("message") or "Consistency violation.",
                        "details": violation,
                    }
                )
        if isinstance(faithfulness_report, dict):
            for issue in faithfulness_report.get("issues") or []:
                errors.append(
                    {
                        "source": "draft_faithfulness_report",
                        "type": issue.get("type", "faithfulness_issue"),
                        "severity": issue.get("severity", "medium"),
                        "message": issue.get("message", "Draft faithfulness issue."),
                        "details": issue.get("details") or issue,
                    }
                )
        if quality_report and getattr(quality_report, "rewrite_recommended", False):
            for problem in list(getattr(quality_report, "problems", []) or [])[:8]:
                errors.append(SimulationRunner._quality_problem_to_error(problem))
        return errors

    @staticmethod
    def _quality_problem_to_error(problem) -> dict[str, Any]:
        if isinstance(problem, dict):
            severity = problem.get("severity", "medium")
            problem_type = problem.get("type", "quality_issue")
            message = problem.get("message", "Quality issue.")
            problem_id = problem.get("problem_id")
            evidence = problem.get("evidence", [])
        else:
            severity = getattr(getattr(problem, "severity", "medium"), "value", getattr(problem, "severity", "medium"))
            problem_type = getattr(getattr(problem, "type", "quality_issue"), "value", getattr(problem, "type", "quality_issue"))
            message = getattr(problem, "message", "Quality issue.")
            problem_id = getattr(problem, "problem_id", None)
            evidence = getattr(problem, "evidence", [])
        return {
            "source": "quality_report",
            "type": problem_type,
            "severity": severity,
            "message": message,
            "details": {"problem_id": problem_id, "evidence": evidence},
        }

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
