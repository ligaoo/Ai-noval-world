# 小说沙盘引擎 V3 版本迭代计划

> V3 主题：导演系统与长期叙事控制  
> V3 目标：从“可模拟、可生成”升级为“可控剧情推进、长期连续、人物弧光稳定”的小说沙盘引擎。

---

## 0. V3 背景

V2 已经实现：

```text
LLM Agent
多地点探索
move 动作
轻量记忆
LLM Narrative Writer
一致性检查
自动修订
```

V3 不应该继续盲目扩大地图、增加 Agent 数量或堆复杂动作。

V3 要解决的是 V2 之后最核心的几个问题：

```text
1. Agent 会行动，但剧情可能没有节奏
2. 多地点能跑，但故事可能变散
3. 记忆可用了，但人物成长不明显
4. 章节能生成，但长篇连续性还不稳定
5. 事件能回放，但缺少剧情因果管理
6. 线索能发现，但伏笔与回收不够可控
```

因此，V3 的核心不是“更多功能”，而是：

```text
故事控制能力
剧情推进能力
人物成长控制
伏笔回收能力
多章连续能力
```

---

## 1. V3 总目标

V3 要让系统具备以下能力：

```text
知道当前剧情处于哪个阶段
知道什么时候太平、太慢、太散
知道该投放什么环境压力
知道哪些真相现在不能暴露
知道人物应该如何逐渐变化
知道伏笔什么时候该埋、什么时候该回收
知道下一章应该继承哪些未解决问题
```

一句话概括：

> V3 要让小说沙盘引擎从“事件模拟器”升级为“故事推进器”。

---

## 2. V3 设计原则

### 2.1 Director 不能直接操控人物

错误做法：

```text
导演让林舟立刻去档案室发现真相。
```

正确做法：

```text
导演让大厅深处传来轻微金属声，开放搜索档案室入口的机会。
至于林舟去不去，由 Agent 自己决定。
```

Director 只能做：

```text
改变环境压力
开放线索机会
增加 NPC 压力
调整时间限制
制造关系触发点
提示可探索方向
```

Director 不能做：

```text
直接暴露真相
强行改变角色动机
替角色做决定
让角色获得未发现信息
让剧情跳过必要阶段
```

---

### 2.2 剧情推进必须符合 Plot Arc

所有关键线索都应绑定剧情阶段。

例如：

```text
setup 阶段：只能发现表层异常
investigation 阶段：可以发现中级线索
confrontation 阶段：可以发现重大线索
revelation 阶段：可以揭露核心真相
```

不能在 setup 阶段直接暴露最终真相。

---

### 2.3 人物变化必须渐进

人物不能因为一个事件突然大彻大悟。

人物变化应通过：

```text
event
belief change
relationship change
reflection
character arc progress
```

逐步推进。

---

### 2.4 多章连续依赖摘要，而不是全文塞上下文

每章结束后要生成：

```text
chapter_summary
open_threads
resolved_threads
new_facts
new_beliefs
character_changes
next_chapter_seeds
```

下一章只继承压缩后的结构化信息，而不是整章正文。

---

## 3. V3 模块总览

### 3.1 P0 必做模块

```text
TensionMonitor
DirectorService
InterventionService
PlotArcService
ChapterContinuityService
```

### 3.2 P1 推荐模块

```text
CharacterArcService
ReflectionMemoryService
ForeshadowingService
```

### 3.3 P2 后续增强

```text
多 POV
群像并行
半 Agent NPC
大规模长期记忆
复杂物品系统
```

---

## 4. V3 版本拆分

建议将 V3 拆成 6 个小版本：

```text
V3.1：TensionMonitor + DirectorService
V3.2：InterventionService
V3.3：PlotArcService
V3.4：ChapterContinuityService
V3.5：CharacterArcService + Reflection
V3.6：ForeshadowingService
```

开发优先级：

```text
先解决剧情卡住和没节奏
再解决剧情阶段控制
再解决多章连续
最后解决人物弧光和伏笔回收
```

---

# V3.1：TensionMonitor + DirectorService

## 1. 目标

