# V5.1 开发计划：Story Quality Evaluator 故事质量评估器

> 版本主题：章节质量评估闭环  
> 版本目标：在章节生成后自动评估故事质量，输出结构化质量报告，为后续 V5.2 自动修稿提供输入。  
> 重要边界：V5.1 只做“评估”和“建议”，不做自动修稿。自动修稿属于 V5.2。

---

## 0. 版本定位

V5.1 是 V5 的第一个子版本，核心是新增：

```text
StoryQualityEvaluator
QualityReport
QualityReport API
Quality Report Panel
Quality Evaluation Tests
V5.1 使用文档
```

它要解决的问题是：

```text
1. 章节生成后不知道好不好
2. ConsistencyCheck 只能检查有没有乱编，不能判断故事质量
3. 用户不知道哪里拖、哪里弱、哪里需要改
4. 系统无法为后续 RewriteOptimizer 提供结构化修稿建议
5. 多章生成后缺少质量趋势数据
```

V5.1 完成后，章节生成流程从：

```text
chapter_plan
↓
narrative_writer
↓
consistency_check
↓
chapter_final
```

升级为：

```text
chapter_plan
↓
narrative_writer
↓
consistency_check
↓
story_quality_evaluator
↓
quality_report.json
↓
chapter_final
```

注意：

```text
V5.1 不自动修改正文
V5.1 不生成 rewrite_diff
V5.1 不负责线程看板
V5.1 不负责长篇稳定性测试
```

---

## 1. V5.1 总目标

V5.1 需要实现：

```text
1. 章节生成后自动触发质量评估
2. 支持手动通过 API 重新评估章节质量
3. 输出标准化 quality_report.json
4. 能给出 overall_score 和多维度评分
5. 能识别常见质量问题
6. 能生成可执行的 rewrite suggestions
7. 能判断是否建议进入 V5.2 自动修稿
8. 质量评估失败不影响 simulation_runner 主流程
9. 前端能展示质量报告
10. 测试覆盖典型质量问题
11. 文档说明使用方式
```

---

## 2. V5.1 不做什么

V5.1 暂时不做：

```text
1. RewriteOptimizer 自动修稿
2. 修稿前后 Diff 页面
3. Long-Run Stability Test
4. OpenThreadManager 线程看板
5. Style Bible 编辑器
6. Project Template Generator
7. 多章节质量趋势复杂图表
8. 自动接受 / 拒绝修稿结果
```

这些放到后续版本：

```text
V5.2：RewriteOptimizer + 修稿对比
V5.3：Long-Run Stability Test
V5.4：OpenThreadManager + 线程看板
V5.5：Style & Voice Consistency
V5.6：Project Template Generator
```

---

## 3. 核心模块

V5.1 后端建议新增以下模块：

```text
StoryQualityEvaluatorService
QualityPreAnalyzer
QualityLLMEvaluator
QualityScoreNormalizer
QualityProblemClassifier
RewriteSuggestionGenerator
QualityReportWriter
QualityReportRepository
QualityEvaluationController
QualityEvaluationConfig
```

目录建议：

```text
app/
  quality/
    story_quality_evaluator_service.py
    quality_pre_analyzer.py
    quality_llm_evaluator.py
    quality_score_normalizer.py
    quality_problem_classifier.py
    rewrite_suggestion_generator.py
    quality_report_writer.py
    quality_report_repository.py
    quality_evaluation_config.py

  api/
    quality_evaluation_controller.py

  schemas/
    quality_report_schema.json
    quality_evaluation_request_schema.json

  prompts/
    story_quality_evaluation_prompt.txt

  tests/
    quality/
      test_quality_report_schema.py
      test_quality_pre_analyzer.py
      test_story_quality_evaluator.py
      test_quality_api.py
      fixtures/
        weak_conflict_chapter.md
        slow_middle_chapter.md
        weak_hook_chapter.md
```

如果你的项目是 Java/Spring，可以对应为：

```text
src/main/java/.../quality/
  StoryQualityEvaluatorService.java
  QualityPreAnalyzer.java
  QualityLlmEvaluator.java
  QualityScoreNormalizer.java
  QualityProblemClassifier.java
  RewriteSuggestionGenerator.java
  QualityReportWriter.java
  QualityReportRepository.java
  QualityEvaluationConfig.java

src/main/java/.../controller/
  QualityEvaluationController.java

src/main/resources/prompts/
  story_quality_evaluation_prompt.txt
```

