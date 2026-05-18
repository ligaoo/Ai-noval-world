# 小说沙盘引擎 V4 开发计划

> V4 主题：从“可调试引擎”升级为“创作平台雏形”  
> V4 目标：在 V3.5 已具备调试、回放、重跑、配置校验能力的基础上，引入世界配置工作台、多 Agent 群像、NPC 分层、物品交互、多 POV 章节生成与人工干预工作流。

---

## 0. V4 定位

V1–V3.5 的路线：

```text
V1：最小闭环
V2：LLM Agent + 多地点 + 轻量记忆
V3：导演系统 + 剧情弧 + 人物弧 + 章节连续
V3.5：Debug / 回放 / 配置校验 / 重跑 / 指标统计
```

V4 的定位：

```text
从“小说沙盘引擎”走向“小说创作平台雏形”
```

V4 不只是继续增强引擎能力，而是开始解决创作者实际使用的问题：

```text
1. 世界配置太工程化，普通用户难以上手
2. 多角色群像能力不足
3. NPC 不应该全部走完整 Agent
4. 缺少人工干预与创作控制
5. 缺少可视化地图、时间线和章节编辑
6. 多 POV 和多角色可见性边界需要更强支持
7. 物品交互与状态变化还不完整
```

一句话：

> V4 要让人类创作者能够创建、观察、干预、修正并持续使用这个 AI 小说世界。

---

## 1. V4 总目标

V4 完成后，系统应具备：

```text
1. 可视化或半可视化创建世界、角色、地点、线索、剧情弧
2. 支持 5–10 个角色参与模拟
3. 支持 Core Agent / Full NPC / Semi-Agent / Reactive NPC / Background NPC 分层
4. 支持多 Agent 调度，不必每 tick 激活所有角色
5. 支持基础物品系统与 take / give / use / drop / unlock
6. 支持单章单 POV、单章多 POV、章节 POV 轮换
7. 支持暂停、人工干预、标记事件、编辑章节计划、重跑
8. 支持 EventLog 时间线、地图视图、角色状态、线索板、章节编辑
9. 所有人工操作可记录、可回放、可重跑
10. 一致性检查覆盖多 Agent 可见性、物品、POV、人工干预影响
```

---

## 2. V4 核心原则

### 2.1 人类创作者优先

V1–V3.5 更偏引擎内部能力。V4 开始要让创作者能用。

因此 V4 的核心不是：

```text
让系统自动生成更多东西
```

而是：

```text
让创作者能创建、检查、控制、修正、复用生成过程
```

### 2.2 引擎边界不能破坏

V4 增加人工干预，但不能破坏已有核心边界：

```text
Agent 仍只输出结构化动作
EnvironmentEngine 仍是事实判定者
EventLog 仍是小说改写的唯一事实来源
NarrativeWriter 仍不能新增事实
ConsistencyCheck 仍需要兜底
```

人工干预也必须进入日志：

```text
control_commands.jsonl
```

保证可回放和可追踪。

### 2.3 不要一上来做完整 SaaS

V4 是创作平台雏形，不是成熟商业平台。

暂时不做：

```text
多用户权限
在线协作
支付系统
发布市场
复杂运营后台
移动端 App
```

---

## 3. V4 模块总览

### 3.1 P0 必做模块

```text
V4.1 World Studio 世界配置工作台
V4.2 Multi-Agent Scheduler 多 Agent 调度
V4.6 Human-in-the-loop 人工干预与创作控制台
```

### 3.2 P1 推荐模块

```text
V4.3 NPC Layer NPC 分层系统
V4.5 Multi-POV Narrative 多视角章节生成
```

### 3.3 P2 可后置模块

```text
V4.4 Inventory & Object Interaction 物品与动作系统
```

---

## 4. V4 版本拆分

```text
V4.1：World Studio 世界配置工作台
V4.2：Multi-Agent Scheduler 多 Agent 调度
V4.3：NPC Layer NPC 分层系统
V4.4：Inventory & Object Interaction 物品与动作系统
V4.5：Multi-POV Narrative 多视角章节生成
V4.6：Human-in-the-loop 人工干预与创作控制台
```

