# 小说沙盘 V1 内测版整体说明文档

> 版本名称：小说沙盘 V1 内测版  
> 版本定位：AI 长篇小说沙盘生产引擎内测版  
> 覆盖范围：统一整合原 V1–V5.7 的全部核心能力  
> 当前重点题材：悬疑灵异 / 恐怖灵异  
> 架构原则：核心引擎通用化，题材能力插件化，当前内置 Horror / Suspense 能力。

---

## 0. 文档目的

本文档用于把此前分散在多个迭代版本中的能力统一归并为：

```text
小说沙盘 V1 内测版
```

本文档重点说明：

```text
1. V1 内测版整体定位
2. 应包含的核心功能
3. 系统整体架构
4. 用户工作流
5. AI 运行流程
6. 世界配置流程
7. 长篇生产流程
8. 动态 NPC / 线索 / 证据生成机制
9. 质量评估与自动修稿
10. 悬疑灵异长篇生产闭环
11. 页面与产品功能建议
12. 内测验收标准
13. 当前边界与后续优化方向
```

---

# 1. V1 内测版定位

## 1.1 一句话定位

小说沙盘 V1 内测版是一个：

> 基于世界设定、角色 Agent、事件模拟、剧情弧控制、线索证据管理、质量评估、自动修稿和全书调度的 AI 长篇小说生产引擎。

它不是简单的：

```text
用户输入一句话 → AI 直接续写小说
```

而是：

```text
用户配置世界和故事骨架
↓
角色在世界中行动和交互
↓
系统记录事件
↓
系统生成章节
↓
系统检查一致性和质量
↓
系统自动修稿
↓
系统管理悬念、证据、伏笔和真相链
↓
系统持续生产到目标字数
↓
系统检查全书收束
↓
系统导出成稿
```

---

## 1.2 当前主要目标

V1 内测版当前主要服务于：

```text
悬疑灵异故事
恐怖灵异故事
旧案调查类故事
都市怪谈类故事
多角色沙盘演练故事
8–12 万字长篇故事原型生成
```

---

## 1.3 产品形态

V1 内测版可以理解为三个系统的组合：

```text
1. World Studio：世界与故事配置工作台
2. Simulation Engine：角色沙盘模拟引擎
3. Novel Production Engine：长篇小说生产引擎
```

---

# 2. V1 内测版核心设计理念

## 2.1 不是纯文本续写，而是事件驱动生成

系统不直接让大模型自由续写，而是使用：

```text
WorldState
AgentAction
EnvironmentResult
EventLog
ChapterPlan
NarrativeWriter
ConsistencyCheck
QualityEvaluator
RewriteOptimizer
```

形成一条稳定链路。

核心原则：

```text
先发生事件
再生成叙事
```

而不是：

```text
先生成正文
再倒推事件
```

---

## 2.2 角色不是设定卡，而是 Agent

角色拥有：

```text
目标
信念
记忆
关系
当前位置
已知信息
可行动作
性格倾向
风险偏好
```

角色可以：

```text
探索地点
询问 NPC
检查物品
移动
隐瞒
误导
协作
冲突
改变信念
```

---

## 2.3 剧情不是完全自由，而是受 PlotArc 控制

系统支持：

```text
setup
investigation
confrontation
revelation
resolution
```

不同阶段允许透露的信息不同。

例如悬疑灵异故事中：

```text
前期只能看到异常
中期可以发现规则
后期才能揭示真相
```

---

## 2.4 NPC 不需要全部手动配置

系统支持：

```text
动态 NPC 生成
候选 NPC 审核
已有角色复用
NPC 知识边界
NPC 合理出场
NPC 注册入库
```

原则是：

```text
剧情缺口驱动
优先复用已有角色
无法复用再生成新 NPC
新 NPC 不能携带超阶段真相
```

---

## 2.5 线索不必全部手动配置，但必须有故事骨架

用户不需要手动配置所有线索，但系统必须在开始模拟前生成或确认：

```text
TruthChain
EvidenceGraph
OpenThreads
CoreClues
RevealSchedule
ForeshadowingPlan
NPC RoleSpecs
```

