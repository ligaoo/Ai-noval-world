# 正式版V1.3 内容质量优化：风格重写与质量反馈闭环

## 1. 版本目标

正式版V1.3 的目标是解决“初稿忠实但不够好看、质量评估不能直接驱动改写、一次 LLM 调用承担过多职责”的问题。

本版本在 V1.1 的 chapter brief 和 V1.2 的 scene plan 基础上，引入多阶段写作：

```text
结构化初稿
→ 忠实度检查
→ 风格质量评估
→ 受约束润色重写
→ 最终一致性检查
```

核心目标：

1. 新增 `NarrativeStyleRewriter`。
2. 将 QualityEvaluator 输出改为可执行 rewrite plan。
3. 支持“只改语言，不改事实”的 style rewrite pass。
4. 生成 `rewrite_plan.json`、`style_rewrite_report.json`。
5. 明显提升正文的小说感、节奏、悬念和人物张力。

---

## 2. 需求文档

### 2.1 背景问题

当前 Writer 一次性负责：

- 遵守事实边界。
- 按事件生成正文。
- 控制节奏。
- 保持文风。
- 制造悬念。
- 避免泄露真相。

这导致模型经常选择保守输出，文本可能正确但不好看。

同时，质量评估如果只给分或列问题，对自动优化帮助有限。

### 2.2 用户价值

用户可以获得：

- 更像小说正文的章节。
- 更少说明文、总结句、后台感。
- 更稳定的悬疑/恐怖/关系冲突风格。
- 可追踪的 rewrite plan。
- 可以区分“事实错误”和“文风不足”。

### 2.3 功能范围

本版本包含：

1. 初稿与润色稿分离。
2. 风格重写服务。
3. QualityEvaluator 输出 rewrite plan。
4. 风格 profile 注入。
5. 改写前后差异报告。
6. 改写后再跑一致性检查。

本版本不包含：

- 前端手动选择风格。
- 多版本候选对比。
- 人工编辑器。
- 长篇全局章节重排。

---

## 3. 需求细节

### 3.1 新增产物

```text
outputs/sim_xxx/chapter_draft_raw.md
outputs/sim_xxx/rewrite_plan.json
outputs/sim_xxx/chapter_draft.md
outputs/sim_xxx/style_rewrite_report.json
```

说明：

- `chapter_draft_raw.md`：结构化初稿，优先忠实。
- `rewrite_plan.json`：质量评估生成的可执行改写计划。
- `chapter_draft.md`：最终正文。
- `style_rewrite_report.json`：记录改写策略、输入约束、是否通过一致性检查。

### 3.2 rewrite_plan 结构

```json
{
  "version": "正式版V1.3",
  "overall_goal": "增强悬疑压迫感，减少事件复述，不新增事实。",
  "problems": [
    {
      "type": "low_scene_tension",
      "location": "scene_002",
      "evidence": "第二场景只复述了检查动作，没有形成新的读者问题。",
      "rewrite_instruction": "利用 scene_plan 中的 suspected facts 增强不确定感，不新增线索。"
    }
  ],
  "rewrite_plan": [
    "压缩第一场景的背景解释。",
    "将第三条线索延后到场景结尾。",
    "增强 POV 对异常物件的感官反应。",
    "减少‘他意识到/他觉得’类总结句。"
  ],
  "forbidden_changes": [
    "不得新增地点。",
    "不得新增角色关系变化。",
    "不得确认 suspected_facts。",
    "不得新增 clue 或 object。"
  ]
}
```

### 3.3 style_rewrite_report 结构

```json
{
  "version": "正式版V1.3",
  "style_profile": "horror_suspense_default",
  "input_draft_chars": 3200,
  "output_draft_chars": 4100,
  "rewrite_applied": true,
  "rewrite_focus": [
    "减少流水账",
    "增强感官压迫",
    "强化结尾钩子"
  ],
  "consistency_after_rewrite": {
    "passed": true,
    "violations": []
  }
}
```

---

## 4. 开发计划

### 4.1 代码模块

新增：

```text
app/services/narrative_style_rewriter.py
app/services/rewrite_plan_builder.py
app/models/rewrite_plan.py
app/genre/style_profiles/
```

修改：

```text
app/services/narrative_service.py
app/quality/story_quality_evaluator_service.py
app/services/consistency_service.py
app/services/draft_faithfulness_checker.py
app/runner/simulation_runner.py
```

### 4.2 开发步骤

#### 步骤 1：保留 raw draft

NarrativeService 当前生成正文后直接写 `chapter_draft.md`。

改为：

1. Writer 生成 raw draft。
2. 保存 `chapter_draft_raw.md`。
3. 后续 rewrite pass 输出最终 `chapter_draft.md`。

#### 步骤 2：QualityEvaluator 输出 rewrite plan

