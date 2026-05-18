# V4.1 开发计划：Dynamic NPC Introduction 受控动态 NPC 生成与引入

> 版本主题：在适当时机动态引入 NPC，保证剧情能继续运行，同时避免角色乱生成、剧透和设定失控。  
> 推荐模块名：`DynamicCharacterIntroductionService`  
> 备用模块名：`NPCIntroductionService` / `ControlledNPCSpawnService`

---

## 0. 背景

V4 已经具备：

```text
World Studio
多 Agent 调度
NPC 分层
人工干预
事件回放
章节连续性
剧情弧
人物弧
配置校验
```

但是如果所有 NPC 都必须在一开始预先定义，会出现几个问题：

```text
1. 世界配置成本过高
2. 用户不可能提前想到所有可能出现的人
3. 剧情运行中可能需要新证人、新阻碍者、新信息来源
4. 某些 open_thread 可能因为缺少合适 NPC 而无法推进
5. 某些地点本应有人，但配置中没有 NPC，会显得世界很空
6. 如果完全让 LLM 自由生成 NPC，又会出现乱加角色、剧透、设定冲突
```

因此 V4.1 要实现：

> 受控动态 NPC 生成与引入机制。

核心思想：

```text
不是“随便生成 NPC”
而是“当剧情缺口真实存在时，生成一个受约束的角色需求 RoleSpec，再基于 RoleSpec 生成、校验、注册和引入 NPC”
```

---

## 1. V4.1 总目标

V4.1 要实现：

```text
1. 检测什么时候需要新 NPC
2. 在生成前优先复用已有角色
3. 生成 RoleSpec，而不是直接生成角色
4. 根据 RoleSpec 生成候选 NPC
5. 校验候选 NPC 是否符合世界、剧情阶段、知识边界
6. 规划 NPC 合理出场方式
7. 将 NPC 注册到动态角色库
8. 将 NPC 出场写入 EventLog
9. 将 NPC 纳入 Scheduler / NPC Response Engine
10. 关键 NPC 生成前可要求用户确认
```

一句话：

> 让系统在剧情需要时自然引入新角色，但所有新角色都必须有叙事功能、知识边界和生命周期管理。

---

## 2. 核心原则

### 2.1 需求驱动，而不是随机生成

动态 NPC 只能因为明确需求出现。

允许触发原因：

```text
1. open_thread 长时间未推进
2. clue 的所有 discover_route 不可用
3. 当前地点合理需要 NPC
4. 当前剧情缺少冲突或阻碍
5. Director 判断需要新信息源
6. 用户显式要求引入新角色
```

禁止：

```text
1. 为了热闹随机加角色
2. 为了写得神秘突然加神秘人
3. 为了推进剧情直接生成真相持有者
4. 为了方便解释世界观添加全知 NPC
```

### 2.2 先 RoleSpec，后 NPC

不要直接让 LLM 生成“一个神秘老人”。

必须先生成：

```text
这个角色为什么需要
他承担什么叙事功能
他能知道什么
他不能知道什么
他适合出现在什么地点
他是临时角色还是长期角色
```

流程：

```text
NeedDetector → RoleSpecGenerator → CandidateGenerator
```

### 2.3 优先复用已有角色

生成新 NPC 前必须先检查：

```text
已有角色能不能承担这个功能？
已有 NPC 是否可以新增 topic？
已有地点对象是否可以承载线索？
已有 open_thread 是否可以通过已有角色推进？
```

只有复用失败，才生成新 NPC。

### 2.4 知识边界必须严格

动态 NPC 最大风险是：

```text
知道太多
剧透
直接解释核心真相
打破 PlotArc 阶段锁
```

所以每个动态 NPC 必须有：

```text
allowed_knowledge
forbidden_knowledge
allowed_clue_levels
forbidden_revelations
```

### 2.5 关键 NPC 需要人工确认

推荐策略：

