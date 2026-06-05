# 正式版V1.2 内容质量优化：事件筛选与 Scene Plan

## 1. 版本目标

正式版V1.2 的目标是解决“事件日志过碎、正文流水账、章节缺少场景结构”的问题。

本版本在 V1.1 的 `chapter_brief` 基础上，引入事件筛选与场景规划。Writer 不再直接面对完整事件列表，而是面对经过筛选、合并、排序、标注叙事作用的 scene plan。

核心目标：

1. 新增 `EventSelectionService`，筛选核心事件。
2. 新增 `ScenePlanService`，把核心事件组织成 2-4 个场景。
3. 输出 `selected_events.json` 与 `scene_plan.json`。
4. NarrativeService 基于 scene plan 写正文。
5. 降低流水账、重复观察、低价值 wait 的正文占比。

---

## 2. 需求文档

### 2.1 背景问题

当前生成正文容易出现：

- 按事件发生顺序逐条复述。
- 多个 observe/search/talk 没有主次。
- 章节像日志，不像小说场景。
- 结尾钩子弱。
- 角色关系和线索推进没有被组织成戏剧结构。

### 2.2 用户价值

用户可以获得更像小说章节的内容：

- 正文由场景组成，而非事件流水。
- 每个场景有明确目的。
- 核心事件被突出，低价值事件被压缩。
- 悬念、冲突、发现、转折更清晰。

### 2.3 功能范围

本版本包含：

1. 事件价值评分。
2. 核心事件筛选。
3. 相似事件合并。
4. Scene Plan 生成。
5. NarrativeService 使用 scene plan。
6. `chapter_plan.json` 升级为兼容 scene 信息。

本版本不包含：

- 多轮风格重写。
- 前端风格控制。
- 自动 rewrite 按钮。
- 质量评估驱动重写。

---

## 3. 需求细节

### 3.1 EventSelectionService

输入：

- `events.jsonl`
- `chapter_brief.json`
- `state.json`
- `world` 配置
- `writer_authorization`

输出：

```text
outputs/sim_xxx/selected_events.json
```

结构：

```json
{
  "version": "正式版V1.2",
  "selected_events": [
    {
      "event_id": "evt_0003",
      "importance": 9,
      "scene_role": "setup",
      "reason": "建立入口异常并推进主问题",
      "thread_ids": ["thread_recent_entry"],
      "character_impact": [
        {
          "character_id": "char_protagonist",
          "impact": "产生继续探索的必要性"
        }
      ],
      "reader_question": "入口为什么像刚被改动过？"
    }
  ],
  "compressed_events": [
    {
      "source_event_ids": ["evt_0004", "evt_0005"],
      "summary": "主角反复观察入口痕迹，确认异常不是错觉。"
    }
  ],
  "discarded_events": [
    {
      "event_id": "evt_0007",
      "reason": "低价值等待事件，不推进线索或关系。"
    }
  ]
}
```

### 3.2 事件评分规则

评分维度：

| 维度 | 说明 |
|---|---|
| progress | 是否推进章节目标 |
| mystery | 是否增加悬念或提出读者问题 |
| conflict | 是否制造关系/目标冲突 |
| danger | 是否提高风险 |
| clue_value | 是否发现或重新解释线索 |
| relationship_value | 是否改变角色关系 |
| uniqueness | 是否避免重复 |

推荐公式：

```text
importance = progress*2 + mystery*1.5 + conflict*1.5 + danger + clue_value*2 + relationship_value*1.5 + uniqueness
```

低于阈值的事件：

- 不进入正文主干。
- 可合并为背景过渡。
- 或完全丢弃。

### 3.3 ScenePlanService

输入：

- `chapter_brief.json`
- `selected_events.json`
- `writer_authorization`
- `safe_context`

输出：

```text
outputs/sim_xxx/scene_plan.json
```

结构：

```json
{
  "version": "正式版V1.2",
  "chapter_title": "入口处的异常",
  "pov": "char_protagonist",
  "scenes": [
    {
      "scene_id": "scene_001",
      "scene_goal": "建立核心地点入口的异常",
      "location_id": "location_gate",
      "pov_state": "警觉但仍试图用常理解释",
      "conflict": "入口状态与世界常识冲突",
      "event_ids": ["evt_0003", "evt_0004"],
      "scene_role": "setup",
      "reveal_budget": {
        "allowed": ["入口近期被改动"],
        "suspected": ["有人比主角更早进入"],
        "forbidden": ["隐藏行动者身份"]
      },
      "emotional_turn": "观察 -> 不安",
      "ending_beat": "主角发现痕迹方向不符合任何正常出入口。"
    }
  ],
  "chapter_hook": {
    "type": "clue_hook",
    "event_id": "evt_0012",
    "requirement": "以未解释的物理痕迹结束。"
  }
}
```

