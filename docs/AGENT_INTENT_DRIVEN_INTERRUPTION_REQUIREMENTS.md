# 需求文档：Agent 意图驱动的真实交互与打断系统

> 版本建议：V1.2 Agent Interaction Realism  
> 所属项目：小说沙盘 / 多 Agent 叙事模拟引擎  
> 核心目标：在不削弱 Agent 个体自主性的前提下，实现真实场景中的插话、打断、抢话、回避、继续说、改口、观察破绽、事实暴露和状态更新。

---

## 1. 背景

当前系统已经从“单主角探索 + Director 塞线索”进化到“多 Agent 在场 + 多轮交互 + InteractionResolver 判定结果”。

但仍存在一个关键问题：

```text
如果系统直接判断：
- 谁打断谁
- 谁被打断后改口
- 谁发现破绽
- 谁产生怀疑

那么角色又会变成系统操控的木偶，Agent 个体意义会丢失。
```

因此，本需求要解决的问题是：

```text
如何让 Agent 自己产生说话、打断、回避、继续说、观察、追问等意图；
系统只负责仲裁这些意图在同一个现实场景中如何碰撞；
Director 只负责风险纠偏；
Writer 只负责文学化真实事件。
```

---

## 2. 核心原则

### 2.1 Agent 是意图来源

Agent 自己决定：

```text
我想说什么
我想隐瞒什么
我想打断谁
我想追问什么
我想继续说还是停下
我被打断后是回避、发火、改口，还是继续说
我是否观察别人动作
我是否暂时沉默
```

系统不允许凭空替 Agent 生成心理动机。

### 2.2 系统是仲裁者，不是演员

系统负责：

```text
多个 Agent 同时想说话，谁先插进去
谁的打断成功
谁的话被截断
谁听见了哪些话
谁看见了哪些动作
哪些事实已经说出口
哪些事实因为打断没有暴露
关系、信任、怀疑如何更新
```

系统不负责：

```text
替角色决定想法
替角色决定要不要撒谎
替角色决定要不要打断
替角色决定被打断后怎么情绪反应
```

### 2.3 Director 是安全网

Director 只在风险出现后介入：

```text
主角即将过早死亡
关键线索永久断裂
真相过早泄露
所有 Agent 陷入重复无意义行为
交互压力过高导致剧情提前崩坏
```

Director 不直接替角色说话，不直接替角色做决定。

### 2.4 Writer 只文学化事件

Writer 不决定事件，只根据结构化结果写小说：

```text
谁说了什么
谁打断了谁
谁没有说完
谁看见了动作破绽
谁产生了怀疑
哪些事实已经暴露
哪些事实仍然隐藏
```

---

## 3. 总体架构

### 3.1 新核心循环

```text
1. ScenePresenceTracker 建立场景
   判断谁在场、谁可见、谁可听、谁隐藏在附近。

2. CurrentSpeaker Agent 生成 SpeechPlan
   说话者自己决定想说什么、说到什么程度、隐藏什么。

3. SpeechSegmenter 拆分发言
   将发言拆成多个可被打断的片段。

4. 播放 SpeechSegment
   一个片段说出口，进入可听范围。

5. 在场 Agent 各自生成 ReactionIntent
   有人可能打断、观察、沉默、插话、质疑、记录。

6. InterruptArbitrator 仲裁打断意图
   多人同时想打断时，判断谁抢到话语权。

7. 被打断者 Agent 生成 ReactionIntent
   被打断者自己决定停顿、改口、继续说、反问、发怒、回避。

8. ExposureTracker 更新事实暴露
   已说出口的事实进入 known_facts；没说出口的不进入。

9. WorldStateUpdater 更新状态
   更新信任、怀疑、情绪、话语权、事件日志。

10. DirectorAgent 风险检查
    必要时制造外部压力或纠偏。

11. NarrativeWriter 文学化输出
```

### 3.2 权责划分

