# 正式版V1.1 内容质量优化：章节 Brief 与世界输入密度

## 1. 版本目标

正式版V1.1 的目标是解决“生成内容缺少明确章节方向、上游世界信息薄、角色行为缺乏持续驱动力”的问题。

本版本不直接重写 Writer 主流程，而是先提升输入质量和章节目标质量，让后续沙盘推演与正文生成有更清晰的叙事约束。

核心目标：

1. 为每章生成结构化 `chapter_brief`。
2. 强化世界、角色、地点配置中的“写作可用字段”。
3. 让 Agent 决策、NarrativeService、QualityEvaluator 都能读取同一份章节目标。
4. 将正式版V1 的运行版本信息统一写入产物。

---

## 2. 需求文档

### 2.1 背景问题

当前生成内容质量受以下因素限制：

- 世界配置只描述基础设定，缺少清晰的主线问题、隐藏真相、揭示边界。
- 角色配置中公开目标、私人动机、秘密、误判、情绪压力不足。
- 地点更多是导航节点，缺少叙事功能定义。
- 章节运行以 tick 为主，缺少“这一章到底要完成什么”的明确结构。
- Writer 只能根据事件日志写正文，容易形成流水账。

### 2.2 用户价值

用户可以获得更稳定的章节生成质量：

- 每章有明确主问题和结尾钩子。
- 角色行动更像围绕目标推进，而不是随机观察/等待。
- Writer 能写出更一致的悬疑、恐怖、关系冲突节奏。
- 产物更容易检查、复盘和二次优化。

### 2.3 功能范围

本版本包含：

1. 新增 `ChapterBriefService`。
2. 新增 `chapter_brief.json` 产物。
3. 扩展 world/characters/map 的推荐字段。
4. Story Bootstrap 生成时补齐新增字段。
5. Runtime validator 检查新增字段基本完整性。
6. Agent context 注入 chapter brief。
7. Narrative prompt 注入 chapter brief。

本版本不包含：

- Scene Plan 重构。
- 多轮 rewrite。
- 前端风格控制。
- 自动重写按钮。

### 2.4 产物定义

新增文件：

```text
outputs/sim_xxx/chapter_brief.json
```

推荐结构：

```json
{
  "version": "正式版V1.1",
  "chapter_no": 1,
  "chapter_title_hint": "入口处的异常",
  "main_question": "主角第一次进入核心地点时，发现了什么无法解释的异常？",
  "chapter_goal": "建立核心异常、打开第一条主线悬念、让主角产生继续探索的必要性。",
  "tone": "克制、压迫、悬疑",
  "must_advance_threads": [
    "thread_recent_entry",
    "thread_hidden_actor_trace"
  ],
  "must_include_clues": [
    "clue_new_lock_core"
  ],
  "relationship_focus": [
    {
      "source": "char_protagonist",
      "target": "npc_gatekeeper",
      "expected_shift": "从礼貌询问转为轻微不信任"
    }
  ],
  "reveal_policy": {
    "allowed_facts": [],
    "suspected_facts": [],
    "forbidden_facts": []
  },
  "ending_hook": {
    "type": "sensory_or_clue_hook",
    "requirement": "以一个具体感官异常或线索缺口结束，不总结。"
  }
}
```

---

## 3. 开发计划

### 3.1 代码模块

预计新增/修改：

```text
app/services/chapter_brief_service.py
app/runner/simulation_runner.py
app/services/character_agent_service.py
app/services/narrative_service.py
app/services/world_runtime_validator.py
app/bootstrap/*_generator.py
app/models/world.py
app/models/chapter_brief.py
```

### 3.2 开发步骤

#### 步骤 1：新增模型

新增 `app/models/chapter_brief.py`：

- `ChapterBrief`
- `RelationshipFocus`
- `RevealPolicy`
- `EndingHookPolicy`

字段原则：

- 全部可 JSON 序列化。
- 字段名保持稳定。
- 对 Writer 直接有用。

#### 步骤 2：新增 ChapterBriefService

职责：

1. 读取 world bible、characters、map、clues、open_threads。
2. 根据章节编号和目标生成 brief。
3. 保存到 `chapter_brief.json`。
4. 供 Runner、Agent、NarrativeService 读取。

服务接口：