---

## 4. 开发计划

### 4.1 代码模块

新增：

```text
app/services/event_selection_service.py
app/services/scene_plan_service.py
app/models/scene_plan.py
```

修改：

```text
app/runner/simulation_runner.py
app/services/narrative_service.py
app/models/narrative.py
app/quality/story_quality_evaluator_service.py
```

### 4.2 开发步骤

#### 步骤 1：新增 ScenePlan 模型

模型包括：

- `ScenePlan`
- `SceneSpec`
- `SceneRevealBudget`
- `ChapterHook`

#### 步骤 2：实现 EventSelectionService

方法：

```python
class EventSelectionService:
    def select(self, events, chapter_brief, state, world) -> SelectedEvents: ...
    def save(self, sim_dir, selected_events) -> None: ...
```

实现重点：

- 事件评分。
- 重复事件合并。
- wait/observe 过滤。
- 至少保留关键因果事件。

#### 步骤 3：实现 ScenePlanService

方法：

```python
class ScenePlanService:
    def build(self, selected_events, chapter_brief, safe_context) -> ScenePlan: ...
    def save(self, sim_dir, scene_plan) -> None: ...
```

场景数量策略：

- 少于 4 个核心事件：1-2 个 scene。
- 5-8 个核心事件：2-3 个 scene。
- 9 个以上核心事件：最多 4 个 scene，合并低价值事件。

#### 步骤 4：Runner 集成

顺序：

```text
读取事件
→ ChapterBriefService
→ EventSelectionService
→ ScenePlanService
→ NarrativeService
```

#### 步骤 5：NarrativeService 改造

新增：

```python
NarrativeService(..., scene_plan: Optional[ScenePlan] = None)
```

Writer prompt 加入：

- `[Scene plan]`
- 每个 scene 的 goal/conflict/reveal_budget/emotional_turn/ending_beat。

正文要求：

- 按 scene 写，但不要输出 scene 标题。
- 每个 scene 必须有动作、感官、信息推进。
- 不要逐条复述事件 ID。

#### 步骤 6：chapter_plan 兼容

`chapter_plan.json` 保留旧字段，同时新增：

```json
{
  "scene_count": 3,
  "scene_ids": ["scene_001", "scene_002"],
  "selected_event_ids": []
}
```

---

## 5. 详细设计

### 5.1 scene_role 分类

支持：

- `setup`：建立场景/异常/目标。
- `escalation`：提高冲突或风险。
- `reveal`：发现线索或确认事实。
- `misdirection`：制造误导。
- `relationship_turn`：关系转折。
- `reversal`：反转已有判断。
- `hook`：结尾钩子。

### 5.2 事件合并规则

可以合并：

- 同地点连续 observe。
- 同一对象连续 inspect/search。
- 没有新增事实的 talk。
- 多次 wait。

不能合并：

- 发现新 clue。
- 关系状态变化。
- 角色公开说出重要台词。
- 风险等级上升。
- Director intervention。

### 5.3 Scene Plan 与授权边界

ScenePlan 不得新增事实。

如果需要写 conflict，但结构化输入没有对应来源，只能写：

- 氛围压迫。
- POV 内心不确定。
- 动作上的回避。

不能新增：

- 新人物关系变化。
- 新线索。
- 新地点。
- 新规则。

---

## 6. 验收标准

1. 每次模拟输出 `selected_events.json`。
2. 每次模拟输出 `scene_plan.json`。
3. `chapter_draft.md` 明显减少事件流水账。
4. 低价值 wait/observe 不再大段进入正文。
5. 每个 scene 至少关联 1 个核心事件。
6. chapter_debug 中能追踪 scene 到 event 的来源。
7. 旧的 chapter_plan 消费方不报错。

---

## 7. 风险与注意事项

- 事件筛选不能丢失关键因果链。
- ScenePlan 不能为了戏剧性新增事实。
- 如果事件过少，ScenePlan 应生成保守结构，而不是强行制造冲突。
- Writer 正文不能暴露 scene_id、event_id、reveal_budget 等后台字段。