```text
AgentMind
负责：想法、意图、话语策略、反应倾向。

SpeechSegmenter
负责：将 Agent 的发言计划拆成可中断片段。

InterruptArbitrator
负责：多个 Agent 同时打断时，判定谁抢到话语权。

InteractionResolver
负责：记录交互结果，而不是替 Agent 生成意图。

WorldStateUpdater
负责：更新事实、关系、情绪、位置、事件日志。

DirectorAgent
负责：风险纠偏。

NarrativeWriter
负责：小说化表达。
```

---

## 4. 模块设计

### 4.1 ScenePresenceTracker

#### 职责

判断当前场景中：

```text
谁在场
谁能看见谁
谁能听见谁
谁隐藏在附近
谁能偷听
谁看不见但能听见
谁能观察到手部动作、眼神、物品边角
```

#### 输出示例

```json
{
  "scene_id": "scene_staircase_001",
  "location_id": "location_staircase",
  "present_agents": [
    "char_ligao",
    "char_linmengdie",
    "char_black_hoodie",
    "char_chen"
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
  "visibility": {
    "lighting": "dim",
    "distance": "close",
    "can_observe_hand_movement": true,
    "can_observe_eye_contact": true
  },
  "audibility": {
    "normal_voice_heard_by_present": true,
    "whisper_requires_check": true,
    "loud_interruption_heard_by_nearby": true
  }
}
```

---

### 4.2 AgentMind

#### 职责

AgentMind 是角色自主性的核心。

它负责生成：

```text
SpeechPlan
ReactionIntent
InterruptIntent
ObservationIntent
PostInterruptionReaction
```

#### Agent 必备字段

```json
{
  "character_id": "char_black_hoodie",
  "name": "沈渡",
  "public_goal": "找到出口",
  "private_goal": "隐藏自己拿走笔记页",
  "secret_facts": [
    "自己拿走了二楼笔记最后一页"
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
  "conversation_style": {
    "assertiveness": 3,
    "evasion": 4,
    "interrupt_tendency": 2,
    "panic_threshold": 6,
    "when_interrupted": [
      "停顿",
      "回避",
      "反问",
      "继续隐瞒"
    ]
  },
  "skills": {
    "observation": 3,
    "deception": 4,
    "persuasion": 2,
    "reaction_speed": 3,
    "dominance": 2,
    "willpower": 3
  }
}
```

---

### 4.3 SpeechPlan

#### 职责

SpeechPlan 由当前说话 Agent 生成。

它表示：

```text
我打算说什么
我打算分几步说
我准备隐藏哪些内容
哪些内容风险高
我在什么情况下会停下
```

#### 示例

```json
{
  "speaker": "char_black_hoodie",
  "topic": "二楼笔记",
  "speech_goal": "提供部分信息，同时隐藏自己拿走一页",
  "segments": [
    {
      "segment_id": "seg_001",
      "content_summary": "二楼有一本笔记",
      "spoken_text": "二楼有一本笔记。",
      "exposes_facts": [
        "fact_note_exists"
      ],
      "exposure_level": "safe",
      "interruptible": true,
      "trigger_keywords": [
        "笔记"
      ]
    },
    {
      "segment_id": "seg_002",
      "content_summary": "笔记提到缺席者留下了钥匙",
      "spoken_text": "里面写着，缺席者留下了钥匙。",
      "exposes_facts": [
        "fact_absentee_left_key"
      ],
      "exposure_level": "medium",
      "interruptible": true,
      "trigger_keywords": [
        "缺席者",
        "钥匙"
      ]
    },
    {
      "segment_id": "seg_003",
      "content_summary": "找到钥匙的人不能说出它的名字",
      "spoken_text": "找到钥匙的人，不能说出它的名字。",
      "exposes_facts": [
        "fact_key_name_taboo"
      ],
      "exposure_level": "high",
      "interruptible": true,
      "trigger_keywords": [
        "名字",
        "不能说"
      ]
    }
  ],
  "withheld_segments": [
    {
      "content_summary": "自己拿走了最后一页",
      "fact_id": "fact_black_took_page",
      "exposure_level": "forbidden"
    },
    {
      "content_summary": "那页上有李高的名字",
      "fact_id": "fact_page_has_ligao_name",
      "exposure_level": "forbidden"
    }
  ]
}
```