推荐开发顺序：

```text
1. V4.1 World Studio
2. V4.6 Human-in-the-loop
3. V4.2 Multi-Agent Scheduler
4. V4.3 NPC Layer
5. V4.5 Multi-POV Narrative
6. V4.4 Inventory & Object Interaction
```

说明：

```text
先让创作者能配置和干预
再扩展多角色能力
再优化 NPC 成本
再提升叙事表现
最后补充复杂物品状态
```

---

# V4.1 World Studio 世界配置工作台

## 1. 目标

将手写 JSON 配置升级为可编辑、可校验、可预览的创作工作台。

V3.5 已有 ConfigValidator，但用户仍需要手写：

```text
world_bible.json
map.json
characters.json
clues.json
plot_arcs.json
character_arcs.json
foreshadowings.json
```

V4.1 要解决配置门槛问题。

---

## 2. 核心功能

```text
1. World Overview 世界总览
2. Character Editor 角色卡编辑器
3. Location / Map Editor 地点与地图编辑器
4. Clue & Route Editor 线索与发现路径编辑器
5. Plot Arc Editor 剧情弧编辑器
6. Character Arc Editor 人物弧编辑器
7. Validation Panel 配置校验面板
8. Import / Export 导入导出
9. Demo World Generator 示例世界生成
```

---

## 3. 页面设计

### 3.1 World Overview

显示：

```text
world_id
title
genre
tone
era
rules
themes
配置完整度
校验错误数量
最近一次 simulation 状态
```

World Bible 示例：

```json
{
  "world_id": "dark_city_001",
  "title": "旧医院真相",
  "genre": "悬疑灵异",
  "tone": "克制、压抑、现实中透出诡异",
  "era": "现代都市",
  "rules": [
    "旧医院午夜后才会出现四楼",
    "看门人害怕惹事，不会主动说出完整真相"
  ],
  "themes": [
    "记忆是否可靠",
    "人如何逃避愧疚"
  ]
}
```

---

### 3.2 Character Editor

字段：

```text
character_id
name
role
traits
goals
fears
secrets
skills
initial_location
known_facts
relationships
activation_policy
agent_type
```

示例：

```json
{
  "character_id": "char_linzho",
  "name": "林舟",
  "role": "protagonist",
  "agent_type": "core_agent",
  "traits": ["克制", "敏感", "逃避冲突"],
  "goals": {
    "short_term": "确认旧医院是否与噩梦有关",
    "long_term": "找回童年事故的真相"
  },
  "skills": {
    "observation": 75,
    "social": 40,
    "courage": 35,
    "logic": 70
  },
  "initial_location": "old_hospital_gate"
}
```

---

### 3.3 Location / Map Editor

功能：

```text
新增地点
编辑地点公开描述
编辑地点隐藏状态
配置 connected_to
配置 objects
配置 available_topics
配置 danger_level
配置 time_effects
地图可达性检查
```

可视化建议：

```text
节点 = location
边 = connected_to
节点颜色 = danger_level
边状态 = locked / open / conditional
```

地点示例：

```json
{
  "location_id": "hospital_lobby",
  "name": "医院大厅",
  "public_description": "大厅里落满灰尘，前台后方有一排旧柜子。",
  "connected_to": ["old_hospital_gate", "archive_room"],
  "objects": ["front_desk", "old_cabinet", "stairs"],
  "available_topics": ["hospital_history", "archive_room"],
  "danger_level": 2
}
```

---

### 3.4 Clue & Route Editor

每个 clue 配置：

```text
clue_id
name
content
level
arc_id
allowed_stages
importance
discover_routes
after_discovered effects
```

每个 route 配置：

```text
route_id
action_type
target
location_id
topic
required_skill
difficulty
required_stage
result
status
```

示例：