否则模拟容易空转。

---

## 2.6 核心引擎通用，题材能力插件化

核心引擎不写死恐怖灵异逻辑。

架构为：

```text
Generic Story Engine
↓
Genre Abstraction Layer
↓
Horror Genre Pack
↓
Suspense / Mystery Logic Module
```

后续可扩展：

```text
Mystery
Romance
Fantasy
Sci-Fi
Urban
Adventure
Wuxia
```

---

# 3. V1 内测版功能总览

## 3.1 世界配置能力

系统支持配置：

```text
世界 ID
标题
题材
时代背景
核心地点
基调
世界规则
禁忌规则
主题
核心真相方向
结局方向
```

示例：

```json
{
  "world_id": "dark_hospital_001",
  "title": "绝命旧院",
  "genre_id": "horror",
  "sub_genre": "suspense_supernatural",
  "era": "现代都市",
  "tone": "克制、压抑、现实中透出诡异",
  "themes": ["记忆是否可靠", "人如何逃避愧疚"],
  "world_rules": [
    "旧医院午夜后会出现不存在的五楼",
    "五楼不会随机杀人，每次死亡都对应旧案真相",
    "看门人知道危险，但不会主动说出完整真相"
  ]
}
```

---

## 3.2 角色生成能力

系统支持：

```text
手动创建角色
AI 生成角色候选
批量生成配角
角色审核
角色入库
角色弧光管理
角色信念变化
角色声音配置
```

角色字段包括：

```text
角色 ID
姓名
身份
性格
目标
恐惧
秘密
已知事实
未知事实
人物弧
关系
行动倾向
当前地点
```

---

## 3.3 NPC 生成能力

系统支持：

```text
页面生成 NPC 候选
运行中动态生成 NPC
根据地点生成 NPC
根据线索缺口生成 NPC
根据 stale thread 生成 NPC
```

NPC 类型：

```text
ephemeral：一次性路人
scene_npc：场景 NPC
recurring_npc：可重复出现 NPC
major_npc：重要 NPC，需要确认
```

NPC 叙事功能：

```text
witness：目击者
clue_holder：线索持有者
obstructor：阻碍者
helper：帮助者
misleader：误导者
connector：连接人物 / 地点 / 组织
authority：制度权力者
victim_related：受害者相关人物
villain_proxy：反派代理人
crowd_flavor：氛围角色
```

---

## 3.4 地图与地点能力

系统支持：

```text
地图节点
地点连接
地点描述
地点可用动作
地点可用 NPC
地点可发现物品
地点可发现线索
地点危险等级
地点 Genre Context
```

悬疑灵异常用地点：

```text
旧医院门口
小卖部
档案馆
派出所
旧楼住户家
医院五楼
地下室
监控室
护士站
废弃病房
```

---

## 3.5 世界规则能力

系统支持：

```text
普通世界规则
Genre 规则
恐怖规则
灵异规则
杀人规则
禁忌规则
揭示阶段规则
```

示例：

```text
旧医院午夜后会出现不存在的五楼。
只有与旧院事故有关，或主动追查真相的人能看见五楼。
五楼不会随机杀人，每次死亡都对应旧医院过去被掩盖的一段真相。
死亡前会出现三次异常征兆。
五楼通过让人重复经历死者最后记忆来杀人。
```

---

## 3.6 线索与证据能力

系统支持：

```text
Clue
Evidence
TruthChain
RevealSchedule
DiscoverRoute
RedHerring
Suspect
DeductionFairnessCheck
```

核心结构：

```text
线索 Clue：角色可以发现的信息
证据 Evidence：可支持或误导推理的信息
真相链 TruthChain：最终真相的分阶段揭示
误导 RedHerring：错误方向，但必须可被纠正
嫌疑人 Suspect：被证据指向的人物
```

---

## 3.7 剧情弧能力

系统支持：

```text
PlotArc
ChapterContinuity
CharacterArc
Foreshadowing
OpenThread
Payoff
FinalClosure
```

PlotArc 阶段示例：