#### 规则

```text
1. SpeechPlan 必须由 AgentMind 生成。
2. SpeechPlan 不代表一定能完整说完。
3. segments 中已说出口的内容才进入事实暴露。
4. withheld_segments 不得进入其他 Agent known_facts。
5. 被打断后，remaining_segments 默认暂停。
```

---

### 4.4 SpeechSegmenter

#### 职责

将 Agent 的发言拆分成可被打断的片段。

#### 拆分规则

```text
1. 每个 segment 只暴露 1 个主要事实。
2. 高风险事实必须单独成段。
3. 包含关键词的句子必须允许 interrupt window。
4. 禁止一口气说完所有关键规则。
5. 每次发言最多 3–5 个 segment。
```

---

### 4.5 ReactionIntent

#### 职责

每个在场 Agent 在听到一个 SpeechSegment 后，自己决定是否反应。

反应类型包括：

```text
interrupt：打断
observe：观察
hold：沉默观察
challenge：质疑
clarify：要求澄清
probe：追问
block_disclosure：阻止继续说
support：支持当前说话者
redirect：转移话题
leave：离开
```

#### 示例：李高打断

```json
{
  "agent_id": "char_ligao",
  "reaction_type": "interrupt",
  "trigger_segment_id": "seg_001",
  "intent_source": "agent_mind",
  "reason": "笔记可能是关键证据，不能只听对方转述",
  "urgency": 8,
  "spoken_text": "笔记在哪？",
  "target_speaker": "char_black_hoodie",
  "pressure_delta": 1
}
```

#### 示例：林梦蝶观察

```json
{
  "agent_id": "char_linmengdie",
  "reaction_type": "observe",
  "trigger_segment_id": "seg_001",
  "intent_source": "agent_mind",
  "focus": [
    "黑衣人的手",
    "黑衣人说到笔记时的停顿",
    "他是否回避视线"
  ],
  "urgency": 5,
  "reason": "黑衣人可能没有说全"
}
```

#### 示例：陈哥阻止披露

```json
{
  "agent_id": "char_chen",
  "reaction_type": "interrupt",
  "interrupt_type": "block_disclosure",
  "trigger_segment_id": "seg_002",
  "intent_source": "agent_mind",
  "reason": "不希望钥匙规则被公开，担心触发禁忌",
  "urgency": 9,
  "spoken_text": "别说那个字。",
  "target_speaker": "char_black_hoodie",
  "pressure_delta": 2
}
```

---

### 4.6 InterruptArbitrator

#### 职责

当多个 Agent 同时产生打断意图时，仲裁谁抢到话语权。

#### 输入

```json
{
  "current_speaker": "char_black_hoodie",
  "current_segment": "seg_002",
  "candidate_reactions": [
    {
      "agent_id": "char_ligao",
      "reaction_type": "interrupt",
      "urgency": 8,
      "dominance": 4,
      "reaction_speed": 4
    },
    {
      "agent_id": "char_chen",
      "reaction_type": "interrupt",
      "urgency": 9,
      "dominance": 6,
      "reaction_speed": 3
    },
    {
      "agent_id": "char_linmengdie",
      "reaction_type": "observe",
      "urgency": 5
    }
  ]
}
```

#### 仲裁因素

```text
urgency：打断紧迫度
dominance：话语压制力
reaction_speed：反应速度
current_speaker_assertiveness：当前说话者是否强势
segment_interruptible：当前片段是否可被打断
relationship_pressure：双方关系压力
scene_pressure：场景危险压力
```

#### 输出

```json
{
  "arbitration_result": {
    "turn_shift": true,
    "winner": "char_chen",
    "interrupted_speaker": "char_black_hoodie",
    "result": "interrupt_success",
    "reason": "陈哥阻止披露的紧迫度和话语压制更高",
    "non_winning_reactions": [
      {
        "agent_id": "char_ligao",
        "result": "not_spoken",
        "effect": "仍然保持追问意图"
      },
      {
        "agent_id": "char_linmengdie",
        "result": "observe_success",
        "effect": "注意到陈哥对钥匙一词反应过度"
      }
    ]
  }
}
```

