# 正式版V1.4 内容质量优化：前端控制、记忆连续性与揭示节奏

## 1. 版本目标

正式版V1.4 的目标是把内容质量优化从后台自动流程扩展到可控产品能力，让用户能够选择生成方向、触发针对性重写，并让角色记忆和真相揭示节奏在多章节中持续生效。

本版本建立三个能力：

1. 前端质量控制面板。
2. 角色记忆与关系连续性增强。
3. Reveal Budget 真相揭示节奏管理。

核心目标：

- 用户可以选择“悬疑推进 / 恐怖氛围 / 角色冲突 / 线索密集 / 慢热铺垫”。
- 用户可以一键重写：“加强悬念 / 减少解释 / 增强角色冲突 / 更像小说正文”。
- Agent 行动与 Writer 正文持续引用角色记忆。
- 每章只能揭示被允许的信息，避免过早说破真相。

---

## 2. 需求文档

### 2.1 背景问题

完成 V1.1-V1.3 后，系统已经具备：

- chapter brief。
- selected events。
- scene plan。
- style rewrite。
- quality feedback。

但仍有三个问题：

1. 用户无法控制想要的质量方向。
2. 多章节之间角色记忆、关系变化、悬念延续不够稳定。
3. 线索和真相揭示缺少明确预算，容易过早揭示或长期不推进。

### 2.2 用户价值

用户可以：

- 选择本章更重悬疑、恐怖、冲突或线索。
- 对不满意的章节执行目标明确的重写。
- 看到本章揭示了什么、保留了什么。
- 获得更稳定的角色连续性。
- 生成更适合长篇连载的章节。

### 2.3 功能范围

本版本包含：

1. 前端新增生成质量控制项。
2. API 接收 `quality_controls`。
3. `ChapterBriefService`、`ScenePlanService`、`NarrativeStyleRewriter` 使用质量控制项。
4. 新增 `RevealBudgetService`。
5. 扩展 MemoryService 的记忆分类。
6. 新增手动 rewrite API。
7. 新增章节末 continuity summary。

本版本不包含：

- 在线富文本编辑器。
- 多候选正文并排比较。
- 自动生成整本小说。
- 人工审批工作流。

---

## 3. 前端需求

### 3.1 质量控制面板

在 Overview 或 Simulation 页面新增：

#### 章节风格

单选或多选：

- 悬疑推进
- 恐怖氛围
- 角色冲突
- 线索密集
- 慢热铺垫

#### 生成强度

单选：

- 保守：更忠实事件
- 平衡：忠实 + 文学化
- 强化：更重视成稿质感

#### 结尾类型

单选：

- 感官钩子
- 线索钩子
- 关系钩子
- 危险钩子

#### 一键重写

按钮：

- 加强悬念
- 减少解释
- 增强角色冲突
- 更像小说正文

### 3.2 前端请求结构

启动模拟：

```json
{
  "world_id": "dark_city_001",
  "mode": "llm",
  "version": "正式版V1",
  "quality_controls": {
    "style_focus": ["悬疑推进", "恐怖氛围"],
    "generation_strength": "平衡",
    "ending_hook_type": "线索钩子",
    "rewrite_policy": "auto_once"
  }
}
```

手动重写：

```json
{
  "rewrite_intent": "加强悬念",
  "preserve_facts": true,
  "preserve_scene_plan": true
}
```

---

## 4. 后端需求

### 4.1 API 模型

新增：

```python
class QualityControls(BaseModel):
    style_focus: List[str] = []
    generation_strength: str = "平衡"
    ending_hook_type: str = "线索钩子"
    rewrite_policy: str = "auto_once"

class RewriteRequest(BaseModel):
    rewrite_intent: str
    preserve_facts: bool = True
    preserve_scene_plan: bool = True
```

`SimulationRequest` 增加：

```python
quality_controls: QualityControls = QualityControls()
```

新增接口：

```text
POST /api/simulations/{sim_id}/rewrite
GET /api/simulations/{sim_id}/quality-controls
GET /api/simulations/{sim_id}/reveal-budget
GET /api/simulations/{sim_id}/continuity
```

### 4.2 QualityControls 传递链路

```text
API request
→ SimulationRunner.run(... quality_controls)
→ ChapterBriefService
→ EventSelectionService
→ ScenePlanService
→ NarrativeService
→ NarrativeStyleRewriter
→ QualityEvaluator
```

---

## 5. Reveal Budget 设计

### 5.1 目标

控制每章的信息揭示节奏。

解决：

- 第一章泄露 hidden truth。
- 线索长期不推进。
- suspected facts 被写成确定事实。
- 读者问题没有节奏管理。

### 5.2 新增服务

```text
app/services/reveal_budget_service.py
app/models/reveal_budget.py
```

接口：

```python
class RevealBudgetService:
    def build(self, world, chapter_no, target_chapters, open_threads, evidence_graph) -> RevealBudget: ...
    def save(self, sim_dir, budget) -> None: ...
```

### 5.3 reveal_budget.json

