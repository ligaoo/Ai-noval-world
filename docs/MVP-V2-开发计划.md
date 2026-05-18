# MVP V2 开发计划（基于 V1 最小集合直接升级：接入大模型）

> 目标：在 V1 “可控闭环”基础上，**接入大模型**让系统具备可读性更强的章节改写能力与更自然的人物决策能力，同时保持 V1 的硬约束：  
> **人物只输出结构化动作、环境是唯一事实生成者、叙事层只改写日志不改事实、两层一致性检查兜底。**

本计划以现有仓库 `novel-sim-v1` 为起点，新增/改造模块，仍采用 **本地文件存储**，用文件夹区分 simulation 管理。

---

## 0. V2 范围与交付（Definition of Done）

### 0.1 V2 核心新增点（相对 V1）
1) **接入大模型用于人物决策（LLM Agent）**：更自然的动作选择，但仍只输出 JSON  
2) **接入大模型用于叙事改写（LLM Narrative Writer）**：章节正文从模板改写升级为“日志改写器”  
3) **记忆（最小可用）**：引入“短期记忆 + 轻量长期记忆文件”，支持检索（V2 不强依赖向量库）  
4) **多地点（小地图）**：至少 3–5 个地点节点 + move 动作生效  

> V2 仍不做：Director（导演系统）、复杂物品使用（use/take）、多 POV 群像并行（可以预留）

### 0.2 V2 交付物
每次运行输出到 `outputs/sim_xxx/`：
- `state.json`（包含多地点、记忆索引、关系值等）
- `events.jsonl`（raw + plot）
- `chapter_plan.json`
- `chapter_draft.md`（**LLM 改写**）
- `consistency_report.json`（规则层 + LLM 层，最多自动修订一次）
- `agent_traces/`（可选：每次 LLM 决策的输入输出留档，便于调试）

### 0.3 成功标准（DoD）
- [ ] LLM Agent 始终输出可解析的 `ActionCommand JSON`，失败有重试/纠错但不“改剧情”
- [ ] 多地点下 move 合法且可回放（同 seed 同配置可复现）
- [ ] 记忆写入与检索可用：AgentContext 中能看到“最近事件 + 相关记忆摘要”
- [ ] LLM Narrative Writer 只基于 plot events 改写，不新增线索/地点/对象/真相
- [ ] 一致性检查能稳定拦截：新增事实/泄露 POV/把猜测写成事实，并可自动修订一次

---

## 1. V2 架构设计（在 V1 单体基础上演进）

### 1.1 逻辑架构
```text
WorldConfig(JSON) ───────────────┐
                                 ▼
                          SimulationRunner
                                 │
          ┌──────────────────────┼───────────────────────┐
          ▼                      ▼                       ▼
 CharacterAgent(LLM)     EnvironmentEngine(rules)    MemoryService
  - decide action JSON     - judge + state change    - write from events
  - strict schema          - clue discover_routes    - retrieve for context
          │                      │                       │
          └──────────────┬───────┴───────────────┬───────┘
                         ▼                       ▼
                    EventLog(raw/plot)        WorldState
                         │
                         ▼
            NarrativeWriter(LLM log-rewrite)
                         │
                         ▼
        ConsistencyCheck(RuleCheck + LLMCheck + revise once)
```

### 1.2 “接入大模型”的边界（V2 必须保持）
- LLM 只做：
  - 人物决策（选动作/目标/topic，输出 JSON）
  - 章节日志改写（写作增强）
  - 语义一致性审查/修订（可选）
- LLM **不得做**：
  - 事实判定（动作成功/失败、线索触发、状态变化都由规则引擎完成）

---

## 2. 本地文件存储与目录（V2）

### 2.1 项目目录（在现有 `novel-sim-v1` 基础上新增）
```text
novel-sim-v1/
  app/
    services/
      memory_service.py          # V2 新增
      narrative_writer_llm.py    # V2 新增（或替换 narrative_writer.py）
      agent_trace_service.py     # V2 新增（可选）
    prompts/
      character_agent_prompt.txt
      narrative_writer_prompt.txt
      consistency_llm_check_prompt.txt
  worlds/
    dark_city_001_v2/            # V2 新世界（避免影响 V1）
  outputs/
    sim_xxx/
      state.json
      events.jsonl
      memories.jsonl             # V2 新增（长期记忆文件）
      chapter_plan.json
      chapter_draft.md
      consistency_report.json
      agent_traces/              # 可选
```

