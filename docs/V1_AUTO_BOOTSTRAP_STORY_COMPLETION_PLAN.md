# V1 内测版补全功能开发计划：模糊设定自动补全 + 多角色沙盘启动

> 功能名称：StoryBootstrapper / AutoBootstrap  
> 目标：用户只给非常模糊的设定时，系统也能自动补全世界、角色、NPC、地图、线索、真相链，并启动多角色自由活动，最后总结成小说。  
> 适用：悬疑、灵异、恐怖、都市怪谈、旧案调查类故事。  

---

## 1. 当前问题

你现在想要的能力是：

```text
用户只输入一句模糊设定
↓
AI 自动补全完整故事世界
↓
多个角色在世界中自由活动
↓
系统记录事件
↓
最后总结成小说
```

但当前运行表现更像：

```text
用户输入模糊设定
↓
系统只生成一个主角
↓
主角在空场景里观察、移动、搜索
↓
Director 反复塞环境 hint
↓
hint 没有转化成 clue / evidence / known_fact
↓
NarrativeWriter 只能写通用悬疑模板
```

典型问题：

```text
1. 只有主角行动，没有 NPC 和隐藏角色行动。
2. Director 只会生成 environment_hint，例如抽屉、脚印、小门。
3. hint 没有绑定 source_character、clue_id、discover_route。
4. 角色看见异常物件，但 state 中 known_facts / inventory / discovered_clues 仍为空。
5. NarrativeWriter 缺少主角目标、私人动机、章节问题、线索意义。
6. 最终文本像“神秘地点探索”，不像有主线的小说。
```

所以新增功能的核心不是提升文笔，而是：

```text
先自动构建一个能自己运转的故事世界。
```

---

## 2. 新功能总目标

新增一个 StoryBootstrapper，在 SimulationRunner 前执行。

它负责把用户模糊设定补全成可运行沙盘配置。

输入：

```json
{
  "user_seed": "废弃医院，午夜出现五楼，主角调查失踪妹妹",
  "target_genre": "horror_suspense",
  "target_words": 100000,
  "auto_confirm": false
}
```

输出：

```text
world_bible.json
map.json
characters.json
npc_role_specs.json
plot_arcs.json
truth_chain.json
evidence_graph.json
clues.json
open_threads.json
chapter_goal.json
opening_chapter_plan.json
scheduler_config.json
writer_story_anchors.json
```

---

## 3. 新增运行模式

新增：

```json
{
  "run_mode": "auto_bootstrap_simulation"
}
```

流程：

```text
用户输入模糊设定
↓
StoryBootstrapper 自动补全
↓
BootstrapValidator 校验
↓
CandidateReview 可选审核
↓
写入 world 配置文件
↓
MultiAgentScheduler 启动多角色沙盘
↓
ClueDiscoveryResolver 处理线索发现
↓
VisibleEventFilter 过滤主角可感知事件
↓
NarrativeWriter 总结成章节
```

禁止直接：

```text
模糊设定 → SimulationRunner
```

因为这样会导致世界空转。

---

## 4. 新增模块

建议新增目录：

```text
bootstrap/
├── story_bootstrapper.py
├── seed_interpreter.py
├── world_bible_generator.py
├── minimum_cast_generator.py
├── bootstrap_map_generator.py
├── truth_chain_generator.py
├── evidence_graph_generator.py
├── open_thread_seed_generator.py
├── clue_route_generator.py
├── opening_chapter_goal_generator.py
├── writer_anchor_generator.py
├── bootstrap_validator.py
└── bootstrap_candidate_review.py
```

需要改造：

```text
scheduler/
└── multi_agent_scheduler.py

director/
├── clue_route_intervention.py
└── intervention_deduplicator.py

simulation/
├── action_resolver.py
├── clue_discovery_resolver.py
└── visible_event_filter.py

writer/
├── narrative_context_builder.py
└── chapter_writer_prompt_builder.py
```

---

## 5. SeedInterpreter：解析模糊设定

### 5.1 职责

从一句模糊设定里解析出可扩展元素。

输入：

```text
废弃医院，午夜出现五楼，主角调查失踪妹妹
```

输出：

```json
{
  "genre": "horror",
  "sub_genre": "suspense_supernatural",
  "core_location": "废弃医院",
  "supernatural_element": "午夜出现不存在的五楼",
  "protagonist_goal": "调查失踪妹妹",
  "missing_person": "妹妹",
  "story_type": "旧案调查",
  "bootstrap_template": "old_hospital_missing_person"
}
```