---

### 4.7 InterruptionResult

#### 职责

记录打断发生后的实际结果。

#### 示例

```json
{
  "interruption_id": "interrupt_001",
  "trigger_segment": "seg_002",
  "interrupter": "char_chen",
  "interrupted_speaker": "char_black_hoodie",
  "success": true,
  "intent_source": "agent_mind",
  "arbitrated_by": "interrupt_arbitrator",
  "effect": {
    "speech_plan_interrupted": true,
    "remaining_segments_suspended": [
      "seg_003"
    ],
    "revealed_facts": [
      "fact_absentee_left_key"
    ],
    "prevented_facts": [
      "fact_key_name_taboo"
    ],
    "pressure_level_delta": 2,
    "turn_owner": "char_chen"
  }
}
```

---

### 4.8 PostInterruptionReaction

#### 职责

被打断者必须自己生成反应，而不是系统替他决定。

#### 输入给被打断 Agent

```json
{
  "event_type": "interrupted",
  "agent_id": "char_black_hoodie",
  "interrupted_by": "char_chen",
  "topic": "二楼笔记",
  "pressure_level": 3,
  "facts_already_revealed": [
    "fact_note_exists",
    "fact_absentee_left_key"
  ],
  "facts_prevented": [
    "fact_key_name_taboo"
  ],
  "risk": "陈哥明显不希望钥匙规则被公开，其他人可能注意到异常"
}
```

#### Agent 输出示例

```json
{
  "agent_id": "char_black_hoodie",
  "reaction_intent": {
    "type": "deflect",
    "intent_source": "agent_mind",
    "spoken_text": "我只是照着笔记念，别问我那是什么意思。",
    "goal": "继续隐藏自己拿走笔记页，并把压力转移给陈哥",
    "emotional_state": "tense",
    "behavioral_leak": "下意识按住口袋",
    "will_hide": [
      "自己拿走了一页",
      "那页上有李高名字"
    ]
  }
}
```

---

### 4.9 TurnState

#### 职责

维护当前话语权状态。

#### 示例

```json
{
  "interaction_id": "int_001",
  "current_speaker": "char_black_hoodie",
  "speech_state": "in_progress",
  "current_segment": "seg_002",
  "turn_control": {
    "speaker_assertiveness": 3,
    "pressure": 2,
    "others_can_interrupt": true
  }
}
```

打断后：

```json
{
  "interaction_id": "int_001",
  "current_speaker": "char_chen",
  "previous_speaker": "char_black_hoodie",
  "speech_state": "interrupted",
  "turn_shift_reason": "block_disclosure"
}
```

---

### 4.10 ExposureTracker

#### 职责

记录哪些事实已经说出口，哪些事实因为打断没有暴露。

#### 规则

```text
1. 只有 spoken segment 暴露的 facts 才能进入 known_facts。
2. remaining_segments_suspended 中的 facts 不得进入 known_facts。
3. withheld_segments 不得进入其他 Agent known_facts。
4. 观察行为只能产生 suspected_facts，不能直接产生 truth_facts。
5. 被打断本身可以产生新怀疑。
```

#### 示例

```json
{
  "fact_exposure_update": {
    "revealed_facts": [
      {
        "fact_id": "fact_note_exists",
        "known_by": [
          "char_ligao",
          "char_linmengdie",
          "char_chen"
        ],
        "source": "spoken_segment_seg_001"
      },
      {
        "fact_id": "fact_absentee_left_key",
        "known_by": [
          "char_ligao",
          "char_linmengdie",
          "char_chen"
        ],
        "source": "spoken_segment_seg_002"
      }
    ],
    "prevented_facts": [
      {
        "fact_id": "fact_key_name_taboo",
        "reason": "speech_plan_interrupted_before_seg_003"
      }
    ],
    "suspected_facts": [
      {
        "fact": "陈哥不希望钥匙规则被说出来",
        "suspected_by": {
          "char_linmengdie": 0.7,
          "char_ligao": 0.5
        },
        "source": "interruption_behavior"
      }
    ]
  }
}
```