```text
setup：建立异常
investigation：调查推进
confrontation：冲突升级
revelation：真相揭示
resolution：结局收束
```

---

## 3.8 模拟能力

系统支持：

```text
多 Agent 调度
角色行动
环境响应
NPC 响应
地点移动
线索发现
物品交互
冲突事件
异常事件
EventLog 记录
```

---

## 3.9 章节生成能力

系统支持：

```text
ChapterPlan
ChapterFunctionPlan
NarrativeWriter
Multi-POV
章节钩子
章节摘要
章节连续性
章节质量评估
章节自动修稿
```

---

## 3.10 长篇生产能力

系统支持：

```text
NovelBlueprint
NovelProductionOrchestrator
NovelProgress
ChapterWordBudgetController
100k LongRun Test
FinalClosureCheck
ManuscriptExporter
```

---

# 4. V1 内测版模块架构

## 4.1 总体模块

```text
World Studio
├── World Config
├── Character Generator
├── NPC Generator
├── Location Generator
├── Clue Generator
├── Candidate Review Panel
├── Genre Settings
├── Horror Rules Editor
└── Novel Blueprint Editor

Simulation Engine
├── SimulationRunner
├── AgentSystem
├── EnvironmentEngine
├── NPCResponseEngine
├── EventLogService
├── MemoryService
├── Scheduler
└── StateSnapshot

Story Control
├── PlotArcService
├── ChapterContinuityService
├── CharacterArcService
├── OpenThreadManager
├── MysteryLogicManager
├── DynamicCharacterIntroductionService
└── Director

Genre System
├── GenreProfile
├── GenreRegistry
├── GenreContextBuilder
├── GenrePromptAdapter
├── HorrorGenrePack
├── HorrorAtmosphereController
├── SupernaturalRuleManager
├── HorrorQualityEvaluator
└── HorrorConsistencyChecker

Novel Production
├── NovelBlueprint
├── NovelProductionOrchestrator
├── ChapterFunctionResolver
├── ChapterPlanner
├── NarrativeWriter
├── ConsistencyCheck
├── StoryQualityEvaluator
├── RewriteOptimizer
├── FinalClosureCheck
├── FullNovelConsistencyCheck
└── ManuscriptExporter
```

---

## 4.2 核心数据流

```text
World Config
↓
Project Template / Story Skeleton
↓
NovelBlueprint
↓
ChapterFunctionPlan
↓
SimulationRunner
↓
EventLog
↓
NarrativeWriter
↓
ChapterDraft
↓
ConsistencyCheck
↓
StoryQualityEvaluator
↓
RewriteOptimizer
↓
FinalChapter
↓
ChapterSummary
↓
OpenThreadManager / MysteryLogicManager Update
↓
Next Chapter
```

---

# 5. 用户侧完整工作流

## 5.1 推荐工作流：半自动模式

这是 V1 内测版最推荐的使用方式。

```text
1. 用户填写世界基础设定
2. 用户填写核心规则 / 主题 / 基调
3. 点击“生成故事骨架”
4. 系统生成 NovelBlueprint / TruthChain / EvidenceGraph / OpenThreads
5. 用户审核候选内容
6. 用户确认入库
7. 点击“开始生产”
8. 系统逐章模拟与生成
9. 系统自动评估质量
10. 系统自动修稿
11. 系统管理悬念和证据链
12. 系统运行到目标章节 / 目标字数
13. 系统执行 FinalClosureCheck
14. 用户查看全书报告
15. 导出 manuscript
```

---

## 5.2 手动精配模式

适合认真打磨一本书。

用户手动配置：

```text
核心真相
核心角色
关键 NPC
关键线索
关键证据
关键地点
剧情阶段
结局方向
```

系统负责：

```text
模拟
动态补充
章节生成
质量评估
自动修稿
长篇生产
```

优点：

```text
最稳定
最可控
适合高质量创作
```

缺点：

```text
前期配置成本高
```

---

## 5.3 全自动模式

用户只输入：

```text
题材
核心地点
一句故事想法
目标字数
```

系统自动生成：

```text
世界设定
角色
NPC
地图
线索
证据链
真相链
章节蓝图
```

