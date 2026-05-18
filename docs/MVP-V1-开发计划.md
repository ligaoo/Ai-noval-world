# MVP V1 具体开发计划：小说沙盘引擎（可实现最小闭环）

> V1 目标：**跑通“模拟 → 事件日志 → 章节改写 → 一致性检查”闭环**，用最小世界与最少动作验证体系可行性；为后续 V2（多地点+记忆）、V3（导演系统）打地基。

---

## 0. V1 交付定义（必须可跑可回放可出稿）

### 0.1 V1 输入 / 输出
**输入（配置）**
- 1 个 World Bible（规则/题材/氛围）
- 1 个地点（可选：大门+大厅合并为 1 个“旧医院入口区”）
- 2 个主 Agent（主角 + 看门人）
- 3 个隐藏事实（线索），每个至少 2 条发现入口（V1 先放宽到 2，V2 起要求 3）
- 1 个章节目标（chapter_goal）
- 1 份独立线索表 `clues.json`（见 §4.2.2），用于定义每个线索的 discover_routes（发现路径）

**输出（产物）**
- simulation_id 的全量 Event Log（可查询、可回放）
- chapter_plan（事件筛选后章节大纲）
- chapter_draft（1 章 2k–3k 字，文风固定）
- consistency_report（是否新增事实/是否泄露 POV 信息/是否违背规则）

### 0.2 V1 成功标准（Definition of Done）
- Agent 只输出 **ActionCommand JSON**（schema 校验通过），不得输出小说正文
- 环境引擎是唯一“事实生成者”，所有事实必须来自：世界设定 + 世界状态 + 判定结果
- 每个 tick 产生 0..n 条 EventLog（包含 visible_to）
- 叙事层只能基于 EventLog 改写，不得新增线索/真相
- 一致性检查能指出至少三类违规：**新增事实 / 泄露信息 / 改变事件结果**

---

## 1. V1 范围裁剪（避免过早复杂化）

### 1.1 动作白名单（V1）
- move（可选；若仅单地点可不做）
- observe
- inspect
- search
- talk
- ask
- wait

> V1 不做：take/give/use/attack/flee/hide/follow/复杂物品系统（可预留字段但不启用）

### 1.2 NPC 分层（V1）
- 仅 2 个主 Agent（都作为完整 Agent 运行）
- 不做“半 Agent NPC / 背景 NPC”系统（V2 再加）

### 1.3 环境裁判（V1）
- **优先只做规则引擎（确定性）**：地点一致性、目标存在、可见性、技能检定、线索触发
- LLM 环境裁判（语义映射）在 V1 作为可选开关（默认关闭），避免“裁判乱编”

---

## 2. V1 架构设计（模块化单体，接口按服务拆分）

### 2.1 逻辑架构（V1）
```text
                 ┌────────────────────────┐
                 │   World Config (JSON)   │
                 └──────────┬─────────────┘
                            │
                    ┌───────▼────────┐
                    │ SimulationRunner │  (tick loop)
                    └───┬──────────┬──┘
                        │          │
        ┌───────────────▼─┐     ┌──▼────────────────┐
        │ CharacterAgentSvc │     │ EnvironmentEngine │
        │ (LLM decide JSON) │     │ (rules judge)     │
        └───────┬───────────┘     └───┬──────────────┘
                │                     │
           ┌────▼─────┐         ┌────▼─────────┐
           │ ActionCmd │         │ ActionResult  │
           └────┬─────┘         └────┬─────────┘
                │                     │
                └──────────┬──────────┘
                           ▼
                    ┌────────────┐
                    │ EventLogSvc │  (append-only)
                    └─────┬──────┘
                          │
          ┌───────────────▼───────────────┐
          │ NarrativeWriter + Consistency │
          │ (log→chapter, then check)     │
          └───────────────────────────────┘
```