### 5.2 必须识别

```text
题材
核心地点
主角目标
缺席人物
灵异元素
初始冲突
推荐故事模板
```

---

## 6. WorldBibleGenerator：自动补全世界设定

### 6.1 输出示例

```json
{
  "world_id": "world_old_hospital_001",
  "title": "绝命旧院",
  "genre_id": "horror",
  "sub_genre": "suspense_supernatural",
  "era": "现代都市",
  "tone": "克制、压抑、现实中透出诡异",
  "core_location": "旧医院",
  "themes": [
    "记忆是否可靠",
    "人如何逃避愧疚",
    "被隐瞒的旧案如何反噬活人"
  ],
  "world_rules": [
    "旧医院午夜后会出现不存在的五楼",
    "五楼不会随机杀人，每次死亡都对应旧案真相",
    "看门人知道危险，但不会主动说出完整真相"
  ],
  "timeline": {
    "accident_years_ago": 10,
    "actual_abandoned_years_ago": 9,
    "official_closed_years_ago": 2
  }
}
```

### 6.2 要求

必须生成具体标题，禁止使用：

```text
Mysterious Place
神秘之地
未知地点
```

---

## 7. MinimumCastGenerator：最小角色组生成

### 7.1 目标

即使用户只给一句设定，系统也必须生成至少：

```text
1 个主角
1 个缺席人物
1 个阻碍者
1 个目击者
1 个隐藏行动者
```

否则沙盘只会变成主角一个人摸场景。

### 7.2 示例 characters.json

```json
[
  {
    "character_id": "char_linzho",
    "name": "林舟",
    "role": "protagonist",
    "active_agent": true,
    "location_id": "location_gate",
    "goal": "寻找失踪妹妹林雪的踪迹",
    "personal_stakes": "曾经没有相信林雪最后一次关于旧医院的求助",
    "known_facts": [],
    "suspicions": [],
    "inventory": []
  },
  {
    "character_id": "char_linxue",
    "name": "林雪",
    "role": "missing_person",
    "active_agent": false,
    "story_function": "主线牵引者",
    "last_known_location": "旧医院附近"
  },
  {
    "character_id": "npc_gatekeeper",
    "name": "老周",
    "role": "gatekeeper",
    "active_agent": true,
    "location_id": "location_gate",
    "goal": "阻止外人进入旧医院，同时隐瞒自己知道的事",
    "narrative_function": ["obstructor", "reluctant_witness"],
    "disclosure_policy": {
      "style": "reluctant",
      "max_new_facts_per_dialogue": 1,
      "avoid_exposition": true
    }
  },
  {
    "character_id": "npc_store_owner",
    "name": "赵婶",
    "role": "witness",
    "active_agent": true,
    "location_id": "location_store",
    "goal": "守着小卖部，不愿卷入旧医院的事",
    "narrative_function": ["witness", "local_information_source"]
  },
  {
    "character_id": "npc_hidden_actor",
    "name": "未知男人",
    "role": "hidden_actor",
    "active_agent": true,
    "visibility": "hidden",
    "narrative_visibility": "trace_only",
    "location_id": "location_frontdesk",
    "goal": "回收旧医院中遗留的某份档案"
  }
]
```

---

## 8. BootstrapMapGenerator：地图自动补全

### 8.1 最小地图

```json
[
  {
    "location_id": "location_gate",
    "name": "旧医院大门",
    "type": "entrance",
    "connected_to": ["location_frontdesk", "location_store"],
    "available_actions": ["observe", "inspect", "talk", "move"]
  },
  {
    "location_id": "location_frontdesk",
    "name": "前台大厅",
    "type": "interior",
    "connected_to": ["location_gate", "location_hallway"],
    "available_actions": ["observe", "inspect", "search", "move"]
  },
  {
    "location_id": "location_hallway",
    "name": "一楼走廊",
    "type": "interior",
    "connected_to": ["location_frontdesk", "location_archive", "location_basement"],
    "available_actions": ["observe", "inspect", "search", "move"]
  },
  {
    "location_id": "location_archive",
    "name": "病案室",
    "type": "archive",
    "connected_to": ["location_hallway"],
    "available_actions": ["inspect", "search"]
  },
  {
    "location_id": "location_basement",
    "name": "地下室入口",
    "type": "danger_zone",
    "connected_to": ["location_hallway"],
    "available_actions": ["observe", "inspect", "move"]
  },
  {
    "location_id": "location_store",
    "name": "旧街口小卖部",
    "type": "external_witness_location",
    "connected_to": ["location_gate"],
    "available_actions": ["talk", "ask", "observe"]
  }
]
```