优点：

```text
启动快
适合灵感探索
```

缺点：

```text
质量波动较大
需要更强审核
```

---

# 6. “生成故事骨架”流程设计

## 6.1 为什么需要故事骨架

如果没有线索链、证据链和真相链，沙盘模拟会容易空转。

所以开始模拟前需要生成：

```text
NovelBlueprint
PlotArc
TruthChain
EvidenceGraph
OpenThread Seeds
Core Clues
Core NPC RoleSpecs
RevealSchedule
ForeshadowingPlan
```

---

## 6.2 生成流程

```text
用户输入世界设定
↓
GenrePack 读取题材规则
↓
Project Template Generator 生成基础项目
↓
MysteryLogicManager 生成 TruthChain
↓
EvidenceGraphManager 生成证据链
↓
OpenThreadManager 生成初始悬念池
↓
DynamicNPCIntroductionService 生成核心 NPC RoleSpecs
↓
Candidate Review Panel 审核
↓
写入正式配置
```

---

## 6.3 最小骨架内容

对于悬疑灵异故事，最小骨架必须包含：

```text
1. 核心真相
2. 阶段性真相揭示
3. 主要悬念
4. 关键证据
5. 误导线索
6. 至少 3 个关键地点
7. 至少 3 个信息源 NPC RoleSpec
8. 结局方向
```

---

## 6.4 示例骨架

```json
{
  "truth_chain": {
    "surface": "旧医院午夜后有异常",
    "partial": "五楼与十年前事故有关",
    "major": "主角过去与事故有关",
    "truth": "五楼是事故记忆残留，逼活人承认真相"
  },
  "open_threads": [
    "五楼为什么会出现？",
    "看门人为什么害怕？",
    "白色面包车是谁的？",
    "主角为什么梦到旧医院？"
  ],
  "evidence": [
    "新换的门锁",
    "白色面包车目击",
    "缺页病历",
    "旧广播录音",
    "烧焦照片"
  ],
  "npc_role_specs": [
    "看门人：阻碍者 + 半知情者",
    "小卖部老板：近期目击者",
    "老护士：旧事知情者",
    "档案员：记录入口"
  ]
}
```

---

# 7. 动态 NPC 生成流程

## 7.1 触发条件

动态 NPC 生成在以下情况下触发：

```text
1. open_thread 长时间未推进
2. 某条 evidence 缺少 discover_route
3. 主角前往某地点获取信息
4. 当前地点合理需要 NPC
5. 现有角色无法自然提供信息
6. Director 判断剧情需要信息源
```

---

## 7.2 生成流程

```text
OpenThreadManager / MysteryLogicManager 发现缺口
↓
NeedDetector 生成 CharacterNeed
↓
ExistingCharacterReusePlanner 尝试复用已有角色
↓
如果可复用：
    给已有角色新增 topic / clue_route / reveal_condition
否则：
    RoleSpecGenerator 生成 NPC 需求规格
↓
CandidateGenerator 生成 NPC 候选
↓
CharacterValidator 校验
↓
GenreRuleChecker / TruthChain 检查
↓
IntroductionPlanner 安排自然出场
↓
CharacterRegistry 注册 NPC
↓
NPCResponseEngine 支持后续交互
```

---

## 7.3 NPC 生成原则

```text
1. 不生成全知 NPC
2. 不生成无意义 NPC
3. 不生成不符合地点的人
4. 不让 NPC 提前说出核心真相
5. 优先复用已有角色
6. 关键 NPC 需要用户确认
7. 每章新增 NPC 有上限
8. NPC 生成后必须进入角色系统
```

---

## 7.4 示例：主角查白色面包车

```text
thread_white_van 卡住
↓
系统判断需要 witness evidence
↓
当前地点为旧医院附近街口
↓
现有 NPC 无合理目击者
↓
生成 RoleSpec：附近商户 / 夜间目击者
↓
生成 NPC：小卖部老板赵婶
↓
可透露：见过白色面包车
↓
禁止透露：司机身份、五楼真相、十年前事故真相
↓
自然出场：旧街口小卖部还亮着灯
```