---

## 5. 运行流程详解

### 5.1 正常发言无打断

```text
A 生成 SpeechPlan
↓
播放 seg_001
↓
其他 Agent 生成 reaction
↓
无人 interrupt
↓
播放 seg_002
↓
继续直到发言结束
↓
ExposureTracker 更新已暴露事实
```

### 5.2 发言中被打断

```text
A 生成 SpeechPlan
↓
播放 seg_001
↓
B 生成 InterruptIntent
↓
InterruptArbitrator 判定 B 抢到话语权
↓
A 的 remaining_segments 暂停
↓
A 根据 interrupted event 生成 reaction
↓
ExposureTracker 记录：
    已说出口 facts
    被阻止 facts
    新增 suspected_facts
```

### 5.3 多人同时打断

```text
A 播放 seg_002
↓
B 想追问
C 想阻止披露
D 想观察
↓
InterruptArbitrator 仲裁
↓
C 抢到话语权
↓
B 的追问意图保留
↓
D 的观察成功
↓
A 反应
```

### 5.4 打断失败

```text
A 播放 seg_002
↓
B 尝试打断
↓
Arbitrator 判定失败：
    A 当前 assertiveness 高
    B urgency 不足
↓
A 继续说 seg_003
↓
B 的关系状态更新：
    frustration +1
    suspicion +1
```

---

## 6. 事件来源追踪

### 6.1 intent_source 必填

所有事件都必须标记来源。

```json
{
  "event_type": "interruption",
  "actor": "char_ligao",
  "intent_source": "agent_mind",
  "intent_reason": "李高认为笔记是关键证据，不能只听黑衣人转述",
  "arbitrated_by": "interrupt_arbitrator",
  "result": "interrupt_success"
}
```

### 6.2 Director 介入也必须标记

```json
{
  "event_type": "external_sound",
  "intent_source": "director_intervention",
  "reason": "交互压力过高，防止第一章过早暴露核心秘密",
  "effect": "楼上传来金属拖行声，打断对话"
}
```

### 6.3 验收规则

```text
1. 所有 interrupt / reaction / speech 都必须有 intent_source。
2. intent_source = agent_mind 表示角色自主产生。
3. intent_source = director_intervention 表示系统纠偏。
4. Writer 输出的关键事件必须能回溯到结构化来源。
```

---

## 7. Writer 输入限制

Writer 只能使用以下内容：

```text
spoken_segments
interruption_results
post_interruption_reactions
exposure_updates
relationship_updates
visible_observations
director_interventions
```

Writer 禁止：

```text
替角色新增意图
让角色知道未暴露 facts
让角色说出 withheld_segments
让未在场角色知道对话
把系统推理写成角色断言
```

---

## 8. 示例：黑衣人笔记对话

### 8.1 初始场景

```json
{
  "scene": "楼梯口",
  "present_agents": [
    "char_ligao",
    "char_linmengdie",
    "char_black_hoodie",
    "char_chen"
  ],
  "topic": "二楼笔记",
  "visible_objects": [
    "黑衣人口袋边缘露出的纸角"
  ]
}
```

### 8.2 黑衣人 SpeechPlan

```json
{
  "speaker": "char_black_hoodie",
  "segments": [
    {
      "segment_id": "seg_001",
      "spoken_text": "二楼有一本笔记。",
      "exposes_facts": ["fact_note_exists"]
    },
    {
      "segment_id": "seg_002",
      "spoken_text": "里面写着，缺席者留下了钥匙。",
      "exposes_facts": ["fact_absentee_left_key"]
    },
    {
      "segment_id": "seg_003",
      "spoken_text": "找到钥匙的人不能说出它的名字。",
      "exposes_facts": ["fact_key_name_taboo"]
    }
  ],
  "withheld_segments": [
    "fact_black_took_page",
    "fact_page_has_ligao_name"
  ]
}
```