让系统能够识别：

```text
剧情停滞
主线推进不足
冲突不足
悬念下降
危险感不足
人物关系无变化
事件重复
```

并给出导演干预建议。

---

## 2. TensionMonitor 评分维度

每个 tick 或每 N 个事件后，计算最近窗口内的剧情状态。

```text
progress_score：主线推进
mystery_score：悬念强度
conflict_score：冲突强度
danger_score：危险感
relationship_score：人物关系变化
novelty_score：新鲜度
emotion_score：人物情绪波动
```

---

## 3. EventLog 增强

每个 plot event 需要包含 plot_value。

```json
{
  "event_id": "evt_0031",
  "event_type": "discovery",
  "result": "林舟发现铁锁最近被更换过。",
  "plot_value": {
    "progress": 6,
    "mystery": 8,
    "conflict": 2,
    "danger": 1,
    "relationship": 0,
    "novelty": 5,
    "emotion": 4
  }
}
```

---

## 4. TensionReport

```json
{
  "simulation_id": "sim_001",
  "tick": 18,
  "window": "last_5_events",
  "scores": {
    "progress": 2.4,
    "mystery": 5.1,
    "conflict": 1.2,
    "danger": 0.5,
    "relationship": 0.0,
    "novelty": 2.0,
    "emotion": 2.6
  },
  "diagnosis": [
    "主线推进不足",
    "冲突偏低",
    "连续事件缺乏新信息"
  ],
  "recommended_intervention_types": [
    "environment_hint",
    "npc_pressure",
    "time_pressure"
  ]
}
```

---

## 5. DirectorService 输入

```json
{
  "simulation_id": "sim_001",
  "chapter_goal": "让林舟确认旧医院近期有人出入",
  "recent_events": ["evt_0012", "evt_0013", "evt_0014"],
  "plot_state": {
    "discovered_clues": ["hf_001"],
    "unresolved_questions": ["谁换了锁？", "看门人为什么隐瞒？"],
    "active_conflicts": ["林舟与看门人的互不信任"]
  },
  "tension_scores": {
    "mystery": 6,
    "conflict": 3,
    "danger": 2,
    "progress": 4,
    "novelty": 3
  },
  "world_rules": [
    "旧医院午夜后才会出现四楼",
    "看门人害怕惹事，不会主动说出完整真相"
  ]
}
```

---

## 6. DirectorService 输出

```json
{
  "need_intervention": true,
  "reason": "连续 4 个 tick 无新线索，冲突强度较低，章节目标推进不足。",
  "intervention_type": "environment_hint",
  "target_location": "hospital_lobby",
  "content": "大厅深处传来一声轻微金属响，像是某个柜门没有关紧。",
  "allowed_followup_actions": ["observe", "inspect", "search"],
  "forbidden_effects": [
    "不能直接暴露档案室真相",
    "不能让角色凭空知道是谁制造了声音"
  ]
}
```

---

## 7. V3.1 DoD

```text
1. 连续 5 tick 无 progress event 时，TensionMonitor 能识别停滞
2. conflict_score 过低时，能推荐 npc_pressure
3. danger_score 过低时，能推荐 danger_signal 或 time_pressure
4. Director 输出的 intervention proposal 不直接暴露核心真相
5. Director proposal 可被 InterventionService 消费
6. tension_reports.jsonl 可回放
```

---

# V3.2：InterventionService

## 1. 目标

将 Director 的干预建议转化为真实环境事件，并写入 EventLog。

---

## 2. V3.2 先实现 3 种干预

```text
environment_hint
npc_pressure
time_pressure
```

后续扩展：

```text
clue_exposure
relationship_trigger
danger_signal
```

---

## 3. environment_hint

适合剧情停滞时使用。

```json
{
  "type": "environment_hint",
  "location_id": "hospital_lobby",
  "description": "风穿过破窗，吹开前台后方一只半掩的抽屉。",
  "unlocked_routes": ["route_hf003_search_front_desk"],
  "visibility": ["char_linzho"]
}
```

效果：

```text
不直接发现线索
只开放新的可交互机会
让 Agent 可以自然选择 inspect/search
```

