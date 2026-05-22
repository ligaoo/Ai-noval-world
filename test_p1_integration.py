"""
P1 端到端冒烟测试：验证 4 个后端特性都真的接入了运行流程

特性清单：
  P1-1 InterventionDeduplicator：相同 hint_key 第二次会被丢弃
  P1-2 DirectorService.clue_route_hint：有未发现 clue 时优先生成 clue_route_hint
  P1-3 MultiAgentScheduler.build_order：顺序 = 主角 → 同地点 NPC → hidden_actor → 其他
  P1-4 VisibleEventFilter：hidden_actor 的事件 visible_to 不含主角

不依赖 LLM / 不依赖 web 服务。
"""
from __future__ import annotations

import sys
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))


def main():
    from app.bootstrap import BootstrapSeed, StoryBootstrapper
    from app.models.world import WorldConfig
    from app.models.event import EventLog
    from app.models.event import PlotValue as EventPlotValue
    from app.models.tension import PlotValue, TensionReport, TensionScores, InterventionProposal
    from app.services.world_state_service import WorldStateService
    from app.services.director_service import DirectorService
    from app.services.intervention_deduplicator import InterventionDeduplicator
    from app.services.multi_agent_scheduler import MultiAgentScheduler
    from app.services.visible_event_filter import VisibleEventFilter

    print("=" * 70)
    print("P1 端到端冒烟测试")
    print("=" * 70)

    # ---- 准备一份 bootstrap 世界 ----
    bootstrapper = StoryBootstrapper(PROJECT_ROOT, llm_client=None)
    seed = BootstrapSeed(user_seed="废弃医院，午夜出现五楼，主角调查失踪妹妹")
    result = bootstrapper.bootstrap(seed, world_id="world_p1_smoke")
    world_dir = bootstrapper.write_to_worlds_dir(result)
    world = WorldConfig.from_directory(world_dir)

    state_svc = WorldStateService()
    state = state_svc.init_state(simulation_id="sim_p1_smoke", world=world, seed=1)
    state.tick = 5

    # ====================================================================
    # P1-1 InterventionDeduplicator
    # ====================================================================
    dedup = InterventionDeduplicator()
    proposal_a = InterventionProposal(
        need_intervention=True, reason="test", intervention_type="clue_route_hint",
        target_location="location_gate", content="门锁有划痕",
        allowed_followup_actions=["inspect"], forbidden_effects=[],
        plot_value=PlotValue(progress=2),
        hint_key="clue_route__clue_new_lock_core",
    )
    proposal_b = InterventionProposal(
        need_intervention=True, reason="test", intervention_type="clue_route_hint",
        target_location="location_gate", content="门锁有划痕",
        allowed_followup_actions=["inspect"], forbidden_effects=[],
        plot_value=PlotValue(progress=2),
        hint_key="clue_route__clue_new_lock_core",  # 同 key
    )

    assert dedup.is_duplicate(proposal_a, state) is False, "第一次应不算重复"
    dedup.record(proposal_a)
    assert dedup.is_duplicate(proposal_b, state) is True, "第二次同 hint_key 必须算重复"
    assert dedup.dropped_count == 1
    print(f"[1/4] OK InterventionDeduplicator 命中去重，dropped={dedup.dropped_count}")

    # ====================================================================
    # P1-2 DirectorService 优先生成 clue_route_hint
    # ====================================================================
    director = DirectorService(world_dir)
    # 模拟一个 tick 时间窗口已超过 cooldown
    director.last_intervention_tick = 0
    state.tick = 10
    tension = TensionReport(
        simulation_id="sim_p1_smoke",
        tick=10,
        window="last_5",
        scores=TensionScores(progress=0.5, mystery=2.0),
        diagnosis=["主线推进不足，progress 长期偏低"],
        recommended_intervention_types=["environment_hint", "npc_pressure"],
        need_intervention=True,
    )
    proposal = director.propose_intervention(state, tension, chapter_goal="Setup")
    assert proposal is not None, "Director 应给出干预"
    assert proposal.intervention_type == "clue_route_hint", \
        f"应优先生成 clue_route_hint，实际={proposal.intervention_type}"
    assert proposal.target_clue_id, "clue_route_hint 必须绑定 target_clue_id"
    assert proposal.hint_key and proposal.hint_key.startswith("clue_route__"), \
        f"hint_key 异常={proposal.hint_key}"
    print(f"[2/4] OK Director 生成 clue_route_hint："
          f"clue={proposal.target_clue_id}, hint_key={proposal.hint_key}")

    # ====================================================================
    # P1-3 MultiAgentScheduler.build_order
    # ====================================================================
    scheduler = MultiAgentScheduler(world)
    order = scheduler.build_order(state)
    # 第一个必须是 POV
    assert order[0] == world.chapter_goal.pov, f"第一个必须是 POV，实际={order[0]}"
    # 必须包含 hidden_actor
    hidden_ids = [c.id for c in world.characters.characters
                  if (c.model_dump().get("visibility") == "hidden")]
    assert any(h in order for h in hidden_ids), \
        f"hidden_actor 必须被纳入调度，hidden={hidden_ids}, order={order}"
    # 不应该包含 missing_person（active_agent=false / visibility=absent）
    missing_ids = [c.id for c in world.characters.characters
                   if c.model_dump().get("visibility") == "absent"
                   or c.model_dump().get("active_agent") is False]
    for mid in missing_ids:
        assert mid not in order, f"缺席人物 {mid} 不应被调度"
    print(f"[3/4] OK MultiAgentScheduler.build_order={order}")
    print(f"        - POV={order[0]}")
    print(f"        - hidden_actor 进入调度={any(h in order for h in hidden_ids)}")
    print(f"        - 缺席人物已排除={missing_ids}")

    # ====================================================================
    # P1-4 VisibleEventFilter：hidden_actor 事件不被主角看见
    # ====================================================================
    ve_filter = VisibleEventFilter()
    pov = world.chapter_goal.pov
    hidden_id = hidden_ids[0] if hidden_ids else "npc_hidden_actor"

    pov_event = EventLog(
        event_id="evt_pov_001",
        event_level="plot",
        time="day1_14:00",
        event_type="action",
        location_id="location_gate",
        actors=[pov],
        action=None,
        result="主角观察了门锁",
        visible_to=[],
        plot_value=EventPlotValue(progress=1),
    )
    hidden_event = EventLog(
        event_id="evt_hidden_001",
        event_level="plot",
        time="day1_14:00",
        event_type="action",
        location_id="location_basement",
        actors=[hidden_id],
        action=None,
        result="hidden_actor 取走了关键档案",
        visible_to=[],
        plot_value=EventPlotValue(progress=1),
    )

    filtered = ve_filter.filter_events([pov_event, hidden_event], pov, scheduler)
    # 找出两条事件 visible_to
    pov_vt = next((e.visible_to for e in filtered if e.event_id == "evt_pov_001"), None)
    hidden_vt = next((e.visible_to for e in filtered if e.event_id == "evt_hidden_001"), None)
    assert pov in (pov_vt or []), f"POV 自己的事件 POV 必须可见，vt={pov_vt}"
    assert pov not in (hidden_vt or []), \
        f"hidden_actor 的事件不能给 POV 看，vt={hidden_vt}"

    # filter_for_narrative：只剩 POV 可见
    narr_events = ve_filter.filter_for_narrative(filtered, pov)
    assert any(e.event_id == "evt_pov_001" for e in narr_events)
    assert not any(e.event_id == "evt_hidden_001" for e in narr_events), \
        "正文用事件中不能包含 hidden_actor 行动"

    print(f"[4/4] OK VisibleEventFilter：")
    print(f"        - pov_event.visible_to={pov_vt}")
    print(f"        - hidden_event.visible_to={hidden_vt}（POV 不在其中）")
    print(f"        - filter_for_narrative 已剔除 hidden 行动")

    # ---- 清理 ----
    shutil.rmtree(world_dir, ignore_errors=True)

    print("=" * 70)
    print("OK 全部 4 项 P1 通过：去重 / clue_route_hint / 多角色调度 / 可见性过滤")
    print("=" * 70)


if __name__ == "__main__":
    main()
