# 需求文档：Agent 自驱交互沙盘系统

> 模块目标：实现“角色 Agent 自主行动 + Agent 间多轮交互 + 世界结果判定 + Director 纠偏 + Writer 文学化”的小说沙盘核心循环。  
> 适用版本：V1 内测版核心增强 / V1.1 Agent Sandbox Core  
> 核心定位：系统不是替用户写剧情，而是让角色在世界中自行产生事件，最后由 Writer 总结成小说。

---

## 1. 背景与目标

当前系统存在的问题：

```text
1. Agent 容易像 NPC，只负责吐露信息。
2. 角色缺少自我目标、隐瞒、怀疑、冲突。
3. Agent 间交互结果不清晰，谁知道什么、谁怀疑什么容易混乱。
4. Director 过度像编剧，容易直接投放线索。
5. Writer 权力过大，容易凭空编剧情，而不是文学化真实事件。
6. “谁在场、谁听见、谁看见、谁偷听”没有成为剧情状态的一部分。
```

本需求要解决：

```text
1. 角色 Agent 自己决定要做什么。
2. Agent 能沟通、隐瞒、撒谎、追问、质疑、合作、冲突。
3. Agent 的行为一定发生，但行为带来的社会结果、信息暴露、信任变化由系统判定。
4. InteractionResolver 负责判定交互结果。
5. ScenePresenceTracker 负责判断谁在场、谁可见、谁可听。
6. Director 只负责纠偏、防崩、保底，不负责直接写剧情。
7. Writer 只根据结构化事件生成小说文本。
```

---

## 2. 核心设计原则

### 2.1 Agent 负责意图，不负责结果

Agent 可以决定：

```text
我想隐瞒
我想追问
我想撒谎
我想观察
我想离开
我想抢夺
我想合作
```

但 Agent 不能决定：

```text
别人是否相信我
别人是否看出破绽
我的谎言是否成功
我的隐藏是否被发现
冲突是否升级
关系怎么变化
```

这些由 InteractionResolver 判定。

---

### 2.2 行为成功不等于目的成功

例如：

```text
黑衣人想隐瞒笔记，只说一部分。
```

这个行为一定发生：

```text
他确实只说了一部分。
```

但目的不一定成功：

```text
李高可能察觉他没有说全。
林梦蝶可能看见他按住口袋。
黑衣人可能保住核心秘密，但信任下降。
```

所以系统要拆分：

```text
行为执行结果
信息暴露结果
关系变化结果
情绪变化结果
剧情推进结果
风险结果
```

---

### 2.3 Writer 不创造剧情

Writer 只处理：

```text
语言
节奏
描写
对话润色
场景转场
章节结构
```

Writer 不负责决定：

```text
谁撒谎成功
谁发现线索
谁听见秘密
谁怀疑谁
谁受伤
谁死亡
```

这些必须来自 EventLog / InteractionResult。

---

### 2.4 Director 不是编剧，而是安全网

Director 只负责：

```text
防止主角过早死亡
防止关键线索永久断裂
防止真相过早泄露
防止 Agent 无限重复
防止故事无推进
防止角色行为严重违背设定
防止世界规则崩坏
```

Director 不应该直接说：

```text
这里出现一个抽屉，里面有钥匙。
```

除非这个抽屉有世界内来源、角色行为来源或谜题结构来源。

---

## 3. 总体架构

### 3.1 核心流程

```text
1. ScenePresenceTracker 构建当前场景
2. AgentPerception 为每个 Agent 生成可感知信息
3. AgentMind 生成各自行动意图
4. ActionArbitrator 合并同场景内互相影响的意图
5. MultiRoundInteractionResolver 进行多轮互动判定
6. WorldStateUpdater 更新状态
7. DirectorAgent 检查是否需要纠偏
8. EventLogWriter 写入结构化事件
9. VisibleEventFilter 过滤主角可感知事件
10. NarrativeWriter 文学化输出
```

---

### 3.2 模块目录建议