### 2.2 “按文件夹分隔”约束
- simulation 是最小运行单元：状态、日志、记忆、正文、报告都在同一目录
- 任何调试信息（LLM 输入输出）写入 `agent_traces/`，避免污染正文/状态文件

---

## 3. V2 数据结构调整（重点：多地点 + 记忆）

### 3.1 map.json（多地点）
V2 推荐 5 个地点（仍小地图）：
- old_hospital_gate（大门）
- hospital_lobby（大厅）
- archive_room（档案室）
- corridor_4f（四楼走廊，V2 可不启用或只做“午夜可见”）
- ward_01（病房）

每个地点包含：
- public_description
- objects（可交互对象）
- connected_to（连通）
- danger_level / time_effects（可选）

### 3.2 WorldState（多地点 + 记忆索引）
在 V1 基础上新增字段（建议）：
- `characters[...].location_id` 随 move 改变
- `characters[...].plan`（可选：短期意图）
- `characters[...].memory_summary`（可选缓存）
- `world.time_of_day` 或 `world_time` 细化（午夜机制）

### 3.3 clues.json（discover_routes 扩展）
V2 增加 route 类型：
- move 到某地点触发（route 可选加 `location_id` 约束）
- observe/inspect/search/talk/ask 继续保留

### 3.4 记忆（V2 最小实现）
不强依赖向量库，采用“可用就行”的 2 层：

**A. 短期记忆（STM）**
- 从 `events.jsonl` 中读取最近 K 条、且 `visible_to` 包含该角色的事件

**B. 轻量长期记忆（LTM）**
- `memories.jsonl`（每行一条记忆）
```json
{
  "memory_id": "mem_0001",
  "agent_id": "char_linzho",
  "time": "day1_20:15",
  "location_id": "old_hospital_gate",
  "content": "锁芯很新，像最近更换过。",
  "tags": ["hospital_gate_lock", "hf_001"],
  "importance": 7
}
```

**检索策略（V2）**
- 先按 tags/关键词（target/topic/clue_id）过滤
- 再按 importance + recency 排序取 topN
> V3 再接入向量检索（pgvector/Qdrant/Milvus）

---

## 4. V2 核心流程（Tick Loop 演进）

### 4.1 Tick Loop（V2）
1) Load WorldState
2) 对每个 active character：
   - 生成 `AgentContext`：
     - 可见地点描述（当前位置）
     - 可用 action 列表、可用 target 列表、可问 topic 列表
     - 最近事件（STM）
     - 相关长期记忆（LTM retrieve）
     - chapter_goal_status + soft_hints
   - LLM 输出 ActionCommand JSON（失败则重试/纠错，仍不允许自由文本）
   - ActionValidator：schema + 白名单 + target/topic/move 合法性
   - EnvironmentEngine 判定（rules + discover_routes）
   - 写 EventLog（raw + plot）
   - MemoryService：从 plot event 写入 memories.jsonl
3) ProgressMonitor：无进展 → soft_hint
4) Stop 条件 → 章节生成与一致性检查

---

## 5. 关键模块改造清单（V2）

### 5.1 CharacterAgentService（升级为 LLM-first）
新增能力：
- “严格 JSON 输出”重试策略
- 给 LLM 明确：可用 actions/targets/topics（禁止自造）
- move 动作必须给出目标地点（target=location_id）

建议加入：
- `max_retries=2`
- 失败原因分类：JSON 不合法 / 字段缺失 / 枚举非法 / target 不可用

### 5.2 EnvironmentEngine（多地点 + move）
新增判定：
- move：检查 connected_to，更新 location_id
- ask/talk：必须同地点；按 attitude + social 检定决定 reveal/evade/refuse