---

# 8. 线索 / 证据 / 真相链流程

## 8.1 TruthChain

TruthChain 负责控制真相逐步揭示。

示例：

```json
{
  "truth_id": "truth_hospital_accident",
  "final_truth": "旧医院灵异现象源自十年前事故记忆残留。",
  "reveal_steps": [
    {
      "stage": "surface",
      "allowed_information": "旧医院并非完全废弃。"
    },
    {
      "stage": "partial",
      "allowed_information": "有人近期进入旧医院，并刻意隐藏痕迹。"
    },
    {
      "stage": "major",
      "allowed_information": "主角过去与旧医院事故有关。"
    },
    {
      "stage": "truth",
      "allowed_information": "事故真相与灵异规则完整揭示。"
    }
  ]
}
```

---

## 8.2 EvidenceGraph

EvidenceGraph 管理证据之间的关系。

证据字段：

```text
evidence_id
content
evidence_type
truth_relevance
reliability
can_mislead
points_to
real_meaning
allowed_reveal_chapters
related_threads
related_clues
```

---

## 8.3 RedHerring

误导线索必须：

```text
有合理依据
能误导读者
后续能被修正
不能永久污染主线
不能成为结尾硬反转
```

---

## 8.4 DeductionFairnessCheck

用于检查：

```text
最终真相是否有前置证据
关键证据是否出现过
推理是否公平
是否结尾突然新增事实
误导是否可被推翻
```

---

# 9. 恐怖灵异 Genre Pack

## 9.1 Horror Genre Pack 功能

当前内测版包含 Horror Genre Pack。

功能：

```text
1. 恐怖阶段控制
2. 恐怖强度递进
3. 恐怖手法选择
4. 灵异规则管理
5. 灵异规则揭示控制
6. 恐怖专项质量评分
7. 恐怖专项一致性检查
8. 恐怖 Prompt 约束注入
```

---

## 9.2 Horror Progression

默认分为：

```text
subtle_anomaly：轻微异常
clear_threat：威胁显形
rule_discovery：规则发现
truth_and_resolution：真相与收束
```

---

## 9.3 SupernaturalRuleManager

负责管理：

```text
灵异规则
规则表层表现
规则真实含义
允许表现阶段
禁止提前揭示内容
违规代价
规则一致性
```

示例：

```json
{
  "rule_id": "rule_fifth_floor",
  "surface_rule": "午夜后旧医院会出现五楼。",
  "true_rule": "五楼是旧院事故记忆残留形成的异常空间。",
  "forbidden_before_reveal": [
    "不能直接说明五楼是记忆空间",
    "不能让 NPC 解释全部规则"
  ]
}
```

---

# 10. 质量评估与自动修稿

## 10.1 StoryQualityEvaluator

每章生成后输出 QualityReport。

评分维度：

```text
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
```

恐怖专属维度：

```text
horror_atmosphere
uncanny_effect
fear_escalation
supernatural_rule_consistency
taboo_pressure
unknown_threat_strength
```

---

## 10.2 RewriteOptimizer

当章节质量低于阈值时自动修稿。

支持：

```text
tighten_pacing
increase_conflict
deepen_character
improve_hook
polish_style
reduce_exposition
improve_dialogue
enhance_suspense
enhance_horror_atmosphere
restore_character_voice
```

约束：

```text
不能新增事实
不能新增线索
不能新增角色
不能新增地点
不能改变 EventLog
不能提前泄露真相
不能违反 GenreRule
```

---

# 11. OpenThreadManager 悬念债务管理

## 11.1 管理对象

```text
主线谜团
支线谜团
人物秘密
灵异规则
关系张力
误导线
威胁线
伏笔回收线
```

---

## 11.2 状态

```text
open
active
in_progress
blocked
payoff_ready
resolved
abandoned
expired
reopened
```

---

## 11.3 作用

```text
1. 防止开坑太多
2. 防止高优先级悬念长期不推进
3. 防止已解决悬念重复出现
4. 指导 ChapterPlanner 下一章推进什么
5. 指导 DynamicNPCService 何时生成信息源
6. 指导 FinalClosureCheck 检查是否收束
```

