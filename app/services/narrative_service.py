from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.llm_client import OpenAICompatibleClient
from app.models.event import EventLog
from app.models.narrative import ChapterBeat, ChapterPlan
from app.models.world import WorldConfig
from app.services.consistency_service import ConsistencyService
from app.services.event_log_service import EventLogService
from app.services.trace_service import LLMTrace, TraceService


class NarrativeService:
    """
    V2.3 叙事生成服务
    两段式：规则生成 chapter_plan → LLM 改写正文
    """

    def __init__(
        self,
        world: WorldConfig,
        sim_dir: Path,
        llm_client: Optional[OpenAICompatibleClient] = None,
        trace_service: Optional[TraceService] = None,
        force_rule_based: bool = False,
        enable_consistency_check: bool = True,
    ):
        self.world = world
        self.sim_dir = sim_dir
        self.llm_client = llm_client
        self.trace_service = trace_service
        self.force_rule_based = force_rule_based
        self.enable_consistency_check = enable_consistency_check
        self.event_svc = EventLogService()
        self.consistency_svc = ConsistencyService(world, sim_dir, llm_client, trace_service)
        # 自动加载 writer_story_anchors.json（由 StoryBootstrapper 写入）
        self.story_anchors: Optional[Dict[str, Any]] = self._load_story_anchors()

    def _load_story_anchors(self) -> Optional[Dict[str, Any]]:
        """从 worlds/<world_id>/writer_story_anchors.json 加载叙事锚点"""
        try:
            # WorldConfig.from_directory 读取时 world_dir 信息没有直接保存，
            # 但 world.world_id 已经存在，通过 sim_dir 上溯到 project_root
            project_root = self.sim_dir.parent.parent  # outputs/sim_xxx -> outputs -> project_root
            anchor_file = project_root / "worlds" / self.world.world_id / "writer_story_anchors.json"
            if anchor_file.exists():
                with open(anchor_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            return None
        return None

    def generate_chapter(self) -> Dict[str, Any]:
        """生成完整章节：plan + draft + consistency report"""
        # 1. 读取事件
        all_events = self.event_svc.read_all(self.sim_dir)
        plot_events = [e for e in all_events if e.event_level == "plot"]

        # P1（plan §19）：VisibleEventFilter — 只写 POV 能感知的事件给 LLM
        # 防止 hidden_actor 的真实行动直接出现在正文中
        from app.services.visible_event_filter import VisibleEventFilter
        ve_filter = VisibleEventFilter()
        pov_id = self.world.chapter_goal.pov
        filtered_plot_events = ve_filter.filter_for_narrative(plot_events, pov_id)
        # 过滤掉直接暴露 hidden_actor 身份的敏感内容
        filtered_plot_events = [e for e in filtered_plot_events if not ve_filter.has_sensitive_content(e)]

        # 2. 规则生成 chapter_plan
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
            }, f, ensure_ascii=False, indent=2)

        # 3. LLM 生成正文（如果有 llm_client）
        draft = ""
        if self.llm_client and not self.force_rule_based:
            draft = self._llm_write_chapter(plan)
            with open(self.sim_dir / "chapter_draft.md", "w", encoding="utf-8") as f:
                f.write(draft)

            # 4. 一致性检查 + revise once
            if self.enable_consistency_check:
                report = self.consistency_svc.check_consistency(draft, plan, plot_events)
                if not report["passed"] and report.get("violations"):
                    draft = self.consistency_svc.revise_once(draft, plan, plot_events)
                    # 重新保存修订后的版本
                    with open(self.sim_dir / "chapter_draft.md", "w", encoding="utf-8") as f:
                        f.write(draft)
            else:
                report = {"passed": True, "mode": "disabled", "violations": []}
                with open(self.sim_dir / "consistency_report.json", "w", encoding="utf-8") as f:
                    json.dump(report, f, ensure_ascii=False, indent=2)
        else:
            # 无 LLM：用规则生成简单草稿
            draft = self._rule_based_draft(plan)
            with open(self.sim_dir / "chapter_draft.md", "w", encoding="utf-8") as f:
                f.write(draft)
            report = {"passed": True, "mode": "rule_based", "violations": []}
            with open(self.sim_dir / "consistency_report.json", "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)

        return {
            "plan": plan,
            "draft": draft,
            "consistency_report": report,
        }

    # ==========================================
    # 规则生成 chapter_plan
    # ==========================================

    def _build_chapter_plan(self, plot_events: List[EventLog]) -> ChapterPlan:
        """从 plot_events 生成章节大纲

        核心原则：一个章节只讲清楚一件事，不要堆砌线索
        """
        plot_events.sort(key=lambda e: e.event_id)

        # 情感曲线：更多"喘息"阶段，不要全程紧张
        emotional_curve = self._build_emotional_curve(plot_events)

        # beats 分组：合并密集事件，每个 beat 只释放 1-2 个核心异常
        beats = self._build_beats(plot_events)

        # ending hook：只选一个有悬念的事件，不要把高潮全放在结尾
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
        """根据事件或世界配置生成默认章节标题"""
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
        """选择结尾钩子：选一个中等悬念的事件，不要选最恐怖的那个"""
        if not plot_events:
            return None
        # 选倒数第二个或第三个事件，留下余韵
        sorted_events = sorted(plot_events, key=lambda e: e.event_id)
        if len(sorted_events) >= 3:
            return sorted_events[-2].event_id
        return sorted_events[-1].event_id

    def _build_emotional_curve(self, events: List[EventLog]) -> List[str]:
        """根据 plot_value 生成情感曲线

        核心原则：紧张与喘息交替，不要全程高能
        """
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
        # 去重保留顺序，但强制插入喘息阶段
        unique = []
        seen = set()
        for i, c in enumerate(curve):
            if c not in seen:
                unique.append(c)
                seen.add(c)
            # 每两个紧张阶段后插入一个"喘息"
            if c in ("紧张", "不安", "危险") and i < len(curve) - 1:
                unique.append("喘息")
                seen.add("喘息")
        # 确保有起承转合
        if len(unique) < 4:
            unique = ["观察", "不安", "紧张", "喘息", "悬念"][:5]
        return unique

    def _build_beats(self, events: List[EventLog]) -> List[ChapterBeat]:
        """按地点分组生成 beats

        核心原则：每个 beat 只释放 1-2 个核心异常，不要堆砌
        多个相似异常合并为一个，只保留最有悬念的那个
        """
        beats: List[ChapterBeat] = []
        beats_by_loc: Dict[str, List[EventLog]] = {}

        for e in events:
            loc_id = e.location_id or "unknown"
            if loc_id not in beats_by_loc:
                beats_by_loc[loc_id] = []
            beats_by_loc[loc_id].append(e)

        for idx, (loc_id, loc_events) in enumerate(beats_by_loc.items()):
            # 核心异常只保留 1-2 个：优先保留 mystery/conflict 高的
            sorted_events = sorted(
                loc_events,
                key=lambda e: e.plot_value.mystery + e.plot_value.conflict + e.plot_value.danger,
                reverse=True
            )
            # 最多保留 2 个核心事件
            core_events = sorted_events[:2]
            # 剩余事件如果太多，合并成一个"观察"类事件
            remaining = sorted_events[2:]

            # 根据地点推断 purpose
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
        """根据事件内容推断 beat 的 purpose

        核心原则：purpose 描述的是主角的行动/心理状态，而不是地点功能
        """
        if not events:
            return "推进情节"

        # 根据事件的神秘感和冲突程度判断
        total_mystery = sum(e.plot_value.mystery for e in events)
        total_conflict = sum(e.plot_value.conflict for e in events)

        if total_mystery > 10:
            return "发现异常"
        elif total_conflict > 8:
            return "冲突与抉择"
        elif "entrance" in loc_id or "gate" in loc_id:
            return "进入陌生空间"
        elif "lobby" in loc_id:
            return "观察与思考"
        elif "archive" in loc_id:
            return "搜索与发现"
        elif "ward" in loc_id:
            return "直面真相"
        return "情节推进"

    # ==========================================
    # LLM 正文改写
    # ==========================================

    def _llm_write_chapter(self, plan: ChapterPlan) -> str:
        """基于 chapter_plan 和事件，用 LLM 写正文。失败时记录详细错误再回退。"""
        if not self.llm_client:
            return self._rule_based_draft(plan)

        try:
            # 构建 allowed_entities
            allowed_entities = self._build_allowed_entities(plan)

            # 构建 prompt
            system = self._build_narrative_system_prompt()
            user = self._build_narrative_user_prompt(plan, allowed_entities)

            # 调用 LLM（temperature=0.7，增加文学性）
            # 注意：小说生成用普通文本模式，不要用 JSON 模式！
            resp = self.llm_client.chat(system=system, user=user, temperature=0.7)

            # 记录 trace
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
            # ========== 记录详细错误日志 ==========
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

            # 保存到错误日志文件
            error_file = self.sim_dir / "llm_error.json"
            import json
            with open(error_file, "w", encoding="utf-8") as f:
                json.dump(error_log, f, ensure_ascii=False, indent=2)

            # 控制台输出详细错误
            print("\n" + "="*80)
            print("❌ LLM 小说生成调用失败！")
            print("="*80)
            print(f"错误类型: {type(e).__name__}")
            print(f"错误信息: {e}")
            print(f"错误日志已保存到: {error_file}")
            print("="*80 + "\n")
            # =========================================

            # 回退到规则生成模式
            print("🔄  回退到规则生成模式...")
            return self._rule_based_draft(plan)

    def _build_allowed_entities(self, plan: ChapterPlan) -> Dict[str, List[str]]:
        """构建允许出现的实体白名单"""
        locations = set()
        objects = set()
        characters = set()
        facts = set()

        # 从世界配置中提取
        for loc in self.world.map.locations:
            locations.add(loc.id)
            locations.add(loc.name)
            for obj in loc.objects:
                objects.add(obj.id)
                objects.add(obj.name)

        for char in self.world.characters.characters:
            characters.add(char.id)
            characters.add(char.name)

        # 从线索内容中提取关键词
        for clue in self.world.clues.clues:
            # 简单收集：提取线索中的实体（简单分词）
            content = clue.content
            # 粗略提取：以分隔符分割
            for word in content.replace("，", " ").replace("。", " ").replace("、", " ").split():
                if len(word) > 1:
                    facts.add(word)

        return {
            "locations": list(locations),
            "objects": list(objects),
            "characters": list(characters),
            "facts": list(facts)[:50],  # 限制数量
        }

    @staticmethod
    def _build_narrative_system_prompt() -> str:
        return (
            "你是一位资深小说作家，擅长氛围营造、人物塑造和悬念控制。\n"
            "你的任务：将事件日志改写为引人入胜的小说章节，严格基于用户消息中给出的【世界设定】与【角色档案】，不要套用你脑海中其它故事的模板。\n"
            "\n"
            "【第一原则：忠于世界设定】\n"
            "❌ 错误做法：忽略给定世界，使用医院/医生/妹妹/老周等任何与本世界无关的角色或场景\n"
            "✅ 正确做法：所有人物、地点、物品、规则都必须严格来自用户消息中的白名单与角色档案\n"
            "- 章节中出现的主角姓名 = 用户消息中【角色档案】里 POV 角色的名字\n"
            "- 章节中出现的地点 = 用户消息中【允许出现的实体·地点】里的名字\n"
            "- 不允许凭空虚构姓名、亲属关系（妹妹/弟弟等）、未在档案中出现的过往\n"
            "\n"
            "【第二原则：节奏控制】\n"
            "❌ 错误做法：每个段落都释放一个高强度事件，读者被喂线索\n"
            "✅ 正确做法：紧张与喘息交替，让读者有消化空间\n"
            "1. 一个 beat（段落）最多写 1-2 个核心事件，不要堆砌\n"
            "2. 释放一个事件后，必须有观察/思考/行动作为喘息\n"
            "3. 主角的心理活动要占一定比例：回忆、推理、猜测\n"
            "\n"
            "【第三原则：氛围与基调】\n"
            "1. 严格遵循【世界基调】（如压抑/恐怖/绝望，或轻松/热血等）所暗示的语感\n"
            "2. 多用具体的感官细节（视/听/嗅/触/痛），不要空洞的形容词\n"
            "3. 心理描写要克制：写身体反应（手心出汗、呼吸停顿），少写直白情绪标签\n"
            "\n"
            "【第四原则：主角动机】\n"
            "主角每一步行动都应能从【角色档案】里的目标/恐惧/秘密推导出来。\n"
            "他的疑问与决定要服务于角色档案中给出的 short_term / long_term goals。\n"
            "\n"
            "【第五原则：悬念控制】\n"
            "1. 结尾只给一点暗示，不要揭示真相\n"
            "2. 让读者带着疑问翻下一页\n"
            "3. 不要在结尾把所有悬念一次性抛出\n"
            "\n"
            "【写作硬性规则】\n"
            "1. 只写 POV 角色能感知到的内容，没有上帝视角\n"
            "2. 不添加白名单外的地点、物品、人物\n"
            "3. 不泄露角色不知道的真相\n"
            "4. 不要复用其它故事的人物名（如「林舟」「老周」「林玥」等），除非它们出现在本次【角色档案】白名单中\n"
        )

    def _build_narrative_user_prompt(self, plan: ChapterPlan, allowed_entities: Dict[str, List[str]]) -> str:
        lines: List[str] = []

        # ====== Bootstrap 注入：写作锚点（最高优先级，放在最前） ======
        if self.story_anchors:
            a = self.story_anchors
            lines.append("【写作锚点（必须遵守）】")
            if a.get("title"):
                lines.append(f"- 作品名：{a['title']}")
            if a.get("protagonist_name"):
                lines.append(f"- 主角名：{a['protagonist_name']}（章节中主角名字必须是这个）")
            if a.get("protagonist_goal"):
                lines.append(f"- 主角目标：{a['protagonist_goal']}")
            if a.get("personal_stakes"):
                lines.append(f"- 私人动机：{a['personal_stakes']}")
            if a.get("current_chapter_goal"):
                lines.append(f"- 本章目标：{a['current_chapter_goal']}")
            if a.get("main_question"):
                lines.append(f"- 主线问题：{a['main_question']}")
            if a.get("required_emotional_beat"):
                lines.append(f"- 必须出现的情感节拍：{a['required_emotional_beat']}")
            if a.get("world_tone"):
                lines.append(f"- 整体基调：{a['world_tone']}")
            forbidden = a.get("forbidden_generic_phrases") or []
            if forbidden:
                lines.append(f"- 禁止使用的泛化表达：{', '.join(forbidden)}")
            lines.append("")

        bible = self.world.bible
        lines.append("【世界设定】")
        lines.append(f"- 世界名：{getattr(bible, 'world_id', '')}")
        if getattr(bible, "genre", ""):
            lines.append(f"- 题材：{bible.genre}")
        if getattr(bible, "era", ""):
            lines.append(f"- 时代：{bible.era}")
        if getattr(bible, "tone", ""):
            lines.append(f"- 基调：{bible.tone}")
        if getattr(bible, "rules", None):
            lines.append("- 世界规则：")
            for r in bible.rules:
                lines.append(f"  · {r}")
        if getattr(bible, "themes", None):
            lines.append(f"- 主题：{', '.join(bible.themes)}")
        lines.append("")

        # 角色档案（重点突出 POV 角色）
        lines.append("【角色档案】")
        pov_id = plan.pov
        for char in self.world.characters.characters:
            tag = " ← POV 主角" if char.id == pov_id else ""
            lines.append(f"- {char.name}（id={char.id}, 角色={char.role}）{tag}")
            traits = char.personality.get("traits") if isinstance(char.personality, dict) else None
            if traits:
                lines.append(f"  · 性格：{', '.join(traits) if isinstance(traits, list) else traits}")
            background = getattr(char, "background", None) or (
                char.personality.get("background") if isinstance(char.personality, dict) else None
            )
            if background:
                lines.append(f"  · 背景：{background}")
            if isinstance(char.goals, dict):
                short_term = char.goals.get("short_term")
                long_term = char.goals.get("long_term")
                if short_term:
                    lines.append(f"  · 短期目标：{short_term}")
                if long_term:
                    lines.append(f"  · 长期目标：{long_term}")
            if char.fears:
                lines.append(f"  · 恐惧：{', '.join(char.fears)}")
        lines.append("")

        # 地点档案
        if self.world.map.locations:
            lines.append("【地点档案】")
            for loc in self.world.map.locations[:15]:
                desc = (loc.public_description or "").strip()
                lines.append(f"- {loc.name}（id={loc.id}）：{desc}")
            lines.append("")

        lines.append(f"【章节标题】{plan.chapter_title}")
        lines.append(f"【POV 角色 id】{plan.pov}")
        lines.append(f"【章节目标】{plan.chapter_goal}")
        lines.append(f"【情感曲线】{' → '.join(plan.emotional_curve)}")
        lines.append("")

        lines.append("【章节结构】")
        lines.append("每个 beat 最多包含 1-2 个核心事件，写完要有喘息空间：")
        lines.append("")
        for beat in plan.beats:
            lines.append(f"## {beat.beat_id}: {beat.purpose}")
            lines.append("包含事件：")
            for e in beat.events:
                lines.append(f"- {e.result}")
            lines.append("→ 这个 beat 后需要喘息阶段（观察/思考/回忆）")
            lines.append("")
        lines.append("")

        if plan.ending_hook_event_id:
            hook_event = next((e for beat in plan.beats for e in beat.events if e.event_id == plan.ending_hook_event_id), None)
            if hook_event:
                lines.append("【结尾钩子】")
                lines.append(f"- {hook_event.result}")
                lines.append("→ 只给暗示，不要揭示真相")
                lines.append("")

        lines.append("【允许出现的实体（白名单）】")
        lines.append(f"地点：{', '.join(allowed_entities['locations'][:15])}")
        lines.append(f"物品：{', '.join(allowed_entities['objects'][:20])}")
        lines.append(f"角色：{', '.join(allowed_entities['characters'][:10])}")
        lines.append("⚠ 严禁写出白名单之外的任何人名、地名（尤其禁止使用「林舟/老周/林玥/第七人民医院」等与本世界无关的名字）。")
        lines.append("")

        lines.append("【写作要求】")
        lines.append("1. 章节长度：2000-4000 字")
        lines.append("2. 每个 beat 后必须有喘息阶段，不要连续释放高强度事件")
        lines.append("3. 心理活动占比：主角的回忆、推理、猜测要有一定篇幅")
        lines.append("4. 感官描写：视觉、听觉、嗅觉、触觉都要有")
        lines.append("5. 细节具体，氛围由细节而非形容词撑起")
        lines.append("6. 结尾钩子：只给一点暗示，让读者想翻下一页")
        lines.append("7. 严格遵循上面【世界设定】+【角色档案】+【白名单】")
        lines.append("")
        lines.append("开始写作：")

        return "\n".join(lines)

    # ==========================================
    # 规则基草稿（无 LLM 时使用）
    # ==========================================

    def _rule_based_draft(self, plan: ChapterPlan) -> str:
        """规则生成简单草稿"""
        lines: List[str] = []
        lines.append(f"# {plan.chapter_title}")
        lines.append("")
        lines.append(f"> 章节目标：{plan.chapter_goal}")
        lines.append(f"> POV：{plan.pov}")
        lines.append("")

        for beat in plan.beats:
            lines.append(f"## {beat.purpose}")
            lines.append("")
            for e in beat.events:
                lines.append(f"{e.result}")
            lines.append("")

        if plan.ending_hook_event_id:
            lines.append("")
            lines.append("---")
            lines.append("")
            lines.append("（本章完，待续...）")

        return "\n".join(lines)