```text
ephemeral / scene_npc：可自动生成
recurring_npc：自动生成但必须通过 validator
major_npc：默认需要用户确认
core_character：不允许自动生成，除非用户显式开启
```

---

## 3. NPC 类型与持久化等级

### 3.1 ephemeral

一次性临时角色。

适合：

```text
路人
临时司机
排队的人
围观者
```

配置：

```json
{
  "persistence": "ephemeral",
  "store_in_registry": false,
  "memory_enabled": false,
  "scheduler_enabled": false
}
```

---

### 3.2 scene_npc

只在当前场景有效。

适合：

```text
值班店员
档案馆工作人员
临时警员
医院前台
```

配置：

```json
{
  "persistence": "scene_npc",
  "store_in_registry": true,
  "available_until": "scene_end",
  "memory_enabled": "minimal",
  "scheduler_enabled": false
}
```

---

### 3.3 recurring_npc

后续可以重复出现。

适合：

```text
附近小卖部老板
看门人朋友
旧案目击者
记者线人
```

配置：

```json
{
  "persistence": "recurring_npc",
  "store_in_registry": true,
  "memory_enabled": "light",
  "relationship_enabled": true,
  "scheduler_enabled": "reactive"
}
```

---

### 3.4 major_npc

重要 NPC。

适合：

```text
关键证人
反派代理人
主角过去认识的人
重要组织代表
```

配置：

```json
{
  "persistence": "major_npc",
  "store_in_registry": true,
  "memory_enabled": "full",
  "relationship_enabled": true,
  "character_arc_enabled": true,
  "scheduler_enabled": true,
  "requires_user_approval": true
}
```

---

## 4. 叙事功能类型

动态 NPC 必须绑定一个 `narrative_function`。

推荐枚举：

```text
clue_holder：持有部分线索的人
witness：目击者
obstructor：阻碍者
helper：帮助者
misleader：误导者
connector：连接地点/人物/组织的人
messenger：传递信息的人
authority：有制度权力的人
victim_related：受害者相关人物
villain_proxy：反派代理人
crowd_flavor：氛围角色
```

### 4.1 clue_holder

可以提供部分线索，但不能直接给答案。

限制：

```text
只能透露当前 PlotArc stage 允许的 clue level
不能透露 truth 级信息
必须通过 reveal_condition 才能透露
```

### 4.2 witness

提供感官事实。

可说：

```text
看见谁来过
听见什么声音
记得某个时间点
看见某个物品
```

不可说：

```text
背后动机
真相解释
反派身份
核心规则
```

### 4.3 obstructor

制造阻碍或冲突。

可做：

```text
阻止进入地点
拒绝回答
警告离开
拖延时间
要求证明身份
```

### 4.4 misleader

提供误导信息。

要求：

```text
必须进入 false_belief 系统
必须可被后续线索修正
不能永久污染主线
不能造成无解误导
```

---

## 5. 触发器设计

### 5.1 stale_open_thread

open_thread 长时间未推进。

```json
{
  "trigger_type": "stale_open_thread",
  "thread_id": "thread_who_changed_lock",
  "stale_chapters": 2,
  "stale_ticks": 20,
  "action": "consider_new_npc"
}
```

触发条件：

```text
open_thread.priority >= threshold
连续 N tick 或 N 章没有相关 progress event
现有角色无法自然推进
```

---

### 5.2 unavailable_clue_route

关键线索所有路径不可用。

```json
{
  "trigger_type": "unavailable_clue_route",
  "clue_id": "hf_004",
  "reason": "all_routes_blocked_or_expired",
  "action": "create_alternative_route_via_npc"
}
```

---

### 5.3 location_requires_population

当前地点合理需要 NPC。

```json
{
  "trigger_type": "location_requires_population",
  "location_id": "archive_office",
  "expected_npc_types": ["clerk", "security_guard"]
}
```

---

### 5.4 low_conflict

冲突不足。

```json
{
  "trigger_type": "low_conflict",
  "recommended_role": "obstructor",
  "purpose": "阻止主角继续调查"
}
```