---

## 4. 章节生成流程集成

### 4.1 simulation_runner 接入点

V5.1 应该在章节生成完成并通过一致性检查后触发。

推荐流程：

```text
SimulationRunner.runChapter()
↓
ChapterPlanner.generatePlan()
↓
NarrativeWriter.generateDraft()
↓
ConsistencyCheck.run()
↓
if consistency passed or final draft available:
    StoryQualityEvaluator.evaluate()
↓
QualityReportWriter.write()
↓
Update RunIndex / Metrics
```

---

### 4.2 伪代码

```python
def generate_chapter(simulation_id: str, chapter_id: str):
    chapter_plan = chapter_planner.generate(simulation_id, chapter_id)

    draft = narrative_writer.generate(
        simulation_id=simulation_id,
        chapter_id=chapter_id,
        chapter_plan=chapter_plan
    )

    consistency_report = consistency_checker.run(
        simulation_id=simulation_id,
        chapter_id=chapter_id,
        draft=draft
    )

    final_draft = draft
    if consistency_report.revise_required:
        final_draft = narrative_writer.revise_once(
            draft=draft,
            consistency_report=consistency_report
        )

    try:
        quality_report = story_quality_evaluator.evaluate(
            simulation_id=simulation_id,
            chapter_id=chapter_id,
            chapter_plan=chapter_plan,
            chapter_draft=final_draft,
            consistency_report=consistency_report
        )
        quality_report_writer.write(simulation_id, chapter_id, quality_report)
    except Exception as e:
        quality_report = QualityReport.failed(
            simulation_id=simulation_id,
            chapter_id=chapter_id,
            error=str(e)
        )
        quality_report_writer.write(simulation_id, chapter_id, quality_report)
        error_logger.warn("Quality evaluation failed", e)

    return ChapterGenerationResult(
        chapter_id=chapter_id,
        draft=final_draft,
        consistency_report=consistency_report,
        quality_report=quality_report
    )
```

---

### 4.3 失败降级原则

质量评估失败时：

```text
不能中断章节生成
不能回滚章节正文
不能影响 EventLog
不能影响一致性报告
```

而是输出失败状态报告：

```json
{
  "report_id": "qr_ch_003_failed",
  "simulation_id": "sim_001",
  "chapter_id": "ch_003",
  "status": "failed",
  "overall_score": null,
  "scores": {},
  "problems": [],
  "suggestions": [],
  "rewrite_recommended": false,
  "error": {
    "message": "LLM response JSON parse failed",
    "type": "QUALITY_EVAL_PARSE_ERROR"
  }
}
```

---

## 5. StoryQualityEvaluator 输入

### 5.1 必需输入

```json
{
  "simulation_id": "sim_001",
  "chapter_id": "ch_003",
  "chapter_plan": {},
  "chapter_draft": "章节正文 markdown/text",
  "selected_events": [],
  "consistency_report": {},
  "chapter_summary": {},
  "plot_arc_state": {},
  "character_states": [],
  "open_threads": []
}
```

---

### 5.2 可选输入

```json
{
  "style_bible": {},
  "character_voice_profiles": [],
  "previous_quality_reports": [],
  "previous_chapter_summaries": [],
  "foreshadowing_state": {},
  "narrative_debt_report": {}
}
```

V5.1 可以先不强依赖 Style Bible。  
如果已有 V5.5 的相关结构，可以先预留字段。

---

## 6. QualityReport 输出结构

### 6.1 顶层结构

```json
{
  "report_id": "qr_ch_003_001",
  "simulation_id": "sim_001",
  "chapter_id": "ch_003",
  "chapter_no": 3,
  "status": "success",
  "evaluated_target": "final_draft",
  "created_at": "2026-05-16T00:00:00+08:00",
  "overall_score": 7.4,
  "grade": "B",
  "scores": {},
  "thresholds": {},
  "pre_analysis": {},
  "problems": [],
  "strengths": [],
  "suggestions": [],
  "rewrite_recommended": true,
  "rewrite_priority": "medium",
  "llm_trace_id": "trace_quality_ch_003",
  "cost": {}
}
```

---

### 6.2 scores 结构

