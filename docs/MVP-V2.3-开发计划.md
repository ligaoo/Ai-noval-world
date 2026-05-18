# MVP V2.3 开发计划：记忆 + LLM 小说改写 + 一致性修订（让输出“像小说”）

> V2.3 目标：在 V2.1（LLM 决策稳定）+ V2.2（多地点稳定）基础上，再引入“叙事质量”相关变量：  
> **记忆（event/fact/belief）→ 更稳的行为；LLM 日志改写器 → 更像小说；一致性检查 + revise once → 更可控。**

---

## 0. 范围与非目标

### 0.1 做什么
- MemoryService（本地文件 memories.jsonl）
  - event_memory / fact_memory / belief_memory 三类
- LLM Narrative Writer（替换 V1 模板改写）
  - 必须先生成 `chapter_plan`（规则生成），再给 LLM 写正文
- 一致性检查强化：
  - 实体白名单（allowed_entities）输入 + 规则层抽取校验
  - LLMCheck 语义审查 + 自动修订一次
- LLM 调用 trace + 成本/缓存（最小实现）

### 0.2 不做什么
- 不做向量库（V3 再上）
- 不做导演系统（V3+）

---

## 1. MemoryService 设计（V2.3 必落地）

### 1.1 memories.jsonl 结构
```json
{
  "memory_id": "mem_0007",
  "agent_id": "char_linzho",
  "type": "belief_memory",
  "time": "day1_20:20",
  "location_id": "old_hospital_gate",
  "content": "林舟怀疑：近期有人进入过旧医院。",
  "tags": ["suspicion", "recent_activity", "hf_001"],
  "confidence": 0.6,
  "importance": 6,
  "source_event_id": "evt_0008"
}
```

字段说明：
- type：event_memory | fact_memory | belief_memory
- confidence：fact 通常 0.8~1.0；belief 0.3~0.7
- source_event_id：用于因果链与回放解释

### 1.2 写入策略（从 EventLog 生成记忆）
- event_memory：对 plot_event/soft_hint 写一条简要经历
- fact_memory：当 clue 被发现（discovered_facts）时写入（“确认事实”）
- belief_memory：当对话失败/含糊/冲突出现时写入（“推测/误解”）

### 1.3 检索策略（无向量库）
- query_tags = {当前地点 objects、最近 action target、最近 topic、已发现 clue ids}
- 先按 tags 命中过滤
- 再按 `importance * 0.7 + recency * 0.3` 排序取 topN

---

## 2. AgentContext 结构（严格分层，避免污染）
建议固定 JSON：
```json
{
  "character": {...},
  "current_state": {
    "location_id": "...",
    "mental_state": "...",
    "known_facts": ["..."],   // fact_memory 摘要（高置信）
    "beliefs": ["..."]       // belief_memory 摘要（中低置信）
  },
  "visible_environment": {
    "description": "...",
    "available_targets": [...],
    "available_topics_by_target": {...},
    "available_moves": [...]
  },
  "recent_events": [...],       // STM
  "relevant_memories": [...],   // LTM retrieve（限长）
  "available_actions": [...],
  "constraints": [...]
}
```

**上下文限长规则（建议）**
- recent_events ≤ 8 条
- relevant_memories ≤ 6 条
- known_facts ≤ 6 条
- beliefs ≤ 6 条

---

## 3. Narrative Writer（V2.3 核心：日志改写器）

### 3.1 两段式：chapter_plan（规则）→ LLM 正文

#### 3.1.1 chapter_plan（规则生成）
输入：plot events（含 plot_value + causality）  
输出示例：
```json
{
  "chapter_title": "生锈的新锁",
  "pov": "char_linzho",
  "chapter_goal": "让林舟意识到旧医院近期有人出入",
  "emotional_curve": ["迟疑", "不安", "怀疑", "被迫继续调查"],
  "beats": [
    {"beat_id":"b001","purpose":"建立氛围","events":["evt_0001","evt_0002"]},
    {"beat_id":"b002","purpose":"发现异常","events":["evt_0005"]},
    {"beat_id":"b003","purpose":"产生冲突","events":["evt_0008","evt_0009"]}
  ],
  "ending_hook_event_id": "evt_0011"
}
```
约束：ending_hook 必须引用 event_id（不能凭空新增）。

#### 3.1.2 LLM 正文生成（log-rewrite）
输入（严格最小化）：
- chapter_plan
- selected plot events（按 beats 分组）
- POV
- 文风
- allowed_entities（见下一节）
- 禁止泄露信息（未发现 clue、他人内心等）

输出：`chapter_draft.md`（建议 3k~6k 字，可配置）

---

## 4. 一致性检查强化：实体白名单 + 两层审查 + revise once

### 4.1 allowed_entities（生成前构建）
```json
{
  "locations": ["old_hospital_gate", "hospital_lobby", "archive_room"],
  "objects": ["hospital_gate_lock", "front_desk", "old_cabinet"],
  "characters": ["char_linzho", "char_guard"],
  "facts": ["医院大门的锁最近被换过", "前台抽屉有近期翻动痕迹"]
}
```

### 4.2 RuleCheck（程序）
- 正文出现的新地点/新对象/新人名 → 违规（若不在 allowed_entities 且不在 EventLog）
- 未发现 clue 的 content/关键词 → 违规
- 关键事件顺序不允许倒置（至少保证因果链方向一致）

### 4.3 LLMCheck（语义）
- 猜测写成事实
- 暗示未公开真相
- 泄露 POV 不知道的信息

### 4.4 revise once（最多一次）
- 将“事实口吻”降级为“推测口吻”
- 删除新增实体段落
- 严禁新增新的线索/地点/对象

---

## 5. LLM 调用 trace / 成本 / 缓存（V2.3 必加最小版）

### 5.1 trace 记录（本地）
写入 `outputs/sim_xxx/agent_traces/llm_calls.jsonl`：
```json
{
  "trace_id": "trace_001",
  "tick": 12,
  "purpose": "agent_decision|narrative_write|consistency_check|revise_once",
  "model": "xxx",
  "input_hash": "abc",
  "output_hash": "def",
  "prompt_tokens": 1200,
  "completion_tokens": 180,
  "retry_count": 0,
  "success": true
}
```

### 5.2 缓存策略（调试省钱）
- 当 temperature=0 且 input_hash 相同：复用输出
- 缓存文件：`outputs/sim_xxx/cache/llm_cache.jsonl`（或全局 cache）

---

## 6. 量化 DoD（必须能测试）
- 运行 10 次，每次 30 ticks，不崩溃
- 记忆写入数量：每次 ≥ 10 条（plot events 驱动）
- 章节字数：每次 3000–6000（可配置）
- RuleCheck 能拦截：新增地点/新增对象/未发现线索
- LLMCheck 能拦截：“猜测写成事实”
- revise once 后：`consistency_report.passed = true`，否则明确列出未修复原因
- 同 seed + 同 mock LLM 输出时，EventLog 完全一致（可复现）

---

## 7. 开发顺序（5~8 天）
1) MemoryService（memories.jsonl）+ 从事件写入三类记忆  
2) AgentContext 分层 + 限长 + 注入 known_facts/beliefs/relevant_memories  
3) chapter_plan 规则生成（beats + ending_hook_event_id）  
4) LLM Narrative Writer（log-rewrite）  
5) allowed_entities 构建 + RuleCheck 增强 + LLMCheck + revise once  
6) trace + 缓存落盘 + 10 次回归  