### 2.2 模块职责（V1 必实现）
- **WorldConfigService**
  - 加载/校验 world_bible.json / map.json / characters.json / clues.json
  - 提供“可见描述/可交互对象/可问 topic/线索发现路径 discover_routes”查询接口
- **WorldStateService**
  - 保存 simulation 运行时状态（见 §4.1 WorldState 结构）
  - 必须包含：`chapter_goal_status`、角色 `known_facts/suspicions/mental_state`、`last_action`、`repeat_action_count`、`no_progress_ticks`
  - V1 可用 JSON 文件或单表 JSON 字段；要求可回放（同 seed 同配置可复现）
- **CharacterAgentService**
  - 构建 Agent 上下文（只给角色可知信息）
  - 调用 LLM 输出 ActionCommand JSON
  - JSON Schema 校验 + Action 白名单校验
  - Knowledge Boundary 校验（V1 先做关键字段检查：target/topic 是否可见、是否在可问 topic 列表内）
- **DialogueResolver（对话判定，V1 必做简化版）**
  - V1 不做自由聊天，采用 **Topic-based Dialogue**：ask/talk 必须带 topic
  - 根据“在场/关系值/技能检定/是否知道该 topic 对应信息”返回：透露/隐瞒/撒谎（撒谎先按“模糊回答”处理，V2 扩展为可追踪谎言）
- **EnvironmentEngineService**
  - applyAction(action, state) → result
  - 规则判定 + 技能检定 + 线索触发（基于 discover_routes）+ 状态更新
  - 生成 EventLog（唯一事实来源）
- **EventLogService**
  - append-only 写入；按 simulation_id/time 查询
- **ProgressMonitor（无进展兜底，V1 必做轻量版）**
  - 维护 `no_progress_ticks`
  - 连续 N tick 无“新线索/关系变化/冲突变化/进展变化”则触发 **soft_hint**（软提示，不新增事实）
- **NarrativeWriterService**
  - 事件筛选（规则：progress/mystery/conflict 评分阈值或 event_type 白名单）
  - 章节编排（V1：单章，pov 固定为主角）
  - 调用 LLM 将事件改写为小说文本（2k–3k 字）
- **ConsistencyCheckService**
  - 两层检查（见 §7.3）：
    - RuleCheck：能程序判断的先拦截（新地点/新对象/顺序错乱/未发现线索关键词等）
    - LLMCheck：语义层（把猜测写成事实、暗示未公开真相、泄露 POV 信息等）
  - 允许最多 **自动修订 1 次**（revise_chapter → final_check）

> V1 不实现：MemoryService（长期记忆/向量检索）、DirectorService（节奏干预）、多地点复杂联通

---

## 3. 技术选型（建议）

### 3.1 语言与运行形态
- **建议：Python**（V1 更快迭代）或 Java（若你既有 Java 基建）
- V1 推荐提供：
  - CLI：`run_sim.py --world ./worlds/dark_city_001 --ticks 30`
  - 可选：简单 HTTP API（后续接前端）

### 3.2 存储（V1 够用即可）
- **SQLite / Postgres（二选一）**
  - V1 若追求极快落地：SQLite（单文件，易部署）
  - 若考虑后续扩展：Postgres（JSONB + 索引更强）
- EventLog 表建议单独一张（append-only），方便回放与调试

### 3.3 LLM 适配层（强烈建议）
封装一个 `LLMClient`：
- 输入：prompt + structured output schema（若模型支持）
- 输出：原始文本 + 解析后的 JSON + token/cost 元数据
便于以后替换模型、做缓存与重试。

---

## 4. 核心数据结构（V1 版本契约）

### 4.1 WorldState（强烈建议在 V1 就定成“可执行状态机”）
> 现阶段最容易“开发卡住”的点就是 WorldState 不够具体。V1 需要明确哪些字段驱动判定、驱动兜底、驱动章节进展。