---

## 9. TruthChainGenerator：真相链自动生成

### 9.1 作用

控制真相分阶段揭示，防止 AI 过早解释五楼或旧案。

### 9.2 示例

```json
{
  "truth_id": "truth_old_hospital",
  "final_truth": "旧医院五楼并非真实楼层，而是十年前事故残留形成的异常空间。",
  "reveal_steps": [
    {
      "stage": "surface",
      "chapter_range": [1, 5],
      "allowed_information": [
        "旧医院近期有人进入",
        "医院并非完全废弃",
        "部分痕迹不符合长期封闭状态"
      ],
      "forbidden_information": [
        "五楼真实来源",
        "十年前事故完整真相"
      ]
    },
    {
      "stage": "partial",
      "chapter_range": [6, 15],
      "allowed_information": [
        "五楼与十年前事故有关",
        "有人刻意隐瞒旧案记录"
      ],
      "forbidden_information": [
        "最终责任人身份",
        "完整灵异规则"
      ]
    },
    {
      "stage": "major",
      "chapter_range": [16, 24],
      "allowed_information": [
        "林雪发现了旧案缺口",
        "主角过去可能与事故有关"
      ],
      "forbidden_information": []
    },
    {
      "stage": "truth",
      "chapter_range": [25, 30],
      "allowed_information": [
        "五楼真实来源",
        "旧案责任链",
        "林雪失踪真正原因"
      ],
      "forbidden_information": []
    }
  ]
}
```

---

## 10. EvidenceGraphGenerator：证据链自动生成

### 10.1 线索必须有意义

每条 evidence 必须绑定：

```text
related_thread
purpose
truth_relevance
allowed_reveal_chapters
real_meaning
```

### 10.2 示例

```json
[
  {
    "evidence_id": "ev_new_lock_core",
    "title": "新换过的锁芯",
    "type": "physical_trace",
    "truth_relevance": "surface",
    "purpose": "证明旧医院近期有人进入",
    "related_thread": "thread_recent_entry",
    "can_mislead": false,
    "real_meaning": "有人近期打开或更换过医院门锁",
    "allowed_reveal_chapters": [1, 3]
  },
  {
    "evidence_id": "ev_fresh_footprints",
    "title": "新鲜脚印",
    "type": "trace",
    "truth_relevance": "surface",
    "purpose": "证明有人在主角之前进入医院",
    "related_thread": "thread_recent_entry",
    "can_mislead": true,
    "real_meaning": "隐藏行动者进入医院留下的痕迹",
    "allowed_reveal_chapters": [1, 4]
  },
  {
    "evidence_id": "ev_linxue_mark",
    "title": "林雪留下的记号",
    "type": "personal_trace",
    "truth_relevance": "minor",
    "purpose": "把主角目标和旧医院绑定",
    "related_thread": "thread_linxue_trace",
    "can_mislead": false,
    "real_meaning": "林雪确实进入过旧医院",
    "allowed_reveal_chapters": [1, 5]
  }
]
```

---

## 11. ClueRouteGenerator：可发现线索入口

### 11.1 为什么必须有 ClueRoute

不能只生成：

```text
前台后方有一只抽屉微微敞开
```

必须生成：

```text
可搜索对象
↓
search / inspect
↓
发现 clue
↓
更新 known_fact / inventory / plot_event
```

### 11.2 示例 clues.json

