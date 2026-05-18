# MVP V2.1 开发计划：LLM Agent 接入版（仍单地点）

> V2.1 目标：只引入一个变量——**人物决策由大模型生成**。  
> 保持 V1：单地点、discover_routes、规则环境裁判、模板章节生成（可继续用 V1），先把“LLM 输出动作”这件事跑稳定。

---

## 0. 范围与非目标

### 0.1 做什么
- 在现有 `novel-sim-v1` 上，把 `--mode llm` 作为主路径打磨到可用：
  - LLM 稳定输出 `ActionCommand JSON`
  - ActionValidator + retry + fallback，保证模拟不中断
  - agent_traces 记录输入/输出/失败原因/重试次数（便于定位）

### 0.2 不做什么
- 不做多地点（move 可保留但不启用地图联通）
- 不做 MemoryService
- 不做 LLM Narrative Writer（章节正文仍可使用 V1 模板改写）
- 不做 Director

---

## 1. 交付物（outputs/sim_xxx/）
- `state.json`
- `events.jsonl`
- `chapter_plan.json`
- `chapter_draft.md`（V1 模板即可）
- `consistency_report.json`（可保留现有两层检查框架）
- **新增**：`agent_traces/`
  - `tick_0001_char_xxx_agent_decision.json`（输入、输出、校验结果、fallback）

---

## 2. 关键设计（必须补齐）

## 2.1 AgentContext 结构化分层（防“推测当事实”）
建议 CharacterAgent 输入统一为 JSON（而不是散乱文本）：
```json
{
  "character": {
    "id": "char_linzho",
    "name": "林舟",
    "traits": ["克制", "敏感", "逃避冲突"],
    "short_term_goal": "确认旧医院是否与噩梦有关"
  },
  "current_state": {
    "location_id": "old_hospital_entrance",
    "mental_state": "uneasy",
    "known_facts": [],
    "beliefs": []
  },
  "visible_environment": {
    "description": "...",
    "available_targets": ["hospital_gate_lock", "front_desk", "char_guard"],
    "available_topics_by_target": {
      "char_guard": ["hospital_gate_lock", "night_visitors"]
    }
  },
  "recent_events": ["..."],
  "available_actions": ["observe", "inspect", "search", "ask", "talk", "wait"],
  "constraints": [
    "只能选择 available_actions 中的动作",
    "target 必须来自 available_targets",
    "ask/talk 的 topic 必须来自 available_topics_by_target[target]"
  ]
}
```

## 2.2 LLM 输出稳定性：重试 + 纠错 + fallback（关键）

### 2.2.1 错误分类
- JSON 不可解析
- 字段缺失（agent_id/action_type/target/expected_gain）
- 枚举非法（action_type/risk_level）
- target/topic 不可用（不在可用列表）
- ask/talk 缺 topic

### 2.2.2 重试策略（建议 max_retries=2）
每次重试只做“格式修复”，不要让模型改剧情：
- 回传校验错误列表
- 强制模型输出“修复后的 JSON”

### 2.2.3 fallback 策略（保证不中断）
当重试仍失败时，必须生成 fallback action：
1) 未检查过的重要对象 → `inspect` 或 `search`
2) 有可问 topic 且同地点有人 → `ask`
3) 否则 `observe` / `wait`

> V2.1 的 DoD 里要求：fallback 后模拟不中断率 = 100%。

---

## 3. 模块改造清单（对现有代码的最小改动）

### 3.1 CharacterAgentService
- 将 LLM prompt 改成“结构化 JSON 上下文”
- 加入 `max_retries` + `validate_or_explain_errors()` + `fallback_action()`
- 输出 trace：输入上下文、LLM 原始输出、解析结果、失败原因、最终采用的动作

### 3.2 LLMClient
- 支持按 purpose 配置不同参数（V2.1 仅 agent_decision）
  - temperature 0.2~0.4
  - max_tokens 512

### 3.3 ActionValidator
- 明确可用 actions/targets/topics 的校验逻辑
- invalid 时返回“可机器处理的 error codes”（用于重试提示）

---

## 4. 量化 DoD（必须能测试）
建议用脚本批量跑 10 次（不同 seed）：
- 运行 10 次，每次 30 ticks，不崩溃
- LLM Agent JSON 成功率 ≥ 95%
- 非法动作率 < 10%
- fallback 后不中断率 = 100%
- 每次至少发现 2/3 个线索（plot clue）

---

## 5. 测试用例（V2.1 必须覆盖）
1) LLM 输出自然语言 → 触发重试 → 失败则 fallback  
2) LLM 选了不存在 target → 校验失败 → 重试/ fallback  
3) LLM 输出 ask 但没 topic → 校验失败 → 重试/ fallback  
4) LLM 重复同一动作 5 次 → 仍能通过 ProgressMonitor 引导（soft_hint）或 fallback 转移目标

---

## 6. 开发顺序（3~5 天）
1) AgentContext JSON 化 + validator error codes  
2) LLM 重试（2 次）+ fallback  
3) agent_traces 输出落盘  
4) 批量跑 10 次统计 JSON 成功率、非法动作率  