推荐最小结构（示例）：
```json
{
  "simulation_id": "sim_001",
  "tick": 12,
  "world_time": "day1_20:35",
  "random_seed": 12345,
  "chapter_goal_status": {
    "goal": "让主角意识到旧医院并非真正废弃",
    "completed": false,
    "progress": 40
  },
  "no_progress_ticks": 0,
  "characters": {
    "char_linzho": {
      "location_id": "old_hospital_entrance",
      "mental_state": "uneasy",
      "known_facts": ["vf_001"],
      "suspicions": [],
      "inventory": [],
      "last_action": "inspect:hospital_gate_lock",
      "repeat_action_count": 1
    },
    "char_guard": {
      "location_id": "old_hospital_entrance",
      "mental_state": "guarded",
      "known_facts": ["hf_002"],
      "attitude_to_char_linzho": -20,
      "last_action": "talk:char_linzho"
    }
  },
  "world": {
    "discovered_facts": {
      "hf_001": false,
      "hf_002": false,
      "hf_003": false
    },
    "objects": {
      "hospital_gate_lock": {"visible": true, "state": "locked"},
      "front_desk": {"visible": true, "state": "dusty"}
    }
  }
}
```

关键字段说明（V1 必须用得上）：
- `chapter_goal_status.progress`：用来判断是否“有剧情进展”
- `repeat_action_count`：用于抑制无意义循环/触发 soft_hint
- `no_progress_ticks`：ProgressMonitor 核心计数器
- `known_facts/suspicions/mental_state`：决定 Agent 行为更稳定、更一致

### 4.1 World Bible（world_bible.json）
最少字段：`world_id, genre, tone, era, rules[], themes[]`

### 4.2 Location（map.json）
V1 只需 1 个 location，也按可扩展结构定义：
- `id/name/public_description/objects/connected_to[]/danger_level/time_effects`

> V1 建议：不要把“线索发现逻辑”散落在 location.hidden_facts 里，而是抽到 `clues.json` 统一维护（一个线索可能来自地点/人物对话/物品/环境变化，未必属于某个地点）。

#### 4.2.1 对象（objects）最小字段
- `id/name/visible/state/description`

#### 4.2.2 线索表（clues.json）——线索 = discover_routes 的集合（V1 必做）
```json
{
  "clues": [
    {
      "id": "hf_001",
      "name": "最近更换的铁锁",
      "content": "医院大门的锁最近被换过。",
      "truth_level": "hidden_fact",
      "importance": 8,
      "discover_routes": [
        {
          "route_id": "route_001",
          "action_type": "inspect",
          "target": "hospital_gate_lock",
          "required_skill": "observation",
          "difficulty": 60,
          "result_text": "铁锁外壳生锈，但锁芯很新，像是最近换过。"
        },
        {
          "route_id": "route_002",
          "action_type": "ask",
          "target": "char_guard",
          "topic": "hospital_gate_lock",
          "required_skill": "social",
          "difficulty": 50,
          "min_attitude": -10,
          "result_text": "看门人含糊地说，前几天有人让他换过锁。"
        }
      ],
      "on_discovered": {
        "add_known_fact_to": "discoverer",
        "plot_value": {"mystery": 8, "progress": 6, "conflict": 2}
      }
    }
  ]
}
```

实现要点：
- EnvironmentEngine 在处理 action 时，扫描匹配的 discover_routes（action_type/target/topic）
- 匹配后再做：在场校验/关系阈值/技能检定/难度
- 成功则触发：写 `world.discovered_facts[hf_x]=true`，并将该线索加入发现者 `known_facts`

### 4.3 Character Profile（characters.json）
最少字段：
- `id, name, role, personality.traits, goals.short_term, skills`

### 4.4 ActionCommand（人物输出）
```json
{
  "agent_id": "char_linzho",
  "intent": "确认医院是否真的废弃",
  "action_type": "inspect",
  "target": "hospital_gate_lock",
  "topic": null,
  "method": "靠近铁门，用手机灯照锁孔和锁身",
  "dialogue": null,
  "expected_gain": "判断这把锁是否长期无人使用",
  "risk_level": "low|medium|high"
}
```

