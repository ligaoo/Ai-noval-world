# V1 整体开发文档：主流程、LLM 调用与关键参数

> 依据当前代码工作区整理。当前 CLI/API 正式运行路径实际标记为 `正式版V1`，但 Story Bootstrap API 注释中仍称为“V1 自动补全 / 22 章”。本文将用户所说的 V1 理解为：从一句设定自动补全世界、确认写盘、启动一次 LLM 沙盘模拟、生成第一章正文并完成 P0 校验的整体版本流程。

## 1. 项目定位

本项目是一个小说沙盘生成系统：

1. 用户输入模糊故事设定。
2. Story Bootstrap 自动补全为可运行世界配置。
3. Agent Sandbox 按 tick 推演角色行动、互动、线索发现与世界状态变化。
4. NarrativeService 将结构化事件转换为章节大纲和正文。
5. 一致性、忠实度、章节目标、产物完整性等验证器生成最终运行状态。

核心入口：

- Web/API：`api/server.py`
- CLI：`app/cli.py`
- 模拟主编排：`app/runner/simulation_runner.py`
- LLM 客户端：`app/llm_client.py`
- V1 自动补全编排：`app/bootstrap/story_bootstrapper.py`

## 2. 目录结构概览

```text
app/
  bootstrap/              # Story Bootstrap：从 seed 自动生成 world 配置
  core/                   # 文件系统、时间工具等基础能力
  genre/                  # 类型抽象层
  genre_packs/            # 类型包，如 horror
  models/                 # Pydantic / dataclass 领域模型
  quality/                # 质量评估相关模块
  runner/                 # SimulationRunner 主流程
  services/               # 沙盘、叙事、校验、记忆、状态等服务
api/
  server.py               # FastAPI 接口
worlds/
  <world_id>/             # 可运行世界配置与 bootstrap 产物
outputs/
  sim_*/                  # 每次模拟输出目录
docs/
  V1_OVERALL_DEVELOPMENT_DOCUMENTATION.md
```

## 3. 配置与 LLM 客户端

### 3.1 配置来源

配置读取逻辑在 `app/config.py`：

- `.env` 优先加载。
- LLM 配置字段：
  - `OPENAI_API_KEY`
  - `OPENAI_BASE_URL`，默认 `https://api.openai.com/v1`
  - `OPENAI_MODEL`，默认 `gpt-4o-mini`
- 运行配置字段：
  - `DEFAULT_MODE`，默认 `scripted`
  - `DEFAULT_TICKS`，默认 `15`
  - `DEFAULT_TEMPERATURE`，默认 `0.2`

参考：`app/config.py:55`、`app/config.py:61`、`app/config.py:67`。

### 3.2 OpenAI Compatible Client

`OpenAICompatibleClient` 位于 `app/llm_client.py`。

关键行为：

- API 端点：`{base_url}/chat/completions`
- 请求方法：`POST`
- 超时：`120s`
- 消息格式：
  - system：调用方传入
  - user：调用方传入
- 模型：`self.model`，来自环境配置
- 默认 temperature：`chat(... temperature=0.2)`
- JSON 模式：`chat_json()` 会设置 `response_format={"type":"json_object"}`
- 缓存：仅当 `temperature <= 0.01` 时生成 cache key；默认 `use_cache=True`
- 成本：按 `usage.prompt_tokens / completion_tokens / total_tokens` 粗略估算
- trace_id：`llm_<timestamp>_<random>`

参考：`app/llm_client.py:43`、`app/llm_client.py:94`、`app/llm_client.py:108`、`app/llm_client.py:110`、`app/llm_client.py:122`、`app/llm_client.py:154`。

## 4. API 主流程

### 4.1 Bootstrap 候选生成

接口：`POST /api/story/bootstrap`

请求模型：`BootstrapRequest`

字段：

- `user_seed: str`
- `target_genre: str = "horror_suspense"`
- `target_words: int = 100000`
- `auto_confirm: bool = False`
- `world_id: Optional[str] = None`

流程：

1. `_build_bootstrapper()` 创建 `StoryBootstrapper`，若 LLM 配置可用则注入 `OpenAICompatibleClient`。
2. 构造 `BootstrapSeed`。
3. 调用 `StoryBootstrapper.bootstrap(seed, world_id)`。
4. 结果放入内存缓存 `bootstrap_candidates`。
5. 如果 `auto_confirm=true` 且校验通过，写入 `worlds/<world_id>/`。
6. 返回 `bootstrap_id / world_id / status / title / summary / validation`。