### 8.3 交互结果

```json
{
  "spoken_segments": [
    "seg_001",
    "seg_002"
  ],
  "interruption": {
    "interrupter": "char_chen",
    "spoken_text": "别说那个字。",
    "intent_source": "agent_mind",
    "result": "interrupt_success"
  },
  "prevented_segments": [
    "seg_003"
  ],
  "observations": [
    {
      "observer": "char_linmengdie",
      "noticed": "陈哥对钥匙一词反应过度",
      "belief_update": "陈哥可能知道钥匙规则"
    },
    {
      "observer": "char_ligao",
      "noticed": "黑衣人被打断后按住口袋",
      "belief_update": "黑衣人可能还有没说完的内容"
    }
  ],
  "post_reaction": {
    "agent": "char_black_hoodie",
    "type": "deflect",
    "spoken_text": "我只是照着笔记念，别问我那是什么意思。"
  },
  "fact_exposure": {
    "revealed_facts": [
      "fact_note_exists",
      "fact_absentee_left_key"
    ],
    "prevented_facts": [
      "fact_key_name_taboo"
    ],
    "still_hidden_facts": [
      "fact_black_took_page",
      "fact_page_has_ligao_name"
    ]
  }
}
```

### 8.4 Writer 应输出的小说效果

```text
“二楼有一本笔记。”黑衣人说。

李高立刻看向他的口袋：“笔记在哪？”

黑衣人的话停了一下。

“里面写着，缺席者留下了钥匙。”他像是没听见李高的问题，继续说。

“别说那个字。”

陈哥的声音压了过来。

楼梯口一瞬间安静下来。

林梦蝶没有看黑衣人，而是看向陈哥。

“哪个字？”她问。
```

---

## 9. DoD 验收标准

### 9.1 Agent 自主性

```text
1. 打断意图必须由 AgentMind 产生。
2. 被打断后的反应必须由被打断 Agent 自己产生。
3. 系统不得凭空决定角色想打断。
4. 所有关键行为必须有 intent_source。
```

### 9.2 打断能力

```text
1. SpeechPlan 可被拆成多个 segment。
2. 每个 segment 后都能产生 interrupt window。
3. 多个 Agent 可同时生成 interrupt intent。
4. InterruptArbitrator 能判定谁抢到话语权。
5. 打断成功后，未说出口的 segment 不得暴露。
6. 打断失败时，说话者可继续发言。
```

### 9.3 事实暴露

```text
1. 已说出口 facts 进入对应听众 known_facts。
2. 未说出口 facts 不进入 known_facts。
3. 观察只能产生 suspected_facts，不能直接产生 truth_facts。
4. 被打断本身可以产生 suspected_facts。
5. FactExposureMatrix 必须更新。
```

### 9.4 在场状态

```text
1. 只有可听范围内 Agent 才能知道 spoken segment。
2. 只有可见范围内 Agent 才能观察动作破绽。
3. nearby hidden Agent 可以偷听，但不可直接参与普通对话。
4. 不在场 Agent 不能凭空知道对话内容。
```

### 9.5 Director 边界

```text
1. Director 不得替 Agent 产生普通打断意图。
2. Director 只能在风险检查后介入。
3. Director 介入必须标记 intent_source = director_intervention。
4. Director 介入优先表现为外部事件、环境压力、风险缓和，而非替角色说话。
```

### 9.6 Writer 边界

```text
1. Writer 只能写结构化事件中发生过的内容。
2. Writer 不能补充未暴露事实。
3. Writer 不能让角色说出未生成的台词意图。
4. Writer 必须体现打断、停顿、改口、观察、话语权转移。
```

---

## 10. 最小开发优先级

### P0

```text
1. SpeechPlan 数据结构
2. SpeechSegmenter
3. ReactionIntent 数据结构
4. InterruptArbitrator
5. TurnState
6. ExposureTracker
7. PostInterruptionReaction
8. intent_source 追踪
```