字段说明（V1 建议强制）：
- `topic`：仅用于 ask/talk（Topic-based Dialogue）
- `expected_gain`：角色期望获得什么，用于判定动作合理性、辅助“无进展”诊断

### 4.5 ActionResult（环境输出）
```json
{
  "valid": true,
  "success": true,
  "result": "锁芯很新，像最近更换过。",
  "discovered_facts": ["hf_001"],
  "state_changes": [
    {"op":"set","path":"world.discovered_facts.hf_001","value":true}
  ],
  "triggered_events": ["evt_00031"],
  "reason_for_judgement": "通过观察技能检定(75>=60)，满足发现条件"
}
```

### 4.6 EventLog（事实记录）
字段建议（V1 必要）：`event_id,time,location,actors,event_type,action,result,visible_to,plot_value`

#### 4.6.1 事件分层（建议 V1 就做）
为减少“小说流水账”，建议在 EventLog 中加入：
- `event_level: raw|plot`

规则：
- raw：所有动作与结果（用于回放/调试）
- plot：可进入小说候选的事件（discovery、冲突、关系变化、显著进展等）

> NarrativeWriter 默认只选择 `event_level=plot`，或按 plot_value 阈值补充选择。

---

## 5. 关键流程（V1 Tick Loop）

### 5.1 单 Tick 顺序
1) 加载 WorldState（见 §4.1）
2) 依次激活角色（V1：固定顺序即可）
3) 对每个角色：
   - 构建 AgentContext（严格可见信息 + 可用 target/topic 列表 + last_k_events）
   - **（阶段 1 可选）**若处于“规则模拟自测模式”，使用预设脚本动作代替 LLM
   - 否则：LLM 决策 → ActionCommand
   - 校验 ActionCommand（schema + 白名单 + target/topic 合法）
   - EnvironmentEngine.applyAction → ActionResult（含 discover_routes 匹配）
   - EventLog append（raw 必写；满足条件则额外写 plot 事件）
   - WorldState apply（状态变更、关系变更、repeat_action_count/no_progress_ticks 更新）
4) ProgressMonitor：若连续 N tick 无进展，触发一次 soft_hint（只引导注意可见对象/可问 topic，不新增事实）
5) 判断 stop 条件：tick 达到上限；或章节目标达成；或关键线索达成阈值
6) 生成章节：
   - select plot events → chapter_plan → chapter_draft
   - rule_check → llm_check
   - 若有违规：自动 revise 一次 → final_check

### 5.2 停止条件（V1）
建议二选一：
- 固定 ticks（如 20~40）
- 或“章节目标达成 + 关键线索至少发现 N 个（如 2/3）”

---

## 6. 规则引擎设计（V1 可解释、可调参）

### 6.1 合法性检查（validity）
- actor 是否存在
- action_type 是否在白名单
- target 是否在地点 objects/可交互列表中
- 若动作需要“可见”：target visible=true 或 discover_condition 已满足

### 6.2 技能检定（success）
V1 建议 d100：
- `roll = random(1..100)`
- `success = (skills[required_skill] + modifiers) >= difficulty`
> 为了可复现调试，随机数要可设置 seed。

### 6.3 线索触发（基于 clues.json 的 discover_routes）
触发流程：
1) 根据 action_type/target/topic 匹配 discover_routes
2) 通过“在场/关系阈值/对象可见性”等规则检查
3) 技能检定通过（或 difficulty=0）
4) 触发 on_discovered：
   - 写入 `world.discovered_facts[hf_id]=true`
   - 将线索加入 discoverer 的 `known_facts`（或 partial 线索）
   - 写入 plot_value，用于章节筛选
   - 生成 discovery 类 plot EventLog