```json
{
  "scores": {
    "plot_progress": 8,
    "conflict_strength": 6,
    "character_depth": 7,
    "emotional_curve": 7,
    "suspense": 8,
    "pacing": 6,
    "scene_vividness": 7,
    "dialogue_quality": 6,
    "style_consistency": 8,
    "chapter_hook": 7,
    "payoff_quality": 5,
    "readability": 8
  }
}
```

评分统一使用：

```text
0–10 分
0–3：严重不足
4–5：偏弱
6：合格
7–8：良好
9–10：优秀
```

---

### 6.3 thresholds 结构

```json
{
  "thresholds": {
    "overall_min": 7.0,
    "plot_progress_min": 6,
    "conflict_strength_min": 6,
    "pacing_min": 6,
    "style_consistency_min": 7,
    "chapter_hook_min": 6
  }
}
```

---

### 6.4 problems 结构

```json
{
  "problems": [
    {
      "problem_id": "prob_001",
      "type": "weak_conflict",
      "severity": "medium",
      "score_dimension": "conflict_strength",
      "location": {
        "section_id": "sec_003",
        "paragraph_range": [12, 18]
      },
      "message": "本章主要是调查和发现，人物之间的正面冲突偏弱。",
      "evidence": [
        "连续三个 beat 都是搜索/观察，没有角色阻碍或目标冲突。"
      ],
      "related_events": ["evt_0031", "evt_0032"],
      "can_be_rewritten": true
    }
  ]
}
```

---

### 6.5 strengths 结构

```json
{
  "strengths": [
    {
      "type": "effective_suspense",
      "score_dimension": "suspense",
      "message": "白色面包车线索推进了旧医院近期出入的问题。",
      "related_events": ["evt_0081"]
    }
  ]
}
```

---

### 6.6 suggestions 结构

```json
{
  "suggestions": [
    {
      "suggestion_id": "sug_001",
      "type": "increase_conflict",
      "message": "可以强化看门人阻拦主角接近档案室的紧张感。",
      "rewrite_task": "increase_conflict",
      "target_sections": ["sec_004"],
      "priority": 8,
      "constraints": [
        "只能强化已有阻拦事件的表达",
        "不能新增身体冲突",
        "不能改变事件结果"
      ]
    }
  ]
}
```

注意：  
V5.1 只生成 suggestion，不执行 rewrite_task。

---

## 7. 评估维度定义

### 7.1 plot_progress 剧情推进

检查：

```text
本章是否推进主线
是否发现新线索
是否解决或推进 open_thread
是否只是原地观察
是否对 PlotArc 有贡献
```

低分表现：

```text
没有新线索
没有关系变化
没有目标变化
没有冲突变化
章节结束状态和开始几乎一样
```

---

### 7.2 conflict_strength 冲突强度

检查：

```text
角色目标是否冲突
是否有阻碍
是否有信息差
是否有内心挣扎
是否有时间压力
```

冲突类型：

```text
character_vs_character
character_vs_environment
character_vs_self
character_vs_truth
character_vs_time
```

---

### 7.3 character_depth 人物深度

检查：

```text
角色行为是否有动机
心理变化是否来自事件
是否体现性格
是否有信念变化
是否不是工具人
```

---

### 7.4 emotional_curve 情绪曲线

检查：

```text
本章情绪是否有起伏
是否从怀疑到确认
是否从安全到不安
是否有情绪高点
是否全章平直
```

---

### 7.5 suspense 悬念强度

检查：

```text
是否有有效未解问题
是否推进旧悬念
是否提出新但合理的问题
是否故弄玄虚
是否过早解释
```

---

### 7.6 pacing 节奏

检查：

```text
是否拖沓
是否重复同类动作
是否过快跳转
是否说明过多
是否行动、对白、心理比例合理
```

---

### 7.7 scene_vividness 场景画面感

检查：

```text
地点是否具体
细节是否服务剧情
是否有感官信息
是否过度形容
是否场景可辨识
```

---

### 7.8 dialogue_quality 对白质量

检查：

```text
对白是否推动剧情
是否符合角色
是否有潜台词
是否过度解释
是否每个角色说话一样
```

---

### 7.9 style_consistency 文风一致性

检查：

```text
是否符合当前项目文风
是否突然爽文化
是否过度煽情
是否和前文风格断裂
```

---

### 7.10 chapter_hook 章节钩子

检查：

```text
结尾是否让人想看下一章
是否来自合法事件
是否虚假悬念
是否过度剧透
```

---

### 7.11 payoff_quality 伏笔回收质量

