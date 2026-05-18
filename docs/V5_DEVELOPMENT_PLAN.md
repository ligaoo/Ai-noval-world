# 小说沙盘引擎 V5 开发计划

> V5 主题：质量闭环、自动修稿、长篇稳定与项目模板化  
> V5 目标：在 V4 已具备创作工作台、多 Agent、NPC 分层、人工干预、动态 NPC 引入、页面生成随机角色/线索等能力后，进一步解决“生成结果质量是否稳定”“长篇是否会散”“用户能否低成本开新项目”的问题。

---

## 0. V5 定位

前置版本能力假设：

```text
V1：最小闭环
- 世界配置
- Agent 动作
- 环境判定
- EventLog
- 单章生成
- 一致性检查

V2：LLM + 多地点 + 轻量记忆
- LLM Agent
- 多地点 move
- memories.jsonl
- LLM Narrative Writer
- 自动修订一次

V3：故事控制
- ProgressMonitor / Director
- PlotArc 阶段锁
- ChapterContinuity
- CharacterArcLite
- Foreshadowing

V3.5：调试稳定化
- Debug Console
- State Snapshot
- Event Replay
- Agent Trace
- ConfigValidator
- Rerun / Diff
- Metrics / Tuning Report

V4：创作平台雏形
- World Studio
- Multi-Agent Scheduler
- NPC Layer
- Human-in-the-loop
- 多 POV / 物品系统规划

V4.1：动态 NPC 引入
- NeedDetector
- RoleSpec
- Candidate NPC
- CharacterValidator
- IntroductionPlanner
- CharacterRegistry

V4.2：World Studio 生成增强
- 页面随机角色生成
- NPC 生成
- 地点生成
- 线索生成
- 关系生成
- 候选审核与入库
```

V5 不建议继续优先扩展“更多世界机制”，而应集中解决：

```text
1. 章节能生成，但质量不稳定
2. 一致性没问题，但故事可能不好看
3. 连续生成长篇时主线会变散
4. open_threads 越开越多，悬念债务失控
5. 动态 NPC 可能增长过快
6. 文风和角色声音会漂移
7. 用户创建新项目仍然有门槛
8. 系统缺少自动评估、自动修稿、自动调优闭环
```

V5 一句话定位：

> 让小说沙盘引擎从“能持续运行”升级为“能稳定产出质量可控的长篇内容”。

---

## 1. V5 总目标

V5 完成后，系统应具备：

```text
1. 每章生成后自动输出故事质量评分
2. 能识别弱冲突、节奏拖沓、人物浅、悬念弱、钩子弱、文风漂移等问题
3. 能根据质量报告自动生成 RewritePlan
4. 能在不新增事实、不改变剧情的前提下自动修稿
5. 能连续运行 10 章、20 章的长篇稳定性测试
6. 能管理所有 open_threads，防止悬念债务失控
7. 能限制动态 NPC 增长，防止角色爆炸
8. 能维持 Style Bible 和 Character Voice Profile
9. 能检测文风漂移和角色声音漂移
10. 用户输入简单项目想法后，能生成完整项目模板
11. 质量报告、修稿报告、长篇测试报告都能在页面查看
12. 系统能够基于质量与稳定性指标给出调优建议
```

---

## 2. V5 核心原则

### 2.1 质量评估不等于一致性检查

已有 ConsistencyCheck 负责：

```text
有没有新增事实
有没有泄露 POV
有没有违反世界规则
有没有改变事件结果
有没有使用不存在的地点、物品、角色
```

V5 的 StoryQualityEvaluator 负责：

```text
好不好看
节奏是否合适
冲突是否足够
人物是否有深度
悬念是否有效
钩子是否吸引人
文风是否稳定
```

二者不能混淆。

---

### 2.2 修稿只能优化表达，不能改事实

RewriteOptimizer 可以改：

```text
节奏
段落顺序
对白力度
场景描写
心理描写
悬念强调
章节结尾
文风统一
```

不能改：

```text
EventLog 结果
角色行动
线索发现状态
PlotArc 阶段
角色已知信息
世界事实
NPC 知识边界
```

---

### 2.3 长篇稳定性要量化

不能只靠主观感觉判断“长篇是否稳定”。

需要指标：

```text
主线连续度
人物状态一致性
open_threads 增长率
resolved_threads 复活率
NPC 增长率
文风漂移度
一致性通过率
平均质量分
用户干预依赖度
```

---

### 2.4 悬念是债务，需要管理

每新增一个 open_thread，系统都要知道：

```text
为什么开这个坑
优先级多少
绑定哪个 PlotArc
预计几章内推进或回收
是否已经拖太久
是否需要 Director / NPC / clue 介入
```

---

### 2.5 模板生成的是配置，不是正文

Project Template Generator 生成结构化项目文件，不直接生成完整小说：

```text
world_bible.json
characters.json
npcs.json
map.json
clues.json
plot_arcs.json
character_arcs.json
style_bible.json
chapter_seed_plan.json
```

---

## 3. V5 版本拆分

```text
V5.1：Story Quality Evaluator 故事质量评估器
V5.2：Rewrite Optimizer 自动修稿优化器
V5.3：Long-Run Stability Test 长篇稳定性测试
V5.4：OpenThreadManager 叙事债务 / 悬念管理器
V5.5：Style & Voice Consistency 文风与角色声音稳定
V5.6：Project Template Generator 项目模板生成器
```

推荐优先级：

```text
P0：
- V5.1 Story Quality Evaluator
- V5.2 Rewrite Optimizer
- V5.4 OpenThreadManager
- V5.3 Long-Run Stability Test

P1：
- V5.5 Style & Voice Consistency
- V5.6 Project Template Generator
```