### 6.4 Topic-based Dialogue（V1 对话判定最小规则）
V1 中 talk/ask 不允许自由聊天，必须带 topic：
- 校验：对话双方在场、topic 是否在可问列表中
- 判定：关系阈值（min_attitude）+ 社交技能检定（social）
- 输出：透露（reveal）/含糊（evade）/拒绝（refuse）
> V1 先不做“可追踪谎言”，但可以在 result 文本里用“含糊其辞”实现效果。

---

## 7. Prompt 设计（V1 必须“强约束输出 JSON”）

### 7.1 人物 Agent Prompt（V1 简化版）
输入段落固定：
- 人物信息（traits/goals/fears/skills）
- 当前地点公开描述
- 当前已知事实（known_facts）
- 最近事件摘要（last_k_events visible_to_me）
- 可用动作与 target 列表（强烈建议把 target 列表显式给出）
- 对话可选 topic 列表（只允许从列表中选择）

输出强约束：
- 只允许输出 JSON
- action_type 必须为枚举之一

### 7.2 小说改写器 Prompt（V1）
输入：
- 选中的事件列表（按时间排序）
- POV=主角
- 文风：克制、压抑、现实中透出诡异
约束：
- 不得新增核心事实/线索
- 不得泄露 POV 不知道的信息

### 7.3 一致性检查 Prompt（V1）
两层检查（强烈建议在 V1 就落地）：

**第一层：RuleCheck（程序规则审查）**
- 正文是否出现未在 EventLog/WorldConfig 出现的新地点/新对象
- 是否出现未发现线索（fact_id）的关键词或等价表述（可用词表/别名）
- 是否出现非 POV 角色明确内心独白
- 事件顺序是否被改写（至少保证“关键事件的先后关系”不颠倒）

**第二层：LLMCheck（语义审查）**
- 是否把猜测写成事实、是否暗示未公开真相
- 是否让角色知道不该知道的信息（泄露 POV）
- 是否改写人物动机/关系走向

**自动修订（V1 允许 1 次）**
```text
chapter_draft → rule_check → llm_check
  if violations:
    revise_chapter_once → final_check
```
LLM 输出建议为结构化 JSON，包含：违规类型、原句、原因、建议修复文本。

---

## 8. API/CLI 设计（V1 最小可用）

### 8.1 CLI（推荐先做）
- `init_world`：生成示例世界配置（可选）
- `run_sim`：运行模拟并输出产物
- `export`：导出 EventLog/章节文本

### 8.2 HTTP API（可选，后续前端用）
- `POST /simulations` 创建 simulation（world_id + seed + tick_limit）
- `POST /simulations/{id}/run` 跑到结束
- `GET /simulations/{id}/events` 拉事件
- `POST /simulations/{id}/chapter` 生成章节
- `GET /simulations/{id}/artifacts` 获取 chapter_draft + report

---

## 9. 工程目录建议（示例）
```text
app/
  core/
    schemas/            # JSON Schema 定义
    models.py           # dataclass/pydantic（或拆分到 models/）
    llm_client.py
    progress_monitor.py
  services/
    world_config.py
    world_state.py
    character_agent.py
    environment_engine.py
    event_log.py
    narrative_writer.py
    consistency_check.py
  runner/
    simulation_runner.py
  prompts/
    character_agent_prompt.txt
    narrative_writer_prompt.txt
    consistency_rule_check.md
    consistency_llm_check_prompt.txt
  worlds/
    dark_city_001/
      world_bible.json
      map.json
      characters.json
      clues.json
      chapter_goal.json
  outputs/
    sim_xxx/
      events.jsonl
      chapter_plan.json
      chapter_draft.md
      consistency_report.json
```

---

## 10. V1 开发排期（建议 10~15 个工作日）

### 第 1–2 天：契约与样例世界（含 clues.json）
- 定义 JSON Schema（World/Location/Character/Action/EventLog）
- 编写示例世界（旧医院入口区 + 3 线索 + 2 角色 + clues.json discover_routes）
- 完成 schema 校验工具（启动时校验配置）