```json
[
  {
    "clue_id": "clue_new_lock_core",
    "title": "新换过的锁芯",
    "level": "surface",
    "related_event": "发现医院锁被更换过",
    "related_thread": "thread_recent_entry",
    "discover_routes": [
      {
        "location_id": "location_gate",
        "object_id": "obj_gate_lock",
        "action": "inspect",
        "difficulty": 1
      }
    ],
    "on_discovered": {
      "add_known_fact": "旧医院的门锁近期被人使用或更换过。",
      "trigger_event": "发现医院锁被更换过",
      "plot_progress": 12
    }
  },
  {
    "clue_id": "clue_frontdesk_key",
    "title": "前台抽屉里的小钥匙",
    "level": "minor",
    "related_event": "发现前台抽屉里的小钥匙",
    "related_thread": "thread_hidden_room",
    "discover_routes": [
      {
        "location_id": "location_frontdesk",
        "object_id": "obj_frontdesk_drawer",
        "action": "search",
        "difficulty": 1
      }
    ],
    "on_discovered": {
      "add_known_fact": "前台抽屉深处藏着一把小钥匙。",
      "add_inventory_item": "item_small_key",
      "trigger_event": "发现前台抽屉里的小钥匙",
      "plot_progress": 8
    }
  }
]
```

---

## 12. OpenThreadSeedGenerator：悬念池自动生成

### 12.1 示例

```json
[
  {
    "thread_id": "thread_linxue_missing",
    "question": "林雪为什么会来到旧医院？",
    "priority": 10,
    "status": "open",
    "opened_at_chapter": 1
  },
  {
    "thread_id": "thread_recent_entry",
    "question": "是谁近期进入了旧医院？",
    "priority": 8,
    "status": "open",
    "opened_at_chapter": 1
  },
  {
    "thread_id": "thread_hidden_room",
    "question": "前台抽屉里的小钥匙能打开哪里？",
    "priority": 6,
    "status": "open",
    "opened_at_chapter": 1
  },
  {
    "thread_id": "thread_fifth_floor",
    "question": "午夜出现的五楼究竟是什么？",
    "priority": 10,
    "status": "open",
    "opened_at_chapter": 1
  }
]
```

---

## 13. OpeningChapterGoalGenerator：第一章目标生成

### 13.1 第一章必须包含

```text
1. 明确主角目标
2. 明确私人动机
3. 一个核心地点
4. 2–3 个核心线索
5. 一个阻力来源
6. 一个轻微灵异钩子
7. 一个具体结尾悬念
```

### 13.2 示例 opening_chapter_plan.json

```json
{
  "chapter_no": 1,
  "chapter_function": "建立旧医院异常，确认林雪可能进入过这里",
  "protagonist_goal": "找到林雪失踪前留下的第一个痕迹",
  "personal_stakes": "林舟曾经没有相信林雪最后一次求助",
  "must_events": [
    "发现医院锁被更换过",
    "发现新鲜脚印",
    "发现林雪相关痕迹"
  ],
  "selected_clues": [
    "clue_new_lock_core",
    "clue_fresh_footprints",
    "clue_linxue_mark"
  ],
  "obstacle": {
    "type": "reluctant_witness",
    "character_id": "npc_gatekeeper"
  },
  "ending_hook": {
    "type": "personalized_clue",
    "content": "钥匙柄背面刻着林雪名字的缩写 LX"
  },
  "forbidden_reveals": [
    "五楼真实来源",
    "十年前完整事故真相",
    "隐藏行动者真实身份"
  ]
}
```

---

## 14. MultiAgentScheduler：多角色自由活动

### 14.1 目标

每个 tick 不只让主角行动，而是让多个 active_agent 行动。

### 14.2 伪代码

```python
class MultiAgentScheduler:
    def step(self, world_state, characters, plot_context):
        active_agents = [
            c for c in characters
            if c.get("active_agent") and self.can_act_now(c, world_state)
        ]

        events = []

        for agent in active_agents:
            action = self.agent_policy.decide(agent, world_state, plot_context)
            result = self.environment.apply(action, world_state)
            events.append(result)

        return events
```

### 14.3 调度顺序

```text
1. 主角行动
2. 当前地点 NPC 响应
3. 隐藏行动者行动
4. 世界规则触发
5. Director 检查是否需要纠偏
```

### 14.4 隐藏行动者

隐藏角色可以行动，但不直接暴露在正文中。

示例：

```json
{
  "event_id": "evt_hidden_actor_001",
  "actor_id": "npc_hidden_actor",
  "action": "move",
  "from_location": "location_frontdesk",
  "to_location": "location_basement",
  "visible_to_protagonist": false,
  "leaves_trace": {
    "object_id": "obj_fresh_footprints",
    "location_id": "location_hallway",
    "description": "地面上有几道新鲜脚印，一直延伸到走廊深处。"
  }
}
```

NarrativeWriter 只能写：

