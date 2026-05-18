# V5.3–V5.7 开发计划：10 万字悬疑灵异长篇生产闭环

> 版本主题：从“章节级生成系统”升级为“全书级长篇生产系统”  
> 目标：让系统能够独自演练并完成一部约 10 万字的悬疑灵异故事。  
> 前置版本假设：V5.1 Story Quality Evaluator 已完成，V5.2 Genre Abstraction Layer + Horror Genre Pack 已完成。

---

## 0. 当前状态

当前系统已经具备：

```text
1. 通用故事核心引擎
2. 恐怖灵异 Genre Pack
3. 章节生成
4. 一致性检查
5. 章节质量评估
6. 恐怖氛围控制
7. 灵异规则管理
8. GenreContext 注入
9. HorrorQualityEvaluator
10. HorrorConsistencyChecker
```

但是要独自完成约 10 万字悬疑灵异长篇，还缺少：

```text
1. 自动修稿能力
2. 悬念债务管理
3. 全书蓝图规划
4. 全书级生产调度
5. 悬疑证据链管理
6. 终局收束检查
7. 10 万字长篇稳定性测试
8. 成稿导出
```

所以后续版本建议拆成：

```text
V5.3：RewriteOptimizer 自动修稿器
V5.4：OpenThreadManager 悬念债务管理器
V5.5：NovelBlueprint + NovelProductionOrchestrator 全书蓝图与生产调度
V5.6：Mystery Logic Module 悬疑逻辑增强
V5.7：100k LongRun Test + Final Closure + Manuscript Exporter
```

---

## 1. 总体目标

完成 V5.3–V5.7 后，系统应具备：

```text
1. 根据质量报告自动修稿
2. 质量低的章节能自动优化并重新评估
3. 所有悬念、线索、坑位进入统一管理
4. 能规划 10 万字 / 20–35 章的全书结构
5. 能自动调度章节生产直到达到目标字数
6. 能控制恐怖灵异氛围递进
7. 能管理悬疑证据链、误导线索和真相链
8. 能防止线索提前泄露或结局硬解释
9. 能运行 10 万字长篇稳定性测试
10. 能检查最终主线、伏笔、人物弧、悬念是否收束
11. 能导出完整 manuscript.md / manuscript.docx
```

---

## 2. 总体架构

```text
Novel Idea / Project Template
↓
NovelBlueprint
↓
NovelProductionOrchestrator
↓
For each chapter:
    ChapterFunctionResolver
    ChapterPlanner
    SimulationRunner
    NarrativeWriter
    ConsistencyCheck
    GenreConsistencyCheck
    StoryQualityEvaluator
    RewriteOptimizer
    StyleCheck
    OpenThreadManager.update
    MysteryLogicManager.update
    NovelProgressMonitor.update
↓
FinalClosureCheck
↓
FullNovelConsistencyCheck
↓
ManuscriptExporter
```

---

# V5.3 RewriteOptimizer 自动修稿器

## 1. 目标

V5.1 已经能评价章节质量，但不能自动改。  
V5.3 要实现自动修稿闭环。

核心流程：

```text
chapter_draft
↓
quality_report
↓
rewrite_plan
↓
rewritten_draft
↓
consistency_check
↓
quality_evaluate_again
↓
accept / reject
```

V5.3 的目标不是“重新编剧情”，而是在不改变事实的前提下提升章节表现力。

---

## 2. 解决的问题

```text
1. V5.1 只能指出问题，不能修复问题
2. 长篇中低质量章节需要人工干预，无法独立完成
3. 恐怖氛围不足时需要自动强化
4. 章节钩子弱时需要自动优化
5. 节奏拖沓时需要自动压缩
6. 对白解释太多时需要自动重写
```

---

## 3. RewriteOptimizer 不允许做什么

禁止：

```text
1. 新增 EventLog 中没有的事实
2. 新增未出现角色
3. 新增未配置地点
4. 新增未发现线索
5. 改变角色行动结果
6. 改变 PlotArc 当前阶段
7. 提前暴露 forbidden_revelations
8. 违反 GenreContext / HorrorRule
9. 改变已写入 WorldState 的状态
```

允许：

```text
1. 优化表达
2. 调整段落节奏
3. 合并重复描写
4. 强化已有冲突表现
5. 增强心理描写
6. 强化章节钩子
7. 改善对白
8. 增强恐怖氛围，但只能使用已允许的 horror devices
```

---

## 4. RewriteTask 类型

```text
tighten_pacing：压缩拖沓
increase_conflict：增强冲突表现
deepen_character：增强人物心理
improve_hook：强化章节钩子
polish_style：文风润色
reduce_exposition：减少解释
improve_dialogue：优化对白
enhance_suspense：增强悬念
enhance_horror_atmosphere：增强恐怖氛围
restore_genre_constraints：修复题材约束偏移
restore_character_voice：修复角色声音漂移
```