---

## 4. npc_pressure

适合冲突不足时使用。

```json
{
  "type": "npc_pressure",
  "actor": "char_guard",
  "target": "char_linzho",
  "description": "看门人忽然挡在楼梯口，语气比刚才更硬。",
  "effect": {
    "relationship_delta": -10,
    "available_topics_added": ["why_block_stairs"]
  }
}
```

效果：

```text
增加冲突
改变关系值
开放新的对话 topic
```

---

## 5. time_pressure

适合节奏拖沓时使用。

```json
{
  "type": "time_pressure",
  "description": "远处传来巡逻车的声音，林舟意识到自己不能在这里待太久。",
  "effect": {
    "remaining_ticks": 8,
    "risk_level_modifier": 10
  }
}
```

效果：

```text
压缩行动时间
提高风险
逼迫 Agent 做更明确选择
```

---

## 6. Intervention EventLog

```json
{
  "event_id": "evt_intervention_001",
  "event_type": "director_intervention",
  "intervention_type": "environment_hint",
  "location_id": "hospital_lobby",
  "result": "风吹开前台后方一只半掩的抽屉。",
  "visible_to": ["char_linzho"],
  "unlocked_routes": ["route_hf003_search_front_desk"],
  "plot_value": {
    "progress": 2,
    "mystery": 4,
    "conflict": 0,
    "danger": 1,
    "novelty": 3,
    "emotion": 2
  }
}
```

---

## 7. V3.2 DoD

```text
1. environment_hint 能解锁新的 route 或 target
2. npc_pressure 能改变 relationship 或新增 topic
3. time_pressure 能影响 remaining_ticks 或 risk_level
4. 干预必须进入 EventLog
5. AgentContext 能感知干预后的可见变化
6. 干预不能直接写入 discovered_facts
```

---

# V3.3：PlotArcService

## 1. 目标

让系统知道故事当前处于哪个阶段，并防止核心真相过早暴露。

---

## 2. plot_arcs.json

```json
{
  "arcs": [
    {
      "arc_id": "arc_hospital_truth",
      "name": "旧医院真相篇",
      "status": "active",
      "current_stage": "setup",
      "progress": 0,
      "stages": [
        {
          "stage_id": "setup",
          "purpose": "建立医院异常",
          "required_events": ["发现医院并非完全废弃"],
          "allowed_clue_levels": ["surface", "minor"],
          "forbidden_revelations": ["ten_years_truth", "real_killer_identity"]
        },
        {
          "stage_id": "investigation",
          "purpose": "收集旧案线索",
          "required_events": ["发现旧档案", "看门人露出破绽"],
          "allowed_clue_levels": ["surface", "minor", "medium"],
          "forbidden_revelations": ["real_killer_identity"]
        },
        {
          "stage_id": "confrontation",
          "purpose": "与隐瞒者产生正面冲突",
          "required_events": ["看门人承认有人让他封锁医院"],
          "allowed_clue_levels": ["surface", "minor", "medium", "major"],
          "forbidden_revelations": []
        },
        {
          "stage_id": "revelation",
          "purpose": "揭露部分真相",
          "required_events": ["主角发现自己十年前来过医院"],
          "allowed_clue_levels": ["surface", "minor", "medium", "major", "truth"]
        }
      ]
    }
  ]
}
```

---

## 3. clue 增加剧情阶段字段

```json
{
  "id": "hf_007",
  "name": "十年前的入院记录",
  "level": "major",
  "arc_id": "arc_hospital_truth",
  "allowed_stages": ["confrontation", "revelation"],
  "content": "林舟十年前曾在旧医院出现过。"
}
```

---

## 4. PlotArcService 职责

```text
1. 加载 plot_arcs.json
2. 判断当前 arc stage
3. 判断当前 stage 的目标是否达成
4. 推进到下一 stage
5. 给 Director 提供推荐方向
6. 给 AgentContext 注入章节目标
7. 限制当前阶段可发现的 clue level
8. 防止 revelation/truth 级信息过早暴露
```

---

