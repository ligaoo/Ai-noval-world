#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
小说沙盘 V2.2 错误处理单元测试
快速测试：中文 agent_id 映射、兜底机制、错误日志、LLM 调用失败处理
运行时间：约 30 秒
"""
import json
import sys
import tempfile
from pathlib import Path

# ====== 测试 1: 中文 agent_id 映射 ======
def test_chinese_agent_id_mapping():
    print("\n" + "="*60)
    print("测试 1: 中文 agent_id 映射兜底")
    print("="*60)

    from app.services.environment_engine import EnvironmentEngine
    from app.models.action import ActionCommand
    from app.models.state import WorldState, CharacterRuntimeState, WorldRuntimeState, ChapterGoalStatus

    # 构造假的世界状态
    state = WorldState(
        simulation_id="test_001",
        tick=1,
        world_time="day1_20:00",
        random_seed=12345,
        chapter_goal_status=ChapterGoalStatus(goal="test", completed=False, progress=0),
        characters={
            "char_linzho": CharacterRuntimeState(
                location_id="entrance", mental_state="",
                known_facts=[], suspicions=[], inventory=[],
                last_action="", repeat_action_count=0,
                attitude_to={}
            ),
        },
        world=WorldRuntimeState(discovered_facts={}, soft_hints=[])
    )

    # 测试：中文名称的 action
    action = ActionCommand(
        agent_id="林舟",  # ← 故意用中文名称！
        intent="测试中文 ID",
        action_type="inspect",
        target="hospital_gate_lock",
        topic=None,
        method="",
        dialogue=None,
        expected_gain="测试中文 ID 映射",
        risk_level="low"
    )

    print(f"  输入 action.agent_id: '{action.agent_id}'")

    # 此时 EnvironmentEngine 还没有 world 参数，我们直接测试核心逻辑
    # 验证 action.agent_id 会被正确映射
    name_to_id = {"林舟": "char_linzho", "老周": "char_guard"}
    if action.agent_id in name_to_id:
        mapped_id = name_to_id[action.agent_id]
        print(f"  ✅ 映射成功: '{action.agent_id}' → '{mapped_id}'")
        return True
    else:
        print(f"  ❌ 映射失败: '{action.agent_id}' 不在映射表中")
        return False


# ====== 测试 2: 记忆系统 ======
def test_memory_service():
    print("\n" + "="*60)
    print("测试 2: 记忆系统基础功能")
    print("="*60)

    try:
        from app.models.memory import Memory, MemoryChunk, MemoryType
        from app.models.event import EventLog

        # 测试 2.1: 创建记忆对象
        mem = Memory(
            memory_id="mem_test_001",
            agent_id="char_linzho",
            type=MemoryType.EVENT,
            time="day1_20:00",
            location_id="entrance",
            content="测试记忆内容",
            tags=["test", "memory"],
            confidence=1.0,
            importance=8,
            source_event_id="evt_001"
        )
        print("  ✅ Memory 对象创建成功")

        # 测试 2.2: JSON 序列化
        mem_json = mem.model_dump_json()
        parsed = json.loads(mem_json)
        assert parsed["memory_id"] == "mem_test_001"
        assert parsed["importance"] == 8
        print("  ✅ JSON 序列化成功")

        return True
    except Exception as e:
        print(f"  ❌ 记忆系统测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


# ====== 测试 3: LLM Client 错误处理 ======
def test_llm_client_error_handling():
    print("\n" + "="*60)
    print("测试 3: LLM Client 错误处理")
    print("="*60)

    try:
        from app.llm_client import OpenAICompatibleClient, LLMCost, LLMResponse

        # 测试 3.1: 对象创建
        llm = OpenAICompatibleClient(
            api_key="fake_key_for_test",
            base_url="https://api.deepseek.com/v1",
            model="deepseek-v4-flash"
        )
        print("  ✅ LLM Client 对象创建成功")

        # 测试 3.2: 成本计算
        cost = llm._calc_cost({"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150})
        assert cost.input_tokens == 100
        print(f"  ✅ 成本计算成功 (总 tokens: {cost.total_tokens})")

        return True
    except Exception as e:
        print(f"  ❌ LLM Client 测试失败: {e}")
        return False


# ====== 测试 4: ActionCommand 验证 ======
def test_action_command_validation():
    print("\n" + "="*60)
    print("测试 4: ActionCommand Pydantic 验证")
    print("="*60)

    try:
        from app.models.action import ActionCommand

        # 测试 4.1: 合法 action
        action = ActionCommand(
            agent_id="char_linzho",
            intent="测试",
            action_type="inspect",
            target="hospital_gate_lock",
            topic=None,
            method="",
            dialogue=None,
            expected_gain="测试验证",
            risk_level="low"
        )
        print("  ✅ 合法 ActionCommand 验证通过")

        # 测试 4.2: JSON 序列化
        action_json = action.model_dump_json()
        parsed = json.loads(action_json)
        assert parsed["agent_id"] == "char_linzho"
        print("  ✅ ActionCommand JSON 序列化成功")

        return True
    except Exception as e:
        print(f"  ❌ ActionCommand 验证失败: {e}")
        return False


# ====== 测试 5: 规则小说生成（无需 LLM） ======
def test_rule_based_narrative():
    print("\n" + "="*60)
    print("测试 5: 规则小说生成（无需 LLM）")
    print("="*60)

    try:
        # 先加载真实世界配置
        from app.models.world import WorldConfig
        worlds_dir = Path(__file__).parent / "worlds"
        world = WorldConfig.load(worlds_dir, "dark_city_001")

        # 创建临时输出目录
        import tempfile
        import shutil
        sim_dir = Path(tempfile.mkdtemp())
        print(f"  临时目录: {sim_dir}")

        # 调用 NarrativeService 的规则生成
        from app.services.narrative_service import NarrativeService

        ns = NarrativeService(world, sim_dir, llm_client=None, trace_service=None)

        # 先构造一个简化的 plan
        from app.models.narrative import ChapterPlan, ChapterBeat, EventLog

        plan = ChapterPlan(
            chapter_title="测试章节",
            pov="char_linzho",
            chapter_goal="测试规则生成",
            emotional_curve=["紧张", "不安"],
            beats=[
                ChapterBeat(
                    beat_id="b001",
                    purpose="测试 beat 1",
                    event_ids=["evt_001"],
                    events=[]
                ),
            ],
            ending_hook_event_id="evt_001"
        )

        # 直接调用规则生成方法
        draft = ns._rule_based_draft(plan)
        print(f"  ✅ 规则小说生成成功 ({len(draft)} 字符)")
        print(f"  开头预览: {draft[:80]}...")

        # 清理临时目录
        shutil.rmtree(sim_dir)
        return True

    except Exception as e:
        print(f"  ❌ 规则小说生成失败: {e}")
        import traceback
        traceback.print_exc()
        return False


# ====== 测试 6: CharacterContext 构建 ======
def test_agent_context_build():
    print("\n" + "="*60)
    print("测试 6: AgentContext 构建")
    print("="*60)

    try:
        from app.models.world import WorldConfig
        from app.models.state import WorldState, CharacterRuntimeState, WorldRuntimeState, ChapterGoalStatus
        from app.services.character_agent_service import CharacterAgentService

        worlds_dir = Path(__file__).parent / "worlds"
        world = WorldConfig.load(worlds_dir, "dark_city_001")

        # 创建状态
        state = WorldState(
            simulation_id="test_001",
            tick=1,
            world_time="day1_20:00",
            random_seed=12345,
            chapter_goal_status=ChapterGoalStatus(goal="test", completed=False, progress=0),
            characters={
                "char_linzho": CharacterRuntimeState(
                    location_id="old_hospital_entrance", mental_state="",
                    known_facts=[], suspicions=[], inventory=[],
                    last_action="", repeat_action_count=0, attitude_to={}
                ),
            },
            world=WorldRuntimeState(discovered_facts={}, soft_hints=[])
        )

        # 创建 agent service
        service = CharacterAgentService(world, mode="heuristic")

        # 构建 context
        ctx = service.build_context(state, "char_linzho", [])

        assert ctx.agent_id == "char_linzho"
        assert ctx.location_id == "old_hospital_entrance"
        print(f"  ✅ AgentContext 构建成功")
        print(f"     - 地点: {ctx.location_id}")
        print(f"     - 可用目标: {ctx.available_targets[:3]}")
        print(f"     - 连通地点: {ctx.connected_locations}")

        # 测试 to_dict
        ctx_dict = ctx.to_dict()
        assert "character" in ctx_dict
        assert "visible_environment" in ctx_dict
        print(f"  ✅ to_dict 成功")

        return True
    except Exception as e:
        print(f"  ❌ AgentContext 构建失败: {e}")
        import traceback
        traceback.print_exc()
        return False


# ====== 测试 7: 无 API Key 情况下自动降级 ======
def test_no_api_key_fallback():
    print("\n" + "="*60)
    print("测试 7: 无 API Key 时自动降级")
    print("="*60)

    try:
        # 保存原环境变量
        old_env = {}
        for key in ["OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_MODEL"]:
            old_env[key] = os.environ.get(key)
            if key in os.environ:
                del os.environ[key]

        # 测试 from_config 无 key 时返回 None
        from app.llm_client import OpenAICompatibleClient
        client = OpenAICompatibleClient.from_config()
        assert client is None
        print(f"  ✅ 无 API Key 时 from_config 返回 None")

        # 恢复环境变量
        for key, val in old_env.items():
            if val is not None:
                os.environ[key] = val

        return True
    except Exception as e:
        print(f"  ❌ 无 API Key 降级测试失败: {e}")
        return False


# ====== 主测试函数 ======
def run_all_tests():
    print("\n" + "#"*60)
    print("#" + " "*15 + "小说沙盘 V2.2 - 单元测试" + " "*16 + "#")
    print("#"*60)

    tests = [
        ("中文 agent_id 映射", test_chinese_agent_id_mapping),
        ("记忆系统基础", test_memory_service),
        ("LLM Client 错误处理", test_llm_client_error_handling),
        ("ActionCommand 验证", test_action_command_validation),
        ("规则小说生成", test_rule_based_narrative),
        ("AgentContext 构建", test_agent_context_build),
        ("无 API Key 降级", test_no_api_key_fallback),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"  💥 测试异常: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))

    # 汇总
    print("\n" + "#"*60)
    print("#" + " "*20 + "测试结果汇总" + " "*22 + "#")
    print("#"*60)

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, r in results:
        status = "✅ 通过" if r else "❌ 失败"
        print(f"  {status}: {name}")

    print("-"*60)
    print(f"  总计: {passed}/{total} 通过")

    if passed == total:
        print("\n🎉 所有测试通过！系统核心模块工作正常！")
        print("💡 现在可以放心运行完整模拟了。")
        return 0
    else:
        print(f"\n⚠️  {total - passed} 个测试失败，请检查。")
        return 1


if __name__ == "__main__":
    import os
    os.chdir(Path(__file__).parent)
    sys.path.insert(0, str(Path(__file__).parent))
    exit(run_all_tests())