推荐开发顺序：

```text
1. V5.1 Story Quality Evaluator
2. V5.2 Rewrite Optimizer
3. V5.4 OpenThreadManager
4. V5.3 Long-Run Stability Test
5. V5.5 Style & Voice Consistency
6. V5.6 Project Template Generator
```

---

# V5.1 Story Quality Evaluator 故事质量评估器

## 1. 目标

建立一套章节级、段落级、计划级的故事质量评估体系。

V5.1 要回答：

```text
这一章好不好？
哪里不好？
为什么不好？
应该怎么改？
是否值得自动修稿？
质量是否比上一章下降？
```

---

## 2. 输入对象

StoryQualityEvaluator 不只评估最终正文，也评估中间结构。

输入：

```text
chapter_plan.json
chapter_draft.md
final_chapter.md
events.jsonl 中本章 selected_events
chapter_summary.json
open_threads
plot_arc_state
character_arc_state
style_bible
character_voice_profiles
consistency_report
```

---

## 3. 评估维度

### 3.1 plot_progress：剧情推进

判断：

```text
本章是否推进主线？
是否发现新线索？
是否解决或推进 open_thread？
是否只是原地打转？
是否有明确章节功能？
```

评分参考：

```text
0–3：几乎无推进
4–6：有轻微推进，但主要是铺垫
7–8：推进明确
9–10：强推进，并带来新问题或转折
```

### 3.2 conflict_strength：冲突强度

判断：

```text
是否有角色目标冲突？
是否有外部阻碍？
是否有内心冲突？
是否有信息差造成张力？
```

冲突类型：

```text
character_vs_character
character_vs_environment
character_vs_self
character_vs_truth
character_vs_time
```

### 3.3 character_depth：人物深度

判断：

```text
角色是否有动机？
行为是否体现性格？
人物是否有信念变化？
是否有非工具人表现？
心理描写是否贴合经历？
```

### 3.4 emotional_curve：情绪曲线

判断：

```text
本章情绪是否有变化？
是否从平静到紧张？
是否从怀疑到确认？
是否有情绪高点和回落？
是否全章情绪平直？
```

### 3.5 suspense：悬念强度

判断：

```text
是否提出有效问题？
是否推进旧问题？
是否制造合理不确定性？
是否过早解释？
是否故弄玄虚但无实质信息？
```

### 3.6 pacing：节奏

判断：

```text
是否拖沓？
是否连续重复同类动作？
是否信息密度过低？
是否转折过快？
是否情绪和行动节奏协调？
```

### 3.7 scene_vividness：场景画面感

判断：

```text
地点是否有具体感？
感官描写是否有效？
是否过度堆砌形容词？
场景是否服务剧情？
```

### 3.8 dialogue_quality：对白质量

判断：

```text
对白是否符合角色声音？
是否推动剧情？
是否有潜台词？
是否过度解释？
是否每个人说话都像同一个人？
```

### 3.9 style_consistency：文风一致性

判断：

```text
是否符合 Style Bible？
是否和前几章风格一致？
是否突然变得网文化、爽文化、过度抒情？
```

### 3.10 chapter_hook：章节钩子

判断：

```text
结尾是否有继续阅读欲望？
是否来自 EventLog 或合法线索？
是否只是虚假悬念？
是否过度剧透？
```

### 3.11 payoff_quality：伏笔回收质量

判断：

```text
是否回收了前文伏笔？
回收是否自然？
是否有铺垫不足的硬转折？
是否有埋了不回的伏笔？
```

### 3.12 readability：可读性

判断：

```text
语言是否流畅？
段落是否清晰？
信息是否容易理解？
是否有重复表达？
是否有过长句子或过度解释？
```

---

## 4. QualityReport 数据结构

```json
{
  "report_id": "qr_ch_003_001",
  "simulation_id": "sim_001",
  "chapter_id": "ch_003",
  "chapter_no": 3,
  "evaluated_target": "chapter_draft",
  "overall_score": 7.4,
  "grade": "B",
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
  },
  "thresholds": {
    "overall_min": 7,
    "conflict_strength_min": 6,
    "pacing_min": 6,
    "style_consistency_min": 7
  },
  "problems": [
    {
      "problem_id": "prob_001",
      "type": "weak_conflict",
      "severity": "medium",
      "location": {
        "section_id": "sec_003",
        "paragraph_range": [12, 18]
      },
      "message": "本章主要是调查和发现，人物之间的正面冲突偏弱。",
      "evidence": [
        "连续三个 beat 都是搜索/观察，没有角色阻碍或目标冲突。"
      ]
    }
  ],
  "strengths": [
    {
      "type": "effective_suspense",
      "message": "白色面包车线索推进了旧医院近期出入的问题。"
    }
  ],
  "suggestions": [
    {
      "suggestion_id": "sug_001",
      "type": "increase_conflict",
      "message": "可以让看门人在主角接近档案室时主动阻拦。",
      "rewrite_task": "increase_conflict",
      "target_sections": ["sec_004"]
    }
  ],
  "rewrite_recommended": true
}
```

---