```json
{
  "clue_id": "hf_001",
  "name": "最近更换的铁锁",
  "content": "医院大门的锁最近被换过。",
  "level": "minor",
  "arc_id": "arc_hospital_truth",
  "allowed_stages": ["setup", "investigation"],
  "discover_routes": [
    {
      "route_id": "route_hf001_inspect_lock",
      "action_type": "inspect",
      "target": "hospital_gate_lock",
      "location_id": "old_hospital_gate",
      "required_skill": "observation",
      "difficulty": 60,
      "result": "锁芯比锁身干净得多，像是最近刚换过。"
    }
  ]
}
```

编辑器提示：

```text
该线索只有 1 条 discover_route，容易卡死
该 route 的 target 不存在
该 route 所在地点不可达
该 clue 为 major，但 setup 阶段可发现，有剧透风险
```

---

### 3.5 Plot Arc Editor

支持编辑：

```text
arc_id
name
current_stage
stages
allowed_clue_levels
required_clues
required_events
forbidden_revelations
```

---

### 3.6 Character Arc Editor

V4.1 可以先支持轻量人物弧：

```text
starting_state
current_stage
beliefs
relationships
current_intention
```

后续扩展完整人物弧：

```text
wound
false_belief
desire
need
acceptance
```

---

### 3.7 Validation Panel

集成 V3.5 ConfigValidator。

展示：

```text
errors
warnings
suggestions
定位到具体文件、字段、对象
一键跳转编辑
```

---

## 4. V4.1 DoD

```text
1. 可以创建 world / character / location / clue / plot_arc
2. 可以导入现有 JSON 配置
3. 可以导出标准 world 文件夹
4. 修改配置后实时或手动运行 ConfigValidator
5. 地图可视化显示地点连通性
6. clue route 可视化显示发现路径
7. 配置错误能定位到具体字段
8. 支持一键生成 demo world
9. 导出的配置可直接被 SimulationRunner 使用
```

---

# V4.2 Multi-Agent Scheduler 多 Agent 调度

## 1. 目标

支持更多重要角色异步行动，但避免每 tick 激活所有 Agent 导致成本爆炸和行为混乱。

V4.2 支持：

```text
5–10 个角色参与模拟
核心角色持续行动
重要 NPC 条件激活
背景 NPC 不进入主循环
反派可以在主角不可见处行动
不同角色只记住自己可见事件
```

---

## 2. 角色激活类型

```text
always：每 tick 激活，主角适用
conditional：满足条件激活，重要 NPC 适用
reactive：被交互时激活
scheduled：按时间点激活
manual：人工指定激活
```

---

## 3. activation_policy

```json
{
  "character_id": "char_guard",
  "activation_policy": {
    "type": "conditional",
    "conditions": [
      "same_location_with_protagonist",
      "mentioned_by_event",
      "has_pending_plan",
      "director_requested"
    ],
    "cooldown_ticks": 2,
    "priority": 60
  }
}
```

---

## 4. Scheduler 输出

```json
{
  "tick": 20,
  "active_agents": [
    {
      "character_id": "char_linzho",
      "reason": "always",
      "priority": 100
    },
    {
      "character_id": "char_guard",
      "reason": "same_location_with_protagonist",
      "priority": 60
    }
  ],
  "skipped_agents": [
    {
      "character_id": "char_villain",
      "reason": "cooldown"
    }
  ]
}
```

---

## 5. 多 Agent Tick Loop

```text
Load WorldState
↓
Scheduler.select_active_agents
↓
按 priority 排序
↓
For each active agent:
    Build local AgentContext
    Agent decide ActionCommand
    ActionValidator
    EnvironmentEngine.applyAction
    EventLog append visible_to
    MemoryService.write only visible events
    CharacterArcService.update
↓
ActionConflictResolver.resolve if needed
↓
Director / PlotArc / Continuity update
```

---

## 6. Action Conflict Resolver

需要处理：

```text
same_target_conflict
location_collision
conversation_collision
resource_conflict
contradictory_action
```

示例：

