from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple

from app.llm_client import OpenAICompatibleClient
from app.models.action import ActionCommand, ActionType
from app.models.memory import MemoryChunk
from app.models.state import WorldState
from app.models.world import WorldConfig
from app.services.action_validator import ActionValidator, ValidationResult
from app.services.memory_service import MemoryService
from app.services.trace_service import TraceService


@dataclass
class AgentContext:
    """V2.3 结构化 Agent 上下文（分层）"""
    # 人物基础信息（无默认值）
    agent_id: str
    agent_name: str
    role: str
    traits: List[str]
    short_term_goal: str

    # 当前状态（无默认值）
    location_id: str
    location_name: str
    mental_state: str
    known_facts: List[str]
    beliefs: List[str]

    # 可见环境（无默认值）
    location_public_description: str
    connected_locations: List[str]
    available_targets: List[str]
    available_character_targets: List[str]
    available_topics_by_target: Dict[str, List[str]]

    # 记忆（无默认值）
    recent_events: List[str]
    relevant_memories: List[MemoryChunk]

    # 可用动作（无默认值）
    available_actions: List[str]
    soft_hints: List[str]

    # V3.3 PlotArc 信息
    plot_arc_stage: str = ""
    plot_arc_purpose: str = ""
    forbidden_revelations: List[str] = field(default_factory=list)

    # V3.4 章节连续性
    previous_chapter_summary: str = ""
    open_threads: List[str] = field(default_factory=list)
    next_chapter_seeds: List[str] = field(default_factory=list)

    # V3.5 人物弧光
    character_arc_stage: str = ""
    internal_conflict: str = ""
    recent_reflections: List[str] = field(default_factory=list)

    # 正式版V1.1 章节 brief
    chapter_main_question: str = ""
    chapter_goal: str = ""
    must_advance_threads: List[str] = field(default_factory=list)
    relationship_focus: List[Dict[str, Any]] = field(default_factory=list)
    reveal_policy: Dict[str, Any] = field(default_factory=dict)

    # V3 导演压力
    soft_director_pressure: List[str] = field(default_factory=list)

    # 通用社交披露约束（仅运行时 prompt/validator 上下文，不持久化）
    private_facts: List[str] = field(default_factory=list)
    disclosure_context_by_target: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    blocked_private_disclosure_targets: List[str] = field(default_factory=list)

    # 有默认值的字段放最后
    background: str = ""
    inventory: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """转换为字典（用于 LLM prompt）"""
        return {
            "character": {
                "name": self.agent_name,
                "role": self.role,
                "traits": self.traits,
                "short_term_goal": self.short_term_goal,
            },
            "current_state": {
                "location_id": self.location_id,
                "location_name": self.location_name,
                "mental_state": self.mental_state,
                "known_facts": self.known_facts[:8],
                "beliefs": self.beliefs[:6],
                "inventory": self.inventory,
            },
            "visible_environment": {
                "description": self.location_public_description,
                "available_targets": self.available_targets,
                "available_character_targets": self.available_character_targets,
                "available_topics_by_target": self.available_topics_by_target,
                "available_moves": self.connected_locations,
            },
            "memory": {
                "recent_events": self.recent_events,
                "relevant_memories": [m.memory.content for m in self.relevant_memories],
            },
            "actions": {"available": self.available_actions},
            "plot_context": {
                "arc_stage": self.plot_arc_stage,
                "stage_purpose": self.plot_arc_purpose,
                "forbidden_revelations": self.forbidden_revelations,
            },
            "continuity_context": {
                "previous_chapter_summary": self.previous_chapter_summary,
                "open_threads": self.open_threads,
                "next_chapter_seeds": self.next_chapter_seeds,
            },
            "chapter_brief": {
                "main_question": self.chapter_main_question,
                "chapter_goal": self.chapter_goal,
                "must_advance_threads": self.must_advance_threads,
                "relationship_focus": self.relationship_focus,
                "reveal_policy": self.reveal_policy,
            },
            "character_arc": {
                "current_stage": self.character_arc_stage,
                "internal_conflict": self.internal_conflict,
                "recent_reflections": self.recent_reflections,
            },
            "director_pressure": self.soft_director_pressure,
            "social_disclosure": {
                "private_facts_count": len(self.private_facts),
                "disclosure_context_by_target": self.disclosure_context_by_target,
                "blocked_private_disclosure_targets": self.blocked_private_disclosure_targets,
            },
        }