---

## 5. 数据结构

### 5.1 RewritePlan

```json
{
  "rewrite_plan_id": "rp_ch_006_001",
  "simulation_id": "sim_001",
  "chapter_id": "ch_006",
  "source_quality_report_id": "qr_ch_006_001",
  "rewrite_mode": "section_rewrite",
  "rewrite_goals": [
    {
      "task_id": "task_001",
      "type": "tighten_pacing",
      "priority": 8,
      "reason": "中段连续三场搜索事件节奏重复。",
      "target_sections": ["sec_002", "sec_003"],
      "constraints": [
        "不能删除 hf_white_van 被发现的事实",
        "不能改变搜索事件顺序"
      ]
    },
    {
      "task_id": "task_002",
      "type": "enhance_horror_atmosphere",
      "priority": 7,
      "reason": "horror_atmosphere 评分低于阈值。",
      "target_sections": ["sec_004"],
      "genre_constraints": [
        "当前 horror_stage = clear_threat",
        "允许使用 space_mismatch / recording_anomaly",
        "禁止正面鬼怪攻击",
        "禁止解释四楼真实来源"
      ]
    }
  ],
  "global_constraints": [
    "不能新增事实",
    "不能新增角色",
    "不能新增地点",
    "不能新增线索",
    "不能泄露 forbidden_revelations"
  ],
  "max_rewrite_attempts": 1
}
```

---

### 5.2 RewriteResult

```json
{
  "rewrite_result_id": "rr_ch_006_001",
  "rewrite_plan_id": "rp_ch_006_001",
  "chapter_id": "ch_006",
  "status": "success",
  "rewritten_draft_file": "rewrite_reports/ch_006_rewritten_draft.md",
  "changed_sections": [
    {
      "section_id": "sec_002",
      "change_type": "tightened",
      "summary": "合并重复搜索描写，减少无效环境描述。"
    },
    {
      "section_id": "sec_004",
      "change_type": "horror_atmosphere_enhanced",
      "summary": "用空间错位细节增强异常感。"
    }
  ],
  "consistency_check": {
    "passed": true,
    "violations": []
  },
  "quality_before": 6.8,
  "quality_after": 7.6,
  "accepted": true,
  "accept_reason": "质量提升 0.8，且一致性检查通过。"
}
```

---

## 6. 模块设计

```text
RewriteOptimizerService
├── RewritePlanGenerator
├── RewritePromptBuilder
├── SectionRewriteExecutor
├── FullChapterRewriteExecutor
├── RewriteConstraintBuilder
├── RewriteDiffGenerator
├── RewriteAcceptanceDecider
├── RewriteReportWriter
└── RewriteRepository
```

---

## 7. RewritePlan 生成规则

输入：

```text
quality_report
consistency_report
chapter_plan
chapter_draft
genre_context
style_bible
character_voice_profiles
```

生成规则：

```text
1. severity = high 的问题优先
2. 分数低于阈值的维度优先
3. 不可修复的问题只记录，不进入 rewrite_task
4. 与事实冲突相关的问题不自动修，只交给一致性修订
5. 恐怖氛围不足时读取 Horror Genre Pack 允许手法
6. 章节钩子弱时只能基于已有 event 强化
```

---

## 8. 修稿模式

### 8.1 section_rewrite

适合：

```text
局部拖沓
某段对白差
某个 section 恐怖氛围不足
结尾钩子弱
```

### 8.2 full_chapter_rewrite

适合：

```text
整体质量低
文风严重不统一
结构混乱
多个 section 都需要重写
```

MVP 建议：

```text
先实现 section_rewrite + full_chapter_rewrite
```

---

## 9. Rewrite Prompt 要点

```text
你是小说修稿器，不是剧情创造者。

你只能根据 RewritePlan 修改表达、节奏、对白、心理描写和氛围。
你不能新增事实。
你不能新增角色。
你不能新增地点。
你不能新增线索。
你不能改变 EventLog 中的事件结果。
你不能泄露 forbidden_revelations。
你必须遵守 GenreContext。
如果当前 genre_id = horror，你必须遵守 Horror Genre Pack 的 allowed_devices 和 forbidden_devices。
输出修稿后的章节正文。
```

---

## 10. 自动接受策略

```json
{
  "rewrite_acceptance_policy": {
    "auto_accept_enabled": true,
    "require_consistency_passed": true,
    "require_genre_consistency_passed": true,
    "min_quality_improvement": 0.4,
    "reject_if_new_fact_detected": true,
    "reject_if_forbidden_revelation_detected": true,
    "fallback_to_original_if_failed": true
  }
}
```