```text
地面上有几道新鲜脚印，一直延伸到走廊深处。
```

不能写：

```text
未知男人走进了地下室。
```

---

## 15. Director 改造：从 environment_hint 改成 clue_route_hint

### 15.1 当前错误格式

```json
{
  "intervention_type": "environment_hint",
  "content": "前台后方有一只抽屉微微敞开"
}
```

这个格式只能制造氛围，不能推进剧情。

### 15.2 新格式

```json
{
  "need_intervention": true,
  "reason": "当前 PlotArc setup 阶段缺少 required_event：发现医院锁被更换过",
  "intervention_type": "clue_route_hint",
  "source": {
    "type": "world_object",
    "source_character_id": "npc_hidden_actor",
    "in_world_reason": "隐藏行动者近期打开过医院大门"
  },
  "target_location": "location_gate",
  "creates_object": {
    "object_id": "obj_gate_lock",
    "object_type": "inspectable_trace",
    "description": "门锁锈得厉害，锁芯却干净得反常，边缘有新鲜划痕。",
    "allowed_actions": ["inspect"]
  },
  "on_successful_action": {
    "action": "inspect",
    "discover_clue_id": "clue_new_lock_core",
    "trigger_event": "发现医院锁被更换过",
    "add_known_fact": "旧医院的门锁近期被人使用或更换过。",
    "plot_progress": 12
  },
  "forbidden_effects": [
    "不能直接暴露五楼真实来源",
    "不能直接说明隐藏行动者身份"
  ]
}
```

### 15.3 Director 优先级

Director 必须按这个顺序补：

```text
1. 当前 PlotArc stage 的 required_events
2. 当前 ChapterGoal 的 must_events
3. 当前 OpenThread 的推进需求
4. 当前 EvidenceGraph 的 discover_route 缺口
5. 当前角色目标的阻力或机会
6. 普通氛围 hint
```

---

## 16. InterventionDeduplicator：干预去重

### 16.1 目的

防止重复生成：

```text
抽屉
脚印
抽屉
脚印
```

### 16.2 规则

每个 intervention 必须有：

```json
{
  "hint_key": "location_frontdesk_obj_drawer_open"
}
```

去重逻辑：

```python
class DirectorInterventionDeduplicator:
    def is_duplicate(self, intervention, world_state, recent_interventions):
        hint_key = intervention.get("hint_key")

        if hint_key in recent_interventions:
            return True

        for obj in world_state.get("objects", {}).values():
            if obj.get("hint_key") == hint_key:
                return True

        return False
```

---

## 17. ActionResolver 改造

### 17.1 目标

如果当前地点有可交互高价值对象，Agent 应优先 inspect/search，而不是继续 move。

### 17.2 伪代码

```python
class ActionResolver:
    def choose_action(self, agent, world_state, plot_context):
        location_id = agent["location_id"]

        actionable_objects = self.find_actionable_objects(
            world_state=world_state,
            location_id=location_id,
            only_unresolved=True
        )

        if actionable_objects:
            obj = self.prioritize(actionable_objects)

            if "inspect" in obj["allowed_actions"]:
                return {"type": "inspect", "target_id": obj["object_id"]}

            if "search" in obj["allowed_actions"]:
                return {"type": "search", "target_id": obj["object_id"]}

        return self.default_policy(agent, world_state, plot_context)
```

---

## 18. ClueDiscoveryResolver

### 18.1 目标

当角色执行 inspect/search 时，把对象转成 clue discovery。

发现线索后必须更新：

```text
world.discovered_facts
plot_arc_state.discovered_clue_ids
character.known_facts
character.inventory
open_threads
event_log
chapter_goal_progress
```

### 18.2 伪代码

```python
class ClueDiscoveryResolver:
    def resolve(self, action, world_state, clues):
        route = self.match_discover_route(action, clues)

        if not route:
            return None

        clue = self.get_clue(route["clue_id"])
        result = clue["on_discovered"]

        self.mark_clue_discovered(clue["clue_id"])
        self.add_known_fact(action["actor_id"], result.get("add_known_fact"))
        self.add_inventory_item(action["actor_id"], result.get("add_inventory_item"))
        self.trigger_event(result.get("trigger_event"))
        self.add_plot_progress(result.get("plot_progress", 0))

        return {
            "event_type": "clue_discovered",
            "clue_id": clue["clue_id"],
            "visible_to": [action["actor_id"]],
            "narrative_summary": result.get("add_known_fact")
        }
```