```text
agent/
├── agent_mind.py
├── agent_perception.py
├── agent_goal_system.py
├── agent_memory.py
├── agent_belief.py
├── agent_relationship.py
├── agent_communication_policy.py
└── agent_intent_generator.py

simulation/
├── scene_presence_tracker.py
├── action_arbitrator.py
├── interaction_resolver.py
├── multi_round_interaction_resolver.py
├── perception_resolver.py
├── fact_exposure_matrix.py
├── world_state_updater.py
├── event_log_writer.py
└── visible_event_filter.py

director/
├── director_agent.py
├── risk_checker.py
├── intervention_policy.py
└── correction_planner.py

writer/
├── narrative_context_builder.py
├── event_to_scene_writer.py
└── chapter_writer.py
```

---

## 4. 核心模块需求

---

## 4.1 ScenePresenceTracker

### 4.1.1 职责

ScenePresenceTracker 负责判断当前场景中：

```text
谁在场
谁不在场
谁隐藏在附近
谁能看见
谁能听见
谁只能听到部分内容
谁能观察到物品
谁能发现动作破绽
```

这决定了后续：

```text
谁知道什么
谁怀疑什么
谁能参与对话
谁能偷听
谁能误解
谁不能凭空知道
```

---

### 4.1.2 输入

```json
{
  "world_state": {},
  "location_id": "location_staircase",
  "tick": 12
}
```

---

### 4.1.3 输出

```json
{
  "scene_id": "scene_staircase_001",
  "location_id": "location_staircase",
  "present_agents": [
    "char_ligao",
    "char_linmengdie",
    "char_black_hoodie"
  ],
  "nearby_agents": [
    {
      "character_id": "char_hidden_actor",
      "location_id": "location_second_floor_corridor",
      "can_hear": true,
      "can_see": false,
      "hidden": true,
      "detection_difficulty": 4
    }
  ],
  "visible_objects": [
    "item_note_corner",
    "wall_symbols",
    "staircase_handprints"
  ],
  "audible_events": [
    "upstairs_knocking"
  ],
  "visibility_rules": {
    "same_room_can_see": true,
    "same_room_can_hear": true,
    "adjacent_room_can_hear_loud_voice": true,
    "hidden_agent_requires_detection_check": true
  },
  "danger_level": "medium"
}
```

---

### 4.1.4 验收标准

```text
1. 同一地点 Agent 默认可互相看见和听见。
2. 相邻地点 Agent 可根据距离、门、音量判断是否听见。
3. hidden_agent 默认不可见，但可能听见。
4. 所有可见物必须来自 world_state.objects。
5. 不在场 Agent 不能获得完整对话信息。
```

---

## 4.2 AgentPerception

### 4.2.1 职责

每个 Agent 只能获得自己能感知的信息。

不能给 Agent 全局真相。

---

### 4.2.2 输入

```json
{
  "agent_id": "char_linmengdie",
  "scene_presence": {},
  "world_state": {},
  "recent_events": []
}
```

---

### 4.2.3 输出

```json
{
  "agent_id": "char_linmengdie",
  "visible_agents": [
    "char_ligao",
    "char_black_hoodie"
  ],
  "visible_objects": [
    "item_note_corner",
    "wall_symbols"
  ],
  "audible_information": [
    "黑衣年轻人提到二楼有笔记"
  ],
  "observed_behaviors": [
    {
      "target": "char_black_hoodie",
      "behavior": "被问到笔记时按住口袋",
      "possible_meaning": "可能藏了东西"
    }
  ],
  "unavailable_information": [
    "黑衣人真实想法",
    "笔记完整内容",
    "隐藏角色位置"
  ]
}
```

---

## 4.3 AgentMind

### 4.3.1 职责

AgentMind 负责根据角色自身状态生成行动意图。

它不写剧情，只输出结构化意图。

---

### 4.3.2 Agent 必备字段