```json
{
  "conflict_type": "same_target_conflict",
  "actions": ["act_001", "act_002"],
  "resolution": "priority_then_speed",
  "winner": "char_linzho",
  "loser_result": "你伸手时，发现档案袋已经被别人拿走了。"
}
```

---

## 7. visible_to 规则

每条 EventLog 必须明确：

```text
哪些角色看见了
哪些角色听见了
哪些角色事后得知
哪些角色完全不知道
```

示例：

```json
{
  "event_id": "evt_0088",
  "event_type": "villain_action",
  "actors": ["char_villain"],
  "location_id": "archive_room",
  "result": "陈砚取走了档案袋。",
  "visible_to": ["char_villain"],
  "hidden_from": ["char_linzho", "char_guard"]
}
```

---

## 8. V4.2 DoD

```text
1. 支持 5–10 个角色配置
2. 每 tick 不必激活所有角色
3. 支持 always / conditional / reactive / scheduled / manual 激活策略
4. Scheduler 输出 active_agents 和 skipped_agents
5. EventLog 正确记录 visible_to / hidden_from
6. 不同角色只能记住自己可见事件
7. 支持同 tick 动作冲突检测
8. 反派可以在主角不可见地点行动
9. 可以回放每个角色的行动轨迹
10. MetricsCollector 能统计每个角色的激活次数和成本
```

---

# V4.3 NPC Layer 分层系统

## 1. 目标

建立 NPC 分层，避免所有 NPC 都走完整 Agent，降低成本并提高可控性。

---

## 2. NPC 类型

```text
core_agent
full_npc_agent
semi_agent_npc
reactive_npc
background_npc
```

---

## 3. 类型说明

### 3.1 core_agent

主角、反派、核心配角。

特点：

```text
完整记忆
完整目标
主动行动
人物弧光
反思
```

### 3.2 full_npc_agent

重要 NPC，例如看门人、记者、警察。

特点：

```text
有目标
有记忆
可主动行动
激活频率低于 core_agent
```

### 3.3 semi_agent_npc

有固定知识、态度、触发条件。

配置示例：

```json
{
  "npc_id": "npc_old_nurse",
  "type": "semi_agent_npc",
  "name": "老护士",
  "personality": "谨慎、怕事、对旧医院心存恐惧",
  "knows": [
    {
      "fact_id": "hf_008",
      "reveal_condition": {
        "relationship_min": 20,
        "topic": "old_fire",
        "required_stage": "investigation"
      }
    }
  ],
  "default_behavior": "avoid_talking",
  "response_style": "含糊、回避、偶尔说漏嘴"
}
```

### 3.4 reactive_npc

只在被交互时响应。

特点：

```text
不会主动行动
无完整长期记忆
通过 topic-based dialogue 返回信息
```

### 3.5 background_npc

纯氛围 NPC。

特点：

```text
不进入 Agent 调度
不进入主剧情因果链
只作为环境描述或 crowd reaction
```

---

## 4. NPC Response Engine

针对 semi_agent_npc / reactive_npc，不走完整 Agent 决策，而是用响应引擎。

输入：

```text
NPC profile
当前 topic
reveal_condition
relationship
plot_stage
asker
world rules
```

输出：

```text
reveal
evade
lie
refuse
hint
```

输出示例：

```json
{
  "response_type": "evade",
  "dialogue": "老护士低头整理袖口，只说那场火早就过去了。",
  "revealed_facts": [],
  "relationship_delta": -2,
  "available_topics_added": ["old_fire_detail"]
}
```

---

## 5. reveal_condition

```json
{
  "fact_id": "hf_008",
  "reveal_condition": {
    "topic": "old_fire",
    "relationship_min": 20,
    "required_stage": "investigation",
    "required_known_facts": ["hf_003"],
    "required_skill": "social",
    "difficulty": 55
  }
}
```

---

## 6. V4.3 DoD

