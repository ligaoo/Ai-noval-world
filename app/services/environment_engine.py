from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import List, Optional, Tuple

from app.models.action import ActionCommand, ActionResult, RelationshipChange, StateChange
from app.models.event import EventLog, PlotValue
from app.models.state import WorldState
from app.models.world import Clue, DiscoverRoute, WorldConfig
from app.services.dynamic_content_generator import DynamicContentGenerator


@dataclass
class AppliedResult:
    action_result: ActionResult
    new_events: List[EventLog]


class EnvironmentEngine:
    """
    V5.0 环境裁判：支持动态内容生成
    - 当没有预设线索时，自动生成合理的发现
    - 让系统具备"想象力"，不需要用户提供所有细节
    """

    def __init__(self, world: WorldConfig, llm_client=None):
        self.world = world
        self.dynamic_generator = DynamicContentGenerator(world, llm_client)
        self.current_chapter = 1

    def apply_action(self, state: WorldState, action: ActionCommand) -> AppliedResult:
        # 0) 兜底修复：如果 LLM 返回了中文名称，映射到角色ID（基于当前世界的角色配置动态生成）
        if action.agent_id not in state.characters:
            name_to_id = {char.name: char.id for char in self.world.characters.characters}
            if action.agent_id in name_to_id:
                action.agent_id = name_to_id[action.agent_id]

        # 0) validity 基础检查
        if action.agent_id not in state.characters:
            return self._invalid(state, action, f"actor 不存在: {action.agent_id}")
        if action.action_type in ("ask", "talk") and not action.topic:
            return self._invalid(state, action, "ask/talk 必须提供 topic（Topic-based Dialogue）")
        if not action.expected_gain:
            return self._invalid(state, action, "expected_gain 不能为空（用于判定动作合理性）")

        actor_state = state.characters[action.agent_id]

        # 1) repeat_action_count
        signature = self._action_signature(action)
        if actor_state.last_action == signature:
            actor_state.repeat_action_count += 1
        else:
            actor_state.repeat_action_count = 0
        actor_state.last_action = signature

        # 2) 执行核心判定与线索触发
        result_text, discovered, plot_value, rel_changes, state_changes, reason = self._judge_and_apply(state, action)

        # 3) 更新 chapter_goal progress
        if plot_value.progress > 0:
            state.chapter_goal_status.progress = min(
                100, state.chapter_goal_status.progress + plot_value.progress
            )
            if state.chapter_goal_status.progress >= self.world.chapter_goal.target_progress:
                state.chapter_goal_status.completed = True

        # 4) 应用状态变化（包括 location 变化）
        for sc in state_changes:
            self._apply_state_change(state, sc)

        # 5) 生成事件
        new_events: List[EventLog] = []
        raw_event = self._make_event(
            state=state,
            action=action,
            event_level="raw",
            event_type="action_result",
            result=result_text,
            plot_value=plot_value if (plot_value.mystery or plot_value.conflict or plot_value.progress) else PlotValue(),
            discovered_facts=discovered,
        )
        new_events.append(raw_event)

        if discovered or rel_changes or (plot_value.mystery + plot_value.conflict + plot_value.progress >= 3):
            plot_event = self._make_event(
                state=state,
                action=action,
                event_level="plot",
                event_type="plot_event",
                result=result_text,
                plot_value=plot_value,
                discovered_facts=discovered,
            )
            new_events.append(plot_event)

        action_result = ActionResult(
            valid=True,
            success=True,
            result=result_text,
            discovered_facts=discovered,
            state_changes=state_changes,
            relationship_changes=rel_changes,
            triggered_events=[e.event_id for e in new_events],
            reason_for_judgement=reason,
        )
        return AppliedResult(action_result=action_result, new_events=new_events)

    # ----------------------------
    # 判定逻辑
    # ----------------------------

    def _judge_and_apply(
        self, state: WorldState, action: ActionCommand
    ) -> Tuple[str, List[str], PlotValue, List[RelationshipChange], List[StateChange], str]:
        actor_state = state.characters[action.agent_id]
        state_changes: List[StateChange] = []

        # V2.2：move 动作专门处理
        if action.action_type == "move":
            return self._handle_move(state, action, actor_state)

        # 目标存在性（对象或人物）
        if action.action_type in ("inspect", "search", "observe", "wait"):
            loc = self.world.map.get_location(actor_state.location_id)
            valid_targets = {o.id for o in loc.objects}
            for other_id, other_state in state.characters.items():
                if other_state.location_id == actor_state.location_id and other_id != action.agent_id:
                    valid_targets.add(other_id)

            # 添加运行时解锁的目标
            for obj_id, obj_data in state.world.objects.items():
                if obj_data.get("location_id") == actor_state.location_id:
                    valid_targets.add(obj_id)

            if action.target not in valid_targets and action.target != actor_state.location_id:
                return (
                    "你试图做点什么，但目标并不明确。",
                    [],
                    PlotValue(),
                    [],
                    [],
                    f"target 不存在或不可交互: {action.target}",
                )

        if action.action_type in ("ask", "talk"):
            if action.target not in state.characters:
                return ("你对着空气说话，没有得到回应。", [], PlotValue(), [], [], "对话目标不存在")

            if state.characters[action.target].location_id != actor_state.location_id:
                return ("对方不在这里。", [], PlotValue(), [], [], "对话目标不在场")

        # 线索发现（discover_routes）
        discovered: List[str] = []
        plot_value = PlotValue()
        rel_changes: List[RelationshipChange] = []

        matched, clue, route, reason = self._match_discover_route(state, action)
        if matched and clue and route:
            ok, reason2 = self._check_route_conditions(state, action, clue, route)
            if ok:
                # V3.3：检查线索阶段锁 - 防止核心线索过早暴露
                if hasattr(self, 'plot_arc_service') and self.plot_arc_service:
                    if not self.plot_arc_service.can_discover_clue(clue.model_dump()):
                        # 返回模糊结果，不直接给真相
                        blocked_text = self.plot_arc_service.get_blocked_clue_message(clue.model_dump())
                        return (blocked_text, [], PlotValue(mystery=2, conflict=0, progress=0), rel_changes, state_changes, "当前阶段无法解锁该线索")

                if not state.world.discovered_facts.get(clue.id, False):
                    state.world.discovered_facts[clue.id] = True
                    discovered.append(clue.id)
                    self._apply_known_fact(state, action.agent_id, clue)
                plot_value = PlotValue(
                    mystery=clue.on_discovered.plot_value.mystery,
                    conflict=clue.on_discovered.plot_value.conflict,
                    progress=clue.on_discovered.plot_value.progress,
                )
                if action.action_type in ("ask", "talk"):
                    rc = RelationshipChange(from_id=action.target, to_id=action.agent_id, delta=-1)
                    rel_changes.append(rc)
                    self._apply_relation(state, rc)
                return (route.result_text, discovered, plot_value, rel_changes, state_changes, f"{reason}; {reason2}")

            fail_text = self._route_fail_text(action, clue, route)
            if action.action_type in ("ask", "talk"):
                rc = RelationshipChange(from_id=action.target, to_id=action.agent_id, delta=-2)
                rel_changes.append(rc)
                self._apply_relation(state, rc)
            return (fail_text, [], PlotValue(mystery=1, conflict=0, progress=0), rel_changes, state_changes, f"{reason}; {reason2}")

        # V5.0：如果没有预设线索，使用动态内容生成
        generic_text = self._generic_result(state, action)

        # 特殊处理 Director 干预解锁的目标
        if action.target.startswith("hint_"):
            hint_plot_value = PlotValue(
                progress=2,
                mystery=3,
                conflict=0,
                danger=1,
                relationship=0,
                novelty=2,
                emotion=1,
            )
            return (generic_text, [], hint_plot_value, [], state_changes, "检查 Director 提示的目标")

        # V5.0：动态生成发现内容，不再返回空的 plot_value
        if action.action_type in ("inspect", "search"):
            # 使用动态内容生成器生成有意义的发现
            location_id = state.characters[action.agent_id].location_id
            discovery = self.dynamic_generator.generate_discovery_for_inspect(
                location_id=location_id,
                target=action.target,
                current_chapter=self.current_chapter,
                current_progress=state.chapter_goal_status.progress,
            )
            return (
                discovery.content,
                [],
                discovery.plot_value,
                [],
                state_changes,
                "动态生成的发现内容",
            )
        elif action.action_type in ("ask", "talk"):
            # 动态生成对话回答
            answer, plot_value = self.dynamic_generator.generate_discovery_for_ask(
                speaker_id=action.agent_id,
                listener_id=action.target,
                topic=action.topic,
                current_chapter=self.current_chapter,
            )
            return (answer, [], plot_value, [], state_changes, "动态生成的对话内容")

        return (generic_text, [], PlotValue(), [], state_changes, "未命中 discover_routes，按通用规则返回")

    def _handle_move(
        self, state: WorldState, action: ActionCommand, actor_state
    ) -> Tuple[str, List[str], PlotValue, List[RelationshipChange], List[StateChange], str]:
        """处理 move 动作。"""
        from_location = self.world.map.get_location(actor_state.location_id)
        to_location = self.world.map.get_location(action.target)

        # 更新 location
        state_changes = [
            StateChange(op="set", path=f"characters.{action.agent_id}.location_id", value=action.target)
        ]

        # 生成移动描述
        result_text = (
            f"你从{from_location.name}走进了{to_location.name}。{to_location.public_description}"
        )

        # 轻微 progress（移动到新地点本身就是一种探索）
        plot_value = PlotValue(progress=1)

        return (
            result_text,
            [],  # discovered
            plot_value,
            [],  # rel_changes
            state_changes,
            f"成功从 {from_location.id} 移动到 {to_location.id}",
        )

    def _match_discover_route(
        self, state: WorldState, action: ActionCommand
    ) -> Tuple[bool, Optional[Clue], Optional[DiscoverRoute], str]:
        actor_location = state.characters[action.agent_id].location_id
        for clue in self.world.clues.clues:
            for r in clue.discover_routes:
                if r.action_type != action.action_type:
                    continue
                if r.target != action.target:
                    continue
                if r.location_id and r.location_id != actor_location:
                    continue
                if r.topic is not None and r.topic != action.topic:
                    continue
                return True, clue, r, f"匹配 discover_route: {clue.id}/{r.route_id}"
        return False, None, None, "未匹配 discover_route"

    def _check_route_conditions(
        self, state: WorldState, action: ActionCommand, clue: Clue, route: DiscoverRoute
    ) -> Tuple[bool, str]:
        actor_profile = self.world.characters.get_character(action.agent_id)
        actor_state = state.characters[action.agent_id]

        # ask/talk 的关系阈值
        if action.action_type in ("ask", "talk") and route.min_attitude is not None:
            target_state = state.characters[action.target]
            attitude = target_state.attitude_to.get(action.agent_id, 0)
            if attitude < route.min_attitude:
                return False, f"关系不足 attitude={attitude} < min_attitude={route.min_attitude}"

        # skill check
        if route.required_skill:
            skill = int(actor_profile.skills.get(route.required_skill, 0))
            roll = self._roll_d100(state.random_seed, state.tick, action.agent_id, action.action_type, action.target)
            total = skill
            ok = total >= route.difficulty
            return ok, f"技能检定 {route.required_skill}={skill} vs diff={route.difficulty}, roll={roll}（V2 暂不叠加）"

        return True, "无需技能检定"

    def _apply_known_fact(self, state: WorldState, discoverer_id: str, clue: Clue) -> None:
        # 优先使用 Bootstrap 注入的自然语言事实（bootstrap_fact），
        # 否则回退到 clue.id 作为 known_fact 标识
        # 兼容现有 Clue 模型：动态字段从原始 model_dump 中取
        try:
            clue_dict = clue.model_dump()
        except Exception:
            clue_dict = {}

        nl_fact = clue_dict.get("bootstrap_fact") or clue.id
        inventory_item = clue_dict.get("bootstrap_inventory")

        def _record(cs):
            # 把自然语言事实和 clue.id 都加入 known_facts，
            # 这样 character_agent_service 在拼 prompt 时可读到"具体内容"，
            # 而 consistency_service 还能用 clue.id 做引用校验
            if nl_fact and nl_fact not in cs.known_facts:
                cs.known_facts.append(nl_fact)
            if clue.id not in cs.known_facts:
                cs.known_facts.append(clue.id)
            if inventory_item and inventory_item not in cs.inventory:
                cs.inventory.append(inventory_item)

        if clue.on_discovered.add_known_fact_to == "all":
            for cid, cs in state.characters.items():
                _record(cs)
        else:
            cs = state.characters.get(discoverer_id)
            if cs is not None:
                _record(cs)

    @staticmethod
    def _apply_relation(state: WorldState, rc: RelationshipChange) -> None:
        from_state = state.characters.get(rc.from_id)
        if not from_state:
            return
        before = from_state.attitude_to.get(rc.to_id, 0)
        from_state.attitude_to[rc.to_id] = before + rc.delta

    @staticmethod
    def _apply_state_change(state: WorldState, sc: StateChange) -> None:
        """应用状态变化，支持嵌套路径。"""
        parts = sc.path.split(".")
        obj = state
        for part in parts[:-1]:
            if hasattr(obj, part):
                obj = getattr(obj, part)
            elif isinstance(obj, dict):
                obj = obj[part]
        last = parts[-1]
        if hasattr(obj, last):
            setattr(obj, last, sc.value)
        elif isinstance(obj, dict):
            obj[last] = sc.value

    # ----------------------------
    # 事件生成
    # ----------------------------

    def _make_event(
        self,
        state: WorldState,
        action: ActionCommand,
        event_level: str,
        event_type: str,
        result: str,
        plot_value: PlotValue,
        discovered_facts: Optional[List[str]] = None,
    ) -> EventLog:
        location_id = state.characters[action.agent_id].location_id
        event_id = self._new_event_id(state, action, event_level)
        return EventLog(
            event_id=event_id,
            event_level=event_level,  # raw|plot
            time=state.world_time,
            location_id=location_id,
            actors=[action.agent_id],
            event_type=event_type,
            action=action,
            result=result,
            visible_to=[action.agent_id],
            discovered_facts=list(discovered_facts or []),
            plot_value=plot_value,
        )

    @staticmethod
    def _new_event_id(state: WorldState, action: ActionCommand, event_level: str) -> str:
        base = f"{state.simulation_id}:{state.tick}:{action.agent_id}:{action.action_type}:{action.target}:{event_level}"
        h = hashlib.md5(base.encode("utf-8")).hexdigest()[:8]
        return f"evt_{state.tick:04d}_{h}"

    # ----------------------------
    # 文本与兜底
    # ----------------------------

    def _route_fail_text(self, action: ActionCommand, clue: Clue, route: DiscoverRoute) -> str:
        actor_name = action.agent_id
        try:
            actor = self.world.characters.get_character(action.agent_id)
            actor_name = actor.name if actor else action.agent_id
        except Exception:
            actor_name = action.agent_id
        if action.action_type in ("ask", "talk"):
            return f"对方的回答含糊其辞，{actor_name}更确定这里有人在回避问题。"
        if action.action_type in ("inspect", "search"):
            return f"{actor_name}仔细看了看，却没有得到能支撑判断的细节。"
        return f"{actor_name}没有得到任何新的信息。"

    def _generic_result(self, state: WorldState, action: ActionCommand) -> str:
        actor_name = action.agent_id
        actor = self.world.characters.get_character(action.agent_id)
        if actor:
            actor_name = actor.name

        if action.action_type == "observe":
            loc = self.world.map.get_location(state.characters[action.agent_id].location_id)
            return loc.public_description
        if action.action_type == "inspect":
            # 特殊处理 Director 干预解锁的目标
            if action.target.startswith("hint_"):
                runtime_obj = state.world.objects.get(action.target, {})
                description = runtime_obj.get("description") or "这里出现了一个可检查的新细节。"
                return f"{actor_name}检查了新出现的线索点。{description}"

            loc = self.world.map.get_location(state.characters[action.agent_id].location_id)
            obj = next((o for o in loc.objects if o.id == action.target), None)
            if obj:
                return f"你检查了{obj.name}，但暂时没发现异常。"
            return "你检查了一会儿，没有收获。"
        if action.action_type == "search":
            return "你翻找了一遍，可疑的只有灰尘和旧纸屑。"
        if action.action_type in ("ask", "talk"):
            return "对方看了你一眼，没有把话说透。"
        if action.action_type == "wait":
            return "时间在沉默里往前挪了一点。"
        if action.action_type == "move":
            return "你换了个位置，试图从不同角度看清这里。"
        return "你什么也没得到。"

    def _invalid(self, state: WorldState, action: ActionCommand, reason: str) -> AppliedResult:
        ev = self._make_event(
            state=state,
            action=action,
            event_level="raw",
            event_type="invalid_action",
            result=f"无效动作：{reason}",
            plot_value=PlotValue(),
        )
        res = ActionResult(valid=False, success=False, result=ev.result, reason_for_judgement=reason)
        return AppliedResult(action_result=res, new_events=[ev])

    @staticmethod
    def _action_signature(action: ActionCommand) -> str:
        t = action.topic or ""
        return f"{action.action_type}:{action.target}:{t}"

    @staticmethod
    def _roll_d100(seed: int, tick: int, actor_id: str, action_type: str, target: str) -> int:
        raw = f"{seed}:{tick}:{actor_id}:{action_type}:{target}".encode("utf-8")
        h = hashlib.sha256(raw).hexdigest()
        n = int(h[:8], 16)
        return (n % 100) + 1