## 5. 问题类型枚举

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
```

---

## 6. 模块设计

```text
StoryQualityEvaluator
├── PlanQualityEvaluator
├── ChapterDraftEvaluator
├── EventQualityAnalyzer
├── CharacterDepthAnalyzer
├── PacingAnalyzer
├── ConflictAnalyzer
├── SuspenseAnalyzer
├── HookAnalyzer
├── StyleQualityAnalyzer
├── QualityReportWriter
└── RewriteSuggestionGenerator
```

---

## 7. 评估流程

```text
Load chapter_plan
Load chapter_draft
Load selected plot events
Load open_threads
Load plot_arc_state
Load character_state
Load style_bible
↓
Rule-based pre-analysis
↓
LLM quality evaluation
↓
Score normalization
↓
Problem classification
↓
Rewrite suggestion generation
↓
Write quality_report.json
```

---

## 8. Rule-based 预分析

尽量先用规则做便宜判断：

```text
本章 plot_event 数量
discovery event 数量
conflict event 数量
dialogue event 数量
open_thread 推进数量
新增 open_thread 数量
resolved_thread 数量
selected_events 是否过于同质
ending_hook 是否存在 source_event_id
```

示例指标：

```json
{
  "event_analysis": {
    "plot_event_count": 12,
    "discovery_event_count": 5,
    "conflict_event_count": 1,
    "dialogue_event_count": 2,
    "new_open_threads": 3,
    "resolved_threads": 0,
    "thread_progress_count": 1
  }
}
```

---

## 9. LLM 评估 Prompt 要点

```text
你是小说质量评估器，不是小说作者。
你不能改写正文。
你必须根据 chapter_plan、chapter_draft、事件日志和风格约束进行评分。
请输出严格 JSON。
评分要具体，不要泛泛而谈。
必须指出可执行的改进建议。
不能建议新增未发生事件。
```

---

## 10. API 设计

```text
POST /simulations/{simulationId}/chapters/{chapterId}/quality/evaluate
GET  /simulations/{simulationId}/chapters/{chapterId}/quality-report
GET  /simulations/{simulationId}/quality-reports
GET  /simulations/{simulationId}/quality-trend
```

---

## 11. 页面设计

### 11.1 Chapter Quality Panel

显示：

```text
总体评分
各维度雷达图
问题列表
优点列表
修稿建议
是否建议自动修稿
与上一章质量对比
```

### 11.2 Quality Trend

显示：

```text
每章 overall_score
pacing 走势
conflict_strength 走势
style_consistency 走势
chapter_hook 走势
```

---

## 12. DoD

```text
1. 每章生成后能输出 quality_report.json
2. quality_report 包含 overall_score 和至少 10 个维度评分
3. 能识别弱冲突、节奏拖沓、钩子弱、人物浅、文风漂移
4. 能给出可执行 rewrite suggestions
5. 能在页面展示质量评分
6. 能对比章节质量趋势
7. 能把 suggestions 转换为 RewriteOptimizer 输入
8. LLM 输出必须通过 JSON Schema 校验
9. 评估不能建议新增未发生的核心事实
10. 评估耗时和 token 成本进入 MetricsCollector
```

---

# V5.2 Rewrite Optimizer 自动修稿优化器

## 1. 目标

根据 StoryQualityEvaluator 的质量报告，对章节进行自动修稿。

目标不是重新编剧情，而是：

```text
在不改变 EventLog 事实的前提下，提高章节可读性、节奏、冲突表现、人物深度和文风一致性。
```

---

## 2. 修稿前后流程

```text
chapter_draft.md
↓
ConsistencyCheck
↓
QualityEvaluator
↓
RewritePlanGenerator
↓
RewriteOptimizer
↓
rewritten_draft.md
↓
ConsistencyCheck again
↓
QualityEvaluator again
↓
Accept / Reject / Manual Review
```

---

## 3. RewriteTask 类型

```text
tighten_pacing：压缩拖沓
increase_conflict：增强冲突表现
deepen_character：增强人物心理
improve_hook：强化结尾钩子
polish_style：文风润色
reduce_exposition：减少解释
improve_dialogue：优化对白
enhance_suspense：增强悬念
improve_scene_transition：改善场景衔接
strengthen_payoff：强化伏笔回收
```

---

## 4. RewritePlan 数据结构

```json
{
  "rewrite_plan_id": "rp_ch_003_001",
  "chapter_id": "ch_003",
  "source_quality_report_id": "qr_ch_003_001",
  "rewrite_goals": [
    {
      "task_id": "task_001",
      "type": "tighten_pacing",
      "reason": "中段连续三场搜索事件节奏重复。",
      "target_sections": ["sec_002", "sec_003"],
      "priority": 8,
      "constraints": [
        "不能删除发现 hf_white_van 的事件",
        "不能改变主角发现线索的顺序"
      ]
    }
  ],
  "global_constraints": [
    "不能新增线索",
    "不能新增地点",
    "不能新增角色",
    "不能改变 EventLog 结果",
    "不能泄露 forbidden_revelations"
  ],
  "max_rewrite_passes": 1
}
```

---

## 5. RewriteDiff 数据结构

```json
{
  "rewrite_diff_id": "rd_ch_003_001",
  "chapter_id": "ch_003",
  "before_quality_score": 7.4,
  "after_quality_score": 8.1,
  "changed_sections": [
    {
      "section_id": "sec_002",
      "change_type": "tightened",
      "summary": "合并两个重复搜索段落，减少环境重复描写。"
    }
  ],
  "consistency_check": {
    "passed": true,
    "violations": []
  },
  "accepted": null
}
```

---

## 6. RewriteOptimizer 约束

必须传入：

```text
selected_events
allowed_entities
allowed_facts
forbidden_revelations
POV boundary
style_bible
character_voice_profiles
chapter_plan
quality_report
rewrite_plan
```

禁止模型自由发挥：

```text
不要补充新的“精彩剧情”
不要添加新角色突然出现
不要添加未发生的发现
不要提前解释真相
```

---

## 7. 修稿 Prompt 要点

```text
你是小说修稿器，不是剧情创造者。