```text
1. NPC 支持 core/full/semi/reactive/background 类型
2. Scheduler 根据 NPC 类型决定是否激活
3. semi_agent_npc 支持 knows / reveal_condition
4. reactive_npc 支持 topic-based response
5. background_npc 不进入模拟主循环
6. NPC Response Engine 支持 reveal / evade / lie / refuse / hint
7. 线索可绑定 NPC reveal_condition
8. NPC 回复不能越过 PlotArc 阶段锁
9. MetricsCollector 能统计 NPC 调用成本
```

---

# V4.4 Inventory & Object Interaction 物品与动作系统

## 1. 目标

补齐基础物品系统，让角色能拿取、交付、使用物品，并让物品改变世界状态。

---

## 2. 新增动作

```text
take
give
use
drop
unlock
```

可后置：

```text
combine
equip
consume
```

---

## 3. Object 数据结构

```json
{
  "object_id": "rusty_key",
  "name": "生锈的钥匙",
  "location_id": "hospital_lobby",
  "visible": false,
  "portable": true,
  "owner": null,
  "state": {
    "condition": "rusty",
    "used": false
  },
  "discover_routes": ["route_find_key_front_desk"],
  "use_effects": [
    {
      "action": "unlock",
      "target": "archive_room_door",
      "effect": "set_unlocked"
    }
  ]
}
```

---

## 4. Inventory

```json
{
  "character_id": "char_linzho",
  "items": [
    {
      "object_id": "rusty_key",
      "acquired_event_id": "evt_0044",
      "visible_to": ["char_linzho"]
    }
  ]
}
```

---

## 5. use 判定

EnvironmentEngine 检查：

```text
actor 是否拥有 item
target 是否在当前地点
item 是否可用于 target
PlotArc 当前阶段是否允许
是否需要技能检定
是否触发状态变化
```

示例：

```json
{
  "action_type": "use",
  "item": "rusty_key",
  "target": "archive_room_door"
}
```

结果：

```json
{
  "success": true,
  "result": "钥匙在锁孔里卡了一下，随后门锁发出一声轻响。",
  "state_changes": [
    {
      "op": "set",
      "path": "locations.archive_room_door.locked",
      "value": false
    }
  ],
  "unlocked_routes": ["route_enter_archive_room"]
}
```

---

## 6. 一致性检查增强

需要拦截：

```text
角色使用未拥有物品
角色拿取不可见物品
角色在错误地点使用物品
物品状态被 NarrativeWriter 擅自改变
正文出现未配置物品
```

---

## 7. V4.4 DoD

```text
1. 支持 portable object
2. 支持角色 inventory
3. 支持 take / give / use / drop / unlock
4. use 能改变 object/location state
5. 物品使用可以解锁 route
6. AgentContext 能看到自己 inventory
7. EventLog 能记录物品流转
8. NarrativeWriter 能正确写物品行为
9. ConsistencyCheck 能拦截“角色使用未拥有物品”
```

---

# V4.5 Multi-POV Narrative 多视角章节生成

## 1. 目标

支持多 POV 章节，让群像小说、反派视角、交叉剪辑更自然。

---

## 2. POV 模式

```text
single_pov：单章单 POV
multi_pov：单章多 POV
rotating_pov：章节轮换 POV
intercut：交叉剪辑
```

---

## 3. POVSelector

选择 POV 的依据：

```text
谁经历了最多关键事件
谁的情绪变化最大
谁知道的信息最适合保持悬念
谁的 POV 不会泄露过多真相
当前章节是否需要反派视角
PlotArc 当前阶段是否允许该 POV
```

---

## 4. ChapterPlan 增强

```json
{
  "chapter_id": "ch_004",
  "title": "档案室的灯",
  "pov_mode": "multi_pov",
  "sections": [
    {
      "section_id": "sec_001",
      "pov": "char_linzho",
      "events": ["evt_0101", "evt_0102"],
      "forbidden_information": ["char_villain_plan"],
      "allowed_facts": ["hf_001", "hf_003"]
    },
    {
      "section_id": "sec_002",
      "pov": "char_villain",
      "events": ["evt_0105", "evt_0106"],
      "forbidden_information": ["protagonist_current_location"],
      "allowed_facts": ["villain_knows_archive_missing"]
    }
  ]
}
```