检查：

```text
是否回收前文伏笔
是否回收自然
是否铺垫不足
是否完全没推进伏笔
```

---

### 7.12 readability 可读性

检查：

```text
语言是否流畅
段落是否清晰
是否重复
是否句子过长
是否信息易理解
```

---

## 8. 问题类型枚举

V5.1 至少支持以下 problem type：

```text
weak_conflict
slow_middle
weak_hook
flat_emotional_curve
low_plot_progress
thin_character_motivation
dialogue_too_expository
style_drift
voice_drift
over_explanation
scene_repetition
suspense_without_payoff
too_many_threads_opened
no_thread_progress
payoff_too_abrupt
low_scene_vividness
unclear_character_goal
poor_dialogue_voice
```

---

## 9. Rule-based Pre-analysis

为了降低成本，先做规则预分析，再交给 LLM。

### 9.1 PreAnalysis 输出

```json
{
  "pre_analysis": {
    "plot_event_count": 12,
    "discovery_event_count": 5,
    "conflict_event_count": 1,
    "dialogue_event_count": 2,
    "relationship_change_event_count": 0,
    "new_open_thread_count": 3,
    "thread_progress_count": 1,
    "resolved_thread_count": 0,
    "selected_event_types": {
      "search": 4,
      "inspect": 3,
      "ask": 2,
      "move": 1
    },
    "possible_flags": [
      "low_conflict",
      "repetitive_search_events",
      "no_resolved_thread"
    ]
  }
}
```

---

### 9.2 Rule-based flags

```text
low_conflict：
conflict_event_count = 0 或 conflict_strength 相关事件过少

repetitive_search_events：
连续多个 search / inspect 事件

weak_hook：
chapter_plan.ending_hook 缺失或没有 source_event_id

low_plot_progress：
discovery_event_count = 0 且 thread_progress_count = 0

too_many_threads_opened：
new_open_thread_count > max_new_threads_per_chapter

no_thread_progress：
open_threads 存在但本章未推进任何 thread
```

---

## 10. LLM Evaluation

### 10.1 LLM 输入压缩

不要把所有历史全文塞给模型。

推荐输入：

```text
chapter_plan
chapter_draft
pre_analysis
selected_events_summary
open_threads_summary
plot_arc_state_summary
character_changes_summary
style_constraints_summary
consistency_report_summary
```

---

### 10.2 Prompt 模板

```text
你是小说沙盘引擎的 Story Quality Evaluator。

你的任务是评估章节质量，不是重写章节。

你必须根据以下输入进行评分：
1. chapter_plan
2. chapter_draft
3. selected_events_summary
4. open_threads_summary
5. plot_arc_state
6. character_state
7. pre_analysis
8. consistency_report_summary

评分要求：
- 所有分数使用 0-10
- 必须输出 overall_score
- 必须输出每个维度分数
- 必须指出具体问题
- 必须给出可执行修改建议
- 建议不能新增 EventLog 中不存在的事实
- 建议不能要求提前泄露 forbidden_revelations
- 输出严格 JSON

评估维度：
plot_progress
conflict_strength
character_depth
emotional_curve
suspense
pacing
scene_vividness
dialogue_quality
style_consistency
chapter_hook
payoff_quality
readability

【输入】
{quality_evaluation_context}

【输出 JSON Schema】
{quality_report_schema}
```

---

### 10.3 LLM 输出校验

必须校验：

```text
JSON 可解析
scores 维度齐全
分数在 0–10
problem type 合法
suggestion type 合法
rewrite_task 合法
不能出现新增事实建议
```

如果不合法：

```text
最多 retry 1 次
仍失败则生成 failed quality_report
```

---

## 11. Score Normalization

LLM 打分可能波动，需要归一化。

### 11.1 总分计算建议

```text
overall_score =
plot_progress * 0.16
+ conflict_strength * 0.12
+ character_depth * 0.12
+ emotional_curve * 0.08
+ suspense * 0.12
+ pacing * 0.10
+ scene_vividness * 0.06
+ dialogue_quality * 0.08
+ style_consistency * 0.08
+ chapter_hook * 0.05
+ payoff_quality * 0.02
+ readability * 0.01
```

说明：

```text
悬疑/剧情类小说中 plot_progress、conflict、character、suspense 权重较高。
```

后续可以按题材配置权重。

---

### 11.2 等级