## 5. PlotArc 与 EnvironmentEngine 的关系

EnvironmentEngine 在触发线索前，需要检查：

```text
clue.arc_id 是否匹配 active arc
clue.allowed_stages 是否包含 current_stage
clue.level 是否在 allowed_clue_levels 内
```

如果不满足：

```json
{
  "valid": true,
  "success": false,
  "result": "你注意到档案袋上似乎有熟悉的痕迹，但灰尘和光线让你无法确认。",
  "blocked_reason": "clue_not_allowed_in_current_stage"
}
```

注意：

```text
不能直接告诉用户“剧情阶段不允许发现”
只能返回符合小说环境的模糊结果
```

---

## 6. V3.3 DoD

```text
1. plot_arcs.json 可加载
2. 每个 clue 可绑定 arc_id / level / allowed_stages
3. setup 阶段不能发现 major/truth 级线索
4. stage required_events 满足后可推进阶段
5. Director 能基于当前 arc stage 选择干预方向
6. chapter_plan 能显示当前 arc_stage
```

---

# V3.4：ChapterContinuityService

## 1. 目标

支持多章连续，让下一章继承上一章的未解决问题、人物状态和伏笔状态。

---

## 2. 每章结束输出 chapter_summary

```json
{
  "chapter_id": "ch_001",
  "summary": "林舟进入旧医院入口区，发现铁锁最近被换过，并与看门人发生第一次冲突。",
  "new_facts": [
    "医院大门的锁最近更换过"
  ],
  "new_beliefs": [
    "林舟怀疑有人近期进入过医院"
  ],
  "open_threads": [
    "谁换了锁？",
    "看门人为什么隐瞒？",
    "医院是否与林舟的噩梦有关？"
  ],
  "resolved_threads": [],
  "character_changes": {
    "char_linzho": {
      "mental_state": "从迟疑转为怀疑",
      "goal_updated": "从确认梦境地点变为调查近期出入者"
    }
  },
  "next_chapter_seeds": [
    "调查大厅前台",
    "追问看门人锁的来源",
    "寻找旧医院档案"
  ]
}
```

---

## 3. ChapterContinuityService 职责

```text
1. 生成 chapter_summary
2. 维护 open_threads
3. 维护 resolved_threads
4. 更新下一章 chapter_goal
5. 压缩上一章内容，避免把全文塞进上下文
6. 检查下一章是否承接上一章状态
7. 防止 resolved_threads 被重复当成主悬念
```

---

## 4. 下一章上下文注入

下一章 AgentContext 应包含：

```json
{
  "previous_chapter_summary": "林舟发现旧医院的锁最近被换过，并开始怀疑看门人隐瞒了近期出入者。",
  "open_threads": [
    "谁换了锁？",
    "看门人为什么隐瞒？"
  ],
  "next_chapter_seeds": [
    "调查大厅前台",
    "追问看门人锁的来源"
  ]
}
```

---

## 5. V3.4 DoD

```text
1. 每章结束必须生成 chapter_summary
2. 下一章 AgentContext 必须包含 open_threads
3. 下一章 chapter_plan 必须承接至少 1 个 next_chapter_seed
4. resolved_threads 不能再次作为主悬念重复出现
5. 多章生成时人物 known_facts / beliefs 不丢失
6. 连续生成 3 章时主线不重置
```

---

# V3.5：CharacterArcService + Reflection

## 1. 目标

让人物不只是执行动作，而是能随着事件改变：

```text
信念
目标
关系
心理阶段
行动倾向
```

---

## 2. character_arcs.json

```json
{
  "characters": [
    {
      "character_id": "char_linzho",
      "arc": {
        "starting_state": "逃避过去，不愿相信自己的记忆有问题",
        "wound": "童年事故造成的记忆断裂",
        "false_belief": "只要不追究过去，就能正常生活",
        "desire": "摆脱噩梦",
        "need": "承认自己曾经逃避的真相",
        "current_stage": "avoidance",
        "stages": [
          {
            "stage": "avoidance",
            "description": "回避过去，只想快速确认梦境来源"
          },
          {
            "stage": "doubt",
            "description": "开始怀疑自己的记忆"
          },
          {
            "stage": "confrontation",
            "description": "被迫面对过去"
          },
          {
            "stage": "acceptance",
            "description": "承认真相并做出选择"
          }
        ]
      }
    }
  ]
}
```