---

### 5.5 user_request

用户人工要求。

```json
{
  "trigger_type": "user_request",
  "request": "下一章引入一个和主角过去有关的人",
  "requires_user_approval": true
}
```

---

## 6. 总体流程

```text
Simulation Running
↓
NeedDetector.detect
↓
ExistingCharacterReusePlanner.check
↓
如果可复用：
    Add topic / Add route / Adjust reveal_condition
    写入 reuse_plan
否则：
    RoleSpecGenerator.generate
    CandidateGenerator.generate
    CharacterValidator.validate
    如果需要用户确认：
        pending_approval
    如果通过：
        IntroductionPlanner.plan
        CharacterRegistry.register
        EventLog 写入 npc_introduction
        ChapterContinuityService 记录 introduced_characters
```

---

## 7. 模块设计

```text
DynamicCharacterIntroductionService
├── NeedDetector
├── ExistingCharacterReusePlanner
├── RoleSpecGenerator
├── CandidateGenerator
├── CharacterValidator
├── IntroductionPlanner
├── CharacterRegistry
├── ContinuityBinder
└── ApprovalService
```

---

## 7.1 NeedDetector

职责：

```text
1. 读取 open_threads
2. 读取 clue route 状态
3. 读取 current location
4. 读取 ProgressMonitor / Director 报告
5. 判断是否需要新 NPC
6. 输出 CharacterNeed
```

输出：

```json
{
  "need_id": "need_001",
  "need_type": "stale_open_thread",
  "priority": 8,
  "reason": "open_thread '谁换了锁' 连续 2 章未推进",
  "related_thread_id": "thread_who_changed_lock",
  "related_clue_id": "hf_004",
  "suggested_narrative_function": "witness",
  "suggested_location": "old_street_shop"
}
```

---

## 7.2 ExistingCharacterReusePlanner

职责：

```text
1. 查找已有角色是否能承担 narrative_function
2. 检查已有 NPC 是否有合理知识来源
3. 检查是否可以通过新增 topic 或 route 推进
4. 避免不必要的新 NPC
```

输出可复用方案：

```json
{
  "can_reuse_existing_character": true,
  "character_id": "char_guard",
  "reuse_method": "add_topic",
  "new_topic": "recent_repair_worker",
  "reason": "看门人本就负责旧医院大门，可以自然知道换锁相关信息。"
}
```

如果不能复用：

```json
{
  "can_reuse_existing_character": false,
  "reason": "现有角色没有合理渠道知道白色面包车信息。"
}
```

---

## 7.3 RoleSpecGenerator

职责：

```text
将 CharacterNeed 转换为 RoleSpec。
```

RoleSpec 示例：

```json
{
  "role_spec_id": "rs_001",
  "reason": "open_thread 长时间未推进：谁换了医院大门的锁？",
  "needed_for": {
    "plot_arc": "arc_hospital_truth",
    "stage": "investigation",
    "open_thread": "thread_who_changed_lock",
    "target_clue": "hf_004"
  },
  "narrative_function": "witness",
  "allowed_knowledge": [
    "见过有人在三天前进入旧医院",
    "不知道那个人真实身份",
    "知道对方戴着黑色鸭舌帽"
  ],
  "forbidden_knowledge": [
    "不能知道反派真实身份",
    "不能知道十年前事故真相",
    "不能知道旧医院真正规则"
  ],
  "world_constraints": {
    "must_fit_location": "old_street_shop",
    "reasonable_roles": [
      "附近小卖部老板",
      "夜班保安",
      "环卫工",
      "附近居民"
    ],
    "time_availability": "night"
  },
  "importance": "medium",
  "persistence": "recurring_npc"
}
```

---

## 7.4 CandidateGenerator

职责：

```text
根据 RoleSpec 生成 NPC 候选。
```

输出：