```json
{
  "character_id": "char_black_hoodie",
  "name": "沈渡",
  "location_id": "location_staircase",
  "public_goal": "找到出口",
  "private_goal": "隐藏自己拿走的笔记页",
  "current_intention": "降低别人怀疑，同时保留核心秘密",
  "secret_facts": [
    "他撕走了二楼笔记最后一页"
  ],
  "known_facts": [
    "二楼有一本笔记",
    "笔记提到缺席者"
  ],
  "beliefs": [],
  "relationships": {
    "char_ligao": {
      "trust": 0,
      "suspicion": 2
    },
    "char_linmengdie": {
      "trust": -1,
      "suspicion": 3
    }
  },
  "skills": {
    "observation": 3,
    "deception": 4,
    "persuasion": 2,
    "physical": 2,
    "willpower": 3
  },
  "risk_tolerance": "medium",
  "information_policy": {
    "default_share": false,
    "can_lie": true,
    "can_withhold": true
  }
}
```

---

### 4.3.3 AgentIntent 输出

```json
{
  "agent_id": "char_black_hoodie",
  "intent_id": "intent_001",
  "intention": "隐瞒自己拿走笔记页，同时降低他人怀疑",
  "action_type": "partial_disclosure",
  "target_agents": [
    "char_ligao",
    "char_linmengdie"
  ],
  "topic": "二楼笔记",
  "will_say": [
    "二楼有一本笔记",
    "笔记提到缺席者和钥匙"
  ],
  "will_hide": [
    "自己拿走了一页",
    "那页上有李高的名字"
  ],
  "behavioral_leak_risk": [
    "被问到笔记时可能按住口袋",
    "被要求交出笔记时可能停顿"
  ],
  "risk": "medium"
}
```

---

### 4.3.4 AgentMind Prompt 原则

```text
你是角色，不是作者。
你不知道全局真相，只知道自己的记忆和可感知信息。
你有自己的目标、恐惧、秘密和信任判断。
请选择当前最符合你利益的行动。
你可以合作、隐瞒、拒绝、撒谎、质疑、探索、移动。
不要为了推进剧情而主动配合。
不要替其他角色决定结果。
```

---

## 4.4 ActionArbitrator

### 4.4.1 职责

同一个 tick 内多个 Agent 可能同时行动。ActionArbitrator 负责把它们合并为可判定的交互事件。

---

### 4.4.2 输入

```json
{
  "tick": 15,
  "scene_id": "scene_staircase_001",
  "raw_intents": [
    {
      "agent": "char_ligao",
      "action": "probe_information",
      "target": "char_black_hoodie",
      "topic": "二楼笔记"
    },
    {
      "agent": "char_black_hoodie",
      "action": "partial_disclosure",
      "topic": "二楼笔记"
    },
    {
      "agent": "char_linmengdie",
      "action": "observe_and_test",
      "target": "char_black_hoodie"
    }
  ]
}
```

---

### 4.4.3 输出

```json
{
  "interaction_id": "int_001",
  "interaction_type": "information_pressure",
  "topic": "二楼笔记",
  "participants": [
    "char_ligao",
    "char_black_hoodie",
    "char_linmengdie"
  ],
  "primary_conflict": {
    "type": "information_withholding",
    "holder": "char_black_hoodie",
    "seeker": "char_ligao",
    "observer": "char_linmengdie"
  },
  "intents": []
}
```

---

### 4.4.4 支持的交互类型

```text
information_pressure：信息追问
information_trade：信息交换
trust_test：信任测试
contested_item_control：争夺物品
route_conflict：路线选择冲突
danger_response：危险应对冲突
accusation：指控
cooperation：合作
deception：欺骗
stealth_observation：偷听 / 观察
physical_block：阻止行动
```

---

## 4.5 MultiRoundInteractionResolver

### 4.5.1 职责

多轮判定 Agent 之间的交互。

它不判断“Agent 意图能不能发生”，而判断：

```text
信息暴露多少
追问是否有效
隐瞒是否被怀疑
观察是否捕捉到破绽
冲突是否升级
关系如何变化
是否触发剧情事件
```

---

### 4.5.2 交互流程

```text
1. 执行初始表达行为
2. PerceptionResolver 判断其他 Agent 感知
3. 生成 ReactionIntent
4. 执行追问 / 回避 / 质疑 / 让步
5. 重复多轮
6. 遇到结束条件后汇总结果
```

---

### 4.5.3 结束条件

```text
达到最大轮数
一方退出
一方拒绝继续
外部事件打断
危险升级
Director 要求中止
信息暴露达到当前 PlotArc 阶段上限
冲突升级到肢体风险
```