---

## 19. VisibleEventFilter

### 19.1 作用

沙盘里可以有隐藏角色行动，但正文只写主角可感知部分。

### 19.2 规则

```text
主角亲眼看到的事件：可写
主角听到的声音：可写
主角发现的痕迹：可写
隐藏角色真实行动：不可直接写
系统真相：不可直接写
NPC 内心：除非 POV 允许，否则不可写
```

---

## 20. WriterStoryAnchorGenerator

### 20.1 作用

防止 NarrativeWriter 写成通用模板。

必须生成 writer_story_anchors.json：

```json
{
  "title": "绝命旧院",
  "protagonist_name": "林舟",
  "protagonist_goal": "寻找失踪妹妹林雪的踪迹",
  "personal_stakes": "林舟曾经没有相信林雪关于旧医院的求助",
  "current_chapter_goal": "确认旧医院近期是否有人进入，并找到林雪可能留下的第一个痕迹",
  "main_question": "林雪是否进入过这座旧医院？",
  "required_emotional_beat": "林舟想起最后一次敷衍林雪的电话",
  "forbidden_generic_phrases": [
    "神秘之地",
    "发现真相",
    "重要的东西",
    "说不清的直觉",
    "有些问题只有走进去才能找到答案",
    "我已经做好继续走下去的准备"
  ]
}
```

### 20.2 Prompt 要求

NarrativeWriter 必须拿到：

```text
主角是谁
主角为什么来
主角当前目标
他如果失败会失去什么
本章必须推进哪条悬念
本章已发现哪些线索
本章结尾钩子是什么
禁止哪些泛化表达
```

---

## 21. BootstrapValidator

### 21.1 目的

防止生成不可运行配置。

### 21.2 校验项

```text
1. 至少有 1 个主角 active_agent。
2. 至少有 2 个 NPC active_agent。
3. 至少有 1 个 hidden_actor。
4. 至少有 5 个 location。
5. 至少有 3 个第一章可发现 clue。
6. 每个 clue 必须有 discover_route。
7. 每个 discover_route 必须对应真实 location 和 object。
8. PlotArc setup 必须有 required_event。
9. ChapterGoal must_events 必须能通过 clue_route 触发。
10. NarrativeWriter 必须有 story_anchors。
11. TruthChain 必须存在。
12. EvidenceGraph 必须存在。
```

### 21.3 校验失败示例

```json
{
  "passed": false,
  "issues": [
    {
      "type": "not_enough_active_agents",
      "message": "当前只有主角可行动，至少需要 2 个 NPC active_agent。"
    },
    {
      "type": "missing_discover_route",
      "message": "clue_frontdesk_key 没有 discover_route。"
    }
  ]
}
```

---

## 22. API 设计

### 22.1 生成 Bootstrap

```http
POST /api/story/bootstrap
```

请求：

```json
{
  "user_seed": "废弃医院，午夜出现五楼，主角调查失踪妹妹",
  "target_genre": "horror_suspense",
  "target_words": 100000,
  "auto_confirm": false
}
```

响应：

```json
{
  "bootstrap_id": "boot_001",
  "world_id": "world_old_hospital_001",
  "status": "candidate_generated",
  "summary": {
    "title": "绝命旧院",
    "characters": 5,
    "locations": 6,
    "clues": 5,
    "open_threads": 4
  }
}
```

### 22.2 查看候选

```http
GET /api/story/bootstrap/{bootstrap_id}
```

### 22.3 确认候选

```http
POST /api/story/bootstrap/{bootstrap_id}/confirm
```

### 22.4 确认并启动模拟

```http
POST /api/story/bootstrap/{bootstrap_id}/start
```

---

## 23. 前端页面建议

### 23.1 模糊设定输入页

字段：

```text
一句话设定
目标题材
目标字数
自动补全强度
是否人工审核
```

按钮：

```text
生成可运行故事世界
```

### 23.2 Bootstrap Preview 页面

展示：

```text
世界标题
故事简介
核心真相候选
角色列表
地图
第一章目标
初始线索
悬念池
风险提示
```

操作：

```text
确认并启动
修改
重新生成
只重新生成角色
只重新生成线索
只重新生成真相链
```

---

## 24. DoD 验收标准

功能完成后必须满足：