将质量问题分类：

- `low_scene_tension`
- `event_log_feel`
- `weak_hook`
- `too_much_exposition`
- `flat_character_reaction`
- `missing_sensory_detail`
- `unclear_thread_progress`
- `style_inconsistent`

每个问题必须包含：

- evidence。
- affected scene。
- rewrite_instruction。
- forbidden_changes。

#### 步骤 3：新增 RewritePlanBuilder

职责：

- 将质量报告转换为 rewrite plan。
- 合并重复建议。
- 过滤不能执行或可能导致越权的建议。
- 加入 writer_authorization 约束。

#### 步骤 4：新增 NarrativeStyleRewriter

接口：

```python
class NarrativeStyleRewriter:
    def rewrite(
        self,
        draft: str,
        scene_plan: dict,
        rewrite_plan: RewritePlan,
        writer_authorization: dict,
        style_profile: dict,
    ) -> str: ...
```

重写原则：

- 允许改段落顺序，但只能在 scene 内微调。
- 允许增强感官描写。
- 允许压缩说明。
- 允许替换句式。
- 不允许新增事实、线索、地点、人物、关系变化。

#### 步骤 5：改写后校验

重写后必须执行：

1. `DraftFaithfulnessChecker`
2. `ConsistencyService.check_consistency`

如果失败：

- 尝试一次受约束修订。
- 仍失败则回退 raw draft 或保留 raw draft 并记录 report。

#### 步骤 6：风格 profile

新增文件示例：

```text
app/genre/style_profiles/horror_suspense_default.json
```

结构：

```json
{
  "style_id": "horror_suspense_default",
  "principles": [
    "少解释，多动作和感官。",
    "延迟确认真相，用异常细节制造不确定。",
    "每个场景至少产生一个新的读者问题。",
    "结尾使用具体感官或动作钩子。"
  ],
  "avoid": [
    "流水账",
    "复述事件日志",
    "后台术语",
    "一次性解释设定",
    "过度使用似乎、仿佛、意识到"
  ],
  "sentence_guidance": [
    "多使用短句制造压迫。",
    "段落结尾优先留下动作或感官残留。"
  ]
}
```

---

## 5. 详细设计

### 5.1 多阶段写作流程

正式版V1.3 的 NarrativeService 流程：

```text
1. 读取 chapter_brief / selected_events / scene_plan
2. 生成 raw draft
3. 保存 chapter_draft_raw.md
4. 运行 faithfulness check
5. 运行 quality evaluator
6. 生成 rewrite_plan.json
7. 调用 NarrativeStyleRewriter
8. 保存 chapter_draft.md
9. 运行 consistency check
10. 保存 style_rewrite_report.json
```

### 5.2 Rewrite Prompt 设计

系统 prompt 核心：

```text
你是受约束的小说润色编辑。
你只能改写语言、节奏、段落衔接和感官呈现。
不得新增 plot-level facts、clues、objects、locations、rules、relationship changes。
所有事实边界以 writer_authorization、scene_plan、rewrite_plan 为准。
```

用户 prompt 包含：

- raw draft。
- scene plan。
- rewrite plan。
- style profile。
- forbidden changes。
- writer authorization。

### 5.3 rewrite 失败策略

失败类型：

1. LLM 调用失败。
2. 改写新增事实。
3. 改写泄露 forbidden facts。
4. 改写删除关键事件。

处理：

- LLM 调用失败：使用 raw draft。
- 一致性失败：尝试 revise once。
- revise once 失败：回退 raw draft，并记录 `rewrite_applied=false`。

### 5.4 质量评分与 rewrite 的关系

质量评分不直接决定是否重写。

触发重写条件：

- overall_score < 阈值。
- 或存在严重问题：weak_hook、event_log_feel、forbidden_style_issue。
- 或用户配置 `always_style_rewrite=true`。

正式版V1.3 默认建议：

```text
always_style_rewrite=true
max_style_rewrite_passes=1
```

---

## 6. 验收标准

1. 每次 LLM 正文生成保存 `chapter_draft_raw.md`。
2. 每次质量评估生成 `rewrite_plan.json`。
3. 最终正文保存为 `chapter_draft.md`。
4. 生成 `style_rewrite_report.json`。
5. 改写后不新增事实、不泄露 forbidden facts。
6. 正文中流水账表达明显减少。
7. 结尾钩子更具体，不以总结句结束。
8. 如果改写失败，可以安全回退 raw draft。

---

## 7. 风险与注意事项

- Rewrite pass 最容易引入新事实，必须强约束。
- 不要让质量评估器提出“新增冲突/新增线索”类建议。
- 所有 rewrite_instruction 必须基于已有 scene_plan 和 writer_authorization。
- 风格提升不能优先于事实忠实。