```text
A+：9.0–10
A：8.5–8.9
B+：8.0–8.4
B：7.0–7.9
C：6.0–6.9
D：5.0–5.9
F：0–4.9
```

---

## 12. rewrite_recommended 判断

V5.1 不修稿，但要判断是否建议修稿。

推荐规则：

```text
overall_score < overall_min
或任一关键维度低于阈值：
- plot_progress
- conflict_strength
- pacing
- style_consistency
- chapter_hook
或存在 severity = high 的 problem
```

示例：

```json
{
  "rewrite_recommended": true,
  "rewrite_priority": "medium",
  "rewrite_reasons": [
    "overall_score 6.8 低于阈值 7.0",
    "conflict_strength 5 低于阈值 6",
    "存在 weak_hook 问题"
  ]
}
```

---

## 13. 配置项

### 13.1 quality_policy.json

```json
{
  "quality": {
    "enabled": true,
    "auto_evaluate_after_chapter_generation": true,
    "evaluate_after_consistency_check": true,
    "fail_open": true,
    "overall_score_min": 7.0,
    "dimension_thresholds": {
      "plot_progress": 6,
      "conflict_strength": 6,
      "pacing": 6,
      "style_consistency": 7,
      "chapter_hook": 6
    },
    "max_llm_retry": 1,
    "store_llm_trace": true,
    "rewrite_recommendation_enabled": true
  }
}
```

---

### 13.2 quality_weight_policy.json

```json
{
  "weights": {
    "plot_progress": 0.16,
    "conflict_strength": 0.12,
    "character_depth": 0.12,
    "emotional_curve": 0.08,
    "suspense": 0.12,
    "pacing": 0.10,
    "scene_vividness": 0.06,
    "dialogue_quality": 0.08,
    "style_consistency": 0.08,
    "chapter_hook": 0.05,
    "payoff_quality": 0.02,
    "readability": 0.01
  }
}
```

---

## 14. 文件输出

### 14.1 输出目录

```text
outputs/sim_xxx/
  quality_reports/
    ch_001_quality.json
    ch_002_quality.json
    ch_003_quality.json

  quality_traces/
    ch_001_quality_llm_trace.json
    ch_002_quality_llm_trace.json

  metrics.json
```

---

### 14.2 run_index.json 增强

```json
{
  "chapters": [
    {
      "chapter_id": "ch_003",
      "draft_file": "chapters/ch_003_draft.md",
      "quality_report_file": "quality_reports/ch_003_quality.json",
      "quality_score": 7.4,
      "rewrite_recommended": true
    }
  ]
}
```

---

## 15. API 设计

### 15.1 手动触发评估

```text
POST /simulations/{simulationId}/chapters/{chapterId}/quality/evaluate
```

请求：

```json
{
  "target": "final_draft",
  "force": false,
  "include_llm_trace": true
}
```

响应：

```json
{
  "success": true,
  "quality_report": {}
}
```

---

### 15.2 获取单章质量报告

```text
GET /simulations/{simulationId}/chapters/{chapterId}/quality-report
```

响应：

```json
{
  "quality_report": {}
}
```

---

### 15.3 获取全部质量报告

```text
GET /simulations/{simulationId}/quality-reports
```

响应：

```json
{
  "simulation_id": "sim_001",
  "reports": [
    {
      "chapter_id": "ch_001",
      "overall_score": 7.8,
      "grade": "B",
      "rewrite_recommended": false
    },
    {
      "chapter_id": "ch_002",
      "overall_score": 6.6,
      "grade": "C",
      "rewrite_recommended": true
    }
  ]
}
```

---

### 15.4 获取质量趋势

```text
GET /simulations/{simulationId}/quality-trend
```

V5.1 简版响应：

```json
{
  "simulation_id": "sim_001",
  "trend": [
    {
      "chapter_id": "ch_001",
      "chapter_no": 1,
      "overall_score": 7.8,
      "plot_progress": 7,
      "conflict_strength": 6,
      "pacing": 8
    },
    {
      "chapter_id": "ch_002",
      "chapter_no": 2,
      "overall_score": 6.6,
      "plot_progress": 6,
      "conflict_strength": 4,
      "pacing": 6
    }
  ]
}
```

---

## 16. 前端页面：Quality Report Panel

V5.1 前端只做最小展示版。

### 16.1 页面入口

建议放在：

```text
/projects/{projectId}/chapters/{chapterId}/quality
```