class CharacterAgentService:
    """V2.3 角色 Agent 服务：
    - scripted: 脚本驱动（快速测试）
    - heuristic: 规则驱动（无 API 可用）
    - llm: LLM 决策（需 API，带重试、兜底）
    """

    ACTIONS_V23: List[ActionType] = ["observe", "move", "inspect", "talk", "ask", "wait"]

    def __init__(
        self,
        world: WorldConfig,
        mode: Literal["scripted", "heuristic", "llm"],
        memory_service: Optional[MemoryService] = None,
        llm_client: Optional[OpenAICompatibleClient] = None,
        trace_service: Optional[TraceService] = None,
        temperature: float = 0.2,
        max_retries: int = 2,
        chapter_brief=None,
    ):
        self.world = world
        self.mode = mode
        self.memory_service = memory_service
        self._llm = llm_client
        self.trace_service = trace_service
        self._validator = ActionValidator(world)
        self._default_temperature = temperature
        self.max_retries = max_retries
        self.chapter_brief = chapter_brief
        self.fallback_actions = 0
        self.agent_decision_failures = 0

    def _get_agent_temperature(self, agent_id: str) -> float:
        """
        V5.1 获取角色专属的 temperature
        优先级：角色配置 llm_temperature > 性格推导 > 默认值
        """
        try:
            return self.world.characters.get_llm_temperature(agent_id, self._default_temperature)
        except Exception:
            return self._default_temperature

    def decide_next_action(self, state: WorldState, ctx: AgentContext) -> ActionCommand:
        if self.mode == "scripted":
            return self._scripted_action(ctx)
        elif self.mode == "heuristic":
            return self._heuristic_action(ctx)
        elif self.mode == "llm":
            if not self._llm:
                raise RuntimeError("LLM mode requires OPENAI_API_KEY")
            return self._llm_action_with_retry(state, ctx)
        else:
            raise ValueError(f"unknown mode: {self.mode}")

    @staticmethod
    def _disclosure_policy(profile) -> Dict[str, Any]:
        policy = dict(getattr(profile, "disclosure_policy", {}) or {})
        return {
            "min_trust_for_secret_disclosure": policy.get("min_trust_for_secret_disclosure", 5),
            "max_suspicion_for_secret_disclosure": policy.get("max_suspicion_for_secret_disclosure", 2),
            "max_hostility_for_secret_disclosure": policy.get("max_hostility_for_secret_disclosure", 1),
            "require_relationship_evidence": policy.get("require_relationship_evidence", True),
            "private_fields": policy.get("private_fields", []),
        }

    @classmethod
    def _private_facts_for_profile(cls, profile) -> List[str]:
        policy = cls._disclosure_policy(profile)
        facts: List[str] = []
        facts.extend([secret for secret in getattr(profile, "secrets", []) if secret])
        for value in [
            getattr(profile, "private_motive", ""),
            getattr(profile, "withheld_information", ""),
        ]:
            if value:
                facts.append(value)
        if "background" in policy["private_fields"] and getattr(profile, "background", ""):
            facts.append(profile.background)
        return facts

    def _build_disclosure_context(
        self, state: WorldState, agent_id: str, visible_targets: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        profile = self.world.characters.get_character(agent_id)
        policy = self._disclosure_policy(profile)
        agent_runtime = state.characters[agent_id]
        context: Dict[str, Dict[str, Any]] = {}

        for target_id in visible_targets:
            if target_id == agent_id or target_id not in state.characters:
                continue

            rel = agent_runtime.relationships.get(target_id)
            trust = rel.trust if rel else 0
            suspicion = rel.suspicion if rel else 0
            hostility = rel.hostility if rel else 0
            affinity = rel.affinity if rel else 0
            evidence = list(rel.evidence) if rel else []

            trust_ok = trust >= policy["min_trust_for_secret_disclosure"]
            suspicion_ok = suspicion <= policy["max_suspicion_for_secret_disclosure"]
            hostility_ok = hostility <= policy["max_hostility_for_secret_disclosure"]
            evidence_ok = (not policy["require_relationship_evidence"]) or bool(evidence) or trust_ok
            allowed = trust_ok and suspicion_ok and hostility_ok and evidence_ok
            high_uncertainty = policy["require_relationship_evidence"] and not evidence and not trust_ok

            reason_parts: List[str] = []
            if not trust_ok:
                reason_parts.append(f"trust {trust} < {policy['min_trust_for_secret_disclosure']}")
            if not suspicion_ok:
                reason_parts.append(f"suspicion {suspicion} > {policy['max_suspicion_for_secret_disclosure']}")
            if not hostility_ok:
                reason_parts.append(f"hostility {hostility} > {policy['max_hostility_for_secret_disclosure']}")
            if not evidence_ok:
                reason_parts.append("缺少关系证据")

            context[target_id] = {
                "trust": trust,
                "suspicion": suspicion,
                "hostility": hostility,
                "affinity": affinity,
                "high_uncertainty": high_uncertainty,
                "private_disclosure_allowed": allowed,
                "reason": "允许私人披露" if allowed else "；".join(reason_parts),
            }

        return context

    def build_context(
        self, state: WorldState, agent_id: str, last_events_text: List[str]
    ) -> AgentContext:
        profile = self.world.characters.get_character(agent_id)
        runtime = state.characters[agent_id]
        loc = self.world.map.get_location(runtime.location_id)

        # 可用 targets：本地点 objects + 在场角色 + 运行时解锁的目标
        targets: List[str] = [o.id for o in loc.objects]
        character_targets: List[str] = []
        for other_id, other_state in state.characters.items():
            if other_state.location_id == runtime.location_id and other_id != agent_id:
                targets.append(other_id)
                character_targets.append(other_id)

        # 添加运行时解锁的目标（由 Director 干预创建）
        for obj_id, obj_data in state.world.objects.items():
            if obj_data.get("location_id") == runtime.location_id and obj_id not in targets:
                targets.append(obj_id)

        # 环境动作可用当前地点 ID 作为 fallback target
        if runtime.location_id not in targets:
            targets.append(runtime.location_id)

        # 可问 topics
        topics_by_target: Dict[str, List[str]] = {}
        for t in targets:
            topics = self.world.clues.all_topics_for_target(t)
            if topics:
                topics_by_target[t] = topics

        # 短期目标
        short_term_goal = ""
        if isinstance(profile.goals, dict):
            st = profile.goals.get("short_term")
            if isinstance(st, list) and st:
                short_term_goal = st[0]
            elif isinstance(st, str):
                short_term_goal = st

        # 背景故事（驱动决策）
        background = getattr(profile, "background", "") or ""

        # 性格特征
        traits = []
        if isinstance(profile.personality, dict):
            traits = profile.personality.get("traits", [])

        known_facts: List[str] = list(runtime.known_facts)
        beliefs: List[str] = []
        relevant_memories: List[MemoryChunk] = []

        if self.memory_service:
            for fact in self.memory_service.get_known_facts(agent_id, limit=6):
                if fact not in known_facts:
                    known_facts.append(fact)
            beliefs = self.memory_service.get_beliefs(agent_id, limit=6)

            # 检索相关记忆
            query_tags = self.memory_service.get_all_tags_for_state(state, agent_id)
            relevant_memories = self.memory_service.retrieve_relevant(
                agent_id=agent_id,
                query_tags=query_tags,
                top_n=6,
                location_id=runtime.location_id,
            )

        brief = self.chapter_brief
        reveal_policy = brief.reveal_policy.model_dump() if brief else {}
        relationship_focus = [item.model_dump() for item in brief.relationship_focus] if brief else []
        private_facts = self._private_facts_for_profile(profile)
        disclosure_context_by_target = self._build_disclosure_context(state, agent_id, targets)
        blocked_private_disclosure_targets = [
            target_id
            for target_id, disclosure_context in disclosure_context_by_target.items()
            if not disclosure_context.get("private_disclosure_allowed", False)
        ]

        return AgentContext(
            agent_id=agent_id,
            agent_name=profile.name,
            role=profile.role,
            traits=traits,
            short_term_goal=short_term_goal,
            location_id=runtime.location_id,
            location_name=loc.name,
            mental_state=runtime.mental_state,
            known_facts=known_facts,
            beliefs=beliefs,
            location_public_description=loc.public_description,
            connected_locations=list(loc.connected_to),
            recent_events=last_events_text[-8:],
            relevant_memories=relevant_memories,
            available_targets=targets,
            available_character_targets=character_targets,
            available_topics_by_target=topics_by_target,
            available_actions=[a for a in self.ACTIONS_V23],
            soft_hints=list(state.world.soft_hints[-2:]),
            chapter_main_question=brief.main_question if brief else "",
            chapter_goal=brief.chapter_goal if brief else "",
            must_advance_threads=list(brief.must_advance_threads) if brief else [],
            relationship_focus=relationship_focus,
            reveal_policy=reveal_policy,
            private_facts=private_facts,
            disclosure_context_by_target=disclosure_context_by_target,
            blocked_private_disclosure_targets=blocked_private_disclosure_targets,
            background=background,
            inventory=list(runtime.inventory),
        )

    # ==========================================
    # scripted（自测）
    # ==========================================

    def _scripted_action(self, ctx: AgentContext) -> ActionCommand:
        if ctx.agent_id != self.world.chapter_goal.pov:
            return ActionCommand(
                agent_id=ctx.agent_id,
                intent="保持警惕，观察对方行动",
                action_type="wait",
                target="",
                topic=None,
                method="",
                dialogue=None,
                expected_gain="观察对方动向",
                risk_level="low",
            )

        # 脚本：主角按顺序推进剧情
        if not ctx.known_facts and ctx.available_topics_by_target:
            target = next(iter(ctx.available_topics_by_target.keys()))
            topics = ctx.available_topics_by_target[target]
            if topics:
                return ActionCommand(
                    agent_id=ctx.agent_id,
                    intent="先从对方口中套取基本信息",
                    action_type="ask",
                    target=target,
                    topic=topics[0],
                    method="委婉询问，不引起对方警惕",
                    dialogue=None,
                    expected_gain="了解更多背景信息",
                    risk_level="low",
                )

        if ctx.available_targets:
            for t in ctx.available_targets:
                if t.startswith("lock") or t == "hospital_gate_lock":
                    return ActionCommand(
                        agent_id=ctx.agent_id,
                        intent="检查铁门是否真的锁上",
                        action_type="inspect",
                        target=t,
                        topic=None,
                        method="仔细检查锁芯和门板",
                        dialogue=None,
                        expected_gain="确认是否可以进入",
                        risk_level="low",
                    )

        if ctx.connected_locations:
            target = ctx.connected_locations[0]
            return ActionCommand(
                agent_id=ctx.agent_id,
                intent="前往下一个地点继续调查",
                action_type="move",
                target=target,
                topic=None,
                method="",
                dialogue=None,
                expected_gain="在新区域找到线索",
                risk_level="low",
            )

        return ActionCommand(
            agent_id=ctx.agent_id,
            intent="整理目前掌握的线索",
            action_type="wait",
            target="",
            topic=None,
            method="",
            dialogue=None,
            expected_gain="整理思路，找到下一步方向",
            risk_level="low",
        )

    # ==========================================
    # heuristic（无 API 可用时的规则驱动）
    # ==========================================

    def _heuristic_action(self, ctx: AgentContext) -> ActionCommand:
        # 策略 0：优先检查 Director 新解锁的目标（hint_ 开头的目标）
        if ctx.available_targets and "inspect" in ctx.available_actions:
            for t in ctx.available_targets:
                if t.startswith("hint_"):
                    return ActionCommand(
                        agent_id=ctx.agent_id,
                        intent=f"仔细检查这个可疑的地方",
                        action_type="inspect",
                        target=t,
                        topic=None,
                        method="仔细检查，不放过任何细节",
                        dialogue=None,
                        expected_gain="发现隐藏的线索",
                        risk_level="low",
                    )

        # 策略 1：有可问的话题先问（低成本获取信息）
        if ctx.available_topics_by_target and ("ask" in ctx.available_actions or "talk" in ctx.available_actions):
            target = next(iter(ctx.available_topics_by_target.keys()))
            topics = ctx.available_topics_by_target[target]
            if topics:
                return ActionCommand(
                    agent_id=ctx.agent_id,
                    intent=f"尝试从{target}处获取信息",
                    action_type="ask",
                    target=target,
                    topic=topics[0],
                    method="委婉询问相关情况",
                    dialogue=None,
                    expected_gain="获得更多信息",
                    risk_level="low",
                )

        # 策略 2：有可疑物体先检查（高价值线索）
        if ctx.available_targets and "inspect" in ctx.available_actions:
            for t in ctx.available_targets:
                if "lock" in t or "door" in t or "desk" in t or "cabinet" in t or "file" in t:
                    return ActionCommand(
                        agent_id=ctx.agent_id,
                        intent=f"仔细检查{t}，寻找线索",
                        action_type="inspect",
                        target=t,
                        topic=None,
                        method="仔细检查，不放过任何细节",
                        dialogue=None,
                        expected_gain="发现隐藏的线索",
                        risk_level="low",
                    )

        # 策略 3：能移动就移动（推进探索）
        if ctx.connected_locations and "move" in ctx.available_actions:
            return ActionCommand(
                agent_id=ctx.agent_id,
                intent="前往新区域继续调查",
                action_type="move",
                target=ctx.connected_locations[0],
                topic=None,
                method="",
                dialogue=None,
                expected_gain="在新区域找到更多线索",
                risk_level="low",
            )

        # 策略 4：否则观察周围环境
        return ActionCommand(
            agent_id=ctx.agent_id,
            intent="仔细观察周围环境",
            action_type="observe",
            target="",
            topic=None,
            method="",
            dialogue=None,
            expected_gain="发现更多细节",
            risk_level="low",
        )

    # ==========================================
    # LLM + 重试 + fallback
    # ==========================================

    def _llm_action_with_retry(self, state: WorldState, ctx: AgentContext) -> ActionCommand:
        if not self._llm:
            raise RuntimeError("LLM mode requires OPENAI_API_KEY")

        # V5.1：获取角色专属的 temperature（优先从角色配置读取，其次根据性格推导，最后用默认）
        agent_temperature = self._get_agent_temperature(ctx.agent_id)

        system = self._build_system_prompt()
        user = self._format_agent_user_prompt(ctx)
        last_error = ""
        first_error_info = None

        for retry in range(self.max_retries + 1):
            try:
                resp = self._llm.chat_json(
                    system=system + f"\n之前的错误：{last_error}" if last_error else system,
                    user=user,
                    temperature=agent_temperature,
                )

                if not resp.parsed_json:
                    raise ValueError(f"LLM 未返回可解析 JSON：{resp.text}")

                # ========== 兜底修复：清理无效字段 ==========
                # 1. 强制 agent_id 为当前角色 ID，防止 LLM 返回中文名称
                resp.parsed_json["agent_id"] = ctx.agent_id
                # 2. 将 null 转换为空字符串（method、expected_gain 等）
                for key in ["method", "dialogue", "topic", "expected_gain", "risk_level"]:
                    if resp.parsed_json.get(key) is None:
                        if key == "risk_level":
                            resp.parsed_json[key] = "low"
                        else:
                            resp.parsed_json[key] = ""
                # 3. 确保 expected_gain 不为空（环境校验要求）
                if not resp.parsed_json.get("expected_gain"):
                    resp.parsed_json["expected_gain"] = "继续调查，获取更多信息"

                action = ActionCommand.model_validate(resp.parsed_json)
                validation = self._validator.validate(action, state, ctx.agent_id)

                if not validation.valid:
                    raise ValueError(f"校验失败：{'; '.join(validation.errors)}")

                self._record_trace(ctx, state.tick, resp, True, retry, "")
                return action

            except Exception as e:
                last_error = str(e)
                if retry == 0:
                    first_error_info = {
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "tick": state.tick,
                        "agent_id": ctx.agent_id,
                        "system_prompt_length": len(system),
                        "user_prompt_length": len(user),
                    }
                if retry < self.max_retries:
                    continue
                # 最后一次重试失败，记录详细错误
                self.agent_decision_failures += 1
                self.fallback_actions += 1
                import json
                import traceback
                error_log = {
                    "first_error": first_error_info,
                    "final_error": {
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "stack_trace": traceback.format_exc(),
                    },
                    "retry_count": retry,
                    "fallback_action": "已触发兜底策略"
                }
                if hasattr(self, "trace_service") and self.trace_service:
                    error_file = Path(self.trace_service.output_dir) / f"agent_error_tick{state.tick}_{ctx.agent_id}.json"
                    with open(error_file, "w", encoding="utf-8") as f:
                        json.dump(error_log, f, ensure_ascii=False, indent=2)
                    print(f"\nAgent {ctx.agent_id} 在 tick={state.tick} LLM 决策失败 {retry + 1} 次")
                    print(f"   错误详情已保存: {error_file}")
                    print(f"   触发兜底动作\n")
                self._record_trace(ctx, state.tick, None, False, retry, last_error)
                return self._fallback_action(ctx)

    def _fallback_action(self, ctx: AgentContext) -> ActionCommand:
        """兜底策略"""
        if ctx.connected_locations:
            return ActionCommand(
                agent_id=ctx.agent_id,
                intent="前往其他区域继续调查",
                action_type="move",
                target=ctx.connected_locations[0],
                topic=None,
                method="",
                dialogue=None,
                expected_gain="在新区域找到线索",
                risk_level="low",
            )

        if ctx.available_topics_by_target:
            target = next(iter(ctx.available_topics_by_target.keys()))
            topics = ctx.available_topics_by_target[target]
            if topics:
                return ActionCommand(
                    agent_id=ctx.agent_id,
                    intent="尝试从对方处获取信息",
                    action_type="ask",
                    target=target,
                    topic=topics[0],
                    method="委婉询问相关情况",
                    dialogue=None,
                    expected_gain="获取更多背景信息",
                    risk_level="low",
                )

        if ctx.available_targets:
            return ActionCommand(
                agent_id=ctx.agent_id,
                intent="仔细检查周围环境",
                action_type="inspect",
                target=ctx.available_targets[0],
                topic=None,
                method="仔细检查细节",
                dialogue=None,
                expected_gain="发现有价值的线索",
                risk_level="low",
            )

        return ActionCommand(
            agent_id=ctx.agent_id,
            intent="观察周围环境",
            action_type="observe",
            target="",
            topic=None,
            method="",
            dialogue=None,
            expected_gain="了解周围情况",
            risk_level="low",
        )

    def _record_trace(
        self,
        ctx: AgentContext,
        tick: int,
        resp,
        success: bool,
        retry_count: int,
        error: str,
    ) -> None:
        """记录 LLM 调用 trace（如果 trace_service 存在）"""
        if not self.trace_service:
            return

        from app.services.trace_service import LLMTrace

        cost = getattr(resp, "cost", None) if resp else None
        trace = LLMTrace(
            trace_id=getattr(resp, "trace_id", "") if resp else "",
            simulation_id="",
            tick=tick,
            agent_id=ctx.agent_id,
            purpose="agent_decision",
            model=getattr(cost, "model", "unknown") if cost else "unknown",
            input_tokens=getattr(cost, "input_tokens", 0) if cost else 0,
            output_tokens=getattr(cost, "output_tokens", 0) if cost else 0,
            total_tokens=getattr(cost, "total_tokens", 0) if cost else 0,
            cost_usd=getattr(cost, "cost_usd", 0.0) if cost else 0.0,
            success=success,
            retry_count=retry_count,
            from_cache=getattr(resp, "from_cache", False) if resp else False,
            error=error,
        )
        self.trace_service.record(trace)

    @property
    def temperature(self) -> float:
        if self.mode == "llm":
            return self._temperature
        return 0.0

    @staticmethod
    def _build_system_prompt() -> str:
        return (
            "你正在扮演小说世界中的一个真实人物，而不是作者。\n"
            "你的所有决策必须基于角色的背景、动机、秘密，而不是基于推进剧情。\n"
            "\n"
            "角色的驱动力来自他的目标、恐惧、秘密，而不是'让故事变得精彩'。\n"
            "如果一个角色害怕某件事，他会下意识回避，哪怕这让读者觉得拖沓。\n"
            "如果一个角色有明确目标，他会优先采取能推进目标的行动。\n"
            "\n"
            "你只能基于给定信息做决策，绝对不能编造你不知道的事实。\n"
            "角色可以被秘密、私心、背景和隐瞒信息驱动，但不能在低信任或高不确定关系下主动说出口。\n"
            "如果目标的 private_disclosure_allowed=false，禁止在 intent/method/dialogue/expected_gain 中透露私人身份、秘密、私下动机、withheld information 或被标记为私密的背景。\n"
            "对禁止私人披露的目标，应优先观察、反问、含糊回应、转移话题、试探或沉默；私人事实只能驱动行动，不能直接写出。\n"
            "除非上下文明确允许私人披露，否则不得在输出字段中写出私人事实。\n"
            "你必须只输出一个 JSON（ActionCommand），不得输出小说正文、解释或额外文字。\n"
            "ask/talk 必须带 topic，topic 只能从 given list 中选择。\n"
            "move.target 只能来自 available_moves，不能使用当前地点或中文地点名。\n"
            "observe/inspect/search/wait.target 只能来自 available_targets。\n"
            "ask/talk.target 必须是在场角色 ID，不能使用地点 ID 或中文名称。\n"
            "target 必须严格使用 ID，禁止使用中文地点名或中文角色名。\n"
            "所有字段必须完整，action_type 必须是枚举之一。\n"
            "重要：agent_id 必须严格使用给定的 ID（如 char_protagonist），禁止使用中文名称！\n"
        )

    @staticmethod
    def _format_agent_user_prompt(ctx: AgentContext) -> str:
        lines: List[str] = []

        lines.append(f"【人物】{ctx.agent_name}（ID: {ctx.agent_id}，{ctx.role}）")
        if ctx.background:
            lines.append(f"【背景故事】{ctx.background}")
        lines.append(f"【性格特征】{'、'.join(ctx.traits)}")
        lines.append(f"【短期目标】{ctx.short_term_goal}")
        lines.append(f"【精神状态】{ctx.mental_state}")
        lines.append(f"【当前地点名称】{ctx.location_name}")
        lines.append(f"【当前地点ID】{ctx.location_id}")
        lines.append(f"【地点可见描述】{ctx.location_public_description}")

        if ctx.connected_locations:
            lines.append(f"【可移动地点】{'、'.join(ctx.connected_locations)}")

        if ctx.soft_hints:
            lines.append("【软提示】" + " / ".join(ctx.soft_hints))
        if ctx.known_facts:
            lines.append("【已知事实】" + " / ".join(ctx.known_facts))
        if ctx.beliefs:
            lines.append("【推测/怀疑】" + " / ".join(ctx.beliefs))

        if ctx.chapter_main_question or ctx.chapter_goal:
            lines.append("【本章 Brief】")
            if ctx.chapter_main_question:
                lines.append(f"- 本章主问题：{ctx.chapter_main_question}")
            if ctx.chapter_goal:
                lines.append(f"- 本章目标：{ctx.chapter_goal}")
            if ctx.must_advance_threads:
                lines.append("- 优先推进悬念：" + " / ".join(ctx.must_advance_threads))
            forbidden = ctx.reveal_policy.get("forbidden_facts") or []
            if forbidden:
                lines.append("- 本章禁止确认/揭示：" + " / ".join(forbidden))
            if ctx.relationship_focus:
                focus_text = [f"{item.get('source')}->{item.get('target')}: {item.get('expected_shift')}" for item in ctx.relationship_focus[:2]]
                lines.append("- 关系压力：" + " / ".join(focus_text))

        if ctx.plot_arc_stage or ctx.plot_arc_purpose:
            lines.append("【剧情阶段】")
            if ctx.plot_arc_stage:
                lines.append(f"- 当前阶段：{ctx.plot_arc_stage}")
            if ctx.plot_arc_purpose:
                lines.append(f"- 阶段目标：{ctx.plot_arc_purpose}")
            if ctx.forbidden_revelations:
                lines.append("- 当前禁止提前确认/揭露：" + " / ".join(ctx.forbidden_revelations))

        if ctx.previous_chapter_summary or ctx.open_threads or ctx.next_chapter_seeds:
            lines.append("【章节连续性】")
            if ctx.previous_chapter_summary:
                lines.append(f"- 上章摘要：{ctx.previous_chapter_summary}")
            if ctx.open_threads:
                lines.append("- 未解决问题：" + " / ".join(ctx.open_threads))
            if ctx.next_chapter_seeds:
                lines.append("- 下一步种子：" + " / ".join(ctx.next_chapter_seeds))

        if ctx.character_arc_stage or ctx.internal_conflict or ctx.recent_reflections:
            lines.append("【人物弧光】")
            if ctx.character_arc_stage:
                lines.append(f"- 当前心理阶段：{ctx.character_arc_stage}")
            if ctx.internal_conflict:
                lines.append(f"- 内心冲突：{ctx.internal_conflict}")
            if ctx.recent_reflections:
                lines.append("- 最近反思：" + " / ".join(ctx.recent_reflections))

        if ctx.soft_director_pressure:
            lines.append("【环境压力】" + " / ".join(ctx.soft_director_pressure))

        if ctx.disclosure_context_by_target:
            lines.append("【社交披露限制】")
            lines.append("- 私人事实可以驱动你的行动，但不代表可以说出口。")
            lines.append("- 对 private_disclosure_allowed=False 的目标，只允许使用公开信息、试探、回避、模糊回应。")
            lines.append(f"- 当前受保护私人事实数量：{len(ctx.private_facts)}（内容不在此处展开，禁止主动写出）")
            for target_id, disclosure_context in ctx.disclosure_context_by_target.items():
                lines.append(
                    f"- {target_id}: "
                    f"trust={disclosure_context.get('trust', 0)}, "
                    f"suspicion={disclosure_context.get('suspicion', 0)}, "
                    f"hostility={disclosure_context.get('hostility', 0)}, "
                    f"affinity={disclosure_context.get('affinity', 0)}, "
                    f"high_uncertainty={disclosure_context.get('high_uncertainty', True)}, "
                    f"private_disclosure_allowed={disclosure_context.get('private_disclosure_allowed', False)}, "
                    f"reason={disclosure_context.get('reason', '')}"
                )

        if ctx.recent_events:
            lines.append("【最近事件】")
            for e in ctx.recent_events:
                lines.append(f"- {e}")

        if ctx.relevant_memories:
            lines.append("【相关回忆】")
            for m in ctx.relevant_memories:
                conf = "确定" if m.memory.confidence > 0.8 else "怀疑"
                lines.append(f"- [{conf}] {m.memory.content}")

        lines.append("【可用动作】" + " / ".join(ctx.available_actions))
        lines.append("【可用目标(target)】" + " / ".join(ctx.available_targets))
        lines.append("【在场角色目标(ask/talk only)】" + (" / ".join(ctx.available_character_targets) if ctx.available_character_targets else "无"))
        lines.append("【target选择规则】move.target 只能从可移动地点中选择；observe/inspect/search/wait.target 从可用目标中选择；ask/talk.target 必须从【在场角色目标】中选择。若在场角色目标为“无”，禁止输出 ask/talk。禁止使用中文地点名作为 target。")

        if ctx.available_topics_by_target:
            lines.append("【可问 topic（按 target 分组）】")
            for t, topics in ctx.available_topics_by_target.items():
                lines.append(f"- {t}: {'、'.join(topics)}")

        lines.append(
            "\n请输出 JSON，严格遵循格式，字段包括：\n"
            "agent_id, intent, action_type, target, topic, method, dialogue, expected_gain, risk_level\n"
            "其中：\n"
            "- topic 可以为 null，但 ask/talk 必须有值\n"
            "- method 可以为空字符串\n"
            "- dialogue 可以为 null\n"
            "- expected_gain 不能为空\n"
            "- risk_level 必须是 low/medium/high 之一\n"
        )

        return "\n".join(lines)