---

## 5. POV 信息边界

每个 section 必须限制：

```text
该角色知道什么
该角色不知道什么
不能写其他角色内心
不能泄露其他地点不可见事件
不能把读者不该知道的真相提前写出
```

---

## 6. ConsistencyCheck 增强

按 section 检查：

```text
POV 角色是否可见该事件
POV 角色是否知道该事实
是否写了其他角色内心
是否泄露 forbidden_information
是否改变事件顺序
```

---

## 7. V4.5 DoD

```text
1. 支持 chapter_pov_mode
2. 支持 POVSelector
3. chapter_plan 能拆分 sections
4. 每个 section 有独立 allowed_facts / forbidden_information
5. NarrativeWriter 能生成多 POV 章节
6. ConsistencyCheck 能按 section 检查 POV 泄露
7. 支持反派短章但不破坏悬念
8. 支持章节 POV 轮换策略
```

---

# V4.6 Human-in-the-loop 人工干预与创作控制台

## 1. 目标

让用户可以参与创作，而不是只能全自动跑。

用户应能：

```text
暂停模拟
查看当前状态
指定下一章目标
锁定某个线索
解锁某个 route
强制某个角色出现
要求某个 NPC 提供模糊提示
重跑某一段
编辑 chapter_plan
修改 chapter_draft
标记某个事件必须进入正文
标记某个事件禁止进入正文
```

---

## 2. 人工干预类型

```text
pause_simulation
resume_simulation
set_chapter_goal
force_character_location
force_intervention
lock_clue
unlock_clue_route
mark_event_must_include
mark_event_exclude
edit_chapter_plan
rerun_from_tick
rewrite_chapter
```

---

## 3. ControlCommand

```json
{
  "command_id": "cmd_001",
  "type": "set_chapter_goal",
  "simulation_id": "sim_001",
  "chapter_id": "ch_003",
  "payload": {
    "chapter_goal": "让林舟发现档案室里有人近期翻动过旧案资料"
  },
  "created_by": "user",
  "created_at": "2026-05-16T00:00:00+08:00"
}
```

---

## 4. Event Annotation

```json
{
  "event_id": "evt_0042",
  "annotations": {
    "must_include_in_chapter": true,
    "exclude_from_narrative": false,
    "user_note": "这个线索很重要，必须写进正文。"
  }
}
```

---

## 5. Chapter Plan 编辑

用户可编辑：

```text
章节标题
POV
beats
ending_hook
must_include_events
forbidden_events
tone
word_count
```

编辑后的 plan 要再次通过：

```text
ConsistencyCheck
ContinuityCheck
POVCheck
```

---

## 6. 人工干预日志

所有人工操作必须记录：

```text
control_commands.jsonl
```

原因：

```text
保证可回放
保证重跑时可复现
保证调试可追踪
```

---

## 7. 重跑策略

重跑时支持：

```text
replay_control_commands = true
replay_control_commands = false
replay_control_commands_until_tick = N
```

---

## 8. V4.6 DoD

```text
1. 支持暂停/继续 simulation
2. 支持设置下一章 chapter_goal
3. 支持标记 event must_include / exclude
4. 支持锁定/解锁 clue route
5. 支持编辑 chapter_plan
6. 支持从人工修改点重跑
7. 所有人工操作写入 control_commands.jsonl
8. 重跑时可选择是否重放人工操作
9. 人工编辑后的 chapter_plan 会重新通过一致性检查
10. 人工干预能被 EventReplayService 回放
```

---

# 5. V4 输出目录建议