---

## 11. API

```text
POST /simulations/{simulationId}/chapters/{chapterId}/rewrite-plan
POST /simulations/{simulationId}/chapters/{chapterId}/rewrite
GET  /simulations/{simulationId}/chapters/{chapterId}/rewrite-result
GET  /simulations/{simulationId}/chapters/{chapterId}/rewrite-diff
POST /simulations/{simulationId}/chapters/{chapterId}/rewrite/accept
POST /simulations/{simulationId}/chapters/{chapterId}/rewrite/reject
```

---

## 12. 输出文件

```text
outputs/sim_xxx/
  rewrite_reports/
    ch_006_rewrite_plan.json
    ch_006_rewrite_result.json
    ch_006_rewrite_diff.json
    ch_006_rewritten_draft.md
```

---

## 13. 测试用例

```text
1. quality_report 低分时生成 rewrite_plan
2. weak_conflict 能生成 increase_conflict task
3. slow_middle 能生成 tighten_pacing task
4. horror_atmosphere 低分能生成 enhance_horror_atmosphere task
5. 修稿后新增事实会被拒绝
6. 修稿后违反 HorrorRule 会被拒绝
7. 修稿后质量提高且一致性通过则自动接受
8. 修稿失败时保留原稿
```

---

## 14. V5.3 DoD

```text
1. 能根据 quality_report 生成 rewrite_plan
2. 支持 section_rewrite
3. 支持 full_chapter_rewrite
4. 修稿后自动跑 ConsistencyCheck
5. 修稿后自动跑 GenreConsistencyCheck
6. 修稿后自动跑 QualityEvaluator
7. 分数提升且检查通过时可自动接受
8. 不允许新增事实、角色、地点、线索
9. 支持 rewrite_diff
10. 支持 API 和页面查看修稿结果
```

---

# V5.4 OpenThreadManager 悬念债务管理器

## 1. 目标

悬疑灵异长篇最怕“开坑不收”。  
V5.4 要建立统一的悬念债务系统。

---

## 2. 解决的问题

```text
1. open_threads 越来越多
2. 重要悬念长期不推进
3. 已解决悬念重复出现
4. 支线淹没主线
5. 结局时大量坑未回收
6. 动态 NPC 因低价值 thread 过度生成
```

---

## 3. Thread 数据结构

```json
{
  "thread_id": "thread_white_van",
  "question": "白色面包车是谁的？",
  "thread_type": "mystery_clue",
  "arc_id": "arc_hospital_truth",
  "priority": 8,
  "status": "in_progress",
  "opened_at_chapter": 3,
  "opened_at_event": "evt_0081",
  "last_progress_chapter": 5,
  "expected_progress_chapter_range": [5, 10],
  "expected_payoff_chapter_range": [12, 18],
  "related_clues": ["clue_white_van"],
  "related_evidence": ["ev_white_van"],
  "related_characters": ["npc_store_owner_001"],
  "related_locations": ["old_street_shop"],
  "staleness": 2,
  "payoff_readiness": 0.45,
  "recommended_action": "introduce_partial_clue",
  "forbidden_actions": [
    "不能直接揭示司机真实身份"
  ]
}
```

---

## 4. Thread 类型

```text
main_mystery：主线谜团
sub_mystery：支线谜团
character_secret：人物秘密
supernatural_rule：灵异规则
relationship_tension：关系张力
red_herring：误导线
danger_thread：威胁线
payoff_thread：伏笔回收线
```

---

## 5. Thread 状态

```text
open：已开启
active：当前章节正在推进
in_progress：近期有推进
blocked：暂时无法推进
payoff_ready：可以回收
resolved：已解决
abandoned：有意放弃
expired：过期
reopened：重新打开，需要强校验
```

---

## 6. NarrativeDebtReport