或章节详情页右侧 Tab：

```text
Chapter Detail
├── Draft
├── Plan
├── Consistency
├── Quality
└── Events
```

---

### 16.2 页面内容

展示：

```text
overall_score
grade
rewrite_recommended
scores 维度列表
problems
strengths
suggestions
评估状态
重新评估按钮
```

---

### 16.3 UI 结构

```text
Quality Summary Card
- Overall Score
- Grade
- Rewrite Recommended
- Status

Dimension Scores
- plot_progress
- conflict_strength
- character_depth
- emotional_curve
- suspense
- pacing
- scene_vividness
- dialogue_quality
- style_consistency
- chapter_hook
- payoff_quality
- readability

Problems List
- severity
- type
- message
- evidence
- related events

Suggestions List
- type
- message
- target sections
- constraints

Actions
- Re-evaluate
- Mark for Rewrite，预留，V5.2 实现
```

---

### 16.4 V5.1 不做的 UI

```text
修稿前后 Diff
自动修稿按钮
复杂雷达图
线程看板
长篇稳定性趋势
Style Bible 编辑器
```

---

## 17. Metrics 增强

metrics.json 增加：

```json
{
  "quality": {
    "evaluated_chapter_count": 3,
    "average_overall_score": 7.2,
    "chapters_below_threshold": 1,
    "rewrite_recommended_count": 1,
    "most_common_problem_types": [
      "weak_conflict",
      "slow_middle"
    ],
    "quality_eval_failed_count": 0,
    "average_quality_eval_latency_ms": 3200,
    "quality_eval_total_tokens": 15000,
    "quality_eval_estimated_cost": 0.12
  }
}
```

---

## 18. 测试计划

### 18.1 单元测试

#### test_quality_report_schema

验证：

```text
quality_report JSON Schema 合法
scores 维度齐全
分数范围 0–10
problem type 合法
suggestion type 合法
```

---

#### test_quality_pre_analyzer

用固定 EventLog 测试：

```text
能统计 plot_event_count
能统计 conflict_event_count
能识别 low_conflict
能识别 repetitive_search_events
能识别 weak_hook
```

---

#### test_score_normalizer

验证：

```text
overall_score 计算正确
权重生效
grade 映射正确
低于阈值时 rewrite_recommended = true
```

---

#### test_problem_classifier

验证：

```text
weak_conflict 分类正确
slow_middle 分类正确
weak_hook 分类正确
未知 problem type 被拒绝
```

---

### 18.2 集成测试

#### test_evaluate_chapter_success

输入：

```text
chapter_plan
chapter_draft
selected_events
consistency_report
```

预期：

```text
生成 success quality_report
写入 quality_reports/ch_xxx_quality.json
run_index 更新
```

---

#### test_quality_eval_failure_does_not_break_runner

模拟 LLM 返回非法 JSON。

预期：

```text
simulation_runner 不失败
生成 failed quality_report
章节正文仍保留
```

---

#### test_manual_api_evaluate

调用：

```text
POST /quality/evaluate
```

预期：

```text
返回 quality_report
落盘
```

---

#### test_get_quality_report

调用：

```text
GET /quality-report
```

预期：

```text
返回最新 quality_report
```

---

### 18.3 场景测试

#### 弱冲突章节

输入 fixture：

```text
weak_conflict_chapter.md
```

预期：

```text
problems 包含 weak_conflict
conflict_strength < 6
rewrite_recommended = true
```

---

#### 拖沓章节

输入 fixture：

```text
slow_middle_chapter.md
```

预期：

```text
problems 包含 slow_middle 或 scene_repetition
pacing < 6
```

---

#### 弱钩子章节

输入 fixture：

```text
weak_hook_chapter.md
```

预期：

```text
problems 包含 weak_hook
chapter_hook < 6
```

---

### 18.4 前端测试

验证：

```text
Quality Report Panel 能展示 overall_score
能展示 scores
能展示 problems
能展示 suggestions
点击 Re-evaluate 会调用 API
评估失败时展示 error 状态
```

---

## 19. 日志与 Trace

### 19.1 quality_llm_trace

```json
{
  "trace_id": "trace_quality_ch_003",
  "simulation_id": "sim_001",
  "chapter_id": "ch_003",
  "purpose": "story_quality_evaluation",
  "model": "xxx",
  "input_hash": "abc",
  "output_hash": "def",
  "prompt_tokens": 4200,
  "completion_tokens": 1300,
  "success": true,
  "retry_count": 0,
  "latency_ms": 3200
}
```