---

# 12. NovelBlueprint 与长篇生产

## 12.1 NovelBlueprint

用于定义全书结构。

字段：

```text
target_words
target_chapters
genre_id
sub_genre
theme
act_structure
chapter_range
word_range
plot_arc_stage
genre_stage
must_reveal
must_not_reveal
```

---

## 12.2 ChapterFunctionPlan

每章必须有明确功能：

```text
本章目标
本章主悬念
本章次悬念
本章需要发现的信息
本章禁止揭示的信息
本章目标字数
本章恐怖阶段
```

---

## 12.3 NovelProductionOrchestrator

负责自动生产全书：

```text
读取 NovelBlueprint
↓
生成 ChapterFunctionPlan
↓
运行 SimulationRunner
↓
生成章节
↓
一致性检查
↓
质量评估
↓
自动修稿
↓
更新悬念 / 证据 / 进度
↓
进入下一章
↓
达到目标后收束检查
↓
导出
```

---

# 13. 10 万字 LongRun 测试

## 13.1 目标

验证系统是否能独自完成 10 万字左右长篇。

---

## 13.2 指标

```text
目标字数
实际字数
章节数
平均质量分
一致性通过率
Genre 一致性通过率
悬念回收率
真相链闭合度
NPC 增长率
文风漂移
FinalClosureCheck 是否通过
```

---

## 13.3 LongRunReport 示例

```json
{
  "target_words": 100000,
  "actual_words": 102430,
  "chapters_generated": 30,
  "average_quality_score": 7.3,
  "consistency_pass_rate": 0.97,
  "thread_resolution_rate": 0.78,
  "truth_chain_closed": true,
  "main_arc_closed": true,
  "final_status": "passed"
}
```

---

# 14. FinalClosureCheck

## 14.1 检查内容

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

---

## 14.2 未通过处理

如果 FinalClosureCheck 未通过：

```text
生成 closure_report
指出未收束项
给出修复建议
返回 NovelProductionOrchestrator 补写或修订
```

---

# 15. ManuscriptExporter

## 15.1 导出内容

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

---

## 15.2 Markdown 结构

```markdown
# 小说标题

## 第一章 章节标题

正文……

## 第二章 章节标题

正文……
```

---

# 16. 页面功能建议

## 16.1 主要页面

```text
1. 世界总览
2. 角色生成器
3. NPC 生成器
4. 线索生成器
5. 地图编辑
6. 剧情弧
7. 角色弧
8. 候选审核面板
9. Genre 设置
10. Horror Rules 编辑器
11. Novel Blueprint 编辑器
12. Production Dashboard
13. Chapter Editor
14. Quality Dashboard
15. Rewrite Panel
16. Thread Board
17. Mystery Board
18. LongRun Dashboard
19. Closure Report
20. Export Center
```

---

## 16.2 世界总览

显示：

```text
世界 ID
标题
题材
时代背景
基调
世界规则
主题
配置统计
当前生产状态
```

---

## 16.3 候选审核面板

用于审核：

```text
AI 生成角色
AI 生成 NPC
AI 生成线索
AI 生成地点
AI 生成证据
AI 生成故事骨架
```

操作：

```text
确认
修改
拒绝
重新生成
入库
```

---

## 16.4 Production Dashboard

显示：

```text
当前章节
当前字数
目标字数
当前 Act
平均质量分
悬念债务
真相链进度
最近失败原因
暂停 / 继续 / 重跑
```

---

# 17. 推荐内测流程

## 17.1 单项目内测

```text
1. 创建一个悬疑灵异项目
2. 输入基础世界设定
3. 生成故事骨架
4. 审核并确认骨架
5. 生成 5 章 smoke test
6. 检查质量报告
7. 检查悬念债务
8. 修正配置
9. 运行 30 章 / 10 万字 LongRun
10. 检查 FinalClosureReport
11. 导出 manuscript
12. 人工阅读评估
```

---

## 17.2 多项目内测

至少准备：