参考：`api/server.py:56`、`api/server.py:791`、`api/server.py:899`、`api/server.py:907`、`api/server.py:914`、`api/server.py:923`。

### 4.2 Bootstrap 查询、确认、启动

- `GET /api/story/bootstrap/{bootstrap_id}`：读取内存候选或磁盘 manifest。
- `POST /api/story/bootstrap/{bootstrap_id}/confirm`：校验通过后写盘。
- `POST /api/story/bootstrap/{bootstrap_id}/start`：确认写盘后启动模拟。

`start` 流程：

1. 校验 bootstrap 候选存在且验证通过。
2. `write_to_worlds_dir(result)` 写入世界配置。
3. `WorldConfig.from_directory(world_dir)` 读取世界。
4. `RuntimeWorldValidator.validate_for_formal_run` 校验正式运行条件。
5. 构造 `SimulationRequest`，固定 `mode="llm"`、`version="正式版V1"`。
6. 调用 `run_simulation(sim_request)`。

参考：`api/server.py:941`、`api/server.py:954`、`api/server.py:983`、`api/server.py:1002`、`api/server.py:1021`。

### 4.3 直接运行模拟

接口：`POST /api/simulations/run`

流程：

1. 检查 LLM 配置，未配置则返回 400。
2. 检查 world 目录存在。
3. 读取 `WorldConfig`。
4. 若不允许不完整世界，则运行正式运行校验。
5. 强制 `request.mode="llm"`、`request.version="正式版V1"`。
6. 创建后台线程执行 `_run_simulation_sync`。
7. 后台线程中调用 `SimulationRunner.run(...)`。

参考：`api/server.py:265`、`api/server.py:270`、`api/server.py:297`、`api/server.py:314`、`api/server.py:210`、`api/server.py:241`。

## 5. CLI 主流程

命令入口：`app/cli.py`

命令参数：

- `--world/-w`：默认 `dark_city_001`
- `--mode/-m`：`scripted/heuristic/llm`，最终默认 `llm`
- `--ticks/-t`
- `--seed/-s`：默认 `12345`
- `--temperature`
- `--max-retries`：默认 `2`
- `--version`：仅支持 `正式版V1`

流程：

1. 加载配置。
2. 命令行参数优先。
3. 如果 `mode=llm` 但 LLM 不可用，自动切到 `heuristic`。
4. 读取世界配置。
5. 调用 `SimulationRunner.run(...)`。

参考：`app/cli.py:30`、`app/cli.py:51`、`app/cli.py:56`、`app/cli.py:69`、`app/cli.py:78`。

## 6. V1 Story Bootstrap 主流程

编排器：`StoryBootstrapper`

主入口：`StoryBootstrapper.bootstrap(seed, world_id)`。

执行顺序：

1. 生成 `bootstrap_id` 与 `world_id`。
2. `SeedInterpreter.interpret`：解析一句话 seed。
3. `WorldBibleGenerator.generate`：生成世界 bible。
4. `MinimumCastGenerator.generate`：生成最小角色组。
5. `BootstrapMapGenerator.generate`：生成最小地图。
6. `TruthChainGenerator.generate`：生成真相链。
7. `EvidenceGraphGenerator.generate`：生成证据图。
8. `ClueRouteGenerator.generate`：生成第一章可发现线索。
9. `OpenThreadSeedGenerator.generate`：生成初始悬念池。
10. `OpeningChapterGoalGenerator.generate`：生成第一章目标。
11. `_ensure_opening_selected_clues`：保证开场计划选中的线索有效且足够。
12. `WriterStoryAnchorGenerator.generate`：生成正文写作锚点。
13. 组装 `BootstrapResult`。
14. `BootstrapValidator.validate` 校验。
15. 返回候选结果，状态为 `validated` 或 `validation_failed`。