```json
{
  "candidate_id": "npc_store_owner_001",
  "character": {
    "name": "赵婶",
    "type": "semi_agent_npc",
    "persistence": "recurring_npc",
    "role": "旧街口小卖部老板",
    "personality": "谨慎、话多但怕惹事",
    "initial_location": "old_street_shop"
  },
  "knowledge_boundary": {
    "known_facts": [
      "三天前夜里见过一辆白色面包车停在旧医院门口",
      "车上下来过一个戴黑色鸭舌帽的人"
    ],
    "unknown_facts": [
      "不知道那个人真实身份",
      "不知道对方为什么去医院",
      "不知道十年前事故真相"
    ],
    "allowed_clue_levels": ["surface", "minor", "medium"],
    "forbidden_revelations": [
      "truth_real_killer",
      "truth_linzho_past"
    ]
  },
  "introduction_hint": "旧街口的小卖部还亮着灯，柜台后坐着一个正在听收音机的中年女人。"
}
```

---

## 7.5 CharacterValidator

职责：

```text
1. 校验是否符合世界时代和地点
2. 校验是否符合当前 PlotArc stage
3. 校验是否携带过高等级线索
4. 校验是否和已有角色重复
5. 校验是否有明确 narrative_function
6. 校验是否有合理出场方式
7. 校验是否会解决过多 open_threads
8. 校验是否会创建无计划新主线
```

校验报告：

```json
{
  "candidate_id": "npc_store_owner_001",
  "passed": true,
  "violations": [],
  "warnings": [
    {
      "type": "role_overlap",
      "message": "该 NPC 与现有看门人都可提供近期出入信息，但小卖部老板拥有地点独立性。",
      "severity": "warning"
    }
  ],
  "suggestions": []
}
```

失败示例：

```json
{
  "candidate_id": "npc_mysterious_old_man_001",
  "passed": false,
  "violations": [
    {
      "type": "overpowered_knowledge",
      "message": "该 NPC 知道反派真实身份，但当前阶段为 investigation，不允许。",
      "severity": "error"
    }
  ],
  "suggestions": [
    "将其知识降级为：只见过白色面包车，不知道车主身份。"
  ]
}
```

---

## 7.6 IntroductionPlanner

职责：

```text
设计 NPC 的合理出场方式。
```

IntroductionPlan：

```json
{
  "introduction_id": "intro_001",
  "character_id": "npc_store_owner_001",
  "introduction_type": "location_presence",
  "location_id": "old_street_shop",
  "timing": "next_scene",
  "entry_event": {
    "event_type": "npc_introduction",
    "description": "旧街口的小卖部还亮着灯，柜台后坐着一个正在听收音机的中年女人。"
  },
  "first_available_topics": [
    "recent_visitors",
    "old_hospital",
    "night_noise"
  ],
  "avoid": [
    "不能主动说出关键线索",
    "不能直接认识主角，除非已有关系设定"
  ]
}
```

出场方式枚举：

```text
location_presence：角色本来就在地点
called_by_someone：被其他角色叫来
encounter：路上偶遇
message_sender：通过电话/短信/纸条出现
institutional_contact：作为机构人员出现
rumor_source：通过他人口中先被提到
flashback_related：与回忆相关，需要阶段允许
```

---

## 7.7 CharacterRegistry

职责：

```text
1. 注册动态 NPC
2. 写入 dynamic_characters.jsonl
3. 更新 npcs.json 或 runtime registry
4. 按 persistence 设置生命周期
5. 将 NPC 纳入 Scheduler / NPC Response Engine
```

注册记录：

```json
{
  "character_id": "npc_store_owner_001",
  "name": "赵婶",
  "type": "semi_agent_npc",
  "persistence": "recurring_npc",
  "introduced_at": {
    "chapter_id": "ch_002",
    "event_id": "evt_0081",
    "location_id": "old_street_shop"
  },
  "narrative_function": "witness",
  "status": "introduced",
  "activation_policy": {
    "type": "reactive"
  }
}
```

---

## 7.8 ContinuityBinder

职责：