你只能优化表达、节奏、段落结构、对白和心理描写。
你不能新增事实。
你不能新增 EventLog 中没有的动作。
你不能改变角色已知信息。
你不能泄露 forbidden_revelations。
你必须遵守 RewritePlan。
输出修订后的章节正文。
```

---

## 8. 修稿模式

### 8.1 full_chapter_rewrite

整章重写。

适合：

```text
质量整体较低
结构问题严重
文风严重漂移
```

### 8.2 section_rewrite

只重写指定 section。

适合：

```text
局部拖沓
结尾钩子弱
某段对白不好
```

### 8.3 line_edit

轻量润色。

适合：

```text
语言流畅性
重复表达
语气调整
```

MVP 建议先做：

```text
section_rewrite
full_chapter_rewrite
```

---

## 9. 自动接受策略

```json
{
  "rewrite_acceptance_policy": {
    "auto_accept_if_consistency_passed": false,
    "auto_accept_if_score_improved_by": 0.5,
    "require_user_review": true,
    "max_rewrite_attempts": 1
  }
}
```

推荐：

```text
开发阶段：require_user_review = true
自动模式：score 提升且 consistency passed 才自动接受
```

---

## 10. API 设计

```text
POST /simulations/{simulationId}/chapters/{chapterId}/rewrite-plan
POST /simulations/{simulationId}/chapters/{chapterId}/rewrite
GET  /simulations/{simulationId}/chapters/{chapterId}/rewrite-diff
POST /simulations/{simulationId}/chapters/{chapterId}/rewrite/accept
POST /simulations/{simulationId}/chapters/{chapterId}/rewrite/reject
```

---

## 11. 页面设计

### 11.1 Rewrite Panel

显示：

```text
质量问题
修稿计划
修稿前正文
修稿后正文
差异对比
一致性检查结果
质量提升幅度
接受 / 拒绝 / 手动编辑
```

---

## 12. DoD

```text
1. 能根据 quality_report 生成 rewrite_plan
2. 至少支持 section_rewrite 和 full_chapter_rewrite
3. 修稿后重新执行 ConsistencyCheck
4. 修稿后重新执行 QualityEvaluator
5. 修稿不能新增事实、地点、角色、线索
6. 能输出 rewrite_diff.json
7. 页面能查看 before / after 对比
8. 用户可以接受或拒绝修稿
9. MetricsCollector 记录修稿次数、成功率、质量提升
10. 修稿失败时能保留原稿
```

---

# V5.3 Long-Run Stability Test 长篇稳定性测试

## 1. 目标

建立自动化长篇稳定性测试框架，验证系统能否连续生成多章而不崩。

需要回答：

```text
连续 10 章后主线还在吗？
人物状态是否重置？
open_threads 是否失控？
NPC 是否越来越多？
文风是否漂移？
一致性检查是否仍稳定？
质量是否下降？
```

---

## 2. 测试类型

```text
single_seed_10ch：单 seed 连续 10 章
multi_seed_10ch：多个 seed 各跑 10 章
single_seed_20ch：单 seed 连续 20 章
template_batch_test：多个项目模板批量测试
dynamic_npc_stress_test：动态 NPC 压力测试
open_thread_stress_test：悬念债务压力测试
style_drift_test：文风漂移测试
```

---

## 3. LongRunTestConfig

```json
{
  "test_id": "longrun_dark_city_10ch_seed123",
  "world_id": "dark_city_001",
  "seed": 123,
  "chapter_limit": 10,
  "tick_limit_per_chapter": 50,
  "enabled_checks": [
    "main_arc_continuity",
    "character_state_consistency",
    "open_thread_growth",
    "npc_growth",
    "world_state_conflict",
    "style_drift",
    "quality_trend",
    "consistency_pass_rate"
  ],
  "thresholds": {
    "average_quality_score_min": 7.0,
    "consistency_pass_rate_min": 0.95,
    "npc_growth_max_per_chapter": 1.2,
    "open_thread_max": 10,
    "style_drift_max": 0.25,
    "resolved_thread_reopened_max": 1
  }
}
```

---

## 4. LongRunReport

```json
{
  "test_id": "longrun_dark_city_10ch_seed123",
  "world_id": "dark_city_001",
  "seed": 123,
  "chapters_generated": 10,
  "passed": false,
  "summary": {
    "average_quality_score": 7.2,
    "consistency_pass_rate": 0.96,
    "main_arc_continuity": 0.88,
    "character_state_consistency": 0.84,
    "style_drift_score": 0.22
  },
  "growth_metrics": {
    "npc_count_start": 5,
    "npc_count_end": 17,
    "npc_growth_rate_per_chapter": 1.2,
    "open_thread_count_start": 2,
    "open_thread_count_end": 11,
    "resolved_thread_reopened_count": 2
  },
  "issues": [
    {
      "type": "npc_growth_too_fast",
      "message": "10 章内新增 12 个 NPC，接近上限。",
      "severity": "medium"
    }
  ],
  "recommendations": [
    "提高 DynamicCharacterIntroductionService 的 reuse_existing 优先级。",
    "OpenThreadManager 应阻止 resolved thread 重新打开。",
    "限制每章新增 open_thread 数量。"
  ]
}
```

---

## 5. Stability 指标

### 5.1 main_arc_continuity

衡量主线是否持续推进。

```text
每章是否有主线相关 event
PlotArc 是否正常推进
是否偏离当前 arc
```

### 5.2 character_state_consistency

衡量人物状态是否连贯。

```text
beliefs 是否丢失
relationships 是否重置
current_intention 是否与前章矛盾
```

### 5.3 open_thread_growth

衡量悬念债务。

```text
新增 open_thread 数量
resolved 数量
stale 数量
expired 数量
```

### 5.4 npc_growth_rate

衡量动态 NPC 是否失控。

```text
每章新增 NPC 数
复用率
major_npc 数量
无后续作用 NPC 数量
```

### 5.5 style_drift_score

衡量文风偏移。

```text
与 Style Bible 的偏差
与前 3 章平均风格的偏差
角色声音漂移
```

---

## 6. 测试 Runner 流程

```text
Load test config
↓
Create simulation run
↓
For chapter in 1..N:
    Run simulation until chapter end
    Generate chapter
    ConsistencyCheck
    QualityEvaluator
    OpenThreadManager update
    StyleCheck
    Collect metrics