参考：`app/bootstrap/story_bootstrapper.py:28`、`app/bootstrap/story_bootstrapper.py:54`、`app/bootstrap/story_bootstrapper.py:59`、`app/bootstrap/story_bootstrapper.py:60`、`app/bootstrap/story_bootstrapper.py:61`、`app/bootstrap/story_bootstrapper.py:62`、`app/bootstrap/story_bootstrapper.py:63`、`app/bootstrap/story_bootstrapper.py:64`、`app/bootstrap/story_bootstrapper.py:65`、`app/bootstrap/story_bootstrapper.py:66`、`app/bootstrap/story_bootstrapper.py:68`、`app/bootstrap/story_bootstrapper.py:70`、`app/bootstrap/story_bootstrapper.py:77`、`app/bootstrap/story_bootstrapper.py:96`。

### 6.1 Bootstrap 写盘产物

`write_to_worlds_dir(result)` 将候选转换成 `WorldConfig.from_directory` 可读格式。

主要输出：

- `world_bible.json`
- `characters.json`
- `map.json`
- `clues.json`
- `chapter_goal.json`
- `writer_story_anchors.json`
- `truth_chain.json`
- `evidence_graph.json`
- `open_threads.json`
- `opening_chapter_plan.json`
- `bootstrap_result.json`
- `bootstrap_manifest.json`

参考：`app/bootstrap/story_bootstrapper.py:133`、`app/bootstrap/story_bootstrapper.py:144`、`app/bootstrap/story_bootstrapper.py:183`、`app/bootstrap/story_bootstrapper.py:209`、`app/bootstrap/story_bootstrapper.py:251`、`app/bootstrap/story_bootstrapper.py:255`、`app/bootstrap/story_bootstrapper.py:260`、`app/bootstrap/story_bootstrapper.py:265`、`app/bootstrap/story_bootstrapper.py:268`、`app/bootstrap/story_bootstrapper.py:271`、`app/bootstrap/story_bootstrapper.py:275`、`app/bootstrap/story_bootstrapper.py:278`、`app/bootstrap/story_bootstrapper.py:282`。

## 7. 模拟运行主流程

主类：`SimulationRunner`

主入口：`SimulationRunner.run(...)`。

### 7.1 初始化阶段

1. 解析 `world_dir`。
2. 若 `allow_incomplete_world=false`，执行 `RuntimeWorldValidator.validate_for_formal_run`。
3. 创建 `outputs/sim_*` 输出目录。
4. 确定 `tick_limit`。
5. 固定 `version="正式版V1"`。
6. 解析 feature flags：
   - `allow_move=True`
   - `enable_memory=True`
   - `force_rule_narrative=False`
   - `enable_consistency_revise=True`
   - `enable_agent_sandbox=True`
   - `enable_fact_exposure_matrix=True`
   - `enable_multi_round_interaction=True`
7. 初始化 `RunManagerLite`。
8. LLM 模式下创建 `TraceService` 与 `OpenAICompatibleClient`。
9. 创建 `EnvironmentEngine`、`MemoryService`、`AgentSandboxLoop` 等。
10. 初始化世界状态并保存。

参考：`app/runner/simulation_runner.py:59`、`app/runner/simulation_runner.py:73`、`app/runner/simulation_runner.py:75`、`app/runner/simulation_runner.py:82`、`app/runner/simulation_runner.py:86`、`app/runner/simulation_runner.py:90`、`app/runner/simulation_runner.py:93`、`app/runner/simulation_runner.py:104`、`app/runner/simulation_runner.py:110`、`app/runner/simulation_runner.py:111`、`app/runner/simulation_runner.py:116`、`app/runner/simulation_runner.py:130`、`app/runner/simulation_runner.py:439`。

### 7.2 Tick 沙盘阶段

每个 tick：

1. 设置 `state.tick=t`。
2. 读取最近事件。
3. 调用 `sandbox_loop.run_tick(state, recent_events[-20:])`。
4. 记录 tension。
5. `ProgressMonitor` 判断是否需要 soft hint。
6. 如果有 hint，写入 `soft_hint` 事件与记忆。
7. 世界时间推进 5 分钟。
8. 保存状态与快照。
9. 如果章节目标完成则提前结束。

参考：`app/runner/simulation_runner.py:142`、`app/runner/simulation_runner.py:146`、`app/runner/simulation_runner.py:147`、`app/runner/simulation_runner.py:153`、`app/runner/simulation_runner.py:155`、`app/runner/simulation_runner.py:171`、`app/runner/simulation_runner.py:172`、`app/runner/simulation_runner.py:175`。

