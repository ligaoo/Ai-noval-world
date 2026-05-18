# 小说沙盘引擎 V3.6 Patch

> **V3.6 Patch 核心：补齐 V3.5 Debug / 可观测性最小闭环，并修复 V1-V3.4 的关键对齐问题**
>
> - ✅ 运行产物标准化：run_manifest / run_status / run_index
> - ✅ 每 tick 状态快照：state_snapshots/
> - ✅ 基础 metrics 与 tuning_report
> - ✅ V3 上下文注入 Agent prompt
> - ✅ CLI temperature / max-retries 参数生效
> - ✅ Consistency RuleCheck 基础拦截

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 运行模式

#### 模式 A：脚本测试（最快）
```bash
python -m app.cli --world dark_city_001 --mode scripted --ticks 10
```

#### 模式 B：启发式 Agent（无需 API Key）
```bash
python -m app.cli --world dark_city_001 --mode heuristic --ticks 15
```

#### 模式 C：LLM Agent（需要 API Key）
```bash
# 设置环境变量（Windows）
$env:OPENAI_API_KEY = "sk-..."
$env:OPENAI_BASE_URL = "https://api.openai.com/v1"  # 或兼容网关
$env:OPENAI_MODEL = "gpt-4o-mini"

# 运行
python -m app.cli --world dark_city_001 --mode llm --ticks 15 --temperature 0.2 --max-retries 2
```

## 输出目录结构

每次运行会在 `outputs/sim_xxx/` 下生成：

```
sim_xxx/
├── run_manifest.json      # 运行元信息：world、seed、engine_version、输入文件
├── run_status.json        # 运行状态：running/completed/failed、当前 tick、最后错误
├── run_index.json         # 关键产物索引
├── state.json             # 世界状态快照
├── state_snapshots/       # 每 tick 状态快照
├── events.jsonl           # 全量事件日志（逐行 append）
├── memories.jsonl         # 角色记忆
├── plot_arc_state.json    # 剧情阶段状态
├── character_arcs_state.json # 人物弧光状态
├── chapter_plan.json      # 章节大纲（规则生成）
├── chapter_draft.md       # 章节正文（模板改写）
├── consistency_report.json # 一致性检查报告
├── metrics.json           # 运行指标
├── tuning_report.md       # 调参建议
├── errors.jsonl           # 统一错误上下文
├── llm_traces.jsonl       # LLM 调用 Trace（仅 llm 模式）
└── llm_summary.json       # LLM 调用汇总（成本 / token / 失败率，仅 llm 模式）
```

## 当前版本链路

- **V1**：模拟 → EventLog → 章节生成 → 一致性检查
- **V2.1**：LLM Agent JSON 决策、重试与 fallback
- **V2.2**：多地点、move、地点上下文隔离
- **V2.3**：记忆、LLM 小说改写、一致性修订
- **V3.1**：剧情停滞检测与轻量导演干预
- **V3.2**：PlotArc 阶段锁与禁止提前剧透
- **V3.3**：章节连续性摘要
- **V3.4**：轻量人物弧光
- **V3.5**：Debug、可观测性与稳定化规划
- **V3.6 Patch**：补齐 V3.5 的最小运行产物与关键实现偏差

## 多地点核心机制

### 1. 地点联通性
每个地点有 `connected_to` 列表，定义可移动方向：
```json
{
  "old_hospital_entrance": {
    "connected_to": ["hospital_lobby"]
  },
  "hospital_lobby": {
    "connected_to": ["old_hospital_entrance", "archive_room"]
  },
  "archive_room": {
    "connected_to": ["hospital_lobby"]
  }
}
```

### 2. move 动作校验链
```
1. action_type == move
2. target 必须是有效的 location_id
3. 当前地点.connected_to 包含 target
4. 更新 WorldState 中角色.location_id
5. 生成 move 事件日志
```

### 3. 上下文隔离
每个地点独立维护：
- **available_targets**：本地点 objects + 在场角色
- **available_topics**：与本地点线索相关的 topics
- **location_public_description**：仅当前地点的公开描述

### 4. LLM 兜底策略
如果 LLM 连续输出非法动作（最多 max_retries 次），自动降级：
```
1. 有可移动地点 → move
2. 有可问的人 → ask
3. 有可检查目标 → inspect
4. 否则 → wait
```

## 下一步版本规划

- **V3.7**：补齐 debug/replay/validate/diff CLI
- **V3.8**：多章 run 内连续生成
- **V3.9**：更严格的 ConfigValidator 与 RunDiff

## 项目结构

```
novel-sim-v1/
├── app/
│   ├── core/
│   ├── models/               # 数据模型（Pydantic）
│   │   ├── world.py
│   │   ├── state.py
│   │   ├── action.py
│   │   └── event.py
│   ├── services/             # 核心服务
│   │   ├── world_state_service.py
│   │   ├── character_agent_service.py  # V2.2：多地点 + move
│   │   ├── action_validator.py         # V2.2：联通性校验
│   │   ├── environment_engine.py       # V2.2：move 逻辑
│   │   ├── event_log_service.py
│   │   ├── progress_monitor.py
│   │   ├── trace_service.py            # V2.2：LLM 调用追踪
│   │   ├── narrative_writer_service.py
│   │   └── consistency_check_service.py
│   ├── runner/              # 模拟运行器
│   ├── llm_client.py        # V2.2：缓存 + 成本统计
│   └── cli.py               # V2.2：temperature/max-retries 参数
├── worlds/
│   └── dark_city_001/       # 示例世界配置
│       ├── world_bible.json
│       ├── map.json         # V2.2：3 地点 + 联通关系
│       ├── characters.json
│       ├── clues.json       # V2.2：4 线索跨地点分布
│       └── chapter_goal.json
├── outputs/                 # 模拟输出（自动创建）
├── requirements.txt
└── README.md
```