↓
Aggregate metrics
↓
Generate long_run_report
↓
Generate tuning suggestions
```

---

## 7. API 设计

```text
POST /projects/{projectId}/long-run-tests
GET  /projects/{projectId}/long-run-tests
GET  /long-run-tests/{testId}
GET  /long-run-tests/{testId}/report
POST /long-run-tests/{testId}/rerun
```

---

## 8. 页面设计

### 8.1 Long Run Dashboard

显示：

```text
测试状态
章节进度
平均质量分
一致性通过率
NPC 增长趋势
open_threads 趋势
文风漂移趋势
失败原因
调优建议
```

---

## 9. DoD

```text
1. 支持一键运行 10 章稳定性测试
2. 支持多 seed 测试
3. 输出 long_run_report.json
4. 能统计 NPC 增长率
5. 能统计 open_threads 增长与回收情况
6. 能检测人物状态重置
7. 能检测文风漂移
8. 能统计质量趋势
9. 能输出稳定性建议
10. 页面能展示 LongRunReport
```

---

# V5.4 OpenThreadManager 叙事债务 / 悬念管理器

## 1. 目标

统一管理所有 open_threads，避免故事越写越散。

OpenThreadManager 要解决：

```text
开坑太多
坑不回收
高优先级悬念长期不推进
已解决悬念被重复提出
支线淹没主线
动态 NPC 为低价值 thread 不断生成
```

---

## 2. Thread 数据结构

```json
{
  "thread_id": "thread_white_van",
  "question": "白色面包车是谁的？",
  "opened_at_chapter": 2,
  "opened_at_event": "evt_0081",
  "priority": 8,
  "arc_id": "arc_hospital_truth",
  "status": "open",
  "expected_payoff_chapter_range": [4, 6],
  "related_clues": ["hf_white_van"],
  "related_characters": ["npc_store_owner_001"],
  "related_locations": ["old_street_shop", "old_hospital_gate"],
  "staleness": 2,
  "last_progress_chapter": 3,
  "recommended_action": "introduce_partial_clue"
}
```

---

## 3. Thread 状态

```text
open：已开启，未推进
active：当前章节正在推进
in_progress：近期有推进，但未解决
blocked：暂时无法推进
payoff_ready：可以回收
resolved：已解决
abandoned：有意放弃
expired：过期，已失去叙事价值
```

---

## 4. Thread 操作

```text
create_thread
update_thread_progress
mark_thread_active
mark_thread_blocked
mark_thread_payoff_ready
resolve_thread
abandon_thread
expire_thread
reopen_thread，需要强校验
```

---

## 5. NarrativeDebtReport

```json
{
  "simulation_id": "sim_001",
  "chapter_id": "ch_006",
  "open_thread_count": 9,
  "active_thread_count": 2,
  "stale_thread_count": 3,
  "high_priority_stale_threads": [
    {
      "thread_id": "thread_white_van",
      "staleness": 3,
      "priority": 8,
      "recommended_action": "payoff_or_progress"
    }
  ],
  "resolved_thread_reopened": [],
  "debt_level": "high",
  "warnings": [
    "高优先级悬念超过 3 章未推进。",
    "本章新增 4 个 open_threads，超过建议值。"
  ],
  "recommendations": [
    {
      "type": "prioritize_thread",
      "thread_id": "thread_white_van",
      "message": "下一章应推进白色面包车线索。"
    }
  ]
}
```

---

## 6. 与 Director 的关系

Director 不应该只看 progress_score，还应看 thread debt。

Director 输入增加：

```json
{
  "narrative_debt": {
    "debt_level": "high",
    "high_priority_stale_threads": ["thread_white_van"],
    "recommended_thread_to_progress": "thread_white_van"
  }
}
```

Director 介入优先级：

```text
高优先级 stale thread
当前 PlotArc required thread
payoff_ready thread
blocked but important thread
```

---

## 7. 与 DynamicCharacterIntroductionService 的关系

如果某个 thread stale 且缺少推进角色，可以触发动态 NPC 需求。

```json
{
  "need_type": "stale_thread_requires_character",
  "thread_id": "thread_white_van",
  "suggested_narrative_function": "witness"
}
```

---

## 8. 与 ChapterPlanner 的关系

ChapterPlanner 生成章节计划时必须：

```text
至少推进一个 high priority open_thread
不能新增过多 open_threads
不能把 resolved_thread 重新当主悬念
优先回收 payoff_ready thread
```

---

## 9. 配置项

```json
{
  "open_thread_manager": {
    "enabled": true,
    "max_open_threads": 10,
    "max_new_threads_per_chapter": 2,
    "stale_chapter_threshold": 2,
    "high_priority_threshold": 7,
    "prevent_resolved_thread_reopen": true,
    "require_reason_for_abandon": true
  }
}
```

---

## 10. API 设计

```text
GET  /simulations/{simulationId}/threads
GET  /simulations/{simulationId}/threads/{threadId}
POST /simulations/{simulationId}/threads/{threadId}/resolve
POST /simulations/{simulationId}/threads/{threadId}/abandon
GET  /simulations/{simulationId}/narrative-debt-report
```

---

## 11. 页面设计

### 11.1 Thread Board

分栏：

```text
Open
Active
Blocked
Payoff Ready
Resolved
Abandoned
```

每个 thread 显示：

```text
问题
优先级
所属 PlotArc
已拖章节数
相关线索
相关角色
推荐动作
```

---

## 12. DoD

```text
1. 所有 open_threads 进入统一管理
2. 每个 thread 有 priority / expected_payoff_range
3. 能识别 stale thread
4. 能输出 narrative_debt_report
5. Director 能优先推进高优先级 stale thread
6. DynamicNPCService 能基于 stale thread 生成 RoleSpec
7. ChapterPlanner 能限制每章新增 thread 数量
8. 已 resolved thread 不会重复作为主悬念
9. 页面可查看 Thread Board
10. LongRunTest 能统计 narrative debt 指标
```

---

# V5.5 Style & Voice Consistency 文风与角色声音稳定

## 1. 目标

解决长篇生成中的风格漂移和角色声音漂移。

常见问题：

```text
第一章克制压抑，第三章变成爽文
角色说话越来越像模型默认语气
所有角色对白趋同
恐怖氛围被过度解释破坏
人物心理描写越来越夸张
```

---

## 2. Style Bible

```json
{
  "style_id": "dark_city_style",
  "tone": "克制、压抑、现实中透出诡异",
  "sentence_style": "中短句为主，避免过度华丽",
  "description_level": "适度环境描写，避免堆砌形容词",
  "dialogue_style": "含蓄、留白、带潜台词",
  "pacing_style": "慢热，但每章必须有实质推进",
  "horror_style": "现实细节中透出异常，避免直接惊吓",
  "forbidden_styles": [
    "热血爽文",
    "过度解释",
    "网络段子化",
    "直接恐怖喊叫",
    "过度华丽辞藻"
  ],
  "preferred_devices": [
    "细节反常",
    "短暂停顿",
    "未说完的话",
    "旧物件带出的记忆"
  ],
  "reference_keywords": [
    "潮湿",
    "昏暗",
    "迟疑",
    "锈迹",
    "旧灯"
  ]
}
```

---

## 3. Character Voice Profile

```json
{
  "character_id": "char_linzho",
  "voice_profile": {
    "speech_style": "克制、短句、不轻易暴露情绪",
    "inner_monologue": "怀疑自己，但习惯压下恐惧",
    "vocabulary": ["确认", "不对", "可能", "等等"],
    "forbidden": [
      "突然热血宣言",
      "过度自我解释",
      "轻浮玩笑"
    ],
    "sample_lines": [
      "我只是想确认一件事。",
      "这把锁，不像是放了十年。"
    ]
  }
}
```

---

## 4. StyleCheckReport

```json
{
  "chapter_id": "ch_004",
  "style_consistency_score": 8.2,
  "voice_consistency": {
    "char_linzho": 8.5,
    "char_guard": 7.2
  },
  "violations": [
    {
      "type": "voice_drift",
      "character_id": "char_linzho",
      "message": "林舟在本章中出现明显热血宣言，与 voice_profile 不符。",
      "severity": "medium"
    },
    {
      "type": "over_explanation",
      "message": "本章多次直接解释恐怖来源，削弱了含蓄氛围。"
    }
  ],
  "suggestions": [
    "将直接解释改为环境细节暗示。",
    "缩短林舟对白，保留停顿和回避。"
  ]
}
```

---

## 5. Style Drift 检测

长篇中维护：

```text
最近 N 章风格摘要
当前章风格摘要
Style Bible 差异
角色对白差异
```

指标：

```json
{
  "style_drift": {
    "chapter_id": "ch_008",
    "drift_from_style_bible": 0.18,
    "drift_from_recent_average": 0.22,
    "high_risk": false
  }
}
```

---

## 6. 与 NarrativeWriter 的关系

NarrativeWriter 输入必须包含：

```text
style_bible
pov_character_voice_profile
major_speakers_voice_profiles
forbidden_styles
```

---

## 7. 与 RewriteOptimizer 的关系

RewriteOptimizer 可以执行：

```text
polish_style
restore_voice
reduce_exposition
adjust_dialogue
```

---

## 8. API 设计

```text
GET  /projects/{projectId}/style-bible
PUT  /projects/{projectId}/style-bible
GET  /projects/{projectId}/characters/{characterId}/voice-profile
PUT  /projects/{projectId}/characters/{characterId}/voice-profile
POST /simulations/{simulationId}/chapters/{chapterId}/style-check
GET  /simulations/{simulationId}/style-drift
```

---

## 9. 页面设计

### 9.1 Style Bible Editor

字段：

```text
tone
sentence_style
dialogue_style
description_level
forbidden_styles
sample_passages
```

### 9.2 Character Voice Editor

字段：

```text
speech_style
inner_monologue
vocabulary
forbidden
sample_lines
```

### 9.3 Style Report Panel

显示：

```text
style_consistency_score
voice_consistency
violations
suggestions
drift trend
```

---

## 10. DoD

```text
1. 支持 style_bible.json
2. 支持 character_voice_profiles.json
3. NarrativeWriter 使用 style_bible
4. RewriteOptimizer 能根据 style_bible 修稿
5. StyleCheck 输出 style_consistency_score
6. 能检测角色声音漂移
7. 长篇测试能统计 style_drift_score
8. 页面可编辑 Style Bible 和 Voice Profile
9. Style violation 可转化为 rewrite task
```

---

# V5.6 Project Template Generator 项目模板生成器

## 1. 目标

降低用户创建新项目的门槛。

用户只输入简单想法，系统生成完整结构化项目模板。

示例输入：

```text
题材：灵异悬疑
主题：记忆与愧疚
主角：失忆青年
核心地点：废弃医院
篇幅：10 章
文风：克制、压抑
```

系统输出：

```text
world_bible.json
characters.json
npcs.json
map.json
clues.json
plot_arcs.json
character_arcs.json
style_bible.json
character_voice_profiles.json
chapter_seed_plan.json
```

---

## 2. TemplateGenerationRequest

```json
{
  "genre": "灵异悬疑",
  "theme": "记忆与愧疚",
  "protagonist_seed": "失忆青年",
  "core_location": "废弃医院",
  "target_length": "10 chapters",
  "tone": "克制、压抑",
  "complexity": "medium",
  "preferred_elements": ["旧案", "梦境", "医院", "目击者"],
  "forbidden_elements": ["爽文复仇", "直接鬼怪大战"]
}
```

---

## 3. ProjectTemplate 输出结构

```json
{
  "template_id": "tpl_dark_hospital_001",
  "world_bible": {},
  "characters": [],
  "npcs": [],
  "map": {},
  "clues": [],
  "plot_arcs": [],
  "character_arcs": [],
  "style_bible": {},
  "character_voice_profiles": [],
  "chapter_seed_plan": [],
  "validation_report": {}
}
```

---

## 4. 生成阶段

```text
1. Concept Expansion：扩展用户想法
2. World Bible Generation：生成世界圣经
3. Core Character Generation：生成主角、反派、关键配角
4. Map Generation：生成初始地图
5. PlotArc Generation：生成主线阶段
6. Clue Graph Generation：生成线索网络
7. CharacterArc Generation：生成人物弧
8. Style Bible Generation：生成文风圣经
9. Chapter Seed Generation：生成章节种子
10. Validation & Repair：校验并修复配置
```

---

## 5. Chapter Seed Plan

```json
{
  "chapter_no": 1,
  "chapter_function": "建立旧医院异常与主角噩梦",
  "target_stage": "setup",
  "must_introduce": ["char_linzho", "old_hospital_gate"],
  "suggested_threads": [
    "旧医院是否真的废弃？",
    "主角为什么梦见医院？"
  ],
  "must_not_reveal": [
    "十年前事故真相",
    "反派真实身份"
  ]
}
```

---

## 6. Template Quality Check

生成后自动检查：

```text
地图是否可达
主线是否完整
线索是否有多路径
角色是否有冲突
章节种子是否覆盖完整 arc
是否存在过早剧透
是否有足够 NPC 入口
Style Bible 是否存在
```

---

## 7. API 设计

```text
POST /projects/templates/generate
GET  /projects/templates
GET  /projects/templates/{templateId}
POST /projects/templates/{templateId}/validate
POST /projects/templates/{templateId}/create-project
```

---

## 8. 页面设计

### 8.1 Template Wizard

步骤：

```text
选择题材
填写核心想法
选择篇幅
选择文风
选择复杂度
生成模板
预览模板
校验模板
创建项目
```

### 8.2 Template Preview

展示：

```text
世界概要
角色列表
地图节点
主线剧情弧
线索图
章节种子
风险提示
```

---

## 9. DoD

```text
1. 用户输入简短项目想法后能生成完整项目模板
2. 生成 world_bible / characters / map / clues / plot_arcs / style_bible
3. 生成的模板能通过 ConfigValidator
4. 每个关键线索至少有 3 条 discover_routes
5. PlotArc 至少包含 setup / investigation / confrontation / revelation
6. 角色至少包含主角、阻碍者、线索持有者
7. 生成后可在 World Studio 中继续编辑
8. 支持保存为模板库
9. 支持从模板一键创建项目
```

---

# V5 输出目录与文件结构

## 1. 输出目录

```text
outputs/sim_xxx/
  quality_reports/
    ch_001_quality.json
    ch_002_quality.json

  rewrite_reports/
    ch_001_rewrite_plan.json
    ch_001_rewrite_diff.json
    ch_001_rewritten_draft.md

  long_run_tests/
    longrun_10ch_seed123.json
    longrun_10ch_seed456.json

  narrative_debt_reports/
    ch_005_debt.json

  style_reports/
    ch_001_style.json
    ch_002_style.json

  metrics.json
  tuning_report.md