---

### 4.5.4 多轮示例

#### Round 1

```json
{
  "round": 1,
  "speaker": "char_black_hoodie",
  "action": "partial_disclosure",
  "says_summary": "二楼有一本笔记，提到缺席者和钥匙。",
  "hides": [
    "自己拿走了一页",
    "那页上有李高的名字"
  ]
}
```

#### Round 2

```json
{
  "round": 2,
  "speaker": "char_ligao",
  "action": "probe",
  "says_summary": "追问笔记在哪里，为什么不拿出来。",
  "pressure_level": 2
}
```

#### Round 3

```json
{
  "round": 3,
  "speaker": "char_black_hoodie",
  "action": "evasive_answer",
  "says_summary": "声称只看清一句，笔记没什么用。",
  "behavioral_leak": "下意识按住口袋"
}
```

#### Round 4

```json
{
  "round": 4,
  "speaker": "char_linmengdie",
  "action": "challenge",
  "says_summary": "指出他说法矛盾：既然只看清一句，为什么知道最后几页被撕掉。"
}
```

#### Round 5

```json
{
  "round": 5,
  "speaker": "char_black_hoodie",
  "action": "forced_partial_reveal",
  "says_summary": "承认笔记有撕痕和印痕。",
  "still_hides": [
    "自己撕走了一页",
    "页上有李高名字"
  ]
}
```

---

### 4.5.5 输出：InteractionResult

```json
{
  "interaction_id": "int_001",
  "interaction_type": "information_pressure",
  "topic": "二楼笔记",
  "rounds": [],
  "final_result": {
    "agent_goal_results": {
      "char_black_hoodie": {
        "hide_core_secret": "success",
        "avoid_suspicion": "failed"
      },
      "char_ligao": {
        "get_full_note": "failed",
        "detect_withholding": "partial_success"
      },
      "char_linmengdie": {
        "detect_inconsistency": "success"
      }
    },
    "revealed_facts": [
      "二楼有笔记",
      "笔记提到缺席者和钥匙",
      "笔记存在缺页或撕痕"
    ],
    "still_hidden_facts": [
      "黑衣人拿走了一页",
      "那页上有李高名字"
    ],
    "suspected_facts": [
      {
        "fact": "黑衣人可能藏了笔记的一部分",
        "suspected_by": ["char_linmengdie"],
        "confidence": 0.7
      },
      {
        "fact": "黑衣人没有说全",
        "suspected_by": ["char_ligao"],
        "confidence": 0.5
      }
    ],
    "relationship_changes": [
      {
        "from": "char_ligao",
        "to": "char_black_hoodie",
        "trust_delta": -1,
        "suspicion_delta": 2
      },
      {
        "from": "char_linmengdie",
        "to": "char_black_hoodie",
        "trust_delta": -2,
        "suspicion_delta": 3
      }
    ],
    "plot_changes": {
      "opened_threads": [
        "thread_absentee",
        "thread_hidden_note_page"
      ],
      "progress_delta": 5
    }
  }
}
```

---

## 4.6 PerceptionResolver

### 4.6.1 职责

判断在交互过程中，其他 Agent 是否注意到：

```text
破绽
动作
表情
停顿
物品边角
语义矛盾
声音
隐藏角色
```

---

### 4.6.2 判定因素

```text
观察者 observation skill
目标 deception skill
当前光线
距离
是否在场
是否专注观察
目标压力
是否有明显证据
目标是否重复矛盾
```

---

### 4.6.3 示例输出

```json
{
  "observer": "char_linmengdie",
  "target": "char_black_hoodie",
  "noticed": [
    "黑衣人被问到笔记时按住口袋",
    "他说到最后几页时停顿"
  ],
  "belief_updates": [
    {
      "content": "黑衣人可能藏了东西",
      "confidence": 0.7
    }
  ]
}
```

---

## 4.7 FactExposureMatrix

### 4.7.1 职责

维护事实暴露矩阵，记录：

```text
真实事实是什么
谁知道
谁不知道
谁怀疑
怀疑置信度是多少
谁误解了
```