```json
{
  "simulation_id": "sim_001",
  "chapter_id": "ch_012",
  "open_thread_count": 9,
  "high_priority_open_count": 4,
  "stale_thread_count": 3,
  "payoff_ready_count": 2,
  "debt_level": "high",
  "high_priority_stale_threads": [
    {
      "thread_id": "thread_white_van",
      "priority": 8,
      "staleness": 3,
      "recommended_action": "progress_or_payoff"
    }
  ],
  "warnings": [
    "高优先级悬念超过 3 章未推进。",
    "当前 open_threads 数量接近上限。"
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

## 7. OpenThreadManager 模块

```text
OpenThreadManager
├── ThreadRegistry
├── ThreadStateUpdater
├── ThreadPriorityCalculator
├── ThreadStalenessDetector
├── PayoffReadinessAnalyzer
├── NarrativeDebtReporter
├── ResolvedThreadGuard
├── ThreadRecommendationEngine
└── ThreadPolicyEnforcer
```

---

## 8. 与其他模块集成

### 8.1 与 ChapterPlanner

ChapterPlanner 必须读取：

```text
high_priority_stale_threads
payoff_ready_threads
max_new_threads_per_chapter
```

章节计划规则：

```text
1. 每章至少推进一个高优先级 thread
2. 中后段减少新增 thread
3. 结尾阶段禁止新增主线级 mystery
4. payoff_ready 的 thread 优先回收
```

---

### 8.2 与 DynamicNPCIntroductionService

如果 thread stale 且缺少角色入口：

```json
{
  "need_type": "thread_requires_character",
  "thread_id": "thread_white_van",
  "suggested_narrative_function": "witness"
}
```

---

### 8.3 与 Mystery Logic Module

OpenThread 绑定：

```text
Evidence
Suspect
TruthChain
RedHerring
```

---

### 8.4 与 NovelProductionOrchestrator

每章结束后：

```text
OpenThreadManager.update_from_chapter_summary()
OpenThreadManager.generate_debt_report()
NovelProductionOrchestrator 根据 debt report 决定下一章目标
```

---

## 9. 配置项

```json
{
  "open_thread_manager": {
    "enabled": true,
    "max_open_threads": 12,
    "max_new_threads_per_chapter": 2,
    "stale_chapter_threshold": 2,
    "high_priority_threshold": 7,
    "prevent_resolved_thread_reopen": true,
    "endgame_new_thread_limit": 0,
    "payoff_ready_threshold": 0.75
  }
}
```

---

## 10. API

```text
GET  /simulations/{simulationId}/threads
GET  /simulations/{simulationId}/threads/{threadId}
POST /simulations/{simulationId}/threads
PUT  /simulations/{simulationId}/threads/{threadId}
POST /simulations/{simulationId}/threads/{threadId}/resolve
POST /simulations/{simulationId}/threads/{threadId}/abandon
GET  /simulations/{simulationId}/narrative-debt-report
```

---

## 11. 页面

### Thread Board

分栏：

```text
Open
Active
In Progress
Blocked
Payoff Ready
Resolved
```

每个卡片显示：

```text
问题
优先级
所属 Arc
拖延章节数
预计回收章节
相关线索
推荐动作
```

---

## 12. 测试用例

```text
1. 新 open_thread 能注册
2. 章节推进后 thread 状态更新
3. 超过阈值的 thread 被标记 stale
4. payoff_ready 能正确识别
5. resolved thread 不能被重复打开
6. 结尾阶段不能新增主线 mystery
7. narrative_debt_report 能输出 high debt warning
```

---

## 13. V5.4 DoD

```text
1. 所有 open_threads 进入统一管理
2. 每个 thread 有 priority / expected_payoff_range
3. 能识别 stale thread
4. 能识别 payoff_ready thread
5. 能输出 narrative_debt_report
6. ChapterPlanner 能读取 thread recommendation
7. DynamicNPCService 能基于 stale thread 生成需求
8. resolved thread 不会重复作为主悬念
9. 页面可查看 Thread Board
10. LongRunTest 可统计 narrative debt 指标
```

---

# V5.5 NovelBlueprint + NovelProductionOrchestrator

## 1. 目标

把系统从“章节生成器”升级为“全书生产器”。

10 万字不能只靠一章章向前跑，必须有全书蓝图和生产调度器。

---

## 2. NovelBlueprint 数据结构

```json
{
  "novel_id": "novel_hospital_001",
  "title": "旧医院真相",
  "target_words": 100000,
  "target_chapters": 30,
  "genre_id": "horror",
  "sub_genre": "suspense_supernatural",
  "theme": "记忆与愧疚",
  "acts": [
    {
      "act_id": "act_1",
      "name": "异常开启",
      "chapter_range": [1, 8],
      "word_range": [1, 25000],
      "function": "建立异常、主角卷入、打开核心悬念",
      "plot_arc_stage": "setup",
      "genre_stage": "subtle_anomaly",
      "goals": [
        "建立旧医院异常",
        "引出主角过去缺口",
        "打开白色面包车线索"
      ],
      "must_not_reveal": [
        "十年前事故真相",
        "四楼真实来源"
      ]
    },
    {
      "act_id": "act_2",
      "name": "调查与逼近",
      "chapter_range": [9, 22],
      "word_range": [25001, 75000],
      "function": "调查推进、误导升级、灵异规则显形",
      "plot_arc_stage": "investigation",
      "genre_stage": "rule_discovery",
      "goals": [
        "推进证据链",
        "强化灵异规则",
        "制造中段反转"
      ]
    },
    {
      "act_id": "act_3",
      "name": "真相与终局",
      "chapter_range": [23, 30],
      "word_range": [75001, 100000],
      "function": "真相揭露、终局选择、余波收束",
      "plot_arc_stage": "revelation",
      "genre_stage": "truth_and_resolution",
      "goals": [
        "揭示核心真相",
        "回收高优先级悬念",
        "完成人物弧"
      ],
      "new_major_thread_allowed": false
    }
  ]
}
```

---

## 3. ChapterFunctionPlan

每章都必须有章节功能，不允许“随便继续”。

```json
{
  "chapter_id": "ch_012",
  "chapter_no": 12,
  "target_words": 3500,
  "act_id": "act_2",
  "chapter_function": "推进白色面包车线索，并让主角第一次验证四楼规则",
  "primary_thread": "thread_white_van",
  "secondary_threads": ["thread_fourth_floor"],
  "required_events": [
    "discover_partial_vehicle_info",
    "experience_space_mismatch"
  ],
  "genre_context": {
    "genre_id": "horror",
    "genre_stage": "rule_discovery",
    "target_horror_intensity": 6
  },
  "must_not_reveal": [
    "四楼真实来源",
    "反派真实身份"
  ]
}
```

---

## 4. NovelProductionOrchestrator

职责：

```text
1. 读取 NovelBlueprint
2. 判断当前章节属于哪个 act
3. 生成 ChapterFunctionPlan
4. 调用 SimulationRunner
5. 调用 NarrativeWriter
6. 调用 ConsistencyCheck
7. 调用 QualityEvaluator
8. 调用 RewriteOptimizer
9. 更新 OpenThreadManager
10. 更新 MysteryLogicManager
11. 更新 NovelProgress
12. 判断是否进入下一章
13. 判断是否进入终局阶段
14. 完成后调用 FinalClosureCheck
```

---

## 5. NovelProgress

```json
{
  "novel_id": "novel_hospital_001",
  "current_chapter": 12,
  "target_chapters": 30,
  "current_words": 40320,
  "target_words": 100000,
  "current_act": "act_2",
  "progress_ratio": 0.4,
  "arc_progress": {
    "arc_hospital_truth": 0.46
  },
  "thread_stats": {
    "open": 8,
    "resolved": 5,
    "stale": 2
  },
  "quality_stats": {
    "average_score": 7.3,
    "chapters_below_threshold": 2
  }
}
```

---

## 6. 生产循环

```text
while current_words < target_words and current_chapter < target_chapters:
    chapter_function = ChapterFunctionResolver.resolve()
    chapter_plan = ChapterPlanner.generate(chapter_function)
    simulation_result = SimulationRunner.run_chapter()
    draft = NarrativeWriter.generate()
    consistency = ConsistencyCheck.run()
    quality = StoryQualityEvaluator.evaluate()
    if quality.rewrite_recommended:
        rewrite = RewriteOptimizer.rewrite()
    OpenThreadManager.update()
    MysteryLogicManager.update()
    NovelProgressMonitor.update()
    if severe_issue:
        pause_or_rerun()