---

### 19.2 errors.jsonl

如果失败：

```json
{
  "time": "2026-05-16T00:00:00+08:00",
  "type": "QUALITY_EVAL_FAILED",
  "simulation_id": "sim_001",
  "chapter_id": "ch_003",
  "message": "LLM output JSON parse failed",
  "recoverable": true
}
```

---

## 20. 文档更新

新增文档：

```text
docs/v5_1_story_quality_evaluator.md
```

内容包括：

```text
1. V5.1 是什么
2. 与 ConsistencyCheck 的区别
3. 什么时候自动触发
4. 如何手动触发 API
5. quality_report 字段说明
6. 评分维度说明
7. rewrite_recommended 含义
8. 常见问题类型说明
9. 前端如何查看
10. 失败降级说明
```

---

## 21. 开发步骤建议

### Step 1：定义 Schema

```text
quality_report_schema.json
quality_evaluation_request_schema.json
problem_type enum
suggestion_type enum
score dimension enum
```

---

### Step 2：实现 QualityPreAnalyzer

```text
读取 EventLog
统计事件类型
统计 conflict / discovery / dialogue
识别 low_conflict / repetitive_search / weak_hook 等基础 flag
```

---

### Step 3：实现 QualityLLMEvaluator

```text
构建压缩上下文
调用 LLM
解析 JSON
retry 1 次
失败返回 recoverable error
```

---

### Step 4：实现 ScoreNormalizer

```text
归一化 scores
计算 overall_score
生成 grade
判断 rewrite_recommended
```

---

### Step 5：实现 QualityReportWriter

```text
写入 quality_reports/ch_xxx_quality.json
更新 run_index
更新 metrics
```

---

### Step 6：集成 simulation_runner

```text
在 ConsistencyCheck 后触发 evaluate
保证 fail_open
保证不影响章节生成
```

---

### Step 7：实现 API

```text
POST evaluate
GET quality-report
GET quality-reports
GET quality-trend
```

---

### Step 8：实现前端最小面板

```text
Quality Summary
Dimension Scores
Problems
Suggestions
Re-evaluate
```

---

### Step 9：补测试

```text
schema tests
pre analyzer tests
service tests
API tests
runner integration tests
frontend tests
```

---

### Step 10：更新文档

```text
docs/v5_1_story_quality_evaluator.md
README 更新版本说明
```

---

## 22. V5.1 DoD

```text
1. 定义并校验 quality_report_schema
2. 章节生成后自动触发 StoryQualityEvaluator
3. 质量评估失败不会中断 simulation_runner
4. 每章生成 quality_reports/ch_xxx_quality.json
5. QualityReport 包含 overall_score、grade、scores、problems、strengths、suggestions
6. scores 至少包含 12 个维度
7. 能识别 weak_conflict、slow_middle、weak_hook 三类典型问题
8. 能输出 rewrite_recommended 和 rewrite_priority
9. API 支持手动触发评估
10. API 支持获取单章 quality_report
11. 前端 Quality Report Panel 能展示质量报告
12. MetricsCollector 记录质量评估次数、失败次数、平均分和成本
13. 测试覆盖 Schema、PreAnalyzer、Service、API、Runner 集成
14. 文档说明 V5.1 使用方式
```

---

## 23. 验收用例清单

```text
Case 1：正常章节生成质量报告
Case 2：低冲突章节识别 weak_conflict
Case 3：拖沓章节识别 slow_middle
Case 4：弱结尾章节识别 weak_hook
Case 5：质量低于阈值时 rewrite_recommended = true
Case 6：LLM 返回非法 JSON 时不影响 simulation_runner
Case 7：手动调用 API 重新评估
Case 8：前端展示 quality_report
Case 9：metrics 正确累计
Case 10：run_index 正确记录 quality_report_file
```

---

## 24. V5.1 一句话总结

V5.1 的核心不是让系统自动改小说，而是：

> 让系统知道一章小说“好不好、哪里不好、为什么不好、应该往哪个方向改”。

它为 V5.2 RewriteOptimizer 提供基础输入。

最终闭环：

```text
生成章节
↓
一致性检查
↓
质量评估
↓
输出 quality_report
↓
标记是否建议修稿
```