---

## 3. Reflection 触发时机

满足任意条件可触发：

```text
发现重要线索
人物关系发生显著变化
章节结束
连续 N 个 plot event 后
人物目标发生变化
```

---

## 4. Reflection 输出

```json
{
  "agent_id": "char_linzho",
  "reflection": {
    "new_understanding": [
      "旧医院并非彻底废弃",
      "看门人至少隐瞒了近期有人出入的事实"
    ],
    "changed_beliefs": [
      {
        "from": "医院只是噩梦里的地点",
        "to": "医院可能与自己的过去有关"
      }
    ],
    "relationship_updates": [
      {
        "target": "char_guard",
        "attitude_delta": -15,
        "reason": "看门人多次回避关键问题"
      }
    ],
    "next_intentions": [
      "寻找近期出入医院的证据",
      "弄清看门人听命于谁"
    ]
  }
}
```

---

## 5. CharacterArcService 职责

```text
1. 根据事件影响更新人物弧光
2. 根据 reflection 更新 beliefs
3. 根据 relationship_updates 更新关系值
4. 根据 next_intentions 更新短期计划
5. 控制人物不会突然跳阶段
6. 给 AgentContext 注入当前 character_arc
7. 给 NarrativeWriter 提供心理变化依据
```

---

## 6. V3.5 DoD

```text
1. 角色每 N 个重要事件可生成一次 reflection
2. reflection 能更新 belief / relationship / next_intentions
3. CharacterArcService 能推进 current_stage
4. AgentContext 能注入当前 character_arc
5. NarrativeWriter 能根据 character_arc 写出连续心理变化
6. 角色不会每章像失忆一样重新行动
```

---

# V3.6：ForeshadowingService

## 1. 目标

管理伏笔的埋设、强化和回收，提高小说感。

---

## 2. foreshadowing 结构

```json
{
  "foreshadow_id": "fs_001",
  "name": "锁上的新划痕",
  "introduced_event_id": "evt_0012",
  "surface_meaning": "锁最近被换过",
  "hidden_meaning": "有人近期多次进入医院",
  "status": "planted",
  "planned_payoff_stage": "investigation",
  "payoff_conditions": [
    "发现档案室门锁同样有新划痕",
    "看门人承认有人让他换锁"
  ],
  "payoff_event_id": null
}
```

---

## 3. 伏笔状态

```text
planned
planted
reinforced
payoff_ready
paid_off
expired
```

---

## 4. ForeshadowingService 职责

```text
1. 根据关键 clue 自动登记伏笔
2. 根据后续事件判断伏笔是否被强化
3. 满足条件时标记 payoff_ready
4. chapter_plan 中提示可回收伏笔
5. NarrativeWriter 根据 chapter_plan 自然回收伏笔
6. paid_off 后不重复回收
7. 长时间未回收时进入 expired 或重新安排 payoff
```

---

## 5. chapter_plan 中引用伏笔

```json
{
  "chapter_id": "ch_003",
  "title": "档案室的第二把锁",
  "beats": [
    {
      "beat_id": "b002",
      "purpose": "发现第二个相似线索",
      "events": ["evt_0110"],
      "foreshadowing_payoff": ["fs_001"]
    }
  ]
}
```

---

## 6. V3.6 DoD

```text
1. 至少 1 个 clue 可自动生成 foreshadowing
2. 后续事件满足条件后状态变为 payoff_ready
3. chapter_plan 可引用 payoff_ready 的伏笔
4. NarrativeWriter 能在正文中自然回收
5. paid_off 后不重复回收
6. 连续 3 章内至少出现 1 次伏笔回收
```

---

# 5. V3 AgentContext 增强

在 V2 AgentContext 基础上，V3 需要增加：