```text
1. 旧医院五楼
2. 废弃学校怪谈
3. 雨夜公寓旧案
4. 山村祠堂禁忌
5. 地铁末班车异常
```

每个项目至少跑：

```text
1 个 5 章 smoke test
1 个 30 章完整 LongRun
```

---

# 18. V1 内测版验收标准

## 18.1 基础验收

```text
1. 能创建世界
2. 能生成故事骨架
3. 能审核候选并入库
4. 能开始模拟
5. 能生成章节
6. 能生成质量报告
7. 能自动修稿
8. 能继续下一章
```

---

## 18.2 动态 NPC 验收

```text
1. 剧情卡住时能发现信息缺口
2. 优先复用已有 NPC
3. 复用不了时生成合理 NPC
4. 新 NPC 有知识边界
5. 新 NPC 不提前剧透
6. 新 NPC 能自然出场
7. 新 NPC 注册入库
```

---

## 18.3 悬疑逻辑验收

```text
1. TruthChain 能分阶段揭示
2. EvidenceGraph 能支撑推理
3. RedHerring 能误导并被清除
4. final truth 不依赖临时新增证据
5. DeductionFairnessCheck 能发现硬解释
```

---

## 18.4 恐怖灵异验收

```text
1. Horror Stage 能随章节推进
2. Horror Intensity 递进合理
3. SupernaturalRule 不提前揭示
4. 灵异规则前后一致
5. 恐怖氛围能被质量评估识别
```

---

## 18.5 长篇验收

```text
1. 能连续生成 10 章
2. 能连续生成 30 章
3. 能达到 8–12 万字
4. 主线能闭合
5. 高优先级悬念大部分回收
6. FinalClosureCheck 通过
7. manuscript.md 导出成功
```

---

# 19. 当前内测版边界

## 19.1 仍需人工审核的内容

```text
1. 核心真相方向
2. 最终结局倾向
3. 关键角色设定
4. 重大 NPC 入库
5. TruthChain 候选
6. FinalClosure 修复建议
```

---

## 19.2 不建议全自动依赖的内容

```text
1. 完全自动生成最终出版级作品
2. 无审核生成复杂真相链
3. 无人工确认生成关键反派
4. 无人工检查直接发布成稿
```

---

## 19.3 当前系统更适合

```text
1. 长篇原型生成
2. 故事结构演练
3. 章节草稿生产
4. 悬疑灵异创意探索
5. 多 seed 故事路线测试
6. 作者辅助创作
```

---

# 20. 推荐使用策略

## 20.1 最推荐

```text
半自动模式
```

即：

```text
用户给核心方向
系统生成骨架
用户审核
系统生产长篇
用户做最终取舍
```

---

## 20.2 不推荐

```text
完全不设定核心真相，直接开始模拟
```

原因：

```text
系统可能生成故事，但真相链容易松散，结局满意度不稳定。
```

---

## 20.3 最小必填信息

建议用户至少填写：

```text
1. 题材
2. 核心地点
3. 主角设定
4. 世界规则
5. 核心真相方向
6. 结局倾向
7. 目标字数 / 章节数
```

---

# 21. V1 内测版总结

V1 内测版已经具备：

```text
世界生成
角色生成
NPC 动态生成
线索生成
证据链管理
剧情弧管理
角色弧管理
恐怖灵异 Genre Pack
质量评估
自动修稿
悬念债务管理
全书蓝图
长篇生产调度
10 万字 LongRun
最终收束检查
成稿导出
```

它的核心闭环是：

```text
世界设定
↓
故事骨架
↓
角色模拟
↓
事件记录
↓
章节生成
↓
质量评估
↓
自动修稿
↓
悬念 / 证据 / 真相链更新
↓
全书生产
↓
最终收束
↓
导出成稿
```

一句话：

> 小说沙盘 V1 内测版是一个能够辅助作者完成悬疑灵异长篇故事原型生产的 AI 沙盘创作引擎。

它当前不是替代作者的“全自动出版系统”，而是：

```text
一个能独立演练、生成、修订并导出长篇小说草稿的 AI 创作生产系统。
```