```text
outputs/sim_xxx/
  run_manifest.json
  run_status.json
  run_index.json

  state.json
  state_snapshots/

  events.jsonl
  control_commands.jsonl

  agent_traces/
  director_traces/

  chapters/
    ch_001_plan.json
    ch_001_draft.md
    ch_001_report.json
    ch_001_summary.json
    ch_001_user_edits.json

  annotations/
    event_annotations.jsonl
    clue_annotations.jsonl

  metrics.json
  tuning_report.md
```

---

# 6. V4 项目配置目录建议

```text
worlds/dark_city_001/
  world_bible.json
  map.json
  characters.json
  npcs.json
  clues.json
  objects.json
  plot_arcs.json
  character_arcs.json
  pov_rules.json
```

---

# 7. V4 最小 UI 页面建议

如果 V4 开始做前端，建议最小页面：

```text
/projects
/projects/{id}/world
/projects/{id}/characters
/projects/{id}/map
/projects/{id}/clues
/projects/{id}/simulation
/projects/{id}/timeline
/projects/{id}/chapters
/projects/{id}/debug
```

---

## 7.1 Project List

```text
项目列表
创建新项目
导入项目
最近运行
运行状态
```

## 7.2 World Studio

```text
世界设定编辑
规则编辑
主题编辑
配置校验
导入导出
```

## 7.3 Character Editor

```text
角色卡编辑
Agent 类型设置
技能设置
目标设置
关系设置
激活策略设置
```

## 7.4 Map View

```text
地点节点图
地点详情
objects
connected_to
danger_level
active routes
```

## 7.5 Clue Board

```text
线索列表
线索等级
所属 arc
允许阶段
发现路径
是否已发现
是否被锁定
```

## 7.6 Simulation Runner

```text
启动模拟
暂停模拟
继续模拟
当前 tick
当前章节
active agents
当前状态
```

## 7.7 Timeline

```text
EventLog 时间线
按角色过滤
按地点过滤
按事件类型过滤
查看单事件详情
查看因果链
```

## 7.8 Chapter Editor

```text
chapter_plan 查看和编辑
chapter_draft 查看和编辑
consistency_report
must_include / exclude event
重写章节
```

## 7.9 Debug Panel

```text
Agent Trace
Director Trace
State Snapshot
Metrics
Tuning Report
Run Diff
```

---

# 8. V4 API 建议

如果提供 HTTP API，可以按资源设计：

```text
GET    /projects
POST   /projects
GET    /projects/{projectId}

GET    /projects/{projectId}/world
PUT    /projects/{projectId}/world

GET    /projects/{projectId}/characters
POST   /projects/{projectId}/characters
PUT    /projects/{projectId}/characters/{characterId}

GET    /projects/{projectId}/locations
POST   /projects/{projectId}/locations
PUT    /projects/{projectId}/locations/{locationId}

GET    /projects/{projectId}/clues
POST   /projects/{projectId}/clues
PUT    /projects/{projectId}/clues/{clueId}

POST   /projects/{projectId}/validate

POST   /projects/{projectId}/simulations
POST   /simulations/{simulationId}/run
POST   /simulations/{simulationId}/pause
POST   /simulations/{simulationId}/resume

GET    /simulations/{simulationId}/events
GET    /simulations/{simulationId}/state
GET    /simulations/{simulationId}/timeline
GET    /simulations/{simulationId}/chapters

POST   /simulations/{simulationId}/commands
POST   /simulations/{simulationId}/rerun
```

---

# 9. V4 一致性检查增强

V4 新增后，需要检查更多类型：

```text
多 Agent 可见性
NPC reveal_condition
物品拥有权
物品位置
物品状态
POV section 信息边界
人工修改后的计划合法性
must_include / exclude 冲突
```

---

## 9.1 多 Agent 可见性

检查正文是否写了 POV 角色不可见事件。

## 9.2 NPC reveal_condition

检查 NPC 是否透露了当前阶段不允许的信息。

## 9.3 物品一致性

检查：

```text
角色是否拥有该物品
物品是否在正确地点
物品状态是否被擅自改变
物品是否已被其他角色拿走
```

## 9.4 人工干预一致性

检查：