```

## 2. 项目配置新增

```text
worlds/dark_city_001/
  style_bible.json
  character_voice_profiles.json
  template_metadata.json
  thread_policy.json
  quality_policy.json
  rewrite_policy.json
```

---

# V5 配置项汇总

## 1. quality_policy.json

```json
{
  "quality": {
    "enabled": true,
    "overall_score_min": 7.0,
    "dimension_thresholds": {
      "plot_progress": 6,
      "conflict_strength": 6,
      "pacing": 6,
      "style_consistency": 7,
      "chapter_hook": 6
    },
    "auto_rewrite_if_below_threshold": true
  }
}
```

## 2. rewrite_policy.json

```json
{
  "rewrite": {
    "enabled": true,
    "max_rewrite_attempts": 1,
    "allowed_rewrite_modes": ["section_rewrite", "full_chapter_rewrite"],
    "require_consistency_check_after_rewrite": true,
    "require_user_review": true,
    "auto_accept_score_improvement_min": 0.5
  }
}
```

## 3. thread_policy.json

```json
{
  "open_thread_manager": {
    "enabled": true,
    "max_open_threads": 10,
    "max_new_threads_per_chapter": 2,
    "stale_chapter_threshold": 2,
    "high_priority_threshold": 7,
    "prevent_resolved_thread_reopen": true
  }
}
```

## 4. long_run_test_policy.json

```json
{
  "long_run_test": {
    "default_chapter_limit": 10,
    "multi_seed_count": 3,
    "average_quality_score_min": 7.0,
    "consistency_pass_rate_min": 0.95,
    "npc_growth_max_per_chapter": 1.2,
    "style_drift_max": 0.25
  }
}
```

---

# V5 Metrics 增强

```json
{
  "quality": {
    "average_overall_score": 7.4,
    "chapters_below_threshold": 2,
    "most_common_quality_issue": "weak_conflict"
  },
  "rewrite": {
    "rewrite_attempts": 4,
    "rewrite_accept_count": 3,
    "average_score_improvement": 0.6,
    "rewrite_consistency_fail_count": 1
  },
  "threads": {
    "open_thread_count": 8,
    "stale_thread_count": 2,
    "resolved_thread_count": 5,
    "resolved_thread_reopened_count": 0
  },
  "style": {
    "average_style_consistency": 8.1,
    "style_drift_score": 0.16,
    "voice_drift_violations": 1
  },
  "long_run": {
    "last_10ch_test_passed": true,
    "average_quality_score_10ch": 7.2,
    "consistency_pass_rate_10ch": 0.96
  }
}
```

---

# V5 页面建议

## 1. Quality Dashboard

```text
章节质量分
各维度评分
问题列表
修稿建议
质量趋势
```

## 2. Rewrite Panel

```text
修稿计划
修稿前后对比
一致性检查结果
质量提升幅度
接受 / 拒绝
```

## 3. Narrative Debt Board

```text
Open Threads
Stale Threads
Payoff Ready
Resolved
每个 thread 的优先级、拖延章节、推荐动作
```

## 4. Long Run Test Dashboard

```text
测试进度
质量趋势
一致性通过率
NPC 增长
open_threads 增长
文风漂移
失败原因
```

## 5. Style Bible Editor

```text
文风规则
禁用风格
角色声音
示例对白
风格检查报告
```

## 6. Template Wizard

```text
输入创意
选择题材
选择篇幅
生成项目模板
预览配置
创建项目
```

---

# V5 API 汇总

```text
# Quality
POST /simulations/{simulationId}/chapters/{chapterId}/quality/evaluate
GET  /simulations/{simulationId}/chapters/{chapterId}/quality-report
GET  /simulations/{simulationId}/quality-trend