### 7.3 Agent Sandbox Tick 内部流程

`AgentSandboxLoop.run_tick`：

1. 初始化事实曝光矩阵。
2. `ScenePresenceTracker.build_scenes` 构建场景。
3. 处理待决关键事件讨论。
4. 对每个活跃 agent：
   - 构建 perception。
   - `AgentMindService.decide_intent` 决策意图。
5. 构建场景冲突。
6. 将意图拆为简单行动与交互 proposal。
7. 简单行动走 `EnvironmentEngine.apply_action`。
8. 复杂交互走 `MultiRoundInteractionResolver.resolve`。
9. `DirectorRiskChecker.check_and_correct` 做导演风险修正。
10. `WorldStateUpdater.apply_interaction_result` 更新状态。
11. `SandboxEventLogWriter.events_from_interaction` 生成事件。
12. 写事件与记忆。

参考：`app/services/agent_sandbox_loop.py:82`、`app/services/agent_sandbox_loop.py:83`、`app/services/agent_sandbox_loop.py:84`、`app/services/agent_sandbox_loop.py:92`、`app/services/agent_sandbox_loop.py:107`、`app/services/agent_sandbox_loop.py:109`、`app/services/agent_sandbox_loop.py:116`、`app/services/agent_sandbox_loop.py:119`、`app/services/agent_sandbox_loop.py:120`、`app/services/agent_sandbox_loop.py:121`、`app/services/agent_sandbox_loop.py:133`、`app/services/agent_sandbox_loop.py:134`、`app/services/agent_sandbox_loop.py:135`、`app/services/agent_sandbox_loop.py:139`。

## 8. 章节生成主流程

章节生成由 `NarrativeService.generate_chapter()` 负责。

流程：

1. 读取全部事件。
2. 过滤出 `event_level == "plot"` 的事件。
3. `VisibleEventFilter.filter_for_narrative` 只保留 POV 可感知事件。
4. 过滤敏感内容，避免 hidden_actor 真相泄露。
5. 强制保留关键因果事件。
6. 构建结构化 writer context。
7. 规则生成 `chapter_plan`。
8. 写入 `chapter_plan.json`。
9. 若有 LLM 且未强制规则正文：调用 `_llm_write_chapter`。
10. 写入 `chapter_draft.md`。
11. 一致性检查；如未通过且有 violations，调用 `revise_once` 修订一次。
12. 写入 `chapter_debug.json`。
13. `DraftFaithfulnessChecker` 检查正文对结构化输入的忠实度。
14. 返回 plan、draft、consistency_report、draft_faithfulness_report。

参考：`app/services/narrative_service.py:84`、`app/services/narrative_service.py:87`、`app/services/narrative_service.py:95`、`app/services/narrative_service.py:97`、`app/services/narrative_service.py:98`、`app/services/narrative_service.py:99`、`app/services/narrative_service.py:102`、`app/services/narrative_service.py:103`、`app/services/narrative_service.py:123`、`app/services/narrative_service.py:124`、`app/services/narrative_service.py:130`、`app/services/narrative_service.py:132`、`app/services/narrative_service.py:149`、`app/services/narrative_service.py:150`。

## 9. 质量评估与 P0 校验

SimulationRunner 在章节生成后执行：

1. `StoryQualityEvaluatorService.evaluate`：故事质量评估。
2. `_run_p0_validation`：聚合 P0 校验。
3. `_write_v2_report`：写运行报告。
4. `RunManagerLite.complete_with_validation`：写最终状态。

P0 校验包含：

- `ArtifactConsistencyValidator`
- `EncodingHealthChecker`
- `ChapterGoalCompletionChecker`
- `DraftFaithfulnessChecker` 报告，如果存在
- 质量报告适配结果，如果存在

输出：

- `validation_summary.json`
- `artifact_consistency_report.json`
- `encoding_health_report.json`
- `draft_faithfulness_report.json`
- `chapter_goal_completion_report.json`
- `version_report.json`

参考：`app/runner/simulation_runner.py:223`、`app/runner/simulation_runner.py:248`、`app/runner/simulation_runner.py:290`、`app/runner/simulation_runner.py:299`、`app/runner/simulation_runner.py:301`、`app/runner/simulation_runner.py:315`、`app/runner/simulation_runner.py:323`、`app/runner/simulation_runner.py:334`、`app/runner/simulation_runner.py:451`。