```text
1. 将新 NPC 绑定到 ChapterSummary
2. 更新 open_threads
3. 更新 available_contacts
4. 更新 recurring_characters
5. 记录该 NPC 与哪些线索、剧情弧、人物相关
```

ChapterSummary 增强：

```json
{
  "introduced_characters": [
    {
      "character_id": "npc_store_owner_001",
      "name": "赵婶",
      "role": "附近小卖部老板",
      "narrative_function": "witness",
      "known_by": ["char_linzho"],
      "open_threads_created": ["thread_white_van"]
    }
  ]
}
```

---

## 7.9 ApprovalService

职责：

```text
1. 判断是否需要用户确认
2. 暂存候选 NPC
3. 接收用户 approve / reject / modify
4. 将用户修改写入 control_commands.jsonl
```

需要确认的情况：

```text
persistence = major_npc
narrative_function = villain_proxy
新 NPC 与主角过去有关
新 NPC 携带 major 线索
会创建新 open_thread
```

ControlCommand：

```json
{
  "command_id": "cmd_approve_npc_001",
  "type": "approve_dynamic_character",
  "payload": {
    "candidate_id": "npc_store_owner_001",
    "approved": true,
    "modifications": {
      "name": "赵婶",
      "persistence": "recurring_npc"
    }
  }
}
```

---

## 8. Prompt 模板

### 8.1 RoleSpec 生成 Prompt

```text
你是小说沙盘引擎的角色需求分析器。

你的任务不是生成角色，而是判断当前剧情是否需要一个新角色，并生成 RoleSpec。

必须遵守：
1. 只有当现有角色无法自然承担功能时，才建议新角色
2. RoleSpec 必须说明 narrative_function
3. 必须列出 allowed_knowledge 和 forbidden_knowledge
4. 必须符合当前 PlotArc stage
5. 不能引入当前阶段不允许的真相
6. 输出 JSON

【World Context】
{world_context}

【PlotArc State】
{plot_arc_state}

【Open Threads】
{open_threads}

【Existing Characters】
{existing_characters}

【Need】
{character_need}

输出 RoleSpec JSON。
```

---

### 8.2 Candidate NPC 生成 Prompt

```text
你是小说沙盘引擎的 NPC 候选生成器。

你不能自由创作角色。
你必须根据 RoleSpec 生成一个符合世界、地点、剧情阶段和知识边界的 NPC。

要求：
1. NPC 必须服务于 narrative_function
2. NPC 不能知道 forbidden_knowledge
3. NPC 不能直接暴露核心真相
4. NPC 必须有合理社会身份
5. NPC 的出场方式必须符合当前地点和时间
6. 如果普通身份能解决，不要生成神秘人物
7. 输出 JSON，不要输出小说正文

【World Context】
{world_context}

【Plot Stage】
{plot_stage}

【RoleSpec】
{role_spec}

【Existing Characters】
{existing_characters_summary}

输出：
{
  "character": {},
  "knowledge_boundary": {},
  "introduction_hint": "",
  "validation_notes": []
}
```

---

## 9. 与现有模块的关系

### 9.1 与 PlotArcService

PlotArcService 决定：

```text
当前阶段允许生成什么类型 NPC
新 NPC 最多可携带什么 clue level
当前禁止哪些 forbidden_revelations
```

plot_arcs.json 可增加：

```json
{
  "stage_id": "setup",
  "allowed_dynamic_roles": ["crowd_flavor", "witness", "obstructor"],
  "forbidden_dynamic_roles": ["truth_holder", "mastermind", "lost_relative"],
  "max_clue_level_for_new_npc": "minor"
}
```

---

### 9.2 与 ChapterContinuityService

新 NPC 必须进入：

```text
introduced_characters
available_contacts
recurring_characters
open_threads
```

---

### 9.3 与 NPC Response Engine

生成的 NPC 后续被 ask/talk 时，走现有 NPC Response Engine。

必须检查：

