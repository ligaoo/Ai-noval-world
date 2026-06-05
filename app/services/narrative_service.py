from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.llm_client import OpenAICompatibleClient
from app.models.event import EventLog
from app.models.narrative import ChapterBeat, ChapterPlan
from app.models.state import WorldState
from app.models.world import WorldConfig
from app.services.chapter_causal_chain_builder import ChapterCausalChainBuilder
from app.services.narrative_context_builder import NarrativeContextBuilder
from app.services.consistency_service import ConsistencyService
from app.services.draft_faithfulness_checker import DraftFaithfulnessChecker
from app.services.event_log_service import EventLogService
from app.services.trace_service import LLMTrace, TraceService
from app.models.rewrite_plan import StyleRewriteReport
from app.services.narrative_style_rewriter import NarrativeStyleRewriter
from app.services.rewrite_plan_builder import RewritePlanBuilder
from app.services.writer_authorization_builder import WriterAuthorizationBuilder


class NarrativeService:
    """
    正式版V1 叙事生成服务。
    先根据事件生成 chapter_plan，再由规则或 LLM 生成章节正文。
    """

    def __init__(
        self,
        world: WorldConfig,
        sim_dir: Path,
        llm_client: Optional[OpenAICompatibleClient] = None,
        trace_service: Optional[TraceService] = None,
        force_rule_based: bool = False,
        enable_consistency_check: bool = True,
        state: Optional[WorldState] = None,
        chapter_brief: Optional[Any] = None,
        scene_plan: Optional[Any] = None,
        reveal_budget: Optional[Any] = None,
        quality_controls: Optional[Any] = None,
    ):
        self.world = world
        self.sim_dir = sim_dir
        self.llm_client = llm_client
        self.trace_service = trace_service
        self.force_rule_based = force_rule_based
        self.enable_consistency_check = enable_consistency_check
        self.chapter_brief = chapter_brief
        self.scene_plan = scene_plan
        self.reveal_budget = reveal_budget
        self.quality_controls = quality_controls
        self.event_svc = EventLogService()
        self.consistency_svc = ConsistencyService(world, sim_dir, llm_client, trace_service)
        self.state = state or self._load_state()
        self.safe_context = self._build_safe_context()
        # 鑷姩鍔犺浇 writer_story_anchors.json锛堢敱 StoryBootstrapper 鍐欏叆锛?
        self.story_anchors: Optional[Dict[str, Any]] = self._load_story_anchors()

    def _load_story_anchors(self) -> Optional[Dict[str, Any]]:
        """浠?worlds/<world_id>/writer_story_anchors.json 鍔犺浇鍙欎簨閿氱偣"""
        try:
            # WorldConfig.from_directory 璇诲彇鏃?world_dir 淇℃伅娌℃湁鐩存帴淇濆瓨锛?
            # 浣?world.world_id 宸茬粡瀛樺湪锛岄€氳繃 sim_dir 涓婃函鍒?project_root
            project_root = self.sim_dir.parent.parent  # outputs/sim_xxx -> outputs -> project_root
            anchor_file = project_root / "worlds" / self.world.world_id / "writer_story_anchors.json"
            if anchor_file.exists():
                with open(anchor_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            return None
        return None

    def _load_state(self) -> Optional[WorldState]:
        state_file = self.sim_dir / "state.json"
        if not state_file.exists():
            return None
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                return WorldState.model_validate(json.load(f))
        except Exception:
            return None

    def _build_safe_context(self) -> Dict[str, Any]:
        if not self.state:
            return {}
        events = self.event_svc.read_all(self.sim_dir)
        return NarrativeContextBuilder(self.world).build(
            self.state,
            events,
            self.world.chapter_goal.pov,
        )

    def generate_chapter(self) -> Dict[str, Any]:
        """鐢熸垚瀹屾暣绔犺妭锛歱lan + draft + consistency report"""
        # 1. 璇诲彇浜嬩欢
        all_events = self.event_svc.read_all(self.sim_dir)
        plot_events = [e for e in all_events if e.event_level == "plot"]

        # P1锛坧lan 搂19锛夛細VisibleEventFilter 鈥?鍙啓 POV 鑳芥劅鐭ョ殑浜嬩欢缁?LLM
        # 闃叉 hidden_actor 鐨勭湡瀹炶鍔ㄧ洿鎺ュ嚭鐜板湪姝ｆ枃涓?
        from app.services.visible_event_filter import VisibleEventFilter
        ve_filter = VisibleEventFilter()
        pov_id = self.world.chapter_goal.pov
        filtered_plot_events = ve_filter.filter_for_narrative(plot_events, pov_id)
        # 杩囨护鎺夌洿鎺ユ毚闇?hidden_actor 韬唤鐨勬晱鎰熷唴瀹?
        filtered_plot_events = [e for e in filtered_plot_events if not ve_filter.has_sensitive_content(e)]
        filtered_plot_events = self._preserve_key_causal_events(plot_events, filtered_plot_events)
        structured_context = self._build_structured_writer_context(filtered_plot_events)

        # 2. 瑙勫垯鐢熸垚 chapter_plan
        plan = self._build_chapter_plan(filtered_plot_events)
        scene_plan_dict = self._scene_plan_dict()
        with open(self.sim_dir / "chapter_plan.json", "w", encoding="utf-8") as f:
            json.dump({
                "chapter_title": plan.chapter_title,
                "pov": plan.pov,
                "chapter_goal": plan.chapter_goal,
                "emotional_curve": plan.emotional_curve,
                "beats": [
                    {
                        "beat_id": b.beat_id,
                        "purpose": b.purpose,
                        "event_ids": b.event_ids,
                    }
                    for b in plan.beats
                ],
                "ending_hook_event_id": plan.ending_hook_event_id,
                "quality_controls": self._quality_controls_dict(),
                "reveal_budget": self._reveal_budget_dict(),
                "chapter_brief": self._chapter_brief_dict(),
                "scene_plan": scene_plan_dict,
                "scene_count": len(scene_plan_dict.get("scenes", [])),
                "scene_ids": [scene.get("scene_id") for scene in scene_plan_dict.get("scenes", [])],
                "selected_event_ids": [event_id for scene in scene_plan_dict.get("scenes", []) for event_id in scene.get("event_ids", [])],
                "writer_structured_context": structured_context,
            }, f, ensure_ascii=False, indent=2)

        draft = ""
        rewrite_report = StyleRewriteReport(rewrite_applied=False)
        if self.llm_client and not self.force_rule_based:
            raw_draft = self._llm_write_chapter(plan)
            with open(self.sim_dir / "chapter_draft_raw.md", "w", encoding="utf-8") as f:
                f.write(raw_draft)

            raw_report = self.consistency_svc.check_consistency(raw_draft, plan, filtered_plot_events) if self.enable_consistency_check else {"passed": True, "mode": "disabled", "violations": []}
            rewrite_plan = RewritePlanBuilder().build(
                quality_report=None,
                chapter_plan=self._load_chapter_plan_dict(),
                scene_plan=self._scene_plan_dict(),
            )
            RewritePlanBuilder().save(self.sim_dir, rewrite_plan)

            draft = raw_draft
            try:
                writer_authorization = structured_context.get("writer_authorization") or {}
                rewritten = NarrativeStyleRewriter(self.llm_client).rewrite(
                    draft=raw_draft,
                    scene_plan=self._scene_plan_dict(),
                    rewrite_plan=rewrite_plan,
                    writer_authorization=writer_authorization,
                )
                rewritten_faithfulness = DraftFaithfulnessChecker(self.world, self.sim_dir).check(
                    draft=rewritten,
                    chapter_plan=self._load_chapter_plan_dict(),
                    visible_events=filtered_plot_events,
                    state=self.state,
                )
                rewritten_report = self.consistency_svc.check_consistency(rewritten, plan, filtered_plot_events) if self.enable_consistency_check else {"passed": True, "mode": "disabled", "violations": []}
                if rewritten_report.get("passed") and rewritten_faithfulness.get("passed", True):
                    draft = rewritten
                    report = rewritten_report
                    rewrite_report = StyleRewriteReport(
                        style_profile="horror_suspense_default",
                        input_draft_chars=len(raw_draft),
                        output_draft_chars=len(rewritten),
                        rewrite_applied=True,
                        rewrite_focus=rewrite_plan.rewrite_plan,
                        consistency_after_rewrite=rewritten_report,
                        faithfulness_after_rewrite=rewritten_faithfulness,
                    )
                else:
                    report = raw_report
                    rewrite_report = StyleRewriteReport(
                        style_profile="horror_suspense_default",
                        input_draft_chars=len(raw_draft),
                        output_draft_chars=len(raw_draft),
                        rewrite_applied=False,
                        rewrite_focus=rewrite_plan.rewrite_plan,
                        consistency_after_rewrite=rewritten_report,
                        faithfulness_after_rewrite=rewritten_faithfulness,
                        fallback_reason="style rewrite failed consistency or faithfulness checks",
                    )
            except Exception as exc:
                report = raw_report
                rewrite_report = StyleRewriteReport(
                    style_profile="horror_suspense_default",
                    input_draft_chars=len(raw_draft),
                    output_draft_chars=len(raw_draft),
                    rewrite_applied=False,
                    rewrite_focus=rewrite_plan.rewrite_plan,
                    consistency_after_rewrite=raw_report,
                    fallback_reason=str(exc),
                )

            with open(self.sim_dir / "chapter_draft.md", "w", encoding="utf-8") as f:
                f.write(draft)
            with open(self.sim_dir / "style_rewrite_report.json", "w", encoding="utf-8") as f:
                json.dump(rewrite_report.model_dump(), f, ensure_ascii=False, indent=2)
        else:
            draft = self._rule_based_draft(plan, structured_context)
            with open(self.sim_dir / "chapter_draft_raw.md", "w", encoding="utf-8") as f:
                f.write(draft)
            with open(self.sim_dir / "chapter_draft.md", "w", encoding="utf-8") as f:
                f.write(draft)
            rewrite_plan = RewritePlanBuilder().build(
                quality_report=None,
                chapter_plan=self._load_chapter_plan_dict(),
                scene_plan=self._scene_plan_dict(),
            )
            RewritePlanBuilder().save(self.sim_dir, rewrite_plan)
            report = {"passed": True, "mode": "rule_based", "violations": []}
            with open(self.sim_dir / "consistency_report.json", "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            with open(self.sim_dir / "style_rewrite_report.json", "w", encoding="utf-8") as f:
                json.dump(rewrite_report.model_dump(), f, ensure_ascii=False, indent=2)

        with open(self.sim_dir / "consistency_report.json", "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        self._write_chapter_debug_report(filtered_plot_events, structured_context, draft)
        draft_faithfulness_report = DraftFaithfulnessChecker(self.world, self.sim_dir).check(
            draft=draft,
            chapter_plan=self._load_chapter_plan_dict(),
            visible_events=filtered_plot_events,
            state=self.state,
        )

        return {
            "plan": plan,
            "draft": draft,
            "consistency_report": report,
            "draft_faithfulness_report": draft_faithfulness_report,
        }

    # ==========================================
    # 瑙勫垯鐢熸垚 chapter_plan
    # ==========================================

    def _build_chapter_plan(self, plot_events: List[EventLog]) -> ChapterPlan:
        """浠?plot_events 鐢熸垚绔犺妭澶х翰

        鏍稿績鍘熷垯锛氫竴涓珷鑺傚彧璁叉竻妤氫竴浠朵簨锛屼笉瑕佸爢鐮岀嚎绱?
        """
        plot_events.sort(key=lambda e: e.event_id)

        # 鎯呮劅鏇茬嚎锛氭洿澶?鍠樻伅"闃舵锛屼笉瑕佸叏绋嬬揣寮?
        emotional_curve = self._build_emotional_curve(plot_events)

        # beats 鍒嗙粍锛氬悎骞跺瘑闆嗕簨浠讹紝姣忎釜 鐗囨 鍙噴鏀?1-2 涓牳蹇冨紓甯?
        beats = self._build_beats(plot_events)

        # ending hook锛氬彧閫変竴涓湁鎮康鐨勪簨浠讹紝涓嶈鎶婇珮娼叏鏀惧湪缁撳熬
        ending_hook_event_id = self._select_ending_hook(beats, plot_events)

        return ChapterPlan(
            chapter_title=self._generate_default_chapter_title(plot_events),
            pov=self.world.chapter_goal.pov,
            chapter_goal=self.world.chapter_goal.goal,
            emotional_curve=emotional_curve,
            beats=beats,
            ending_hook_event_id=ending_hook_event_id,
        )

    def _generate_default_chapter_title(self, plot_events: List[EventLog]) -> str:
        """鏍规嵁浜嬩欢鎴栦笘鐣岄厤缃敓鎴愰粯璁ょ珷鑺傛爣棰?"""
        if plot_events and hasattr(plot_events[0], "location_id") and plot_events[0].location_id:
            try:
                loc = self.world.map.get_location(plot_events[0].location_id)
                if loc and loc.name and loc.name != "Starting Point":
                    return loc.name
            except KeyError:
                pass

        if plot_events and hasattr(plot_events[0], "result"):
            first_result = plot_events[0].result
            if len(first_result) > 10:
                return first_result[:10]

        return "第一章" if self.world.bible.era == "古代" else "序章"

    def _select_ending_hook(self, beats: List[ChapterBeat], plot_events: List[EventLog]) -> Optional[str]:
        """閫夋嫨缁撳熬閽╁瓙锛氶€変竴涓腑绛夋偓蹇电殑浜嬩欢锛屼笉瑕侀€夋渶鎭愭€栫殑閭ｄ釜"""
        if not plot_events:
            return None
        # 閫夊€掓暟绗簩涓垨绗笁涓簨浠讹紝鐣欎笅浣欓煹
        sorted_events = sorted(plot_events, key=lambda e: e.event_id)
        if len(sorted_events) >= 3:
            return sorted_events[-2].event_id
        return sorted_events[-1].event_id

    def _build_emotional_curve(self, events: List[EventLog]) -> List[str]:
        """根据 plot_value 生成情绪曲线，交替保留紧张与喘息。"""
        curve = []
        for e in events:
            pv = e.plot_value
            tension = (pv.conflict + pv.mystery + pv.danger) / 3
            if pv.danger > 7:
                curve.append("危险")
            elif pv.conflict > 6:
                curve.append("紧张")
            elif pv.mystery > 5:
                curve.append("不安")
            elif tension > 4:
                curve.append("压迫")
            elif pv.progress > 5:
                curve.append("推进")
            else:
                curve.append("观察")

        unique = []
        seen = set()
        for i, c in enumerate(curve):
            if c not in seen:
                unique.append(c)
                seen.add(c)
            if c in ("紧张", "不安", "危险") and i < len(curve) - 1:
                unique.append("喘息")
                seen.add("喘息")

        if len(unique) < 4:
            unique = ["观察", "不安", "紧张", "喘息", "悬念"][:5]
        return unique

    def _build_beats(self, events: List[EventLog]) -> List[ChapterBeat]:
        """鎸夊湴鐐瑰垎缁勭敓鎴?beats

        鏍稿績鍘熷垯锛氭瘡涓?鐗囨 鍙噴鏀?1-2 涓牳蹇冨紓甯革紝涓嶈鍫嗙爩
        澶氫釜鐩镐技寮傚父鍚堝苟涓轰竴涓紝鍙繚鐣欐渶鏈夋偓蹇电殑閭ｄ釜
        """
        beats: List[ChapterBeat] = []
        beats_by_loc: Dict[str, List[EventLog]] = {}

        for e in events:
            loc_id = e.location_id or "unknown"
            if loc_id not in beats_by_loc:
                beats_by_loc[loc_id] = []
            beats_by_loc[loc_id].append(e)

        for idx, (loc_id, loc_events) in enumerate(beats_by_loc.items()):
            # 鏍稿績寮傚父鍙繚鐣?1-2 涓細浼樺厛淇濈暀 mystery/conflict 楂樼殑
            sorted_events = sorted(
                loc_events,
                key=lambda e: e.plot_value.mystery + e.plot_value.conflict + e.plot_value.danger,
                reverse=True
            )
            # 鏈€澶氫繚鐣?2 涓牳蹇冧簨浠?
            core_events = sorted_events[:2]
            # 鍓╀綑浜嬩欢濡傛灉澶锛屽悎骞舵垚涓€涓?瑙傚療"绫讳簨浠?
            remaining = sorted_events[2:]

            # 鏍规嵁鍦扮偣鎺ㄦ柇 purpose
            purpose = self._infer_purpose(loc_id, core_events)

            beat = ChapterBeat(
                beat_id=f"b{idx:03d}",
                purpose=purpose,
                event_ids=[e.event_id for e in core_events],
                events=core_events,
            )
            beats.append(beat)

        return beats

    def _infer_purpose(self, loc_id: str, events: List[EventLog]) -> str:
        """Infer a generic beat purpose from event plot values."""
        if not events:
            return "观察变化"

        total_mystery = sum(e.plot_value.mystery for e in events)
        total_conflict = sum(e.plot_value.conflict for e in events)
        total_danger = sum(e.plot_value.danger for e in events)
        total_progress = sum(e.plot_value.progress for e in events)
        event_types = {e.event_type for e in events}

        if total_danger > 8:
            return "危险逼近"
        if total_conflict > 8 or "interaction" in event_types:
            return "关系施压"
        if total_mystery > 8:
            return "异常浮现"
        if total_progress > 6:
            return "线索推进"
        return "观察变化"

    # ==========================================
    # LLM 姝ｆ枃鏀瑰啓
    # ==========================================

    def _llm_write_chapter(self, plan: ChapterPlan) -> str:
        """Write chapter text from the chapter plan using the LLM."""
        if not self.llm_client:
            return self._rule_based_draft(plan)

        try:
            # 鏋勫缓 allowed_entities
            allowed_entities = self._build_allowed_entities(plan)

            # 鏋勫缓 prompt
            system = self._build_narrative_system_prompt()
            user = self._build_narrative_user_prompt(plan, allowed_entities)

            # 璋冪敤 LLM锛坱emperature=0.7锛屽鍔犳枃瀛︽€э級
            # 娉ㄦ剰锛氬皬璇寸敓鎴愮敤鏅€氭枃鏈ā寮忥紝涓嶈鐢?JSON 妯″紡锛?
            resp = self.llm_client.chat(system=system, user=user, temperature=0.7)

            # 璁板綍 trace
            if self.trace_service:
                trace = LLMTrace(
                    trace_id=resp.trace_id,
                    simulation_id=self.world.world_id,
                    tick=0,
                    agent_id="narrative_writer",
                    purpose="narrative_write",
                    model=self.llm_client.model,
                    input_tokens=resp.cost.input_tokens,
                    output_tokens=resp.cost.output_tokens,
                    total_tokens=resp.cost.total_tokens,
                    cost_usd=resp.cost.cost_usd,
                    success=True,
                    retry_count=0,
                    from_cache=resp.from_cache,
                    error="",
                )
                self.trace_service.record(trace)

            return resp.text
        except Exception as e:
            # ========== 璁板綍璇︾粏閿欒鏃ュ織 ==========
            import traceback
            import time

            error_log = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "error_type": type(e).__name__,
                "error_message": str(e),
                "stack_trace": traceback.format_exc(),
                "system_prompt_length": len(system) if 'system' in locals() else 0,
                "user_prompt_length": len(user) if 'user' in locals() else 0,
            }

            # 淇濆瓨鍒伴敊璇棩蹇楁枃浠?
            error_file = self.sim_dir / "llm_error.json"
            import json
            with open(error_file, "w", encoding="utf-8") as f:
                json.dump(error_log, f, ensure_ascii=False, indent=2)

            print("\n" + "="*80)
            print("LLM 章节生成失败")
            print("="*80)
            print(f"错误类型: {type(e).__name__}")
            print(f"错误信息: {e}")
            print(f"错误日志已保存到: {error_file}")
            print("="*80 + "\n")
            # =========================================

            # 鍥為€€鍒拌鍒欑敓鎴愭ā寮?
            print("Falling back to rule-based generation...")
            return self._rule_based_draft(plan)

    def _build_allowed_entities(self, plan: ChapterPlan) -> Dict[str, List[str]]:
        """鏋勫缓鍏佽鍑虹幇鐨勫疄浣撶櫧鍚嶅崟"""
        locations = set()
        objects = set()
        characters = set()
        facts = set()

        # 浠庝笘鐣岄厤缃腑鎻愬彇
        for loc in self.world.map.locations:
            locations.add(loc.id)
            locations.add(loc.name)
            for obj in loc.objects:
                objects.add(obj.id)
                objects.add(obj.name)

        for char in self.world.characters.characters:
            characters.add(char.name)

        # 浠庣嚎绱㈠唴瀹逛腑鎻愬彇鍏抽敭璇?
        for clue in self.world.clues.clues:
            # 绠€鍗曟敹闆嗭細鎻愬彇绾跨储涓殑瀹炰綋锛堢畝鍗曞垎璇嶏級
            content = clue.content
            for sep in ("，", "。", "、", ",", ".", ";", "；", ":", "："):
                content = content.replace(sep, " ")
            for word in content.split():
                if len(word) > 1:
                    facts.add(word)

        return {
            "locations": list(locations),
            "objects": list(objects),
            "characters": list(characters),
            "character_ids": [char.id for char in self.world.characters.characters],
            "facts": list(facts)[:50],  # 闄愬埗鏁伴噺
        }

    @staticmethod
    def _build_narrative_system_prompt() -> str:
        return (
            "你是章节 Writer。你的职责不是创造新的冲突，而是把上游结构化结果文学化。\n"
            "1. 只能写 POV 能看见、听见、触碰、回忆或合理怀疑的内容。\n"
            "2. allowed_facts 可以写成确定事实；suspected_facts 只能写成怀疑、异常或不确定感。\n"
            "3. forbidden_fact_labels 和 prevented_facts 不得写成真相。\n"
            "4. 台词只能来自 spoken_segments、interruption_results、post_interruption_reactions。\n"
            "5. 质疑、反驳、打断、隐瞒、让步必须来自 agent_reactions、group_decisions、private_tendency_triggers、relationship_updates、interaction_events。\n"
            "6. 如果结构化输入里没有对应来源，不得自行制造冲突、怀疑链或关系变化。\n"
            "7. 不要把系统字段名、ID 或后台术语写进正文。\n"
            "8. Do not add plot-level facts, clues, rules, objects, routes, locations, or relationship changes beyond writer_authorization and structured upstream context.\n"
        )

    def _build_narrative_user_prompt(self, plan: ChapterPlan, allowed_entities: Dict[str, List[str]]) -> str:
        lines: List[str] = []
        structured_context = self._build_structured_writer_context(
            [event for beat in plan.beats for event in beat.events]
        )

        if self.story_anchors:
            lines.append("[Story anchors]")
            for key, value in self.story_anchors.items():
                if value:
                    lines.append(f"- {key}: {value}")
            lines.append("")

        bible = self.world.bible
        lines.append("[World]")
        lines.append(f"- world_id: {getattr(bible, 'world_id', '')}")
        if getattr(bible, "genre", ""):
            lines.append(f"- genre: {bible.genre}")
        if getattr(bible, "era", ""):
            lines.append(f"- era: {bible.era}")
        if getattr(bible, "tone", ""):
            lines.append(f"- tone: {bible.tone}")
        if getattr(bible, "rules", None):
            lines.append("- rules:")
            for rule in bible.rules:
                lines.append(f"  - {rule}")
        if getattr(bible, "themes", None):
            lines.append(f"- themes: {', '.join(bible.themes)}")
        lines.append("")

        lines.append("[Characters]")
        pov_id = plan.pov
        for char in self.world.characters.characters:
            tag = " (POV)" if char.id == pov_id else ""
            lines.append(f"- {char.name} (id={char.id}, role={char.role}){tag}")
            traits = char.personality.get("traits") if isinstance(char.personality, dict) else None
            if traits:
                lines.append(f"  - traits: {', '.join(traits) if isinstance(traits, list) else traits}")
            background = getattr(char, "background", None) or (
                char.personality.get("background") if isinstance(char.personality, dict) else None
            )
            if background:
                lines.append(f"  - background: {background}")
            if isinstance(char.goals, dict):
                short_term = char.goals.get("short_term")
                long_term = char.goals.get("long_term")
                if short_term:
                    lines.append(f"  - short_term_goal: {short_term}")
                if long_term:
                    lines.append(f"  - long_term_goal: {long_term}")
            if char.fears:
                lines.append(f"  - fears: {', '.join(char.fears)}")
        lines.append("")

        if self.world.map.locations:
            lines.append("[Locations]")
            for loc in self.world.map.locations[:15]:
                desc = (loc.public_description or "").strip()
                lines.append(f"- {loc.name} (id={loc.id}): {desc}")
            lines.append("")

        quality_controls = self._quality_controls_dict()
        if quality_controls:
            lines.append("[Quality controls]")
            lines.append(json.dumps(quality_controls, ensure_ascii=False, indent=2))
            lines.append("")

        reveal_budget = self._reveal_budget_dict()
        if reveal_budget:
            lines.append("[Reveal budget]")
            lines.append(json.dumps(reveal_budget, ensure_ascii=False, indent=2))
            lines.append("")

        chapter_brief = self._chapter_brief_dict()
        if chapter_brief:
            lines.append("[Chapter brief]")
            lines.append(json.dumps(chapter_brief, ensure_ascii=False, indent=2))
            lines.append("")

        scene_plan = self._scene_plan_dict()
        if scene_plan:
            lines.append("[Scene plan]")
            lines.append(json.dumps(scene_plan, ensure_ascii=False, indent=2))
            lines.append("")

        lines.append("[Chapter plan]")
        lines.append(f"- title: {plan.chapter_title}")
        lines.append(f"- pov: {plan.pov}")
        lines.append(f"- goal: {plan.chapter_goal}")
        lines.append(f"- emotional_curve: {' -> '.join(plan.emotional_curve)}")
        lines.append("")

        if self.safe_context:
            lines.append("[POV-safe facts]")
            lines.append(f"allowed_facts: {json.dumps(self.safe_context.get('allowed_facts') or [], ensure_ascii=False)}")
            lines.append(f"suspected_facts: {json.dumps(self.safe_context.get('suspected_facts') or [], ensure_ascii=False)}")
            lines.append(f"forbidden_fact_labels: {json.dumps(self.safe_context.get('forbidden_fact_labels') or [], ensure_ascii=False)}")
            relationships = self.safe_context.get("relationship_state_visible_to_pov") or {}
            if relationships:
                lines.append(f"relationships: {json.dumps(relationships, ensure_ascii=False)}")
            lines.append("")

        lines.append("[Structured upstream context]")
        lines.append(json.dumps(structured_context, ensure_ascii=False, indent=2))
        lines.append("")

        lines.append("[Visible beats]")
        for beat in plan.beats:
            lines.append(f"- {beat.purpose}")
            for event in beat.events:
                lines.append(f"  - {event.event_id}: {event.result}")
        lines.append("")

        if plan.ending_hook_event_id:
            lines.append("[Ending hook event]")
            lines.append(plan.ending_hook_event_id)
            lines.append("")

        lines.append("[Allowed entities]")
        lines.append(f"locations: {', '.join(allowed_entities['locations'][:15])}")
        lines.append(f"objects: {', '.join(allowed_entities['objects'][:20])}")
        lines.append(f"characters: {', '.join(allowed_entities['characters'][:10])}")
        lines.append(f"character_ids_internal_only: {', '.join(allowed_entities.get('character_ids', [])[:10])}")
        lines.append("")

        lines.append("[Writing requirements]")
        lines.append("Write chapter prose only. Do not expose system field names, IDs, or backend structure in the prose.")
        lines.append("Use the scene plan as structure, but do not print scene titles, scene IDs, event IDs, or reveal_budget labels.")
        lines.append("Each scene must have action, sensory detail, and information movement; do not restate events as a log.")
        lines.append("Use only visible facts and allowed entities. Do not reveal forbidden or prevented facts as truth.")
        lines.append("Dialogue and interpersonal conflict must come from the structured upstream context.")
        lines.append("Do not add plot-level facts, clues, rules, objects, routes, locations, or relationship changes that are absent from writer_authorization and structured upstream context.")
        lines.append("End with one concrete sensory or action hook, not a summary.")

        return "\n".join(lines)

    def _preserve_key_causal_events(self, all_plot_events: List[EventLog], filtered_events: List[EventLog]) -> List[EventLog]:
        kept_ids = {event.event_id for event in filtered_events}
        result = list(filtered_events)
        for event in all_plot_events:
            if event.event_id not in kept_ids and ChapterCausalChainBuilder.should_force_keep(event):
                result.append(event)
                kept_ids.add(event.event_id)
        order = {event.event_id: index for index, event in enumerate(all_plot_events)}
        result.sort(key=lambda event: order.get(event.event_id, len(order)))
        return result

    def _build_structured_writer_context(self, plot_events: List[EventLog]) -> Dict[str, Any]:
        event_map: Dict[str, Dict[str, Any]] = {}
        agent_reactions: List[Dict[str, Any]] = []
        group_decisions: List[Dict[str, Any]] = []
        private_tendency_triggers: List[Dict[str, Any]] = []
        relationship_updates: List[Dict[str, Any]] = []
        interaction_events: List[Dict[str, Any]] = []

        for event in plot_events:
            source = event.source_interaction or {}
            mapped = {
                "event_id": event.event_id,
                "interaction_id": event.interaction_id,
                "agent_reaction_summaries": [],
                "group_decision_summaries": [],
                "private_tendency_summaries": [],
                "relationship_update_summaries": [],
                "interaction_event_summaries": [],
            }

            for reaction in source.get("agent_reactions") or []:
                item = {
                    "event_id": event.event_id,
                    "interaction_id": event.interaction_id,
                    "reaction_id": reaction.get("reaction_id"),
                    "agent_id": reaction.get("agent_id"),
                    "reaction_type": reaction.get("reaction_type"),
                    "target_agent": reaction.get("target_agent"),
                    "spoken_text": reaction.get("spoken_text"),
                    "reasoning": reaction.get("reasoning"),
                    "will_express": reaction.get("will_express", True),
                }
                item["summary"] = self._reaction_summary_text(item)
                mapped["agent_reaction_summaries"].append(item["summary"])
                agent_reactions.append(item)

            decision = source.get("group_decision")
            if decision:
                decision_item = dict(decision)
                decision_item["event_id"] = event.event_id
                decision_item["interaction_id"] = event.interaction_id
                decision_item["summary"] = self._group_decision_summary_text(decision_item)
                mapped["group_decision_summaries"].append(decision_item["summary"])
                group_decisions.append(decision_item)

            for trigger in source.get("private_tendency_triggers") or []:
                item = {
                    "event_id": event.event_id,
                    "interaction_id": event.interaction_id,
                    "trigger_id": trigger.get("trigger_id"),
                    "agent_id": trigger.get("agent_id"),
                    "trigger_type": trigger.get("trigger_type"),
                    "resulting_bias": trigger.get("resulting_bias"),
                }
                item["summary"] = self._private_tendency_summary_text(item)
                mapped["private_tendency_summaries"].append(item["summary"])
                private_tendency_triggers.append(item)

            for update in source.get("relationship_updates") or []:
                item = {
                    "event_id": event.event_id,
                    "interaction_id": event.interaction_id,
                    "impact_id": update.get("impact_id"),
                    "source_agent": update.get("source_agent"),
                    "target_agent": update.get("target_agent"),
                    "impact_type": update.get("impact_type"),
                    "delta_value": update.get("delta_value"),
                    "cause": update.get("cause"),
                }
                item["summary"] = self._relationship_summary_text(item)
                mapped["relationship_update_summaries"].append(item["summary"])
                relationship_updates.append(item)

            for interaction_event in source.get("interaction_events") or []:
                item = {
                    "event_id": event.event_id,
                    "interaction_id": event.interaction_id,
                    "interaction_event_id": interaction_event.get("event_id"),
                    "event_type": interaction_event.get("event_type"),
                    "summary": str(interaction_event.get("summary") or ""),
                }
                mapped["interaction_event_summaries"].append(item["summary"])
                interaction_events.append(item)

            event_map[event.event_id] = mapped

        counts = {
            "agent_reaction_count": len(agent_reactions),
            "group_decision_count": len(group_decisions),
            "private_tendency_trigger_count": len(private_tendency_triggers),
            "relationship_update_count": len(relationship_updates),
            "interaction_event_count": len(interaction_events),
        }
        causal_context = ChapterCausalChainBuilder().build(plot_events, self.state)
        return {
            "counts": counts,
            "agent_reactions": agent_reactions,
            "group_decisions": group_decisions,
            "private_tendency_triggers": private_tendency_triggers,
            "relationship_updates": relationship_updates,
            "interaction_events": interaction_events,
            "event_map": event_map,
            "writer_authorization": WriterAuthorizationBuilder(self.world).build(
                self.state,
                plot_events,
                self.safe_context,
                self.world.chapter_goal.pov,
            ),
            "key_event_chains": causal_context["key_event_chains"],
            "discussion_results": causal_context["discussion_results"],
            "stance_changes": causal_context["stance_changes"],
            "unresolved_threads": causal_context["unresolved_threads"],
        }

    def _quality_controls_dict(self) -> Dict[str, Any]:
        if not self.quality_controls:
            return {}
        if hasattr(self.quality_controls, "model_dump"):
            return self.quality_controls.model_dump()
        if isinstance(self.quality_controls, dict):
            return self.quality_controls
        return {}

    def _reveal_budget_dict(self) -> Dict[str, Any]:
        if not self.reveal_budget:
            return {}
        if hasattr(self.reveal_budget, "model_dump"):
            return self.reveal_budget.model_dump()
        if isinstance(self.reveal_budget, dict):
            return self.reveal_budget
        return {}

    def _scene_plan_dict(self) -> Dict[str, Any]:
        if not self.scene_plan:
            return {}
        if hasattr(self.scene_plan, "model_dump"):
            return self.scene_plan.model_dump()
        if isinstance(self.scene_plan, dict):
            return self.scene_plan
        return {}

    def _chapter_brief_dict(self) -> Dict[str, Any]:
        if not self.chapter_brief:
            return {}
        if hasattr(self.chapter_brief, "model_dump"):
            return self.chapter_brief.model_dump()
        if isinstance(self.chapter_brief, dict):
            return self.chapter_brief
        return {}

    def _load_chapter_plan_dict(self) -> Dict[str, Any]:
        try:
            with open(self.sim_dir / "chapter_plan.json", "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _write_chapter_debug_report(
        self,
        plot_events: List[EventLog],
        structured_context: Dict[str, Any],
        draft: str,
    ) -> None:
        traceability: List[Dict[str, Any]] = []
        for event in plot_events:
            source = structured_context["event_map"].get(event.event_id, {})
            structured_sources = {
                "agent_reactions": source.get("agent_reaction_summaries", []),
                "group_decisions": source.get("group_decision_summaries", []),
                "private_tendency_triggers": source.get("private_tendency_summaries", []),
                "relationship_updates": source.get("relationship_update_summaries", []),
                "interaction_events": source.get("interaction_event_summaries", []),
            }
            if any(structured_sources.values()):
                traceability.append(
                    {
                        "event_id": event.event_id,
                        "event_result": event.result,
                        "structured_sources": structured_sources,
                    }
                )

        report = {
            "counts": structured_context["counts"],
            "writer_input_contract_enforced": True,
            "quality_controls": self._quality_controls_dict(),
            "reveal_budget": self._reveal_budget_dict(),
            "chapter_brief": self._chapter_brief_dict(),
            "scene_plan": self._scene_plan_dict(),
            "traceability": traceability,
            "draft_preview": draft[:1200],
        }
        with open(self.sim_dir / "chapter_debug.json", "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

    @staticmethod
    def _reaction_summary_text(item: Dict[str, Any]) -> str:
        return (
            f"{item.get('agent_id')} expressed {item.get('reaction_type')} toward "
            f"{item.get('target_agent') or 'the group'} because "
            f"{item.get('reasoning') or item.get('spoken_text') or 'of the situation'}."
        )

    @staticmethod
    def _group_decision_summary_text(item: Dict[str, Any]) -> str:
        return (
            f"Before acting, the group made a {item.get('decision_type') or 'group'} decision "
            f"about {item.get('topic') or 'the proposal'}."
        )

    @staticmethod
    def _private_tendency_summary_text(item: Dict[str, Any]) -> str:
        return (
            f"{item.get('agent_id')} showed a {item.get('trigger_type')} tendency, biasing behavior toward "
            f"{item.get('resulting_bias') or 'self-protection'}."
        )

    @staticmethod
    def _relationship_summary_text(item: Dict[str, Any]) -> str:
        return (
            f"The interaction shifted {item.get('source_agent')} -> {item.get('target_agent')} as "
            f"{item.get('impact_type')} because {item.get('cause') or 'the exchange'}."
        )

    # ==========================================
    # 瑙勫垯鍩鸿崏绋匡紙鏃?LLM 鏃朵娇鐢級
    # ==========================================

    def _rule_based_draft(self, plan: ChapterPlan, structured_context: Optional[Dict[str, Any]] = None) -> str:
        """Generate a fallback chapter draft strictly from structured upstream inputs."""
        lines: List[str] = []
        lines.append(f"# {plan.chapter_title}")
        lines.append("")

        event_map = (structured_context or {}).get("event_map", {})
        for beat in plan.beats:
            for e in beat.events:
                lines.append(f"{e.result}")
                source = event_map.get(e.event_id, {})
                for summary in source.get("agent_reaction_summaries", [])[:2]:
                    lines.append(summary)
                for summary in source.get("group_decision_summaries", [])[:1]:
                    lines.append(summary)
                for summary in source.get("private_tendency_summaries", [])[:1]:
                    lines.append(summary)
                for summary in source.get("relationship_update_summaries", [])[:2]:
                    lines.append(summary)
            lines.append("")

        if plan.ending_hook_event_id:
            lines.append("")
            lines.append("---")
            lines.append("")
            lines.append("(chapter continues)")

        return "\n".join(lines)