### 5.3 MemoryService（V2 新增）
职责：
- `write_from_event(event)`：把 plot event 写入 memories.jsonl
- `retrieve(agent_id, query_tags, limit)`：返回摘要
- 可选：记忆去重（同 clue 同 target 同内容）

### 5.4 NarrativeWriter（从模板改写升级为 LLM 改写器）
输入必须最小化：
- plot events（按时间）
- POV
- 文风
- forbidden_information（不在正文泄露）
- 允许出现的：地点/对象/已发现线索 content（可作为约束表）

输出：
- `chapter_draft.md`

### 5.5 ConsistencyCheck（更严格）
RuleCheck 增强：
- 正文中出现的地点/对象必须在 world config 内
- 正文不得出现未发现 clue 的 content 或其关键词（可维护别名词表）
- move 顺序与关键事件先后不颠倒

LLMCheck：
- 检查“把猜测写成事实”
- 检查“暗示未公开真相”

---

## 6. V2 的 Prompt 资产（建议落地为 prompts/*.txt）

### 6.1 人物 Agent Prompt（V2）
必须包含：
- 角色设定（traits/goals）
- 当前地点公开描述
- STM（最近事件摘要）
- LTM（相关记忆摘要）
- 可用 actions / targets / topics（强约束）
- 输出 JSON schema（字段、枚举、示例）

### 6.2 叙事改写 Prompt（V2）
强约束：
- 你是“日志改写器”，不是剧情创造者
- 只能用给定事件写作
- 不能新增线索/对象/地点/真相
- POV 限制（只能写 POV 可感知/可推测）
- 文风固定（克制、压抑、现实中透出诡异）

### 6.3 一致性审查 Prompt（V2）
输出 JSON：
```json
{
  "passed": false,
  "violations": [
    {
      "type": "leaked_pov_info",
      "text": "...",
      "reason": "...",
      "suggested_fix": "..."
    }
  ]
}
```

---

## 7. 开发顺序与里程碑（建议 2 周左右）

### Milestone 1：LLM Agent 接入（2–3 天）
- 支持 llm mode 的稳定 JSON 输出（重试/纠错）
- move 动作合法性与 connected_to 校验
- agent_traces 落盘（输入/输出/校验失败原因）

### Milestone 2：多地点世界跑通（2–3 天）
- 新 world：`dark_city_001_v2`（3–5 地点、10 条线索）
- 最少能通过 move + inspect/search/ask 触发 3–5 个线索

### Milestone 3：MemoryService（2–3 天）
- memories.jsonl 写入
- 检索注入 AgentContext
- 观察是否显著降低“重复动作/无进展”

### Milestone 4：LLM Narrative Writer（2–3 天）
- 事件筛选 → chapter_plan
- LLM 改写生成 3k–6k 字章节（可配置）
- 确保不泄露未发现线索

### Milestone 5：一致性检查强化 + 自动修订一次（1–2 天）
- RuleCheck 增强
- LLMCheck + revise_once 稳定

---

## 8. 风险与兜底（V2）

1) **LLM 不稳定输出 JSON**
- 明确 schema + 只允许从列表选择
- 重试 2 次；仍失败则 fallback 到 heuristic（不中断模拟）

2) **LLM 叙事新增事实**
- 输入只给 plot events + 允许列表（地点/对象/线索）
- RuleCheck 把新实体先拦掉
- 自动修订一次（把“事实口吻”降级为“猜测口吻”）

3) **多地点导致卡死**
- 每条关键线索至少 3 条 discover_routes（V2 建议恢复到 3）
- ProgressMonitor soft_hint 引导“可去的地点/可问 topic”

---

## 9. V2 最小集合（你可以按这个直接开工）

1) 新增 `worlds/dark_city_001_v2`（5 地点 + 10 线索 + discover_routes>=3）  
2) CharacterAgentService：LLM-first + JSON 重试 + trace 落盘  
3) EnvironmentEngine：move + topic 对话判定增强  
4) MemoryService：memories.jsonl 写入/检索注入上下文  
5) NarrativeWriter：从模板改写升级为 LLM 日志改写器  
6) ConsistencyCheck：RuleCheck 增强 + LLMCheck + revise once  