```text
reveal_condition
knowledge_boundary
PlotArc stage
relationship
topic
```

---

### 9.4 与 Human-in-the-loop

用户可以：

```text
开启或关闭自动 NPC 生成
要求 major_npc 生成前确认
拒绝某个候选 NPC
修改 NPC 名字和身份
将 scene_npc 升级为 recurring_npc
将 NPC 标记为 retired
```

---

## 10. 配置项

```json
{
  "dynamic_character_introduction": {
    "enabled": true,
    "prefer_reuse_existing": true,
    "max_new_characters_per_chapter": 2,
    "max_major_npc_per_arc": 3,
    "allow_ephemeral_npc": true,
    "allow_scene_npc": true,
    "allow_recurring_npc": true,
    "allow_major_npc_generation": false,
    "require_user_approval_for_major_npc": true,
    "require_user_approval_for_past_related_npc": true,
    "stale_open_thread_chapter_threshold": 2,
    "stale_open_thread_tick_threshold": 20,
    "auto_register_scene_npc": true
  }
}
```

---

## 11. 生命周期

动态 NPC 生命周期：

```text
needed
role_spec_generated
candidate_generated
validated
pending_approval
approved
introduced
active
recurring
promoted
retired
rejected
```

状态变化示例：

```text
needed
↓
role_spec_generated
↓
candidate_generated
↓
validated
↓
introduced
↓
recurring
```

---

## 12. 角色升级机制

临时 NPC 可以升级。

升级条件：

```text
参与多个 plot event
与主角关系变化明显
持有关键信息
用户标记为重要
Director 判断可复用
```

升级记录：

```json
{
  "character_id": "npc_store_owner_001",
  "from": "scene_npc",
  "to": "recurring_npc",
  "reason": "该角色已参与 3 个 plot event，并持有后续线索入口。",
  "event_id": "evt_0120"
}
```

---

## 13. 文件结构

```text
app/
  services/
    dynamic_character_introduction_service.py
    need_detector.py
    existing_character_reuse_planner.py
    role_spec_generator.py
    candidate_generator.py
    character_validator.py
    introduction_planner.py
    character_registry.py
    continuity_binder.py
    approval_service.py

  prompts/
    role_spec_generation_prompt.txt
    dynamic_npc_candidate_prompt.txt

worlds/
  dark_city_001/
    dynamic_character_policy.json

outputs/
  sim_xxx/
    dynamic_character_needs.jsonl
    role_specs.jsonl
    npc_candidates.jsonl
    dynamic_character_validation_reports.jsonl
    introduction_plans.jsonl
    dynamic_characters.jsonl
    introduced_characters.jsonl
    control_commands.jsonl
```

---

## 14. EventLog 增强

### 14.1 npc_introduction

```json
{
  "event_id": "evt_npc_intro_001",
  "event_type": "npc_introduction",
  "character_id": "npc_store_owner_001",
  "location_id": "old_street_shop",
  "result": "旧街口的小卖部还亮着灯，柜台后坐着一个正在听收音机的中年女人。",
  "visible_to": ["char_linzho"],
  "introduced_character": {
    "name": "赵婶",
    "type": "semi_agent_npc",
    "persistence": "recurring_npc",
    "narrative_function": "witness"
  }
}
```

---

### 14.2 npc_reuse

```json
{
  "event_id": "evt_npc_reuse_001",
  "event_type": "npc_reuse",
  "character_id": "char_guard",
  "reuse_method": "add_topic",
  "new_topic": "recent_repair_worker",
  "reason": "复用看门人作为换锁信息入口。"
}
```

---

## 15. 验收用例

### 用例 1：open_thread 卡住触发 NPC 需求

条件：

```text
thread_who_changed_lock 连续 2 章未推进
```

预期：

```text
NeedDetector 生成 CharacterNeed
RoleSpecGenerator 生成 RoleSpec
```

---

### 用例 2：优先复用已有 NPC

条件：

```text
已有看门人可以提供换锁相关 topic
```