## 10. LLM 调用清单与关键参数

### 10.1 通用 LLM 请求参数

所有 `OpenAICompatibleClient` 调用共享：

| 参数 | 来源/值 |
|---|---|
| endpoint | `{OPENAI_BASE_URL}/chat/completions` |
| model | `OPENAI_MODEL`，默认 `gpt-4o-mini` |
| messages | `[system, user]` |
| timeout | `120s` |
| response_format | `chat_json` 使用 `json_object`；`chat` 不设置 |
| cache | `use_cache=True`，仅 `temperature <= 0.01` 生效 |
| max_tokens | 当前代码未显式设置 |
| retry | LLM client 内部未显式重试；CLI 有 `max_retries` 参数但当前主流程未传给 client 使用 |

参考：`app/llm_client.py:94`、`app/llm_client.py:110`、`app/llm_client.py:118`、`app/llm_client.py:122`、`app/llm_client.py:154`。

### 10.2 Bootstrap LLM 调用

| 阶段 | 文件/函数 | 方法 | temperature | response_format | system 角色 | 关键 user 输入 | 失败策略 |
|---|---|---:|---:|---|---|---|---|
| Seed 解析 | `SeedInterpreter._interpret_with_llm` | `chat_json` | `0.2` | JSON object | 故事设定解析专家 | `user_seed`，要求输出 genre/sub_genre/core_location/protagonist_goal/story_type 等 | 返回 None，规则解析兜底 |
| World Bible | `WorldBibleGenerator._generate_with_llm` | `chat_json` | `0.5` | JSON object | 故事世界设定生成专家 | ParsedSeed 字段、template、title/era/tone/themes/rules/timeline 要求 | 返回 None，规则生成兜底 |
| 最小角色组 | `MinimumCastGenerator._generate_with_llm` | `chat_json` | `0.55` | JSON object，但 prompt 要 JSON array | 故事角色配置生成器 | ParsedSeed、角色字段、主角/缺席角色/visible NPC/hidden_actor 硬性要求 | 校验不通过则 fallback |
| 地图 | `BootstrapMapGenerator._generate_with_llm` | `chat_json` | `0.45` | JSON object，但 prompt 要 JSON array | 可运行地图生成器 | ParsedSeed、固定 location_id、固定对象要求 | 校验 location_id 后 fallback |
| 真相链 | `TruthChainGenerator._generate_with_llm` | `chat_json` | `0.45` | JSON object | 真相链生成器 | ParsedSeed、surface/partial/major/truth 四阶段 | fallback |
| 证据图 | `EvidenceGraphGenerator._generate_with_llm` | `chat_json` | `0.45` | JSON object，但 prompt 要 JSON array | 证据图生成器 | ParsedSeed、evidence_id/title/type/truth_relevance 等字段，至少 3 条 | fallback |
| 线索发现路径 | `ClueRouteGenerator._generate_with_llm` | `chat_json` | `0.45` | JSON object，但 prompt 要 JSON array | 线索与发现路径生成器 | ParsedSeed、至少 4 条 clue、discover_routes、on_discovered | fallback |
| 初始悬念池 | `OpenThreadSeedGenerator._generate_with_llm` | `chat_json` | `0.4` | JSON object，但 prompt 要 JSON array | 悬念池生成器 | ParsedSeed、至少 3 条 thread、主题悬念要求 | fallback |
| 第一章目标 | `OpeningChapterGoalGenerator._generate_with_llm` | `chat_json` | `0.45` | JSON object | 长篇小说第一章目标设计器 | ParsedSeed、主角名、章节目标/阻力/ending_hook/forbidden_reveals 等 | fallback |
| 正文叙事锚点 | `WriterStoryAnchorGenerator._generate_with_llm` | `chat_json` | `0.45` | JSON object | 小说正文叙事锚点生成器 | title、ParsedSeed、opening_chapter_plan、禁用总结句/泛化短语 | fallback |

引用：