```

---

## 7. 字数控制

新增 ChapterWordBudgetController。

```json
{
  "chapter_word_budget": {
    "target_words": 3500,
    "min_words": 3000,
    "max_words": 4200,
    "current_draft_words": 3680,
    "status": "within_range"
  }
}
```

规则：

```text
1. 每章目标字数由 NovelBlueprint 分配
2. 如果章节过短，允许扩写已有情绪/场景，不允许新增事实
3. 如果章节过长，压缩重复描写
4. 总字数接近目标时自动收束
```

---

## 8. API

```text
POST /projects/{projectId}/novel-blueprint
GET  /projects/{projectId}/novel-blueprint
PUT  /projects/{projectId}/novel-blueprint

POST /projects/{projectId}/production/start
POST /productions/{productionId}/pause
POST /productions/{productionId}/resume
GET  /productions/{productionId}/status
GET  /productions/{productionId}/progress
```

---

## 9. 页面

### Novel Production Dashboard

显示：

```text
目标字数
当前字数
目标章节数
当前章节
当前 Act
主线进度
悬念债务
平均质量分
最近失败原因
暂停 / 继续 / 重跑当前章
```

---

## 10. 测试用例

```text
1. NovelBlueprint 能创建 30 章结构
2. ChapterFunctionPlan 能按章节生成
3. Orchestrator 能连续生成多章
4. 字数统计正确
5. 低质量章节触发 RewriteOptimizer
6. 结尾阶段禁止新增 major thread
7. 生产过程中失败可恢复
```

---

## 11. V5.5 DoD

```text
1. 支持 NovelBlueprint
2. 支持 ChapterFunctionPlan
3. 支持 NovelProgress
4. 支持 NovelProductionOrchestrator
5. 支持自动逐章生产
6. 支持章节目标字数控制
7. 支持暂停 / 恢复 / 重跑当前章
8. 能接入 QualityEvaluator / RewriteOptimizer / OpenThreadManager
9. 页面能查看全书生产进度
10. 能生产至少 10 章连续草稿
```

---

# V5.6 Mystery Logic Module 悬疑逻辑增强

## 1. 目标

悬疑灵异不是纯恐怖。  
它还需要证据链、误导、嫌疑人、真相链和推理公平性。

V5.6 建议实现为：

```text
Mystery Logic Module
```

它可以作为：

```text
genre_packs/mystery
```

也可以作为 horror 的子模式：

```text
horror.sub_genre = suspense_supernatural
```

推荐做成可组合模块：

```text
Horror Genre Pack
+
Mystery Logic Module
```

---

## 2. 核心对象

```text
Evidence：证据
Suspect：嫌疑人
RedHerring：误导线索
TruthChain：真相链
DeductionStep：推理步骤
RevealSchedule：揭示计划
MisdirectionBudget：误导预算
```

---

## 3. Evidence 数据结构

```json
{
  "evidence_id": "ev_white_van",
  "content": "三天前夜里白色面包车停在旧医院门口。",
  "evidence_type": "witness_statement",
  "truth_relevance": "medium",
  "reliability": 0.7,
  "can_mislead": true,
  "points_to": ["suspect_guard", "suspect_unknown_man"],
  "real_meaning": "真正进入医院的是反派代理人，不是看门人。",
  "allowed_reveal_chapters": [4, 12],
  "related_threads": ["thread_white_van"],
  "related_clues": ["clue_white_van"]
}
```

---

## 4. Suspect 数据结构

```json
{
  "suspect_id": "suspect_guard",
  "character_id": "char_guard",
  "suspicion_level": 0.65,
  "apparent_motive": "隐瞒旧医院近期出入记录",
  "real_role": "covering_minor_truth",
  "evidence_against": ["ev_changed_lock", "ev_white_van"],
  "evidence_clearing": ["ev_guard_alibi"],
  "can_be_red_herring": true
}
```

---

## 5. RedHerring 数据结构

```json
{
  "red_herring_id": "rh_guard_as_culprit",
  "points_to": "suspect_guard",
  "introduced_at_chapter": 4,
  "expected_clear_chapter_range": [12, 18],
  "supporting_evidence": ["ev_changed_lock", "ev_guard_evasion"],
  "clearing_evidence": ["ev_guard_alibi"],
  "status": "active",
  "risk": "不能让误导持续到结尾，否则读者会认为硬转折"
}
```

---

## 6. TruthChain 数据结构

```json
{
  "truth_id": "truth_hospital_accident",
  "final_truth": "旧医院灵异现象源自十年前事故记忆残留。",
  "reveal_steps": [
    {
      "step_id": "truth_step_001",
      "chapter_range": [1, 6],
      "reveal_level": "surface",
      "allowed_information": "旧医院并非完全废弃。",
      "required_evidence": ["ev_changed_lock"]
    },
    {
      "step_id": "truth_step_002",
      "chapter_range": [7, 15],
      "reveal_level": "partial",
      "allowed_information": "有人近期进入旧医院，并刻意隐藏痕迹。",
      "required_evidence": ["ev_white_van", "ev_removed_file"]
    },
    {
      "step_id": "truth_step_003",
      "chapter_range": [16, 24],
      "reveal_level": "major",
      "allowed_information": "主角过去与旧医院事故有关。",
      "required_evidence": ["ev_child_record", "ev_old_photo"]
    },
    {
      "step_id": "truth_step_004",
      "chapter_range": [25, 30],
      "reveal_level": "truth",
      "allowed_information": "事故真相与灵异规则完整揭示。",
      "required_evidence": ["ev_final_memory", "ev_rule_origin"]
    }
  ]
}
```

---

## 7. MysteryLogicManager

模块：

```text
MysteryLogicManager
├── EvidenceGraphManager
├── SuspectTracker
├── RedHerringManager
├── TruthChainManager
├── DeductionFairnessChecker
├── RevealScheduleManager
├── MisdirectionBudgetManager
└── MysteryConsistencyChecker
```

---

## 8. DeductionFairnessChecker

检查：

```text
1. 真相揭示前是否给过足够证据
2. 关键证据是否被读者见过
3. 误导是否有可被推翻的证据
4. 结局是否靠突然新增事实解释
5. 嫌疑人转移是否自然
```

输出：

```json
{
  "passed": false,
  "violations": [
    {
      "type": "unfair_reveal",
      "message": "最终真相依赖第 29 章首次出现的新证据，缺少前文铺垫。",
      "severity": "high"
    }
  ]
}
```

---

## 9. 与 OpenThreadManager 集成

每个 thread 可绑定：

```text
Evidence
Suspect
TruthChain step
RedHerring
```

例如：

```json
{
  "thread_id": "thread_white_van",
  "related_evidence": ["ev_white_van"],
  "related_suspects": ["suspect_guard", "suspect_unknown_man"],
  "related_truth_chain": "truth_hospital_accident"
}
```

---

## 10. 与 ChapterPlanner 集成

章节计划必须参考：

```text
当前应 reveal 哪个 truth_step
当前应强化哪个 red_herring
当前应清除哪个误导
当前是否证据不足
```

---

## 11. 配置项

```json
{
  "mystery_logic": {
    "enabled": true,
    "max_active_red_herrings": 3,
    "require_evidence_before_major_reveal": true,
    "forbid_final_truth_without_prior_evidence": true,
    "red_herring_clear_required": true,
    "deduction_fairness_check_enabled": true
  }
}
```

---

## 12. API

```text
GET  /simulations/{simulationId}/evidence
GET  /simulations/{simulationId}/suspects
GET  /simulations/{simulationId}/red-herrings
GET  /simulations/{simulationId}/truth-chains
GET  /simulations/{simulationId}/mystery-report
POST /simulations/{simulationId}/deduction-fairness-check
```

---

## 13. 页面

### Mystery Board

显示：

```text
证据板
嫌疑人列表
误导线索
真相链
当前揭示进度
推理公平性报告
```

---

## 14. 测试用例

```text
1. evidence 能绑定 thread
2. suspect suspicion_level 能随证据变化
3. red_herring 能在指定章节前清除
4. truth_chain 不能跳级 reveal
5. final_truth 缺少前置证据时被拦截
6. 推理公平性检查能发现硬解释
```

---

## 15. V5.6 DoD

```text
1. 支持 EvidenceGraph
2. 支持 SuspectTracker
3. 支持 RedHerringManager
4. 支持 TruthChain
5. 支持 DeductionFairnessChecker
6. 关键真相不能缺少前置证据直接揭示
7. 误导线索可追踪并可清除
8. ChapterPlanner 能读取 Mystery recommendation
9. 页面可查看 Mystery Board
10. FinalClosureCheck 能检查悬疑逻辑闭合
```

---

# V5.7 100k LongRun Test + Final Closure + Manuscript Exporter

## 1. 目标

验证系统能独自完成一部约 10 万字悬疑灵异长篇，并导出成稿。

---

## 2. 100k LongRun Test 配置

```json
{
  "test_id": "longrun_100k_horror_suspense_001",
  "project_id": "dark_hospital_001",
  "target_words": 100000,
  "target_chapters": 30,
  "genre_id": "horror",
  "sub_genre": "suspense_supernatural",
  "seed": 12345,
  "thresholds": {
    "average_quality_score_min": 7.0,
    "consistency_pass_rate_min": 0.95,
    "thread_resolution_rate_min": 0.7,
    "main_thread_resolution_required": true,
    "style_drift_max": 0.25,
    "npc_growth_max_per_chapter": 1.0,
    "final_closure_required": true
  }
}
```

---

## 3. LongRunReport

```json
{
  "test_id": "longrun_100k_horror_suspense_001",
  "chapters_generated": 30,
  "total_words": 102430,
  "average_quality_score": 7.3,
  "consistency_pass_rate": 0.97,
  "genre_consistency_pass_rate": 0.96,
  "thread_resolution_rate": 0.78,
  "main_arc_closed": true,
  "truth_chain_closed": true,
  "style_drift_score": 0.19,
  "npc_growth_rate_per_chapter": 0.7,
  "final_status": "passed",
  "major_issues": []
}
```

---

## 4. FinalClosureCheck

检查：

```text
1. 主 PlotArc 是否完成
2. 核心真相是否揭示
3. 高优先级 open_threads 是否解决
4. TruthChain 是否闭合
5. RedHerring 是否清除或解释
6. 重要人物弧是否完成
7. 灵异规则是否解释到应解释程度
8. 结尾是否新增大坑
9. 结局是否符合 GenreProfile
10. 字数是否达到目标区间
```

输出：

```json
{
  "closure_report_id": "closure_novel_001",
  "passed": false,
  "checks": {
    "main_arc_closed": true,
    "truth_chain_closed": true,
    "high_priority_threads_resolved": false,
    "character_arcs_closed": true,
    "supernatural_rules_resolved": true,
    "no_new_major_thread_in_ending": true
  },
  "unresolved_items": [
    {
      "type": "open_thread",
      "id": "thread_missing_archive_photo",
      "priority": 8,
      "message": "高优先级悬念未解决。"
    }
  ],
  "recommendations": [
    "在终章前增加一段对档案照片来源的解释，不能新增新证据，只能使用已发现 ev_old_photo。"
  ]
}
```

---

## 5. FullNovelConsistencyCheck

检查全书级问题：

```text
1. 角色名字是否一致
2. 地点状态是否一致
3. 时间线是否一致
4. 已死亡/离开的角色是否错误出现
5. 已解决悬念是否重复出现
6. 灵异规则是否前后矛盾
7. 证据链是否前后矛盾
8. 文风是否严重漂移
```

---

## 6. ManuscriptExporter

导出：

```text
manuscript.md
manuscript.docx
chapter_index.json
full_novel_report.json
quality_summary.json
thread_resolution_report.json
mystery_logic_report.json
genre_report.json
```

Markdown 结构：

```markdown
# 小说标题