---

### 4.7.2 示例

```json
{
  "fact_exposure_matrix": [
    {
      "fact_id": "fact_note_exists",
      "truth": "二楼有一本笔记",
      "known_by": [
        "char_black_hoodie",
        "char_ligao",
        "char_linmengdie"
      ],
      "confidence": {
        "char_ligao": 0.9,
        "char_linmengdie": 0.9
      }
    },
    {
      "fact_id": "fact_black_took_page",
      "truth": "黑衣人拿走了一页",
      "known_by": [
        "char_black_hoodie"
      ],
      "suspected_by": {
        "char_linmengdie": 0.7,
        "char_ligao": 0.4
      }
    },
    {
      "fact_id": "fact_page_has_ligao_name",
      "truth": "被拿走的那页上有李高的名字",
      "known_by": [
        "char_black_hoodie"
      ],
      "suspected_by": {}
    }
  ]
}
```

---

## 4.8 WorldStateUpdater

### 4.8.1 职责

根据 InteractionResult 更新世界状态。

更新范围：

```text
Agent known_facts
Agent suspected_facts
Agent beliefs
Agent relationships
Agent emotional_state
物品归属
位置变化
OpenThreads
PlotArc progress
EventLog
```

---

### 4.8.2 更新示例

```json
{
  "updates": {
    "characters.char_ligao.known_facts": [
      "二楼有一本笔记",
      "笔记提到缺席者和钥匙"
    ],
    "characters.char_ligao.suspicions": [
      "黑衣人没有说全"
    ],
    "characters.char_linmengdie.beliefs": [
      {
        "content": "黑衣人可能藏了东西",
        "confidence": 0.7
      }
    ],
    "relationships.char_linmengdie.char_black_hoodie.suspicion": "+3",
    "open_threads": [
      "thread_hidden_note_page"
    ]
  }
}
```

---

## 4.9 DirectorAgent

### 4.9.1 职责

DirectorAgent 在结果产生后检查是否需要纠偏。

注意：Director 不抢 Agent 的意图，只调整世界后果或制造外部压力。

---

### 4.9.2 检查项

```text
1. 主角是否即将死亡
2. 关键线索是否永久丢失
3. 真相是否过早泄露
4. 剧情是否连续多 tick 无推进
5. Agent 是否重复无意义行动
6. 所有 Agent 是否长时间不互动
7. 角色是否知道了自己不可能知道的信息
8. 核心 NPC 是否过早死亡
9. 当前危险是否超过章节阶段上限
```

---

### 4.9.3 纠偏方式

```text
制造外部声音打断
降低致死结果为受伤 / 失物 / 分离
让关键线索留下副痕迹
让关闭的门短暂打开
让 NPC 产生合理警觉
让危险迫使角色集合
阻止过早解释真相
```

---

### 4.9.4 示例

```json
{
  "director_check": {
    "need_intervention": true,
    "reason": "关键笔记页被黑衣人成功藏走，线索链可能永久断裂",
    "intervention_type": "preserve_clue_route",
    "correction": {
      "type": "leave_trace",
      "content": "黑衣人藏起笔记页时，页角撕下一小片，落在楼梯缝里。",
      "future_discover_route": {
        "location_id": "location_staircase",
        "object_id": "obj_torn_page_corner",
        "action": "inspect",
        "difficulty": 2
      }
    }
  }
}
```

---

## 4.10 NarrativeWriter

### 4.10.1 职责

NarrativeWriter 根据结构化事件写小说。

输入：

```text
ScenePresence
InteractionResult
VisibleEvents
CharacterStates
StylePolicy
ForbiddenReveals
```

不允许凭空新增：

```text
新事实
新线索
新角色
新物品
新的真相解释
```

---

### 4.10.2 Writer 输入示例