```text
1. 用户只输入一句模糊设定，也能生成完整 world_bible。
2. 自动生成至少 1 个主角、2 个 NPC、1 个隐藏行动者。
3. 自动生成至少 5 个地点。
4. 自动生成 TruthChain。
5. 自动生成 EvidenceGraph。
6. 自动生成至少 3 个第一章可发现线索。
7. 每个线索都有 discover_route。
8. 每个 discover_route 都能触发 known_fact / clue_discovered / plot_event。
9. Scheduler 能让多个 active_agent 行动。
10. hidden_actor 可以行动，但正文只显示痕迹。
11. Director 不再重复生成同类 hint。
12. Director 优先补 PlotArc required_event。
13. NarrativeWriter 不再输出 Mysterious Place / 神秘之地 / 发现真相 等泛化表达。
14. 第一章必须包含具体主角目标。
15. 第一章必须有个人情感动机。
16. 第一章至少发现 1 个有效线索。
17. 运行结束时 discovered_clues 不得为 0。
18. 运行结束时主角 known_facts 不得为空。
19. 运行结束时至少有 1 个 unresolved_thread。
20. 章节正文必须围绕具体人物、具体目标、具体线索展开。
```

---

## 25. 实现优先级

### P0：必须先做

```text
1. StoryBootstrapper
2. MinimumCastGenerator
3. ClueRouteGenerator
4. BootstrapValidator
5. MultiAgentScheduler
6. ClueDiscoveryResolver
7. NarrativeWriter story_anchors 注入
```

### P1：强烈建议

```text
1. DirectorClueRouteIntervention
2. DirectorInterventionDeduplicator
3. VisibleEventFilter
4. OpeningChapterPlanGenerator
5. CandidateReview 页面
```

### P2：后续增强

```text
1. 多 seed 自动生成
2. 用户偏好学习
3. 不同题材 bootstrap template
4. 自动评估 bootstrap 质量
5. 自动生成多个故事方案供选择
```

---

## 26. 推荐实现顺序

```text
第一步：StoryBootstrapper 生成完整候选配置
第二步：BootstrapValidator 检查配置能否运行
第三步：ClueRouteGenerator 确保线索可发现
第四步：MinimumCastGenerator 确保多角色
第五步：MultiAgentScheduler 确保多角色行动
第六步：ClueDiscoveryResolver 确保 hint 转 clue
第七步：NarrativeWriter 注入 story_anchors
第八步：Director 改为 clue_route_hint
第九步：VisibleEventFilter 控制隐藏角色叙事
第十步：前端 Bootstrap Preview
```

---

## 27. 预期效果

用户输入：

```text
废弃医院，午夜出现五楼，主角调查失踪妹妹
```

系统自动生成：

```text
标题：绝命旧院
主角：林舟
失踪者：林雪
阻碍者：看门人老周
目击者：小卖部老板赵婶
隐藏行动者：未知男人
地图：大门、前台、走廊、病案室、地下室、小卖部
第一章线索：新锁芯、新脚印、林雪记号、小钥匙
主线悬念：林雪为什么来旧医院、谁近期进过医院、五楼是什么
第一章目标：确认旧医院近期有人进入，并发现林雪可能留下的第一个痕迹
```

运行后 state 至少应出现：

```json
{
  "discovered_clue_ids": [
    "clue_new_lock_core"
  ],
  "known_facts": [
    "旧医院的门锁近期被人使用或更换过。"
  ],
  "unresolved_questions": [
    "是谁近期进入了旧医院？",
    "林雪是否进入过这里？"
  ]
}
```

而不是：

```json
{
  "discovered_clue_ids": [],
  "known_facts": [],
  "inventory": []
}
```

---

## 28. 总结

这个补全功能要解决的核心问题是：

```text
用户只给模糊设定时，系统不能直接开始模拟。
系统必须先自动补全一个能运转的故事世界。
```

新增 StoryBootstrapper 后，流程变为：

```text
用户给模糊设定
↓
系统自动补全世界、角色、地图、线索、真相链
↓
多角色开始行动
↓
隐藏角色留下痕迹
↓
主角通过调查发现线索
↓
线索推进 PlotArc
↓
NarrativeWriter 根据真实事件总结成小说
```

一句话：

> 这不是单纯提升 AI 文笔，而是让沙盘先拥有一个完整、可运行、会自行产生事件的故事世界。