# Rewrite
POST /simulations/{simulationId}/chapters/{chapterId}/rewrite-plan
POST /simulations/{simulationId}/chapters/{chapterId}/rewrite
GET  /simulations/{simulationId}/chapters/{chapterId}/rewrite-diff
POST /simulations/{simulationId}/chapters/{chapterId}/rewrite/accept
POST /simulations/{simulationId}/chapters/{chapterId}/rewrite/reject

# Long Run
POST /projects/{projectId}/long-run-tests
GET  /projects/{projectId}/long-run-tests
GET  /long-run-tests/{testId}/report

# Threads
GET  /simulations/{simulationId}/threads
GET  /simulations/{simulationId}/threads/{threadId}
POST /simulations/{simulationId}/threads/{threadId}/resolve
POST /simulations/{simulationId}/threads/{threadId}/abandon
GET  /simulations/{simulationId}/narrative-debt-report

# Style
GET  /projects/{projectId}/style-bible
PUT  /projects/{projectId}/style-bible
GET  /projects/{projectId}/characters/{characterId}/voice-profile
PUT  /projects/{projectId}/characters/{characterId}/voice-profile
POST /simulations/{simulationId}/chapters/{chapterId}/style-check

# Template
POST /projects/templates/generate
GET  /projects/templates
GET  /projects/templates/{templateId}
POST /projects/templates/{templateId}/validate
POST /projects/templates/{templateId}/create-project
```

---

# V5 总 DoD

```text
1. 每章生成后有 quality_report.json
2. quality_report 至少包含 10 个维度评分
3. 系统能识别弱冲突、节奏拖沓、钩子弱、人物浅、文风漂移
4. 系统能根据质量报告生成 rewrite_plan
5. RewriteOptimizer 能自动修稿并重新跑一致性检查
6. 修稿不能新增事实、地点、角色、线索
7. 页面能查看修稿前后对比
8. 支持连续 10 章稳定性测试
9. LongRunReport 能统计 NPC 增长、open_threads 增长、文风漂移
10. OpenThreadManager 能管理所有悬念债务
11. Director 能优先推进高优先级 stale thread
12. Style Bible 和 Character Voice Profile 能被 NarrativeWriter 使用
13. StyleCheck 能检测文风和角色声音漂移
14. 用户输入简单想法能生成项目模板
15. 模板能通过 ConfigValidator 并进入 World Studio 编辑
16. MetricsCollector 能记录质量、修稿、悬念债务、文风和长篇测试指标
```

---

# V5 不建议做的内容

V5 暂时不要做：

```text
1. 多用户协作
2. 公开发布平台
3. 商业支付系统
4. 移动端 App
5. 漫画 / 视频生成
6. 大型游戏战斗系统
7. 超大规模开放世界
8. 实时多人共同创作
```

V5 的重点是：

```text
质量闭环
自动修稿
长篇稳定
悬念债务管理
模板化创建
```

---

# V5 完成后的项目进度预估

V5 完成后，项目大概达到：

```text
核心引擎：90%
小说生成系统：85%
创作工具：75%–80%
可商用产品：70%
成熟平台：55%–60%
```

这时项目会从：

```text
可用的创作引擎
```

进入：

```text
可持续生产内容的创作系统
```

---

# V5 一句话总结

V5 的核心不是“让 AI 做更多”，而是：

> 让 AI 写得更稳定、更好、更长，而且能自我评估和自我修正。

V5 的最终闭环：

```text
生成章节
↓
一致性检查
↓
质量评估
↓
自动修稿
↓
长篇稳定监控
↓
叙事债务管理
↓
继续生成
```