## 第一章 XXX

正文...

## 第二章 XXX

正文...
```

---

## 7. API

```text
POST /projects/{projectId}/long-run-tests/100k
GET  /long-run-tests/{testId}
GET  /long-run-tests/{testId}/report

POST /productions/{productionId}/final-closure-check
GET  /productions/{productionId}/closure-report

POST /productions/{productionId}/export
GET  /productions/{productionId}/exports
```

---

## 8. 页面

### 100k LongRun Dashboard

显示：

```text
目标字数
当前字数
章节进度
平均质量分
一致性通过率
悬念回收率
真相链闭合度
NPC 增长
文风漂移
最终收束状态
导出按钮
```

---

## 9. 测试用例

```text
1. 能运行 10 章 smoke test
2. 能运行 30 章 100k test
3. 能统计总字数
4. 能检测 unresolved high priority thread
5. 能检测 TruthChain 未闭合
6. 能检测结尾新增大坑
7. 能导出 manuscript.md
8. 导出章节顺序正确
```

---

## 10. V5.7 DoD

```text
1. 支持 100k LongRunTest
2. 支持 LongRunReport
3. 支持 FinalClosureCheck
4. 支持 FullNovelConsistencyCheck
5. 支持 ManuscriptExporter
6. 能导出完整 manuscript.md
7. 能统计质量、悬念、证据链、文风、字数
8. 终局未收束时能给出修复建议
9. 页面能查看 100k 生产结果
10. 至少通过一次 10 万字悬疑灵异测试
```

---

# 全局输出目录

```text
outputs/production_xxx/
  novel_blueprint.json
  novel_progress.json

  chapters/
    ch_001.md
    ch_002.md

  quality_reports/
    ch_001_quality.json

  rewrite_reports/
    ch_001_rewrite_plan.json
    ch_001_rewrite_result.json

  thread_reports/
    ch_001_debt.json

  mystery_reports/
    evidence_graph.json
    suspect_tracker.json
    truth_chain.json
    deduction_fairness_report.json

  longrun_reports/
    longrun_100k_report.json

  closure/
    final_closure_report.json
    full_novel_consistency_report.json

  exports/
    manuscript.md
    manuscript.docx
    full_novel_report.json
