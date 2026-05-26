from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.llm_client import OpenAICompatibleClient
from app.models.event import EventLog
from app.models.narrative import ChapterBeat, ChapterPlan
from app.models.state import WorldState
from app.models.world import WorldConfig
from app.services.narrative_context_builder import NarrativeContextBuilder
from app.services.consistency_service import ConsistencyService
from app.services.event_log_service import EventLogService
from app.services.trace_service import LLMTrace, TraceService


class NarrativeService:
    """
    V2.3 鍙欎簨鐢熸垚鏈嶅姟
    涓ゆ寮忥細瑙勫垯鐢熸垚 chapter_plan 鈫?LLM 鏀瑰啓姝ｆ枃
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
    ):
        self.world = world
        self.sim_dir = sim_dir
        self.llm_client = llm_client
        self.trace_service = trace_service
        self.force_rule_based = force_rule_based
        self.enable_consistency_check = enable_consistency_check
        self.event_svc = EventLogService()
        self.consistency_svc = ConsistencyService(world, sim_dir, llm_client, trace_service)
        self.state = state or self._load_state()
        self.safe_context = self._build_safe_context()
        # 鑷姩鍔犺浇 writer_story_anchors.json锛堢敱 StoryBootstrapper 鍐欏叆锛?
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

        # P1锛坧lan 搂19锛夛細VisibleEventFilter 鈥?鍙啓 POV 鑳芥劅鐭ョ殑浜嬩欢缁?LLM
        # 闃叉 hidden_actor 鐨勭湡瀹炶鍔ㄧ洿鎺ュ嚭鐜板湪姝ｆ枃涓?
        from app.services.visible_event_filter import VisibleEventFilter
        ve_filter = VisibleEventFilter()
        pov_id = self.world.chapter_goal.pov
        filtered_plot_events = ve_filter.filter_for_narrative(plot_events, pov_id)
        # 杩囨护鎺夌洿鎺ユ毚闇?hidden_actor 韬唤鐨勬晱鎰熷唴瀹?
        filtered_plot_events = [e for e in filtered_plot_events if not ve_filter.has_sensitive_content(e)]
        structured_context = self._build_structured_writer_context(filtered_plot_events)

        # 2. 瑙勫垯鐢熸垚 chapter_plan
        plan = self._build_chapter_plan(filtered_plot_events)
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
                "writer_structured_context": structured_context,
            }, f, ensure_ascii=False, indent=2)

        # 3. LLM 鐢熸垚姝ｆ枃锛堝鏋滄湁 llm_client锛?
        draft = ""
        if self.llm_client and not self.force_rule_based:
            draft = self._llm_write_chapter(plan)
            with open(self.sim_dir / "chapter_draft.md", "w", encoding="utf-8") as f:
                f.write(draft)

            # 4. 涓€鑷存€ф鏌?+ revise once
            if self.enable_consistency_check:
                report = self.consistency_svc.check_consistency(draft, plan, filtered_plot_events)
                if not report["passed"] and report.get("violations"):
                    draft = self.consistency_svc.revise_once(draft, plan, filtered_plot_events)
                    # 閲嶆柊淇濆瓨淇鍚庣殑鐗堟湰
                    with open(self.sim_dir / "chapter_draft.md", "w", encoding="utf-8") as f:
                        f.write(draft)
            else:
                report = {"passed": True, "mode": "disabled", "violations": []}
                with open(self.sim_dir / "consistency_report.json", "w", encoding="utf-8") as f:
                    json.dump(report, f, ensure_ascii=False, indent=2)
        else:
            # 鏃?LLM锛氱敤瑙勫垯鐢熸垚绠€鍗曡崏绋?
            draft = self._rule_based_draft(plan, structured_context)
            with open(self.sim_dir / "chapter_draft.md", "w", encoding="utf-8") as f:
                f.write(draft)
            report = {"passed": True, "mode": "rule_based", "violations": []}
            with open(self.sim_dir / "consistency_report.json", "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)

        self._write_chapter_debug_report(filtered_plot_events, structured_context, draft)

        return {
            "plan": plan,
            "draft": draft,
            "consistency_report": report,
        }

    # ==========================================
    # 瑙勫垯鐢熸垚 chapter_plan
    # ==========================================

    def _build_chapter_plan(self, plot_events: List[EventLog]) -> ChapterPlan:
        """浠?plot_events 鐢熸垚绔犺妭澶х翰

        鏍稿績鍘熷垯锛氫竴涓珷鑺傚彧璁叉竻妤氫竴浠朵簨锛屼笉瑕佸爢鐮岀嚎绱?
        """
        plot_events.sort(key=lambda e: e.event_id)

        # 鎯呮劅鏇茬嚎锛氭洿澶?鍠樻伅"闃舵锛屼笉瑕佸叏绋嬬揣寮?
        emotional_curve = self._build_emotional_curve(plot_events)

        # beats 鍒嗙粍锛氬悎骞跺瘑闆嗕簨浠讹紝姣忎釜 鐗囨 鍙噴鏀?1-2 涓牳蹇冨紓甯?
        beats = self._build_beats(plot_events)

        # ending hook锛氬彧閫変竴涓湁鎮康鐨勪簨浠讹紝涓嶈鎶婇珮娼叏鏀惧湪缁撳熬
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
        """鏍规嵁浜嬩欢鎴栦笘鐣岄厤缃敓鎴愰粯璁ょ珷鑺傛爣棰?""
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

        return "绗竴绔? if self.world.bible.era == "鍙や唬" else "搴忕珷"

    def _select_ending_hook(self, beats: List[ChapterBeat], plot_events: List[EventLog]) -> Optional[str]:
        """閫夋嫨缁撳熬閽╁瓙锛氶€変竴涓腑绛夋偓蹇电殑浜嬩欢锛屼笉瑕侀€夋渶鎭愭€栫殑閭ｄ釜"""
        if not plot_events:
            return None
        # 閫夊€掓暟绗簩涓垨绗笁涓簨浠讹紝鐣欎笅浣欓煹
        sorted_events = sorted(plot_events, key=lambda e: e.event_id)
        if len(sorted_events) >= 3:
            return sorted_events[-2].event_id
        return sorted_events[-1].event_id

    def _build_emotional_curve(self, events: List[EventLog]) -> List[str]:
        """鏍规嵁 plot_value 鐢熸垚鎯呮劅鏇茬嚎

        鏍稿績鍘熷垯锛氱揣寮犱笌鍠樻伅浜ゆ浛锛屼笉瑕佸叏绋嬮珮鑳?
        """
        curve = []
        for e in events:
            pv = e.plot_value
            tension = (pv.conflict + pv.mystery + pv.danger) / 3
            if pv.danger > 7:
                curve.append("鍗遍櫓")
            elif pv.conflict > 6:
                curve.append("绱у紶")
            elif pv.mystery > 5:
                curve.append("涓嶅畨")
            elif tension > 4:
                curve.append("鍘嬭揩")
            elif pv.progress > 5:
                curve.append("鎺ㄨ繘")
            else:
                curve.append("瑙傚療")
        # 鍘婚噸淇濈暀椤哄簭锛屼絾寮哄埗鎻掑叆鍠樻伅闃舵
        unique = []
        seen = set()
        for i, c in enumerate(curve):
            if c not in seen:
                unique.append(c)
                seen.add(c)
            # 姣忎袱涓揣寮犻樁娈靛悗鎻掑叆涓€涓?鍠樻伅"
            if c in ("绱у紶", "涓嶅畨", "鍗遍櫓") and i < len(curve) - 1:
                unique.append("鍠樻伅")
                seen.add("鍠樻伅")
        # 纭繚鏈夎捣鎵胯浆鍚?
        if len(unique) < 4:
            unique = ["瑙傚療", "涓嶅畨", "绱у紶", "鍠樻伅", "鎮康"][:5]
        return unique

    def _build_beats(self, events: List[EventLog]) -> List[ChapterBeat]:
        """鎸夊湴鐐瑰垎缁勭敓鎴?beats

        鏍稿績鍘熷垯锛氭瘡涓?鐗囨 鍙噴鏀?1-2 涓牳蹇冨紓甯革紝涓嶈鍫嗙爩
        澶氫釜鐩镐技寮傚父鍚堝苟涓轰竴涓紝鍙繚鐣欐渶鏈夋偓蹇电殑閭ｄ釜
        """
        beats: List[ChapterBeat] = []
        beats_by_loc: Dict[str, List[EventLog]] = {}

        for e in events:
            loc_id = e.location_id or "unknown"
            if loc_id not in beats_by_loc:
                beats_by_loc[loc_id] = []
            beats_by_loc[loc_id].append(e)

        for idx, (loc_id, loc_events) in enumerate(beats_by_loc.items()):
            # 鏍稿績寮傚父鍙繚鐣?1-2 涓細浼樺厛淇濈暀 mystery/conflict 楂樼殑
            sorted_events = sorted(
                loc_events,
                key=lambda e: e.plot_value.mystery + e.plot_value.conflict + e.plot_value.danger,
                reverse=True
            )
            # 鏈€澶氫繚鐣?2 涓牳蹇冧簨浠?
            core_events = sorted_events[:2]
            # 鍓╀綑浜嬩欢濡傛灉澶锛屽悎骞舵垚涓€涓?瑙傚療"绫讳簨浠?
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
        """鏍规嵁浜嬩欢绫诲瀷鍜?plot_value 鎺ㄦ柇閫氱敤鑺傚鏍囩銆?""
        if not events:
            return "瑙傚療鍙樺寲"

        total_mystery = sum(e.plot_value.mystery for e in events)
        total_conflict = sum(e.plot_value.conflict for e in events)
        total_danger = sum(e.plot_value.danger for e in events)
        total_progress = sum(e.plot_value.progress for e in events)
        event_types = {e.event_type for e in events}

        if total_danger > 8:
            return "鍗遍櫓閫艰繎"
        if total_conflict > 8 or "interaction" in event_types:
            return "鍏崇郴鏂藉帇"
        if total_mystery > 8:
            return "寮傚父娴幇"
        if total_progress > 6:
            return "绾跨储鎺ㄨ繘"
        return "瑙傚療鍙樺寲"

    # ==========================================
    # LLM 姝ｆ枃鏀瑰啓
    # ==========================================

    def _llm_write_chapter(self, plan: ChapterPlan) -> str:
        """鍩轰簬 chapter_plan 鍜屼簨浠讹紝鐢?LLM 鍐欐鏂囥€傚け璐ユ椂璁板綍璇︾粏閿欒鍐嶅洖閫€銆?""
        if not self.llm_client:
            return self._rule_based_draft(plan)

        try:
            # 鏋勫缓 allowed_entities
            allowed_entities = self._build_allowed_entities(plan)

            # 鏋勫缓 prompt
            system = self._build_narrative_system_prompt()
            user = self._build_narrative_user_prompt(plan, allowed_entities)

            # 璋冪敤 LLM锛坱emperature=0.7锛屽鍔犳枃瀛︽€э級
            # 娉ㄦ剰锛氬皬璇寸敓鎴愮敤鏅€氭枃鏈ā寮忥紝涓嶈鐢?JSON 妯″紡锛?
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
            # ========== 璁板綍璇︾粏閿欒鏃ュ織 ==========
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

            # 淇濆瓨鍒伴敊璇棩蹇楁枃浠?
            error_file = self.sim_dir / "llm_error.json"
            import json
            with open(error_file, "w", encoding="utf-8") as f:
                json.dump(error_log, f, ensure_ascii=False, indent=2)

            # 鎺у埗鍙拌緭鍑鸿缁嗛敊璇?
            print("\n" + "="*80)
            print("鉂?LLM 灏忚鐢熸垚璋冪敤澶辫触锛?)
            print("="*80)
            print(f"閿欒绫诲瀷: {type(e).__name__}")
            print(f"閿欒淇℃伅: {e}")
            print(f"閿欒鏃ュ織宸蹭繚瀛樺埌: {error_file}")
            print("="*80 + "\n")
            # =========================================

            # 鍥為€€鍒拌鍒欑敓鎴愭ā寮?
            print("馃攧  鍥為€€鍒拌鍒欑敓鎴愭ā寮?..")
            return self._rule_based_draft(plan)

    def _build_allowed_entities(self, plan: ChapterPlan) -> Dict[str, List[str]]:
        """鏋勫缓鍏佽鍑虹幇鐨勫疄浣撶櫧鍚嶅崟"""
        locations = set()
        objects = set()
        characters = set()
        facts = set()

        # 浠庝笘鐣岄厤缃腑鎻愬彇
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
            # 绠€鍗曟敹闆嗭細鎻愬彇绾跨储涓殑瀹炰綋锛堢畝鍗曞垎璇嶏級
            content = clue.content
            # 绮楃暐鎻愬彇锛氫互鍒嗛殧绗﹀垎鍓?
            for word in content.replace("锛?, " ").replace("銆?, " ").replace("銆?, " ").split():
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
            "浣犳槸绔犺妭 Writer銆備綘鐨勮亴璐ｄ笉鏄垱閫犲啿绐侊紝鑰屾槸鎶婁笂娓哥粨鏋勫寲缁撴灉鏂囧鍖栥€俓n"
            "1. 鍙兘鍐?POV 鍙銆佸彲闂汇€佸彲瑙︺€佸彲鍥炲繂銆佸彲鍚堢悊鎬€鐤戠殑鍐呭銆俓n"
            "2. allowed_facts 鍙互鍐欐垚纭畾浜嬪疄锛泂uspected_facts 鍙兘鍐欐垚鎬€鐤戞垨寮傚父銆俓n"
            "3. forbidden_fact_labels 鍜?prevented_facts 涓嶅緱鍐欐垚鐪熺浉銆俓n"
            "4. 鍙拌瘝鍙兘鏉ヨ嚜 spoken_segments銆乮nterruption_results銆乸ost_interruption_reactions銆俓n"
            "5. 璋佽川鐤戙€佽皝鍙嶅銆佽皝鎵撴柇銆佽皝闅愮瀿銆佽皝璁╂锛屽繀椤绘潵鑷?agent_reactions銆乬roup_decisions銆乸rivate_tendency_triggers銆乺elationship_updates銆乮nteraction_events銆俓n"
            "6. 濡傛灉缁撴瀯鍖栬緭鍏ラ噷娌℃湁瀵瑰簲鏉ユ簮锛屼笉寰楄嚜琛屽埗閫犲啿绐併€佹€€鐤戦摼鎴栧叧绯诲彉鍖栥€俓n"
            "7. 涓嶈鎶婄郴缁熷瓧娈靛悕鎴栧悗鍙版湳璇啓杩涙鏂囥€俓n"
        )
        return (
            "浣犳槸涓€浣嶅皬璇翠綔鑰咃紝璇锋妸缁欏畾绱犳潗鍐欐垚绗笁浜虹О鏈夐檺瑙嗚鐨勭珷鑺傛鏂囥€俓n"
            "鍙娇鐢ㄧ敤鎴锋秷鎭噷缁欏嚭鐨勪笘鐣屻€佽鑹层€佸湴鐐广€佺墿浠躲€佸彲瑙佷簨浠跺拰瀹夊叏浜嬪疄锛涗笉瑕佸鐢ㄥ叾瀹冩晠浜嬫ā鏉裤€俓n"
            "\n"
            "銆愪簨瀹炶竟鐣屻€慭n"
            "1. 鍙啓 POV 鑳界湅瑙併€佸惉瑙併€佽Е纰般€佸洖蹇嗘垨鍚堢悊鎬€鐤戠殑鍐呭銆俓n"
            "2. allowed_facts 鍙啓鎴愮‘瀹氫簨瀹烇紱suspected_facts 鍙兘鍐欐垚鎬€鐤戙€佽繜鐤戙€佺煕鐩惧姩浣滄垨寮傚父鍙嶅簲銆俓n"
            "3. forbidden_fact_labels 鍜?prevented_facts 涓嶅緱琚‘璁わ紝涓嶅緱鍐欐垚鏃佺櫧鐪熺浉鎴栧凡鍑哄彛鍙拌瘝銆俓n"
            "4. 鍙拌瘝鍙兘鏉ヨ嚜 spoken_segments銆乮nterruption_results銆乸ost_interruption_reactions锛沺revented_segments / withheld_segments 涓嶈兘鍐欐垚宸茶鍑哄彛銆俓n"
            "\n"
            "銆愬疄浣撹竟鐣屻€慭n"
            "1. 姝ｆ枃涓殑瑙掕壊鍚嶃€佸湴鐐瑰悕銆佺墿浠跺悕鍙兘鏉ヨ嚜鐧藉悕鍗曘€俓n"
            "2. 绂佹鍑┖澧炲姞涓嶅湪鐧藉悕鍗曚腑鐨勪笓鏈夊悕銆佹満鏋勫悕銆佷翰灞炲叧绯汇€佽繃寰€缁忓巻鎴栦笘鐣岃鍒欍€俓n"
            "3. 瑙掕壊 ID 鍙綔涓哄唴閮ㄧ害鏉燂紝涓嶈鍐欒繘姝ｆ枃銆俓n"
            "\n"
            "銆愬彊浜嬫柟寮忋€慭n"
            "1. 涓嶈鍦ㄦ鏂囦腑澶嶈堪鎻愮ず璇嶇粨鏋勩€佺礌鏉愭竻鍗曘€佺郴缁熻瘝鎴栧悗鍙拌瘝銆俓n"
            "2. 姝ｆ枃涓嶅緱鍑虹幇锛氫换鍔°€佺珷鑺傜洰鏍囥€佺墖娈点€佷簨浠舵棩蹇椼€乼ick銆丄gent銆佹矙鐩樸€佺煩闃点€佺郴缁熴€佸悗鍙般€佸墽鎯呭姬銆俓n"
            "3. 涓栫晫绂佸繉銆佷紶闂诲拰鐜绾︽潫鍙兘閫氳繃琛屼负銆佽繜鐤戙€佸悗鏋溿€佺墿浠剁粏鑺傘€佹梺浜轰紶闂绘垨韬綋鍙嶅簲浣撶幇銆俓n"
            "4. POV 瑙掕壊鐨勯瀵兼潈蹇呴』鐢辫瘉鎹€佸叧绯讳俊浠汇€佸嵄闄╁帇鍔涘拰褰撳墠鐘舵€侀€愭鑾峰緱锛涗綆璇佹嵁銆佷綆淇′换銆佷綆鍘嬪姏鏃朵笉瑕佽 POV 蹇€熸帉鎺у叏灞€銆俓n"
            "5. 鐢ㄥ叿浣撴劅瀹樺拰鍔ㄤ綔鍒堕€犳皼鍥达紝閬垮厤鎬荤粨寮忔彮闇层€俓n"
        )

    def _build_narrative_user_prompt(self, plan: ChapterPlan, allowed_entities: Dict[str, List[str]]) -> str:
        lines: List[str] = []
        structured_context = self._build_structured_writer_context(
            [event for beat in plan.beats for event in beat.events]
        )

        # ====== Bootstrap 娉ㄥ叆锛氬啓浣滈敋鐐癸紙鏈€楂樹紭鍏堢骇锛屾斁鍦ㄦ渶鍓嶏級 ======
        if self.story_anchors:
            a = self.story_anchors
            lines.append("銆愮礌鏉愯竟鐣屼笌娼滃湪寮犲姏锛堜笉寰楀師鏍峰啓鍏ユ鏂囷級銆?)
            if a.get("title"):
                lines.append(f"- 浣滃搧鍚嶏細{a['title']}")
            if a.get("protagonist_name"):
                lines.append(f"- 涓昏鍚嶏細{a['protagonist_name']}锛堢珷鑺備腑涓昏鍚嶅瓧蹇呴』鏄繖涓級")
            if a.get("protagonist_goal"):
                lines.append(f"- 涓昏鐩爣锛歿a['protagonist_goal']}")
            if a.get("personal_stakes"):
                lines.append(f"- 绉佷汉鍔ㄦ満锛歿a['personal_stakes']}")
            if a.get("current_chapter_goal"):
                lines.append(f"- 褰撳墠鍐呭湪鍘嬪姏锛歿a['current_chapter_goal']}")
            if a.get("main_question"):
                lines.append(f"- 涓荤嚎闂锛歿a['main_question']}")
            if a.get("required_emotional_鐗囨"):
                lines.append(f"- 蹇呴』鍑虹幇鐨勬儏鎰熻妭鎷嶏細{a['required_emotional_鐗囨']}")
            if a.get("protagonist_private_hook"):
                lines.append("- 涓昏绉佷汉閽╁瓙锛氫粎浣滀负 POV 鍐呭湪寮犲姏澶勭悊锛屼笉鐩存帴鍐欐垚鏈毚闇蹭簨瀹?)
            if a.get("required_interpersonal_conflict"):
                lines.append(f"- 蹇呴』鍑虹幇鐨勪汉闄呭啿绐侊細{a['required_interpersonal_conflict']}")
            if a.get("core_motif"):
                lines.append(f"- 鏍稿績姣嶉锛歿a['core_motif']}锛屾湰绔犺鐢ㄩ噸澶嶆剰璞°€佽鑹查€夋嫨鎴栫幆澧冨彉鍖栬瀹冩垚涓烘偓蹇碉紝鑰屼笉鏄彛鍙?)
            if a.get("concrete_ending_hook"):
                lines.append(f"- 缁撳熬蹇呴』钀藉湪杩欎釜鍏蜂綋寮傚父涓婏細{a['concrete_ending_hook']}")
            if a.get("world_tone"):
                lines.append(f"- 鏁翠綋鍩鸿皟锛歿a['world_tone']}")
            forbidden = a.get("forbidden_generic_phrases") or []
            if forbidden:
                lines.append(f"- 绂佹浣跨敤鐨勬硾鍖栬〃杈撅細{', '.join(forbidden)}")
            forbidden_summary = a.get("forbidden_summary_sentences") or []
            if forbidden_summary:
                lines.append(f"- 绂佹鐢ㄤ綔缁撳熬鎴栨钀芥敹鏉熺殑鎬荤粨鍙ワ細{', '.join(forbidden_summary)}")
            lines.append("")

        bible = self.world.bible
        lines.append("銆愪笘鐣岀蹇?/ 浼犻椈 / 鐜绾︽潫銆?)
        lines.append(f"- 涓栫晫鍚嶏細{getattr(bible, 'world_id', '')}")
        if getattr(bible, "genre", ""):
            lines.append(f"- 棰樻潗锛歿bible.genre}")
        if getattr(bible, "era", ""):
            lines.append(f"- 鏃朵唬锛歿bible.era}")
        if getattr(bible, "tone", ""):
            lines.append(f"- 鍩鸿皟锛歿bible.tone}")
        if getattr(bible, "rules", None):
            lines.append("- 绂佸繉/浼犻椈/鐜绾︽潫锛堝彧鑳介€氳繃琛屼负銆佽繜鐤戙€佸悗鏋溿€佷紶闂绘垨鐗╀欢缁嗚妭浣撶幇锛夛細")
            for r in bible.rules:
                lines.append(f"  路 {r}")
        if getattr(bible, "themes", None):
            lines.append(f"- 涓婚锛歿', '.join(bible.themes)}")
        lines.append("")

        # 瑙掕壊妗ｆ锛堥噸鐐圭獊鍑?POV 瑙掕壊锛?
        lines.append("銆愯鑹叉。妗堛€?)
        pov_id = plan.pov
        for char in self.world.characters.characters:
            tag = " 鈫?POV 涓昏" if char.id == pov_id else ""
            lines.append(f"- {char.name}锛坕d={char.id}, 瑙掕壊={char.role}锛墈tag}")
            traits = char.personality.get("traits") if isinstance(char.personality, dict) else None
            if traits:
                lines.append(f"  路 鎬ф牸锛歿', '.join(traits) if isinstance(traits, list) else traits}")
            background = getattr(char, "background", None) or (
                char.personality.get("background") if isinstance(char.personality, dict) else None
            )
            if background:
                lines.append(f"  路 鑳屾櫙锛歿background}")
            if isinstance(char.goals, dict):
                short_term = char.goals.get("short_term")
                long_term = char.goals.get("long_term")
                if short_term:
                    lines.append(f"  路 鐭湡鐩爣锛歿short_term}")
                if long_term:
                    lines.append(f"  路 闀挎湡鐩爣锛歿long_term}")
            if char.fears:
                lines.append(f"  路 鎭愭儳锛歿', '.join(char.fears)}")
            public_motive = getattr(char, "public_motive", "")
            private_motive = getattr(char, "private_motive", "")
            withheld_information = getattr(char, "withheld_information", "")
            suspicious_micro_actions = getattr(char, "suspicious_micro_actions", [])
            private_hook = getattr(char, "private_hook", "")
            emotional_core = getattr(char, "emotional_core", "")
            if public_motive:
                lines.append(f"  路 鍏紑鍔ㄦ満锛歿public_motive}")
            if char.id == pov_id and private_motive:
                lines.append(f"  路 绉佷汉鍔ㄦ満锛歿private_motive}")
            if char.id == pov_id and withheld_information:
                lines.append(f"  路 闅愮瀿淇℃伅锛歿withheld_information}")
            if suspicious_micro_actions:
                actions = suspicious_micro_actions if isinstance(suspicious_micro_actions, list) else [str(suspicious_micro_actions)]
                lines.append(f"  路 鍙枒寰姩浣滐細{'锛?.join(actions)}")
            if char.id == pov_id and private_hook:
                lines.append(f"  路 绉佷汉閽╁瓙锛歿private_hook}")
            if char.id == pov_id and emotional_core:
                lines.append(f"  路 鎯呮劅鏍稿績锛歿emotional_core}")
        lines.append("")

        # 鍦扮偣妗ｆ
        if self.world.map.locations:
            lines.append("銆愬湴鐐规。妗堛€?)
            for loc in self.world.map.locations[:15]:
                desc = (loc.public_description or "").strip()
                lines.append(f"- {loc.name}锛坕d={loc.id}锛夛細{desc}")
            lines.append("")

        lines.append(f"銆愮珷鑺傛爣棰樸€憑plan.chapter_title}")
        lines.append(f"銆怭OV 瑙掕壊銆憑plan.pov}")
        lines.append(f"銆愬彊浜嬭妭濂忋€憑' 鈫?'.join(plan.emotional_curve)}")
        lines.append("")

        lines.append("銆怶riter 杈撳叆濂戠害銆?)
        lines.append("Writer 鍙兘娑堣垂 agent_reactions銆乬roup_decisions銆乸rivate_tendency_triggers銆乺elationship_updates銆乮nteraction_events銆?)
        lines.append("Writer 涓嶈兘鐩存帴鍐冲畾璋佹€€鐤戙€佽皝鍙嶅銆佽皝鎵撴柇銆佽皝闅愮瀿銆佽皝璁╂銆?)
        lines.append("")

        if self.safe_context:
            allowed_facts = self.safe_context.get("allowed_facts") or []
            suspected_facts = self.safe_context.get("suspected_facts") or []
            forbidden_labels = self.safe_context.get("forbidden_fact_labels") or []
            lines.append("銆怭OV 瀹夊叏浜嬪疄涓婁笅鏂囥€?)
            lines.append(f"allowed_facts锛堝彲鍐欐垚纭畾浜嬪疄锛夛細{json.dumps(allowed_facts, ensure_ascii=False)}")
            lines.append(f"suspected_facts锛堝彧鑳藉啓鎴愭€€鐤?寮傚父锛夛細{json.dumps(suspected_facts, ensure_ascii=False)}")
            lines.append(f"forbidden_fact_labels锛堢姝㈠啓鎴愮湡鐩革級锛歿json.dumps(forbidden_labels, ensure_ascii=False)}")
            relationships = self.safe_context.get("relationship_state_visible_to_pov") or {}
            if relationships:
                lines.append("銆愬叧绯绘€佸娍銆?)
                lines.append(json.dumps(relationships, ensure_ascii=False))
            lines.append("")

        lines.append("銆愬唴閮ㄧ礌鏉愯鏄庯紙涓嶅緱澶嶈堪缁撴瀯璇嶏級銆?)
        lines.append("浠ヤ笅鍐呭鍙敤浜庣害鏉熼『搴忓拰姘涘洿锛屼笉瑕佹妸缂栧彿鎴栬鏄庡啓杩涙鏂囷細")
        lines.append("")
        for beat in plan.beats:
            lines.append(f"- {beat.purpose}")
            for e in beat.events:
                lines.append(f"  路 {e.result}")
            lines.append("  路 涔嬪悗鐣欏嚭瑙傚療銆佽繜鐤戞垨韬綋鍙嶅簲鐨勪綑闊?)
        lines.append("")

        if plan.ending_hook_event_id:
            hook_event = next((e for beat in plan.beats for e in beat.events if e.event_id == plan.ending_hook_event_id), None)
            if hook_event:
                lines.append("銆愮粨灏鹃挬瀛愩€?)
                lines.append(f"- {hook_event.result}")
                lines.append("鈫?鍙粰鏆楃ず锛屼笉瑕佹彮绀虹湡鐩?)
                lines.append("")

        lines.append("銆愬厑璁稿嚭鐜扮殑瀹炰綋锛堢櫧鍚嶅崟锛夈€?)
        lines.append(f"鍦扮偣锛歿', '.join(allowed_entities['locations'][:15])}")
        lines.append(f"鐗╁搧锛歿', '.join(allowed_entities['objects'][:20])}")
        lines.append(f"瑙掕壊锛歿', '.join(allowed_entities['characters'][:10])}")
        lines.append(f"瑙掕壊 ID锛堝唴閮ㄧ害鏉燂紝涓嶅緱杩涘叆姝ｆ枃锛夛細{', '.join(allowed_entities.get('character_ids', [])[:10])}")
        lines.append("鈿?涓ョ鍐欏嚭鐧藉悕鍗曚箣澶栫殑浠讳綍涓撴湁鍚嶃€佹満鏋勫悕銆佷翰灞炲叧绯汇€佸湴鐐瑰悕鎴栦笘鐣岃鍒欙紱瑙掕壊 ID 浠呬綔鍐呴儴绾︽潫锛屼笉寰楄繘鍏ユ鏂囥€?)
        lines.append("")

        lines.append("銆愬啓浣滆姹傘€?)
        lines.append("1. 绔犺妭闀垮害锛?000-4000 瀛?)
        lines.append("2. 姣忎釜 鐗囨 鍚庡繀椤绘湁鍠樻伅闃舵锛屼笉瑕佽繛缁噴鏀鹃珮寮哄害浜嬩欢")
        lines.append("3. 蹇冪悊娲诲姩鍗犳瘮锛氫富瑙掔殑鍥炲繂銆佹帹鐞嗐€佺寽娴嬭鏈変竴瀹氱瘒骞?)
        lines.append("4. 鎰熷畼鎻忓啓锛氳瑙夈€佸惉瑙夈€佸梾瑙夈€佽Е瑙夐兘瑕佹湁")
        lines.append("5. 缁嗚妭鍏蜂綋锛屾皼鍥寸敱缁嗚妭鑰岄潪褰㈠璇嶆拺璧?)
        lines.append("6. 缁撳熬閽╁瓙锛氬彧缁欎竴涓叿浣撳紓甯哥墿銆佸０闊虫垨鍔ㄤ綔锛屼笉瑕佺敤鎬荤粨鍙ユ敹鏉?)
        lines.append("7. NPC 瀵硅瘽涓嶈兘鍙В閲婅瀹氾紝蹇呴』鍚屾椂鏆撮湶绔嬪満銆佹亹鎯с€侀殣鐬掓垨绉佷汉鍒╃泭")
        lines.append("8. 姣忎釜鍏抽敭绾跨储鑷冲皯缁戝畾涓€涓汉鐗╁弽搴旀垨鍏崇郴瑁傜紳")
        lines.append("9. 涓ユ牸閬靛惊涓婇潰銆愪笘鐣岀蹇?/ 浼犻椈 / 鐜绾︽潫銆?銆愯鑹叉。妗堛€?銆愮櫧鍚嶅崟銆?)
        lines.append("")
        lines.append("寮€濮嬪啓浣滐細")

        return "\n".join(lines)

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
        return {
            "counts": counts,
            "agent_reactions": agent_reactions,
            "group_decisions": group_decisions,
            "private_tendency_triggers": private_tendency_triggers,
            "relationship_updates": relationship_updates,
            "interaction_events": interaction_events,
            "event_map": event_map,
        }

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
    # 瑙勫垯鍩鸿崏绋匡紙鏃?LLM 鏃朵娇鐢級
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