预期：

```text
ExistingCharacterReusePlanner 返回 can_reuse_existing_character = true
不生成新 NPC
```

---

### 用例 3：生成 witness NPC

条件：

```text
现有角色无法提供白色面包车线索
当前地点附近有小卖部
```

预期：

```text
生成小卖部老板作为 witness
知识边界不包含反派身份
```

---

### 用例 4：阻止过强 NPC

条件：

```text
Candidate NPC 知道反派真实身份
current_stage = investigation
```

预期：

```text
CharacterValidator 拒绝
violations 包含 overpowered_knowledge
```

---

### 用例 5：major_npc 需要人工确认

条件：

```text
Candidate persistence = major_npc
```

预期：

```text
状态进入 pending_approval
不会直接 introduced
```

---

### 用例 6：NPC 出场后可被询问

条件：

```text
npc_store_owner_001 已 introduced
```

预期：

```text
AgentContext 出现该 NPC
available_topics 包含 recent_visitors
ask 后走 NPC Response Engine
```

---

### 用例 7：ChapterSummary 记录新角色

条件：

```text
ch_002 引入赵婶
```

预期：

```text
chapter_summary.introduced_characters 包含 npc_store_owner_001
```

---

## 16. Metrics

新增指标：

```json
{
  "dynamic_characters": {
    "needs_detected": 4,
    "reuse_success_count": 2,
    "npc_candidates_generated": 2,
    "npc_candidates_rejected": 1,
    "npc_introduced": 1,
    "major_npc_pending_approval": 0,
    "average_validation_errors": 0.5
  }
}
```

---

## 17. DoD

```text
1. open_thread 长时间未推进时能触发 CharacterNeed
2. clue route 全部不可用时能触发 CharacterNeed
3. 生成新 NPC 前必须先尝试复用已有角色
4. RoleSpec 必须包含 narrative_function / allowed_knowledge / forbidden_knowledge
5. Candidate NPC 不能携带当前阶段不允许的线索
6. CharacterValidator 能拦截 overpowered_knowledge
7. scene_npc 可以自动引入
8. recurring_npc 必须通过 validator
9. major_npc 默认需要用户确认
10. 新 NPC 出场写入 EventLog
11. 新 NPC 注册到 dynamic_characters.jsonl
12. ChapterSummary 记录 introduced_characters
13. 新 NPC 后续可被 Scheduler / NPC Response Engine 使用
14. 系统能限制每章最大新 NPC 数量
15. MetricsCollector 能统计动态 NPC 生成情况
```

---

## 18. MVP 范围

V4.1 MVP 只做：

```text
1. NeedDetector
2. ExistingCharacterReusePlanner
3. RoleSpecGenerator
4. CandidateGenerator
5. CharacterValidator
6. IntroductionPlanner
7. CharacterRegistry
```

MVP 暂不做：

```text
复杂人物弧
自动生成核心角色
复杂势力关系
大规模 NPC 社会网络
多候选排序系统
```

---

## 19. 推荐开发顺序

```text
1. dynamic_character_policy.json
2. NeedDetector
3. ExistingCharacterReusePlanner
4. RoleSpec 数据结构
5. Candidate 数据结构
6. CharacterValidator
7. CandidateGenerator
8. IntroductionPlanner
9. CharacterRegistry
10. EventLog npc_introduction
11. ChapterSummary introduced_characters
12. NPC Response Engine 接入
13. ApprovalService
14. Metrics
```

---

## 20. 一句话总结

V4.1 的核心不是“生成更多 NPC”，而是：

> 在剧情需要时，以受控、可校验、可追踪、可复用的方式引入新角色。

正确流程是：

```text
剧情缺口驱动
↓
优先复用已有角色
↓
RoleSpec 先行
↓
生成候选 NPC
↓
知识边界校验
↓
PlotArc 阶段校验
↓
合理出场
↓
注册到角色系统
↓
进入后续调度和章节连续性
```
