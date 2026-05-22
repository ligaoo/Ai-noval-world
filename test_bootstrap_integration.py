"""
端到端冒烟测试：验证 Bootstrap 是否真的接入了原有流程
不依赖 LLM、不依赖 web 服务。

通过点：
  1) StoryBootstrapper.bootstrap() 能产出 BootstrapResult
  2) BootstrapValidator 校验通过
  3) write_to_worlds_dir() 写入的目录能被 WorldConfig.from_directory 加载
  4) NarrativeService 能加载 writer_story_anchors.json
  5) EnvironmentEngine 通过 inspect 触发 clue 后，character 的 known_facts 中有
     "自然语言事实"（bootstrap_fact），不再只是 clue.id
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
    from app.models.action import ActionCommand
    from app.services.world_state_service import WorldStateService
    from app.services.environment_engine import EnvironmentEngine
    from app.services.narrative_service import NarrativeService

    print("=" * 70)
    print("Bootstrap 端到端冒烟测试")
    print("=" * 70)

    # ---- 1) 生成 ----
    bootstrapper = StoryBootstrapper(PROJECT_ROOT, llm_client=None)
    seed = BootstrapSeed(user_seed="废弃医院，午夜出现五楼，主角调查失踪妹妹")
    result = bootstrapper.bootstrap(seed, world_id="world_smoketest_001")

    assert result.bootstrap_id, "bootstrap_id 必须存在"
    assert result.title, "title 不能为空"
    assert len(result.characters) >= 5, f"角色数 {len(result.characters)} < 5"
    assert len(result.map) >= 5, f"地点数 {len(result.map)} < 5"
    assert len(result.clues) >= 3, f"线索数 {len(result.clues)} < 3"
    assert result.truth_chain, "truth_chain 必须存在"
    assert result.evidence_graph, "evidence_graph 必须存在"
    assert result.writer_story_anchors, "writer_story_anchors 必须存在"

    print(f"[1/5] OK 生成成功 title={result.title} chars={len(result.characters)} "
          f"locs={len(result.map)} clues={len(result.clues)} status={result.status}")

    ensemble_seed = BootstrapSeed(user_seed="噩梦医院，几个人一起醒来，必须在天亮前找到出口活下去")
    ensemble = bootstrapper.bootstrap(ensemble_seed, world_id="world_smoketest_ensemble")
    visible_active = [
        c for c in ensemble.characters
        if c.active_agent and c.visibility == "visible"
    ]
    opening_visible = [c for c in visible_active if c.location_id == "location_gate"]
    assert ensemble.parsed_seed.cast_mode == "ensemble_survival", \
        f"群像生存 seed 解析错误：{ensemble.parsed_seed}"
    assert len(visible_active) >= 3, \
        f"群像生存至少需要 3 个可见 active 角色，实际={[(c.character_id, c.role) for c in visible_active]}"
    assert len(opening_visible) >= 3, \
        f"群像生存开场至少 3 个可见角色同场，实际={[(c.character_id, c.location_id) for c in opening_visible]}"
    assert ensemble.writer_story_anchors and "只属于自己" in ensemble.writer_story_anchors.required_emotional_beat, \
        "群像生存叙事锚点不能退化成单人调查"
    assert ensemble.validation and ensemble.validation.passed, \
        f"群像生存 BootstrapValidator 失败：{[i.message for i in ensemble.validation.issues]}"
    print(f"[1b/5] OK 群像生存 seed 生成 visible_active={len(visible_active)} opening={len(opening_visible)}")

    # ---- 2) 校验通过 ----
    assert result.validation and result.validation.passed, \
        f"BootstrapValidator 失败：{[i.message for i in result.validation.issues]}"
    print(f"[2/5] OK BootstrapValidator 校验通过（0 issue, "
          f"{len(result.validation.warnings)} warn）")

    # ---- 3) 写盘 + WorldConfig 加载 ----
    world_dir = bootstrapper.write_to_worlds_dir(result)
    expected_files = [
        "world_bible.json", "characters.json", "map.json", "clues.json",
        "chapter_goal.json", "writer_story_anchors.json",
        "truth_chain.json", "evidence_graph.json",
        "open_threads.json", "opening_chapter_plan.json",
        "bootstrap_manifest.json", "bootstrap_result.json",
    ]
    for fn in expected_files:
        assert (world_dir / fn).exists(), f"缺少文件 {fn}"
    print(f"[3a/5] OK 写盘完成 {world_dir}，共 {len(expected_files)} 个文件")

    world = WorldConfig.from_directory(world_dir)
    assert world.world_id == "world_smoketest_001"
    assert len(world.characters.characters) >= 5
    assert len(world.map.locations) >= 5
    assert len(world.clues.clues) >= 3
    # 验证 bootstrap 扩展字段被透传
    sample_clue = world.clues.clues[0]
    assert hasattr(sample_clue, "bootstrap_fact") and sample_clue.bootstrap_fact, \
        "clue.bootstrap_fact 未透传"
    print(f"[3b/5] OK WorldConfig.from_directory 加载成功，"
          f"bootstrap_fact='{sample_clue.bootstrap_fact[:30]}...' 已透传")

    # ---- 4) NarrativeService 加载 anchors ----
    sim_dir = PROJECT_ROOT / "outputs" / "sim_smoketest_001"
    if sim_dir.exists():
        shutil.rmtree(sim_dir)
    sim_dir.mkdir(parents=True, exist_ok=True)

    narrative = NarrativeService(world=world, sim_dir=sim_dir, llm_client=None)
    assert narrative.story_anchors is not None, \
        "NarrativeService.story_anchors 未自动加载"
    assert narrative.story_anchors.get("protagonist_name")
    assert "禁止使用的泛化表达" or "forbidden_generic_phrases" in str(narrative.story_anchors)
    print(f"[4/5] OK NarrativeService 自动加载 anchors（"
          f"protagonist={narrative.story_anchors['protagonist_name']}, "
          f"goal='{narrative.story_anchors['protagonist_goal'][:20]}...'）")

    # ---- 5) EnvironmentEngine 触发 clue 后 bootstrap_fact 写入 known_facts ----
    state_svc = WorldStateService()
    state = state_svc.init_state(simulation_id="sim_smoketest_001", world=world, seed=1)
    engine = EnvironmentEngine(world=world, llm_client=None)
    pov_id = world.chapter_goal.pov

    # 找一个 inspect 类型的 clue，构造 action
    clue = next(c for c in world.clues.clues if any(r.action_type == "inspect" for r in c.discover_routes))
    route = next(r for r in clue.discover_routes if r.action_type == "inspect")

    # 把主角放到正确的 location，避免被 location 校验拒绝
    if route.location_id:
        state.characters[pov_id].location_id = route.location_id

    action = ActionCommand(
        agent_id=pov_id,
        intent="验证线索发现链路",
        action_type="inspect",
        target=route.target,
        topic=None,
        expected_gain="验证线索发现链路",
    )
    applied = engine.apply_action(state, action)

    pov_state = state.characters[pov_id]
    event_discovered = [fact for ev in applied.new_events for fact in ev.discovered_facts]
    print(f"      applied.discovered_facts={applied.action_result.discovered_facts}")
    print(f"      event.discovered_facts={event_discovered}")
    print(f"      pov.known_facts={pov_state.known_facts}")
    print(f"      pov.inventory={pov_state.inventory}")

    assert clue.id in pov_state.known_facts, \
        f"clue.id={clue.id} 未写入 known_facts"
    assert any(clue.bootstrap_fact in f for f in pov_state.known_facts), \
        f"bootstrap_fact='{clue.bootstrap_fact}' 未写入 known_facts"
    print(f"[5/5] OK EnvironmentEngine 触发 clue 后，自然语言事实已写入 known_facts")

    # ---- 清理 ----
    shutil.rmtree(sim_dir, ignore_errors=True)
    shutil.rmtree(world_dir, ignore_errors=True)

    print("=" * 70)
    print("OK 全部 5 项通过，Bootstrap 已真正接入现有流程")
    print("=" * 70)


if __name__ == "__main__":
    main()