- `app/bootstrap/seed_interpreter.py:65`、`app/bootstrap/seed_interpreter.py:91`
- `app/bootstrap/world_bible_generator.py:103`、`app/bootstrap/world_bible_generator.py:132`
- `app/bootstrap/minimum_cast_generator.py:38`、`app/bootstrap/minimum_cast_generator.py:59`
- `app/bootstrap/bootstrap_map_generator.py:61`、`app/bootstrap/bootstrap_map_generator.py:75`
- `app/bootstrap/truth_chain_generator.py:30`、`app/bootstrap/truth_chain_generator.py:45`
- `app/bootstrap/evidence_graph_generator.py:30`、`app/bootstrap/evidence_graph_generator.py:44`
- `app/bootstrap/clue_route_generator.py:33`、`app/bootstrap/clue_route_generator.py:48`
- `app/bootstrap/open_thread_seed_generator.py:30`、`app/bootstrap/open_thread_seed_generator.py:45`
- `app/bootstrap/opening_chapter_goal_generator.py:34`、`app/bootstrap/opening_chapter_goal_generator.py:55`
- `app/bootstrap/writer_anchor_generator.py:49`、`app/bootstrap/writer_anchor_generator.py:67`

注意：多个 bootstrap generator 的 prompt 要求返回 JSON array，但通过 `chat_json()` 设置的是 `response_format=json_object`。如果目标 OpenAI 兼容服务严格执行 JSON object，array 输出可能存在兼容风险。

### 10.3 Agent Sandbox LLM 调用

| 阶段 | 文件/函数 | 方法 | temperature | response_format | system/user 来源 | 输出模型 | 关键校验 |
|---|---|---:|---:|---|---|---|---|
| Agent 意图决策 | `AgentMindService._llm_intent` | `chat_json` | `self.temperature`，由 `SimulationRunner.run(temperature)` 传入，默认 `0.2` | JSON object | `PromptTemplateService.render("agent_mind_system.txt")` 与 `agent_mind_user.txt` | `AgentIntent` | agent_id 与 scene_id 必须匹配 |

调用链：

`SimulationRunner.run` → `AgentSandboxLoop(... temperature=temperature)` → `AgentMindService(... temperature)` → `decide_intent` → `_llm_intent`。

参考：`app/runner/simulation_runner.py:116`、`app/runner/simulation_runner.py:127`、`app/services/agent_sandbox_loop.py:58`、`app/services/agent_mind_service.py:245`、`app/services/agent_mind_service.py:249`、`app/services/agent_mind_service.py:258`、`app/services/agent_mind_service.py:263`。

### 10.4 章节正文 LLM 调用

| 阶段 | 文件/函数 | 方法 | temperature | response_format | system | user 关键内容 | trace purpose |
|---|---|---:|---:|---|---|---|
| 正文生成 | `NarrativeService._llm_write_chapter` | `chat` | `0.7` | 无 | Writer 约束：只能使用 POV 可感知内容、allowed_facts、structured upstream context，不得新增 plot-level facts | Story anchors、World、Characters、Locations、Chapter plan、POV-safe facts、Structured upstream context、Visible beats、Allowed entities、Writing requirements | `narrative_write` |

失败策略：捕获异常，写 `llm_error.json`，回退到规则正文。

参考：`app/services/narrative_service.py:322`、`app/services/narrative_service.py:332`、`app/services/narrative_service.py:333`、`app/services/narrative_service.py:337`、`app/services/narrative_service.py:341`、`app/services/narrative_service.py:360`、`app/services/narrative_service.py:375`、`app/services/narrative_service.py:392`、`app/services/narrative_service.py:431`、`app/services/narrative_service.py:466`。

### 10.5 一致性检查与修订 LLM 调用

| 阶段 | 文件/函数 | 方法 | temperature | response_format | system | user 关键内容 | trace purpose |
|---|---|---:|---:|---|---|---|
| 语义一致性检查 | `ConsistencyService._llm_check` | `chat_json` | `0.0` | JSON object | 小说一致性审查员，检查 speculation_as_fact / leaked_info / pov_violation / new_entity | POV、章节目标、前 20 条事件、草稿前 3000 字 | `consistency_check` |
| 自动修订一次 | `ConsistencyService.revise_once` | `chat` | `0.2` | 无 | 修订系统 prompt | draft、plan、plot_events、violations report | `revise_once` |