```json
{
  "scene_id": "scene_staircase_001",
  "visible_events": [
    {
      "type": "interaction",
      "summary": "黑衣人承认二楼有笔记，但隐瞒自己拿走了一页。李高追问，林梦蝶指出说法矛盾。黑衣人被迫承认笔记有缺页。"
    }
  ],
  "allowed_facts": [
    "二楼有笔记",
    "笔记提到缺席者和钥匙",
    "笔记存在缺页"
  ],
  "forbidden_facts": [
    "黑衣人拿走了一页",
    "那页上有李高名字"
  ],
  "relationship_state": [
    "李高开始怀疑黑衣人",
    "林梦蝶强烈怀疑黑衣人"
  ],
  "style_policy": {
    "avoid_ai_generic_phrases": true,
    "prefer_concrete_action": true
  }
}
```

---

## 5. 交互压力系统

### 5.1 压力等级

```text
Level 0：普通交流
Level 1：试探
Level 2：追问
Level 3：质疑
Level 4：威胁 / 抢夺 / 强制查看
Level 5：肢体冲突
```

---

### 5.2 升级条件

```text
对方拒绝回答
出现前后矛盾
可见证据暴露
旁观者指出破绽
涉及生死规则
涉及关键物品
信任值低
压力环境增强
```

---

### 5.3 降级条件

```text
外部危险出现
有人主动让步
Director 打断
角色选择暂时合作
新线索出现转移注意力
```

---

## 6. 支持的 Agent 行动类型

```text
observe：观察
inspect：检查物体
search：搜查区域
move：移动
ask：询问
answer：回答
refuse：拒绝
hide：隐藏物品
lie：撒谎
withhold：隐瞒部分信息
follow：跟踪
block：阻止别人
suggest：提出计划
challenge：质疑别人
share_info：分享信息
trade_info：交换信息
take_item：拿走物品
mark_location：做记号
listen：偷听
wait：等待
retreat：撤退
call_out：呼喊
test_rule：试探规则
accuse：指控
force_check：强行查看
protect：保护某人
attack：攻击
escape：逃离
```

---

## 7. API 设计

### 7.1 单 tick 模拟

```http
POST /api/simulation/{simulation_id}/tick
```

响应：

```json
{
  "tick": 12,
  "scene_results": [
    {
      "scene_id": "scene_staircase_001",
      "interaction_id": "int_001",
      "interaction_type": "information_pressure",
      "summary": "黑衣人隐瞒笔记页，李高追问，林梦蝶发现矛盾。",
      "director_intervened": false
    }
  ],
  "state_updates": {},
  "new_events": []
}
```

---

### 7.2 查看场景状态

```http
GET /api/simulation/{simulation_id}/scene/{scene_id}
```

---

### 7.3 查看 Agent 状态

```http
GET /api/simulation/{simulation_id}/agents/{agent_id}
```

---

### 7.4 查看交互详情

```http
GET /api/simulation/{simulation_id}/interactions/{interaction_id}
```

---

## 8. 前端页面建议

### 8.1 Agent 状态面板

展示：

```text
当前目标
当前意图
已知事实
怀疑事实
秘密事实
信任关系
当前情绪
当前位置
```

---

### 8.2 Scene Presence 面板

展示：

```text
当前场景
在场 Agent
附近 Agent
隐藏 Agent
可见物
可听事件
危险等级
```

---

### 8.3 Interaction Timeline 面板

展示：

```text
Round 1：谁说了什么
Round 2：谁追问
Round 3：谁回避
Round 4：谁质疑
最终暴露事实
保留秘密
新增怀疑
关系变化
Director 是否介入
```

---

### 8.4 Fact Exposure Matrix 面板

展示：

```text
事实
知道者
怀疑者
置信度
误解者
当前是否允许揭示
```

---

## 9. DoD 验收标准

### 9.1 Agent 自驱

```text
1. 每个 active_agent 每 tick 都能基于自身目标生成意图。
2. Agent 不依赖用户手动指定下一步行动。
3. Agent 不知道全局真相，只知道可感知信息。
4. Agent 可以选择隐瞒、拒绝、撒谎、追问、合作。
```

---

### 9.2 场景在场判定

```text
1. 系统能判断谁在同一地点。
2. 系统能判断谁能听见对话。
3. 系统能判断隐藏角色是否偷听。
4. 不在场角色不能凭空获得信息。
```

---

### 9.3 多轮交互