### P1

```text
1. ScenePresenceTracker 增强
2. FactExposureMatrix 联动
3. Agent conversation_style
4. 多人同时打断仲裁
5. 打断失败逻辑
6. Writer 输入限制
```

### P2

```text
1. 隐藏 Agent 偷听
2. 低声说话 / 耳语系统
3. 群体争吵场景
4. 肢体阻止 / 抢夺
5. 情绪升级系统
6. 长期话语权风格学习
```

---

## 11. 推荐开发顺序

```text
第一步：新增 SpeechPlan / SpeechSegment 数据结构
第二步：让 AgentMind 输出 SpeechPlan
第三步：实现 SpeechSegmenter
第四步：每个 segment 后触发在场 Agent ReactionIntent
第五步：实现 InterruptArbitrator
第六步：实现 TurnState 话语权转移
第七步：实现 PostInterruptionReaction
第八步：实现 ExposureTracker
第九步：接入 FactExposureMatrix
第十步：限制 Writer 只能使用 spoken_segments 和 interaction_results
第十一步：接入 Director 风险检查
```

---

## 12. 最小测试用例

### 12.1 测试目标

验证：

```text
A 说话未完成时，B / C 可以由 AgentMind 自主产生打断意图。
系统只负责仲裁。
未说出口事实不会暴露。
被打断者自行反应。
```

### 12.2 测试场景

```text
地点：楼梯口
在场：李高、林梦蝶、黑衣人、陈哥
话题：二楼笔记
黑衣人持有秘密：他拿走了一页，上面有李高名字
陈哥持有秘密：他知道“钥匙”一词危险
```

### 12.3 预期行为

```text
1. 黑衣人开始说二楼笔记。
2. 李高听到“笔记”后想打断追问。
3. 黑衣人继续说“缺席者留下了钥匙”。
4. 陈哥听到“钥匙”后产生更高 urgency 的打断。
5. InterruptArbitrator 判定陈哥抢到话语权。
6. 黑衣人后续“不能说出名字”没有说出口。
7. 林梦蝶观察到陈哥反应异常。
8. 黑衣人被打断后由 AgentMind 生成回避反应。
9. FactExposureMatrix 更新：
   - 二楼有笔记：已知
   - 缺席者留下钥匙：已知
   - 不能说出名字：未暴露
   - 黑衣人拿走一页：未暴露
   - 陈哥知道钥匙危险：被怀疑
```

### 12.4 预期结构化输出

```json
{
  "spoken_segments": [
    "seg_note_exists",
    "seg_absentee_left_key"
  ],
  "interruption_result": {
    "interrupter": "char_chen",
    "intent_source": "agent_mind",
    "result": "interrupt_success",
    "spoken_text": "别说那个字。"
  },
  "prevented_segments": [
    "seg_key_name_taboo"
  ],
  "post_interruption_reaction": {
    "agent": "char_black_hoodie",
    "intent_source": "agent_mind",
    "type": "deflect"
  },
  "observations": [
    {
      "observer": "char_linmengdie",
      "noticed": "陈哥对钥匙一词反应过度",
      "suspected_fact": "陈哥可能知道钥匙规则"
    }
  ],
  "fact_exposure": {
    "revealed": [
      "fact_note_exists",
      "fact_absentee_left_key"
    ],
    "prevented": [
      "fact_key_name_taboo"
    ],
    "hidden": [
      "fact_black_took_page",
      "fact_page_has_ligao_name"
    ]
  }
}
```

---

## 13. 总结

本需求的核心不是让系统决定角色行为，而是让系统仲裁 Agent 意图的碰撞。

最终架构：

```text
Agent 决定自己想说什么、藏什么、问什么、打断什么；
Agent 决定自己被打断后的反应；
系统只判断谁抢到话语权、哪些话说出口、哪些事实暴露；
Director 只做风险纠偏；
Writer 只文学化真实事件。
```

一句话：

> Agent 是意图来源，系统是现实仲裁器，Director 是安全网，Writer 是记录者。