参考：`app/services/consistency_service.py:181`、`app/services/consistency_service.py:192`、`app/services/consistency_service.py:195`、`app/services/consistency_service.py:237`、`app/services/consistency_service.py:255`、`app/services/consistency_service.py:278`、`app/services/consistency_service.py:300`、`app/services/consistency_service.py:304`。

### 10.6 其他 LLM 调用点

当前代码还存在下列调用点，属于扩展或旧路径，未必在 API 的主模拟链路中必然触发：

- `app/services/llm_character_generator.py`：`/api/generate/characters` 使用，角色候选生成。
- `app/services/character_agent_service.py`：角色 agent 服务中存在 `chat_json` 调用。
- `app/services/consistency_check.py`：旧/独立一致性检查路径。

可通过搜索 `.chat_json(` 与 `.chat(` 继续维护调用清单。

## 11. 输出产物清单

一次完整 bootstrap + simulation 可能产生：

### worlds/<world_id>/

- `world_bible.json`
- `characters.json`
- `map.json`
- `clues.json`
- `chapter_goal.json`
- `writer_story_anchors.json`
- `truth_chain.json`
- `evidence_graph.json`
- `open_threads.json`
- `opening_chapter_plan.json`
- `bootstrap_result.json`
- `bootstrap_manifest.json`

### outputs/sim_*/

- `state.json`
- `events.jsonl`
- `chapter_plan.json`
- `chapter_draft.md`
- `chapter_debug.json`
- `consistency_report.json`
- `draft_faithfulness_report.json`
- `validation_summary.json`
- `version_report.json`
- `llm_error.json`，仅 LLM 正文失败时
- `quality_reports/ch_*_quality.json`，质量评估可用时
- trace summary，LLM 模式启用 `TraceService` 时

参考：`app/runner/simulation_runner.py:468`、`app/runner/simulation_runner.py:477`、`app/services/narrative_service.py:103`、`app/services/narrative_service.py:125`、`app/services/narrative_service.py:740`。

## 12. V1 版本内容定义

本文建议将当前 V1 的范围定义为以下闭环：

1. **自动世界补全**：一句 seed 生成完整 world，包括 bible、角色、地图、线索、真相链、证据图、悬念池、第一章目标、叙事锚点。
2. **候选确认机制**：bootstrap 只生成候选，确认后才写入 `worlds/`。
3. **正式运行阻断**：未通过 runtime validation 的 world 不能正式运行，除非显式 `allow_incomplete_world=true`。
4. **Agent Sandbox 推演**：多 agent 根据感知与记忆决定行动，事件进入 event log。
5. **POV 安全叙事**：正文只能使用 POV 可见事件、allowed facts 与结构化上游上下文。
6. **一致性修订**：正文生成后执行 LLM 语义检查，必要时修订一次。
7. **P0 验证闭环**：产物一致性、编码健康、章节目标、正文忠实度、质量评估聚合到最终 validation status。

## 13. 当前实现注意点

1. **版本命名不一致**：API 注释称 V1 自动补全，但 CLI/Runner 强制 `正式版V1`。
2. **Bootstrap JSON array 与 response_format 的潜在冲突**：多个 generator 要 array，但 `chat_json` 请求 JSON object。
3. **CLI max_retries 未进入 LLM client**：`max_retries` 参数传入 Runner，但当前 LLM client 未使用重试参数。
4. **正文 prompt 存在编码异常文本**：`NarrativeService` 中部分中文字符串显示为 mojibake，但功能约束仍可读到部分英文关键规则。
5. **docs 目录当前为空**：git status 显示多份旧文档被删除，本文作为新的整体开发文档沉淀。

## 14. 推荐后续文档拆分

如果后续要继续完善，建议拆为：

1. `V1_OVERALL_DEVELOPMENT_DOCUMENTATION.md`：总体流程与接口。
2. `V1_LLM_CALLS_AND_PROMPTS.md`：所有 LLM 调用点、参数、输入输出 schema。
3. `V1_ARTIFACT_CONTRACT.md`：worlds 与 outputs 文件契约。
4. `V1_VALIDATION_AND_BLOCKING.md`：runtime validation、P0 validation、质量门槛。
5. `V1_AGENT_SANDBOX_FLOW.md`：Agent Sandbox tick、互动、事件、记忆、事实曝光矩阵。
6. `V1_NARRATIVE_WRITER_CONTRACT.md`：正文 writer 的可写/禁写边界。