```json
{
  "version": "正式版V1.4",
  "chapter_no": 1,
  "allowed_reveals": [
    {
      "fact": "入口近期被改动",
      "level": "surface",
      "source": "clue_new_lock_core"
    }
  ],
  "suspected_only": [
    {
      "fact": "现场可能有未被看见的行动者",
      "reason": "只能通过痕迹暗示，不能确认身份"
    }
  ],
  "forbidden_reveals": [
    {
      "fact": "隐藏行动者身份",
      "until_chapter": 4
    }
  ],
  "required_questions": [
    "入口为什么像刚被改动过？",
    "谁比主角更早进入？"
  ],
  "payoff_targets": [
    {
      "thread_id": "thread_recent_entry",
      "expected_payoff_chapter": 3
    }
  ]
}
```

### 5.4 使用位置

- ChapterBriefService：确定本章主问题和 reveal policy。
- ScenePlanService：每个 scene 设置 reveal_budget。
- NarrativeService：控制 allowed/suspected/forbidden。
- ConsistencyService：检查是否越权揭示。
- QualityEvaluator：检查是否完全没有推进。

---

## 6. 记忆连续性设计

### 6.1 Memory 分类

扩展 MemoryService：

```json
{
  "memory_type": "fact | suspicion | emotional_memory | relationship_memory | unresolved_question",
  "owner_character_id": "char_protagonist",
  "content": "",
  "source_event_id": "",
  "confidence": 0.7,
  "emotional_weight": 0.8,
  "related_thread_id": "thread_recent_entry",
  "visible_to_pov": true
}
```

### 6.2 Agent 使用记忆

Agent 每次决策必须参考：

- 1 条事实记忆。
- 1 条怀疑或未解问题。
- 如果有互动，则参考 1 条关系记忆。

Agent prompt 增加：

```text
你的行动必须考虑相关记忆。不要无视上一章或前几 tick 已经发生的事实。
```

### 6.3 Writer 使用记忆

Writer 只能使用 POV 可见记忆。

正文中记忆体现方式：

- 动作迟疑。
- 对某人不信任。
- 对某个物件产生联想。
- 重复出现的感官细节。

禁止：

- 把 memory_id 写进正文。
- 把非 POV 记忆写成确定事实。

### 6.4 章节末 continuity summary

新增：

```text
outputs/sim_xxx/chapter_continuity.json
```

结构：

```json
{
  "version": "正式版V1.4",
  "chapter_no": 1,
  "resolved_threads": [],
  "open_threads": [],
  "new_questions": [],
  "character_memory_updates": [],
  "relationship_changes": [],
  "next_chapter_seeds": []
}
```

---

## 7. 手动重写设计

### 7.1 API 行为

接口：

```text
POST /api/simulations/{sim_id}/rewrite
```

流程：

1. 读取 `chapter_draft.md`。
2. 读取 `scene_plan.json`。
3. 读取 `writer_authorization` 或 `chapter_debug.json`。
4. 根据 `rewrite_intent` 生成临时 rewrite plan。
5. 调用 `NarrativeStyleRewriter`。
6. 运行一致性检查。
7. 保存新版本：

```text
chapter_draft_rewrite_001.md
manual_rewrite_report_001.json
```

### 7.2 rewrite_intent 映射

| rewrite_intent | 指令 |
|---|---|
| 加强悬念 | 延迟解释、增强读者问题、强化异常细节 |
| 减少解释 | 压缩背景说明，改成动作/感官呈现 |
| 增强角色冲突 | 只使用已有 relationship_updates 和 interaction_events |
| 更像小说正文 | 减少日志感，优化段落、节奏和句式 |

---

## 8. 开发计划

### 8.1 代码模块

新增：

```text
app/models/quality_controls.py
app/models/reveal_budget.py
app/services/reveal_budget_service.py
app/services/manual_rewrite_service.py
```

修改：

```text
api/server.py
web/src/views/Overview.vue
app/runner/simulation_runner.py
app/services/chapter_brief_service.py
app/services/scene_plan_service.py
app/services/narrative_service.py
app/services/narrative_style_rewriter.py
app/services/memory_service.py
app/services/consistency_service.py
```

### 8.2 实施顺序

1. 新增 QualityControls 模型。
2. API 和前端传递 quality_controls。
3. 新增 RevealBudgetService。
4. 将 reveal_budget 注入 brief/scene/writer/consistency。
5. 扩展 MemoryService 分类。
6. Agent context 注入分类记忆。
7. 新增 chapter_continuity 输出。
8. 新增 manual rewrite API。
9. 前端增加控制面板和一键重写按钮。

---

## 9. 验收标准

1. 前端能选择风格方向、生成强度、结尾类型。
2. API 能接收并保存 `quality_controls`。
3. 每次模拟输出 `reveal_budget.json`。
4. Writer 不会把 forbidden reveals 写成真相。
5. Agent 决策能引用相关记忆。
6. 每章输出 `chapter_continuity.json`。
7. 用户可以通过 API 或页面触发手动重写。
8. 手动重写不新增事实，不破坏 scene plan。
9. 完成弹窗和状态接口显示 `正式版V1`。

---

## 10. 风险与注意事项

- 用户选择“强化”不能绕过事实边界。
- 手动重写必须强制一致性检查。
- Reveal Budget 不能阻止所有推进，否则章节会停滞。
- 记忆不能污染 POV 权限。
- 前端控制项需要简单，避免让用户配置负担过重。