```

---

# 总体开发顺序

```text
1. V5.3 RewriteOptimizer
2. V5.4 OpenThreadManager
3. V5.5 NovelBlueprint + NovelProductionOrchestrator
4. V5.6 Mystery Logic Module
5. V5.7 100k LongRun Test + ManuscriptExporter
```

---

# 最短可用 MVP

如果要最快跑通 10 万字，可以缩小范围：

```text
MVP-1：RewriteOptimizer
- section_rewrite
- consistency check after rewrite
- quality re-evaluate

MVP-2：OpenThreadManager
- thread registry
- stale detection
- payoff_ready
- debt report

MVP-3：NovelProductionOrchestrator
- target_chapters = 30
- target_words = 100000
- chapter function plan
- production loop

MVP-4：Mystery Logic 简版
- EvidenceGraph
- TruthChain
- RedHerring
- DeductionFairnessCheck

MVP-5：LongRun + Export
- 30 章生成测试
- final closure check
- manuscript.md 导出
```

---

# 最终目标

完成后，系统应能做到：

```text
用户输入悬疑灵异故事设定
↓
系统生成全书蓝图
↓
系统自动逐章演练和生成
↓
系统自动评价章节质量
↓
系统自动修稿
↓
系统管理悬念和证据链
↓
系统控制恐怖灵异规则和氛围
↓
系统生成约 10 万字全文
↓
系统检查全书收束
↓
系统导出 manuscript
```

这标志着系统从“AI 小说章节生成器”升级为：

> AI 长篇小说生产引擎。