```json
{
  "plot_context": {
    "current_arc": "旧医院真相篇",
    "arc_stage": "investigation",
    "chapter_goal": "找到近期有人进入医院的证据",
    "forbidden_revelations": [
      "不能直接知道十年前事故真相"
    ]
  },
  "character_arc": {
    "current_stage": "avoidance",
    "internal_conflict": "想查清噩梦来源，但害怕发现自己和医院有关"
  },
  "recent_reflections": [
    "看门人可能隐瞒了近期有人出入医院的事实"
  ],
  "soft_director_pressure": [
    "林舟感觉继续留在大厅并不安全，但档案室可能有答案。"
  ],
  "open_threads": [
    "谁换了锁？",
    "看门人为什么隐瞒？"
  ]
}
```

注意：

```text
soft_director_pressure 不是命令
forbidden_revelations 是约束
open_threads 是悬念继承
character_arc 是人物心理阶段
```

---

# 6. V3 章节生成流程

V3 不再只生成单章，而是支持多章连续。

```text
selected plot events
↓
plot arc state
↓
character arc state
↓
foreshadowing state
↓
previous chapter summary
↓
chapter_plan
↓
chapter_draft
↓
consistency_check
↓
continuity_summary
↓
update arc states
```

---

## chapter_plan 升级

```json
{
  "chapter_id": "ch_003",
  "title": "档案室的第二把锁",
  "pov": "char_linzho",
  "arc_stage": "investigation",
  "chapter_function": "推进主线并强化锁的伏笔",
  "beats": [
    {
      "purpose": "承接上一章的怀疑",
      "events": ["evt_0101", "evt_0102"]
    },
    {
      "purpose": "发现第二个相似线索",
      "events": ["evt_0110"],
      "foreshadowing_payoff": ["fs_001"]
    },
    {
      "purpose": "制造人物冲突",
      "events": ["evt_0117", "evt_0118"]
    }
  ],
  "emotional_curve": ["怀疑", "紧张", "确认异常", "被迫深入"],
  "ending_hook": {
    "source_event_id": "evt_0120",
    "text": "档案袋上的姓名，和林舟梦里听见的那个名字一样。"
  }
}
```

---

# 7. V3 输出目录

```text
outputs/sim_xxx/
  state.json
  events.jsonl
  memories.jsonl
  reflections.jsonl
  interventions.jsonl
  tension_reports.jsonl
  foreshadowings.jsonl
  chapter_summaries.jsonl
  agent_traces/
  chapters/
    ch_001_plan.json
    ch_001_draft.md
    ch_001_report.json
    ch_001_summary.json
    ch_002_plan.json
    ch_002_draft.md
    ch_002_report.json
    ch_002_summary.json
```

---

# 8. V3 Tick Loop

```text
Load WorldState
Load PlotArc / CharacterArc / Memory
↓
For each active character:
    Build AgentContext
    LLM decide ActionCommand
    Validate Action
    EnvironmentEngine.applyAction
    EventLog append
    MemoryService.write
    CharacterArcService.update
↓
TensionMonitor.evaluate
↓
DirectorService.decide_intervention
↓
If needed:
    InterventionService.apply
    EventLog append intervention
↓
ForeshadowingService.update
↓
ProgressMonitor.check_stop_condition
↓
If chapter end:
    Generate chapter_plan
    NarrativeWriter.generate
    ConsistencyCheck.run
    Revise once if needed
    ChapterContinuityService.summarize
    Update next chapter seeds
```

---

# 9. V3 开发里程碑

## Milestone 1：TensionMonitor + DirectorService

建议时间：3–5 天

实现：

```text
事件窗口评分
无进展判断
冲突不足判断
Director 输出 intervention proposal
tension_reports.jsonl
```

验收：

```text
连续 5 tick 无进展时，能生成合理干预建议
干预建议不会直接暴露隐藏真相
```

---

## Milestone 2：InterventionService

建议时间：3–5 天

实现：

```text
environment_hint
npc_pressure
time_pressure
interventions.jsonl
干预事件写入 EventLog
```

验收：

```text
干预能解锁新的 route 或 topic
Agent 能基于干预继续行动
```