### 第 3–5 天：环境引擎 + 事件日志（先不接 LLM）
- EnvironmentEngine.applyAction（合法性/技能检定/线索触发（discover_routes）/状态更新）
- EventLogService（JSONL 或 DB 表 append-only）
- WorldStateService（保存/加载/可回放 + repeat_action_count/no_progress_ticks）
- **规则模拟自测模式**：用预设脚本动作跑通“动作→判定→日志→状态变化”

### 第 6–8 天：接人物 Agent（只输出 JSON）
- ContextBuilder（只给可见信息 + last_k_events）
- LLM 调用与 JSON 解析（失败重试/纠错：只限“补全字段/修正枚举”，禁止改剧情）
- ActionValidator（schema + 白名单 + target/topic 存在性 + expected_gain 合理性）
- Topic-based Dialogue 判定（ask/talk → 环境引擎统一裁决）
- ProgressMonitor：连续无进展 → soft_hint（不新增事实）

### 第 9–10 天：跑通 SimulationRunner
- tick loop + stop 条件 + 产物落盘
- 可复现（seed）+ 运行日志（每步输入输出留档）

### 第 11–12 天：章节生成 + 两层一致性检查 + 自动修订一次
- 事件筛选（规则法：保留 discovery/conflict/progress>阈值）
- LLM 改写生成 chapter_draft（2k–3k 字）
- RuleCheck（程序审查）+ LLMCheck（语义审查）
- 若违规：自动 revise 一次，再 final_check

### 第 13–15 天：稳定性与验收用例
- 3 套 world 配置回归（至少不同线索路径）
- 失败处理：LLM 输出不合法 JSON、重复动作、无进展
- 产物质量校准：事件选择、节奏、文风一致性

---

## 11. V1 风险点与硬性防线（必须落地）

1) **Agent 乱编/输出小说**
- schema 校验失败直接拒绝并要求“只输出 JSON”
- 提供显式 target 列表，减少自由发挥空间

2) **环境裁判“凭空加真相”**
- V1 默认禁用 LLM 裁判；若启用只做“动作归一化”，不允许生成新事实字段

3) **日志变流水账**
- EventLog 写全量，但进入章节前必须“筛选+编排”

4) **故事卡死**
- 给每个关键线索至少 2 入口
- 对连续重复动作设置惩罚：repeat_action_count 增长并影响决策权重
- ProgressMonitor：连续 N tick 无进展触发 soft_hint（引导注意可见对象/可问 topic，不新增事实）

---

## 12. V1 最小验收用例（建议直接写成自动化脚本）

- 用例 A：主角通过 inspect 发现“锁芯更新”
- 用例 B：主角通过 talk/ask 从看门人处获得替代线索
- 用例 C：主角多次失败后仍能通过另一入口获得线索（不至于卡死）
- 用例 D：章节文本中不得出现“反派计划/世界真相”等 POV 不可知信息

---

## 13. V1 之后的升级接口（提前留钩子）

- MemoryService 接口（V2 上向量检索）
- DirectorService 接口（V3 张力指标与事件投放）
- 多地点与对象状态（V2 扩展 map/connected_to）

---

## 14. 你可以直接照这个顺序开工的“任务清单”（最小集合）

1) 固化 schema + 示例世界（world_bible/map/characters/**clues(discover_routes)**）
2) **先不接 LLM**：用脚本动作跑通 EnvironmentEngine（判定→状态→EventLog）
3) 接入 CharacterAgent（严格 JSON 输出 + target/topic 列表 + expected_gain）
4) 加入 Topic-based Dialogue + ProgressMonitor（无进展兜底）
5) 章节生成：只吃 plot events → chapter_plan → chapter_draft
6) 一致性检查：RuleCheck → LLMCheck → 自动修订一次
7) 调参：线索难度、soft_hint 触发阈值、事件筛选阈值、章节字数与文风