```text
用户强制目标是否存在
用户锁定 clue 后是否仍被发现
must_include 与 exclude 是否冲突
人工编辑 chapter_plan 是否引用不存在 event
```

---

# 10. V4 Metrics 增强

新增指标：

```json
{
  "multi_agent": {
    "active_agent_count_avg": 3.2,
    "activation_count_by_agent": {
      "char_linzho": 50,
      "char_guard": 18,
      "char_villain": 9
    },
    "conflict_resolution_count": 3
  },
  "npc": {
    "full_agent_calls": 20,
    "semi_agent_calls": 12,
    "reactive_npc_calls": 18,
    "background_npc_events": 7
  },
  "human_control": {
    "control_command_count": 6,
    "manual_chapter_plan_edits": 2,
    "rerun_after_manual_edit": 1
  },
  "inventory": {
    "items_discovered": 4,
    "items_used": 2,
    "invalid_item_actions": 1
  },
  "pov": {
    "multi_pov_chapters": 2,
    "pov_leak_violations": 1
  }
}
```

---

# 11. V4 总 DoD

```text
1. 用户可以通过工作台创建和编辑 world / character / location / clue / plot_arc
2. 支持导入导出现有 JSON 世界配置
3. 配置编辑后可运行 ConfigValidator
4. 系统支持 5–10 个角色，其中部分为完整 Agent，部分为 NPC
5. Scheduler 能按激活策略运行多 Agent
6. NPC 支持 core/full/semi/reactive/background 类型
7. 支持基础物品系统和 take / give / use / drop / unlock
8. 支持单章单 POV / 多 POV / POV 轮换
9. 用户可以暂停、继续、干预 simulation
10. 用户可以标记 event must_include / exclude
11. 用户可以编辑 chapter_plan
12. EventLog 可以以时间线形式查看
13. 地图和角色位置可以可视化查看
14. 所有人工干预可记录、可回放、可重跑
15. 一致性检查覆盖物品、POV、多 Agent 可见性、人工干预影响
```

---

# 12. V4 MVP 建议

如果控制范围，V4 MVP 只做：

```text
V4.1 World Studio 简化版
V4.2 Multi-Agent Scheduler 简化版
V4.6 Human-in-the-loop 简化版
```

---

## V4 MVP 功能范围

```text
1. 简单 UI 或 CLI 表单编辑 world / character / location / clue
2. 运行 5 个角色：
   - 2 个 core/full Agent
   - 3 个 reactive NPC
3. 支持暂停 / 继续 simulation
4. 支持设置下一章 chapter_goal
5. 支持标记事件 must_include / exclude
6. 支持查看 EventLog 时间线
7. 支持从指定 tick 重跑
8. 支持生成连续 3 章
```

---

## V4 MVP DoD

```text
1. 能编辑基础世界配置并导出
2. 能通过 ConfigValidator
3. 能运行 5 个角色
4. 能暂停和继续
5. 能人工设置下一章目标
6. 能标记事件进入或排除正文
7. 能查看时间线
8. 能从指定 tick 重跑
9. 能生成连续 3 章且不丢失主线
```

---

# 13. V4 不建议做的内容

V4 暂时不要做：

```text
1. 完整商业化 SaaS
2. 多人实时协作
3. 支付系统
4. 发布市场
5. 复杂经济系统
6. 大型游戏式战斗系统
7. 自动生成百万字长篇
8. 多模态漫画 / 视频生成
9. 移动端 App
```

---

# 14. V4 完成后的项目进度

V4 完成后，项目大致达到：

```text
核心引擎：80%–85%
小说生成系统：75%
创作工具：60%–70%
可商用产品：60%左右
成熟平台：45%–50%
```

---

# 15. V4 一句话总结

V4 的重点不是让模型更会写，而是：

> 让人类创作者能够控制这个 AI 小说世界。

V1–V3.5 解决的是：

```text
AI 世界能不能自己跑
```

V4 解决的是：

```text
人能不能创建、观察、干预、修正、使用这个世界
```