```python
class ChapterBriefService:
    def build(self, world, chapter_no: int, target_chapters: int) -> ChapterBrief: ...
    def save(self, sim_dir: Path, brief: ChapterBrief) -> None: ...
    def load(self, sim_dir: Path) -> Optional[ChapterBrief]: ...
```

#### 步骤 3：Runner 集成

在 `SimulationRunner.run()` 初始化后、tick 循环前：

1. 创建 `ChapterBriefService`。
2. 调用 `build()`。
3. 保存 `chapter_brief.json`。
4. 将 brief 传给 Agent context。
5. 将 brief 传给 NarrativeService。

#### 步骤 4：Agent context 注入

在 `AgentContext` 中增加：

```python
chapter_main_question: str
chapter_goal: str
must_advance_threads: list[str]
relationship_focus: list[dict]
reveal_policy: dict
```

Agent 决策 prompt 加入：

- 你的行动应该服务本章目标。
- 优先推进 `must_advance_threads`。
- 不要揭示 `forbidden_facts`。
- 每次行动说明验证了什么假设。

#### 步骤 5：NarrativeService 注入

在 `_build_narrative_user_prompt()` 增加 `[Chapter brief]` 区块。

Writer 必须遵守：

- 本章主问题。
- 本章情绪基调。
- 结尾钩子要求。
- reveal policy。

#### 步骤 6：Story Bootstrap 扩展字段

世界 Bible 增加：

```json
{
  "core_motif": "",
  "main_question": "",
  "hidden_truth": "",
  "first_volume_goal": "",
  "ending_direction": "",
  "forbidden_early_reveals": []
}
```

角色增加：

```json
{
  "public_motive": "",
  "private_motive": "",
  "withheld_information": "",
  "misbeliefs_about_others": [],
  "current_pressure": "",
  "triggered_behavior_patterns": []
}
```

地点增加：

```json
{
  "narrative_function": "",
  "information_gap": "",
  "suitable_conflicts": [],
  "forbidden_events": []
}
```

#### 步骤 7：Validator 检查

`RuntimeWorldValidator` 增加正式版V1.1 检查：

- world bible 是否有主线问题。
- POV 角色是否有私人动机。
- 至少 3 个地点有叙事功能。
- 至少 3 条线索有 related_thread。

---

## 4. 详细设计

### 4.1 ChapterBrief 生成策略

优先级：

1. 使用 world bible 中的主线问题。
2. 使用 chapter_goal 中的目标。
3. 使用 open_threads 中 priority 最高的悬念。
4. 使用 clues/evidence 中允许第一章揭示的内容。
5. 如果信息不足，生成保守 brief。

### 4.2 reveal_policy 规则

`allowed_facts`：

- POV 已知事实。
- 本章可公开推进的 surface clue。

`suspected_facts`：

- POV 可以怀疑但不能确认的内容。
- hidden_actor 的行动痕迹。

`forbidden_facts`：

- hidden_truth。
- forbidden_early_reveals。
- allowed_reveal_chapters 大于当前章节的证据。

### 4.3 Agent 决策约束

Agent 输出中新增：

```json
{
  "hypothesis_to_test": "",
  "thread_to_advance": "",
  "expected_story_value": ""
}
```

这样后续 EventSelectionService 可以评估事件价值。

### 4.4 兼容策略

- 旧 world 不含新增字段时不报硬错误，先 warning。
- Story Bootstrap 新生成的 world 必须补齐。
- `chapter_brief.json` 缺失时 NarrativeService 使用保守默认 brief。

---

## 5. 验收标准

1. 每次模拟输出 `chapter_brief.json`。
2. `version_report.json.version` 为 `正式版V1`。
3. Agent prompt 中出现 chapter brief 信息。
4. chapter_draft 不再只依赖事件日志，应体现 main_question、tone、ending_hook。
5. Runtime validator 能指出 world 输入密度不足的问题。
6. 旧世界仍可运行，但会产生字段缺失 warning。

---

## 6. 风险与注意事项

- 不要让 brief 自行创造新事实。
- brief 只能组织已有设定与线索。
- hidden_truth 只能进入 forbidden/suspected，不得直接写入 Writer 的 allowed facts。
- Agent 可以知道系统目标，但 Writer 正文不能暴露后台字段名。