---

## Milestone 3：PlotArcService

建议时间：4–6 天

实现：

```text
plot_arcs.json
arc stage
stage allowed clue levels
stage forbidden revelations
stage progress update
```

验收：

```text
系统不会在 setup 阶段提前暴露 revelation/truth 级线索
章节目标能根据 arc stage 自动变化
```

---

## Milestone 4：ChapterContinuityService

建议时间：3–5 天

实现：

```text
chapter_summaries.jsonl
open_threads
resolved_threads
next_chapter_seeds
下一章上下文继承
```

验收：

```text
连续生成 3 章时，主线不重置
下一章能承接上一章 open_threads
```

---

## Milestone 5：CharacterArcService + Reflection

建议时间：4–6 天

实现：

```text
character_arcs.json
reflection 生成
belief 更新
relationship 更新
next_intentions 更新
```

验收：

```text
角色会基于经历改变目标和态度
不会每章像失忆一样重新行动
```

---

## Milestone 6：ForeshadowingService

建议时间：4–6 天

实现：

```text
foreshadowings.jsonl
伏笔状态更新
payoff_ready 检测
chapter_plan 引用伏笔
```

验收：

```text
后续章节能引用并回收前文伏笔
paid_off 后不重复回收
```

---

# 10. V3 总 DoD

```text
1. 连续运行 10 次，每次 3 章，不崩溃
2. 每章至少有 1 个 progress event
3. 每章至少有 1 个 conflict 或 danger event
4. 连续 5 tick 无进展时，Director 必须介入
5. Director 干预不能直接新增核心真相
6. setup 阶段不能发现 revelation/truth 级线索
7. 每章结束必须生成 chapter_summary
8. 下一章必须继承上一章 open_threads
9. 至少 1 个伏笔能在后续章节被回收
10. 主角 relationship / belief / goal 至少发生一次变化
11. 连续 3 章生成时，主线、人物状态、已发现事实不能重置
12. ConsistencyCheck 仍能拦截新增事实、POV 泄露、事件结果篡改
```

---

# 11. V3 不建议做的内容

V3 暂时不要做：

```text
1. 十几个 Agent 并发
2. 完全开放世界
3. 复杂战斗系统
4. 复杂物品合成系统
5. 自动生成几十万字完整长篇
6. 大规模向量数据库
7. 多用户协作创作平台
8. 高复杂前端编辑器
```

这些建议放到 V4 或更后面。

V3 的重点是：

```text
导演系统
剧情弧
人物弧
伏笔回收
章节连续性
```

---

# 12. V3 最小可交付版本

如果要控制范围，V3 MVP 只做：

```text
1. TensionMonitor
2. DirectorService
3. InterventionService 三种干预
   - environment_hint
   - npc_pressure
   - time_pressure
4. PlotArcService
5. ChapterContinuityService
```

先不做完整人物弧光和伏笔系统也可以。

---

## V3 MVP 闭环

```text
V2 模拟
↓
连续无进展
↓
TensionMonitor 发现问题
↓
Director 选择干预
↓
InterventionService 投放环境提示
↓
Agent 接收到新可见信息
↓
剧情继续推进
↓
章节结束生成 summary
↓
下一章继承 open_threads
```

---

# 13. V3 完成后的后续方向

V3 完成后，可以进入 V4。

V4 可考虑：

```text
1. 多 POV 群像
2. 多 Agent 并行调度
3. 半 Agent NPC / 背景 NPC
4. 复杂物品系统
5. use/take/give/flee/hide/follow
6. 向量数据库长期记忆
7. 前端可视化回放
8. 世界编辑器
9. 剧情 Debug 面板
10. 多章节自动连载生成
```

---

# 14. V3 一句话总结

V3 要实现的不是“更多 Agent”或者“更大地图”，而是：

> 让系统拥有故事控制能力。

即：

```text
知道剧情现在在哪
知道剧情什么时候卡住
知道该如何轻量干预
知道真相什么时候能暴露
知道人物如何逐步变化
知道伏笔如何埋设和回收
知道下一章如何承接上一章
```