```text
1. Agent 行为能被执行。
2. 交互至少支持 2–5 轮。
3. 系统能生成追问、回避、质疑、让步。
4. 旁观 Agent 可以插话、观察、质疑。
5. 交互可以被外部事件打断。
```

---

### 9.4 结果判定

```text
1. 系统能判断信息暴露程度。
2. 系统能判断谁怀疑谁。
3. 系统能更新信任、怀疑、敌意。
4. 系统能保留 still_hidden_facts。
5. 系统能记录 suspected_facts。
6. 系统能更新 FactExposureMatrix。
```

---

### 9.5 Director 纠偏

```text
1. Director 不直接主导剧情。
2. Director 只在风险出现后介入。
3. 主角过早死亡时能转换结果。
4. 关键线索被隐藏时能保留未来发现路线。
5. 真相过早泄露时能阻断或模糊化。
```

---

### 9.6 Writer

```text
1. Writer 只能使用 visible_events。
2. Writer 不能新增结构化事件之外的真相。
3. Writer 不能让角色知道未暴露事实。
4. Writer 输出必须体现交互中的隐瞒、追问、质疑和关系变化。
```

---

## 10. 最小实现优先级

### P0：核心必做

```text
1. ScenePresenceTracker
2. AgentPerception
3. AgentMind
4. ActionArbitrator
5. MultiRoundInteractionResolver
6. WorldStateUpdater
7. FactExposureMatrix
8. DirectorAgent
```

---

### P1：增强体验

```text
1. Interaction Timeline 前端
2. Agent 状态面板
3. Fact Exposure Matrix 面板
4. VisibleEventFilter
5. Writer 事件文学化
```

---

### P2：后续增强

```text
1. Agent 个性化策略学习
2. 长期关系网络演化
3. 多场景并行调度
4. 隐藏 Agent 潜行动作
5. 高级情绪模型
6. 多结局沙盘模拟
```

---

## 11. 推荐开发顺序

```text
第一步：实现 ScenePresenceTracker
第二步：实现 AgentPerception
第三步：实现 AgentIntent 数据结构
第四步：实现 AgentMind 简版决策
第五步：实现 ActionArbitrator
第六步：实现 MultiRoundInteractionResolver
第七步：实现 FactExposureMatrix
第八步：实现 WorldStateUpdater
第九步：实现 DirectorAgent 风险检查
第十步：接入 NarrativeWriter
第十一步：做前端调试面板
```

---

## 12. 最小测试用例

### 12.1 测试场景

```text
地点：楼梯口
在场：李高、林梦蝶、黑衣人
附近隐藏：未知角色，可听不可见
物品：黑衣人口袋露出笔记边角
话题：二楼笔记
```

---

### 12.2 预期交互

```text
黑衣人只说部分信息。
李高追问笔记在哪里。
黑衣人回避。
林梦蝶发现他说法矛盾。
黑衣人被迫承认笔记有缺页。
黑衣人继续隐藏自己拿走了一页。
李高和林梦蝶对他产生怀疑。
```

---

### 12.3 预期输出

```json
{
  "revealed_facts": [
    "二楼有笔记",
    "笔记提到缺席者和钥匙",
    "笔记存在缺页"
  ],
  "still_hidden_facts": [
    "黑衣人拿走了一页",
    "那页上有李高名字"
  ],
  "suspected_facts": [
    "黑衣人可能藏了东西"
  ],
  "relationship_changes": [
    "李高对黑衣人怀疑 +2",
    "林梦蝶对黑衣人怀疑 +3"
  ],
  "director_intervention": false
}
```

---

## 13. 总结

本需求的核心是建立真正的小说沙盘交互机制：

```text
Agent 自己产生意图
Agent 之间产生多轮互动
系统判断互动后果
世界状态真实更新
Director 只在风险时纠偏
Writer 只文学化真实事件
```

最终目标：

```text
用户不需要手动安排每个冲突。
角色会因为自己的目标、秘密、怀疑和关系自然产生冲突。
```

一句话：

> Agent 可以决定自己要说什么、藏什么、问什么；但别人会不会信、会不会追问、会不会看出破绽，由 InteractionResolver 和场景状态决定。
