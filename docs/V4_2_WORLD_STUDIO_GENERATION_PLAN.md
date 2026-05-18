# V4.2 开发计划：World Studio 生成增强版

> 版本主题：在页面中生成随机角色、NPC、地点、线索与配置候选，降低创作者配置成本。  
> 目标：让用户不用手写大量 JSON，可以在页面内通过“生成候选 → 编辑 → 校验 → 确认入库”的方式快速完善小说世界。

---

## 0. 背景

V4.1 已经解决了动态 NPC 引入问题：

```text
剧情运行中，如果 open_thread 卡住、线索路径不可用、地点缺少合理 NPC，系统可以受控生成 NPC 候选。
```

但 V4.1 更偏运行时机制。

V4.2 要解决的是创作阶段的问题：

```text
1. 用户创建世界时，不知道该配置哪些角色
2. 用户不想手写角色卡、NPC、地点、线索
3. 用户希望快速生成一批候选角色
4. 用户希望随机生成但又不能破坏世界设定
5. 用户希望在页面里挑选、编辑、确认
6. 生成的角色要能通过 ConfigValidator
7. 生成结果要能直接进入 characters.json / npcs.json / clues.json
```

一句话：

> V4.2 是 World Studio 的生成增强版本，让用户能在页面里生成、筛选、编辑并接入随机角色和世界配置。

---

## 1. V4.2 总目标

实现页面内生成能力：

```text
1. 随机生成主角候选
2. 随机生成配角候选
3. 随机生成 NPC 候选
4. 随机生成反派 / 阻碍者候选
5. 随机生成地点候选
6. 随机生成线索候选
7. 随机生成角色关系网
8. 随机生成角色初始秘密
9. 随机生成角色目标与冲突
10. 生成后支持编辑、校验、确认入库
```

核心流程：

```text
用户输入世界方向
↓
点击生成
↓
生成候选列表
↓
用户筛选 / 编辑
↓
ConfigValidator 校验
↓
确认写入世界配置
```

---

## 2. 核心原则

### 2.1 生成的是候选，不是直接入库

系统不能自动把所有生成结果写进正式配置。

正确流程：

```text
Generate Candidate
↓
Preview
↓
Edit
↓
Validate
↓
Approve
↓
Commit to world config
```

这样避免随机生成污染世界。

---

### 2.2 生成必须受世界约束

随机角色不能脱离已有世界设定。

生成时必须参考：

```text
world_bible
genre
tone
era
rules
themes
existing_characters
existing_locations
plot_arcs
forbidden_revelations
```

例如悬疑灵异现代都市世界中，不能随机生成：

```text
中世纪骑士
星际舰长
知道全部真相的神秘先知
```

---

### 2.3 生成必须有叙事功能

每个角色候选必须说明：

```text
他为什么存在
能制造什么冲突
能提供什么线索
和谁有关
是否可能重复出现
```

不要生成“好看但无用”的角色。

---

### 2.4 生成后必须可校验

所有候选都必须通过：

```text
SchemaValidator
ReferenceValidator
PlotStageValidator
KnowledgeBoundaryValidator
DuplicationValidator
```

---

## 3. 页面功能总览

V4.2 建议新增这些页面或面板：

```text
Character Generator
NPC Generator
Relationship Generator
Location Generator
Clue Generator
Secret Generator
Candidate Review Panel
Batch Commit Panel
Generation History
```

---

# 4. Character Generator 角色生成器

## 4.1 目标

在页面中生成主角、配角、反派、关键 NPC 候选。

---

## 4.2 生成入口

用户可选择：

```text
生成主角候选
生成配角候选
生成反派候选
生成关键 NPC
生成普通 NPC
生成一组角色
```

---

## 4.3 用户输入参数

```json
{
  "world_id": "dark_city_001",
  "character_type": "supporting_character",
  "count": 5,
  "genre": "悬疑灵异",
  "tone": "克制、压抑、现实中透出诡异",
  "must_fit_locations": ["old_hospital_gate", "old_street_shop"],
  "preferred_functions": ["witness", "obstructor", "clue_holder"],
  "forbidden_functions": ["truth_holder"],
  "allowed_secret_level": "minor",
  "randomness": 0.7
}
```

---

## 4.4 CharacterCandidate 数据结构

```json
{
  "candidate_id": "char_candidate_001",
  "candidate_type": "supporting_character",
  "name": "许曼",
  "role": "地方新闻记者",
  "agent_type": "full_npc_agent",
  "narrative_function": "connector",
  "summary": "一个追查旧医院火灾旧案的记者，掌握公开档案和旧新闻线索，但不知道核心真相。",
  "traits": ["敏锐", "强势", "有职业执念"],
  "goals": {
    "short_term": "找到旧医院火灾的新闻价值",
    "long_term": "证明当年的报道被人为压下"
  },
  "skills": {
    "observation": 65,
    "social": 75,
    "logic": 70,
    "courage": 60
  },
  "initial_location": "old_street_shop",
  "knowledge_boundary": {
    "known_facts": [
      "旧医院十年前发生过火灾",
      "当年的报道很快被撤下"
    ],
    "unknown_facts": [
      "不知道林舟与事故的关系",
      "不知道真正幕后人物"
    ],
    "allowed_clue_levels": ["surface", "minor", "medium"],
    "forbidden_revelations": ["truth_linzho_past", "truth_real_killer"]
  },
  "relationships_suggestions": [
    {
      "target": "char_linzho",
      "type": "potential_ally",
      "initial_attitude": 10,
      "reason": "她认为林舟可能掌握旧医院线索。"
    }
  ],
  "plot_hooks": [
    "她可以提供旧报纸线索",
    "她会推动主角去档案馆",
    "她可能和看门人发生冲突"
  ],
  "validation_status": "pending"
}
```

---

## 4.5 页面操作

每个候选角色支持：

```text
预览
重新生成
局部重写
编辑字段
查看风险
运行校验
批准入库
丢弃
标记为稍后使用
```

---

## 4.6 入库目标

根据类型写入：

```text
characters.json
npcs.json
dynamic_character_pool.json
```

---

# 5. NPC Generator 随机 NPC 生成器

## 5.1 目标

生成适合某个地点、某个剧情阶段、某个叙事功能的 NPC。

---

## 5.2 生成类型

```text
地点 NPC
线索 NPC
阻碍 NPC
目击者 NPC
氛围 NPC
机构 NPC
反派代理人候选
```

---

## 5.3 输入参数

```json
{
  "location_id": "old_street_shop",
  "plot_stage": "investigation",
  "npc_type": "semi_agent_npc",
  "narrative_function": "witness",
  "count": 3,
  "max_clue_level": "medium",
  "requires_reveal_condition": true
}
```

---

## 5.4 NPC 候选示例

```json
{
  "candidate_id": "npc_candidate_001",
  "name": "赵婶",
  "type": "semi_agent_npc",
  "persistence": "recurring_npc",
  "role": "旧街口小卖部老板",
  "location_id": "old_street_shop",
  "narrative_function": "witness",
  "personality": "话多、谨慎、怕惹事",
  "knows": [
    {
      "fact_id": "hf_white_van",
      "content": "三天前夜里有白色面包车停在旧医院门口",
      "reveal_condition": {
        "topic": "recent_visitors",
        "relationship_min": 0,
        "required_stage": "investigation"
      }
    }
  ],
  "forbidden_knowledge": [
    "不能知道司机身份",
    "不能知道十年前事故真相"
  ],
  "first_available_topics": [
    "recent_visitors",
    "old_hospital",
    "night_noise"
  ],
  "validation_status": "pending"
}
```

---

# 6. Relationship Generator 关系生成器

## 6.1 目标

为已有角色或候选角色生成初始关系网。

角色不是孤立存在的，关系能制造冲突、信任、误解和动机。

---

## 6.2 关系类型

```text
ally：盟友
rival：竞争者
distrust：不信任
old_acquaintance：旧识
family_related：亲属相关
professional_contact：职业关系
debtor：债务关系
secret_keeper：秘密持有者
manipulator：操纵关系
```

---

## 6.3 RelationshipCandidate

```json
{
  "candidate_id": "rel_candidate_001",
  "from": "char_linzho",
  "to": "char_guard",
  "relationship_type": "distrust",
  "initial_attitude": -20,
  "trust": 25,
  "reason": "林舟觉得看门人在旧医院问题上多次回避。",
  "secret": null,
  "plot_value": {
    "conflict": 6,
    "mystery": 4
  },
  "risk": [
    "不应让看门人知道林舟的过去真相"
  ]
}
```

---

## 6.4 页面功能

```text
生成全局关系网
为某个角色生成关系
为两个角色生成冲突
生成隐藏关系
生成误解关系
关系强度滑动调节
关系图可视化
```

---

# 7. Location Generator 地点生成器

## 7.1 目标

生成符合世界设定的地点候选，并可连接到现有地图。

---

## 7.2 输入参数

```json
{
  "location_type": "clue_location",
  "connected_to": "old_hospital_gate",
  "function": "archive_access",
  "count": 3,
  "danger_level_range": [1, 4]
}
```

---

## 7.3 LocationCandidate

```json
{
  "candidate_id": "loc_candidate_001",
  "location_id": "old_street_shop",
  "name": "旧街口小卖部",
  "public_description": "街角的小卖部还亮着一盏旧灯，货架间弥漫着潮湿纸箱的味道。",
  "connected_to": ["old_hospital_gate"],
  "objects": ["old_radio", "counter", "street_facing_window"],
  "available_topics": ["recent_visitors", "old_hospital", "night_noise"],
  "narrative_function": "witness_location",
  "danger_level": 1,
  "possible_npcs": ["npc_store_owner"],
  "validation_status": "pending"
}
```

---

# 8. Clue Generator 线索生成器

## 8.1 目标

帮助用户生成线索候选，并自动配置 discover_routes。

---

## 8.2 输入参数

```json
{
  "arc_id": "arc_hospital_truth",
  "stage": "investigation",
  "clue_level": "medium",
  "count": 3,
  "must_have_routes": 3,
  "allowed_route_types": ["search", "inspect", "ask"]
}
```

---

## 8.3 ClueCandidate

```json
{
  "candidate_id": "clue_candidate_001",
  "clue_id": "hf_white_van",
  "name": "白色面包车",
  "content": "三天前夜里有一辆白色面包车停在旧医院门口。",
  "level": "medium",
  "arc_id": "arc_hospital_truth",
  "allowed_stages": ["investigation", "confrontation"],
  "discover_routes": [
    {
      "route_id": "route_ask_store_owner_white_van",
      "action_type": "ask",
      "target": "npc_store_owner_001",
      "topic": "recent_visitors",
      "location_id": "old_street_shop",
      "difficulty": 45
    },
    {
      "route_id": "route_inspect_street_window",
      "action_type": "inspect",
      "target": "street_facing_window",
      "location_id": "old_street_shop",
      "difficulty": 60
    },
    {
      "route_id": "route_search_old_receipt",
      "action_type": "search",
      "target": "counter",
      "location_id": "old_street_shop",
      "difficulty": 65
    }
  ],
  "validation_status": "pending"
}
```

---

# 9. Secret Generator 秘密生成器

## 9.1 目标

为角色生成可控秘密，不直接破坏主线。

---

## 9.2 秘密等级

```text
surface：表层秘密
minor：轻度秘密
medium：中等秘密
major：重大秘密
truth：核心真相
```

V4.2 默认只允许自动生成：

```text
surface
minor
medium
```

major / truth 需要用户确认。

---

## 9.3 SecretCandidate

```json
{
  "candidate_id": "secret_candidate_001",
  "owner": "char_guard",
  "secret_level": "minor",
  "content": "看门人最近确实换过医院大门的锁，但他说是别人要求的。",
  "can_be_revealed_in_stages": ["setup", "investigation"],
  "forbidden_until": null,
  "related_clues": ["hf_001"],
  "risk": "不能直接透露要求换锁的人是谁"
}
```

---

# 10. Candidate Review Panel 候选审核面板

## 10.1 目标

所有生成结果统一进入候选池，用户在页面中选择是否入库。

---

## 10.2 候选状态

```text
generated
edited
validated
approved
committed
rejected
archived
```

---

## 10.3 CandidateRecord

```json
{
  "candidate_id": "char_candidate_001",
  "candidate_type": "character",
  "status": "generated",
  "source": {
    "generator": "CharacterGenerator",
    "prompt_version": "v4.2.0",
    "created_at": "2026-05-16T00:00:00+08:00"
  },
  "content": {},
  "validation_report": {},
  "user_edits": [],
  "commit_target": "characters.json"
}
```

---

## 10.4 页面功能

```text
查看候选
编辑候选
运行校验
查看风险
批准入库
批量批准
拒绝候选
重新生成
局部重写
对比多个候选
```

---

# 11. 生成器服务设计

## 11.1 GeneratorService 总入口

```text
GeneratorService
├── CharacterGenerator
├── NPCGenerator
├── RelationshipGenerator
├── LocationGenerator
├── ClueGenerator
├── SecretGenerator
├── CandidateValidator
├── CandidateRegistry
└── CandidateCommitService
```

---

## 11.2 CharacterGenerator

```python
class CharacterGenerator:
    def generate(self, request: CharacterGenerationRequest) -> list[CharacterCandidate]:
        pass
```

---

## 11.3 CandidateCommitService

负责将候选写入正式配置。

```python
class CandidateCommitService:
    def commit_candidate(self, candidate_id: str, target: str) -> CommitResult:
        pass

    def batch_commit(self, candidate_ids: list[str]) -> BatchCommitResult:
        pass
```

入库前必须：

```text
schema 校验通过
引用校验通过
知识边界校验通过
用户确认
```

---

# 12. Prompt 设计

## 12.1 随机角色生成 Prompt

```text
你是小说沙盘引擎的角色候选生成器。

你不是小说作者。
你不能生成最终剧情。
你只能生成符合世界设定、剧情阶段、知识边界的角色候选。

要求：
1. 角色必须符合 genre / tone / era
2. 角色必须有 narrative_function
3. 角色不能知道 forbidden_revelations
4. 角色不能直接携带 truth 级线索
5. 角色必须能被系统结构化使用
6. 输出 JSON 数组

【World Bible】
{world_bible}

【Existing Characters】
{existing_characters}

【PlotArc State】
{plot_arc_state}

【Generation Request】
{generation_request}

输出 CharacterCandidate[]。
```

---

## 12.2 线索生成 Prompt

```text
你是小说沙盘引擎的线索候选生成器。

你只能生成符合当前 PlotArc stage 的线索。
每个线索必须有至少 {route_count} 条 discover_routes。
不能直接暴露 forbidden_revelations。
输出 JSON。
```

---

# 13. 校验规则

候选生成后必须检查：

```text
Schema 是否合法
ID 是否重复
引用目标是否存在
地点是否可达
角色是否符合世界时代
角色知识是否越界
线索是否越过 PlotArc stage
是否与已有角色高度重复
discover_routes 是否足够
是否会造成剧情过早解答
```

---

# 14. 页面交互流程

## 14.1 生成单个角色

```text
打开 Character Generator
↓
选择角色类型
↓
输入生成条件
↓
点击生成
↓
显示 3–5 个候选
↓
用户选择一个
↓
编辑字段
↓
运行校验
↓
确认入库
```

---

## 14.2 生成一组 NPC

```text
选择 location
↓
选择 NPC 数量
↓
选择 NPC 功能分布
↓
生成候选
↓
批量审核
↓
入库 npcs.json 或 dynamic_character_pool.json
```

---

## 14.3 生成线索 + NPC 联动

```text
选择 PlotArc stage
↓
生成 clue candidate
↓
系统发现需要 witness NPC
↓
联动生成 NPC candidate
↓
自动绑定 discover_route
↓
用户确认
↓
同时写入 clues.json 和 npcs.json
```

---

# 15. 数据文件

```text
worlds/dark_city_001/
  generator_config.json
  candidate_pool.jsonl
  dynamic_character_pool.json
  generated_relationships.json
```

输出目录：

```text
outputs/sim_xxx/
  generation_history.jsonl
  candidate_validation_reports.jsonl
  candidate_commits.jsonl
```

---

# 16. API 建议

```text
POST /projects/{projectId}/generate/characters
POST /projects/{projectId}/generate/npcs
POST /projects/{projectId}/generate/locations
POST /projects/{projectId}/generate/clues
POST /projects/{projectId}/generate/relationships
POST /projects/{projectId}/generate/secrets

GET  /projects/{projectId}/candidates
GET  /projects/{projectId}/candidates/{candidateId}
PUT  /projects/{projectId}/candidates/{candidateId}
POST /projects/{projectId}/candidates/{candidateId}/validate
POST /projects/{projectId}/candidates/{candidateId}/commit
POST /projects/{projectId}/candidates/batch-commit
```

---

# 17. UI 页面建议

## 17.1 Generator Hub

统一入口：

```text
生成角色
生成 NPC
生成地点
生成线索
生成关系
生成秘密
查看候选池
```

---

## 17.2 Character Generator 页面

区域：

```text
左侧：生成条件
中间：候选列表
右侧：候选详情 / 编辑
底部：校验报告
```

---

## 17.3 Candidate Review 页面

功能：

```text
按类型筛选
按风险筛选
按状态筛选
批量校验
批量入库
批量丢弃
```

---

# 18. 配置项

```json
{
  "world_studio_generation": {
    "enabled": true,
    "default_candidate_count": 5,
    "max_candidate_count": 20,
    "allow_major_secret_generation": false,
    "allow_truth_generation": false,
    "require_validation_before_commit": true,
    "require_user_approval_before_commit": true,
    "min_discover_routes_per_clue": 3,
    "dedupe_similarity_threshold": 0.82
  }
}
```

---

# 19. Metrics

```json
{
  "generation": {
    "character_candidates_generated": 24,
    "npc_candidates_generated": 18,
    "location_candidates_generated": 6,
    "clue_candidates_generated": 12,
    "candidates_committed": 19,
    "candidates_rejected": 9,
    "validation_failed_count": 6,
    "average_edit_before_commit": 1.4
  }
}
```

---

# 20. DoD

```text
1. 页面可以生成角色候选
2. 页面可以生成 NPC 候选
3. 页面可以生成地点候选
4. 页面可以生成线索候选
5. 候选不会直接写入正式配置
6. 候选可以编辑
7. 候选可以运行 ConfigValidator
8. 校验失败不能入库
9. 候选入库后写入对应 JSON
10. 支持批量生成和批量入库
11. 线索生成时至少生成 3 条 discover_routes
12. 角色生成时必须包含 narrative_function
13. 角色生成时必须包含 knowledge_boundary
14. 不允许自动生成 truth 级秘密
15. 所有生成历史写入 generation_history.jsonl
```

---

# 21. MVP 范围

V4.2 MVP 只做：

```text
1. Character Generator
2. NPC Generator
3. Clue Generator
4. Candidate Review Panel
5. Candidate Validator
6. Candidate Commit
```

暂不做：

```text
复杂关系图
地点自动布局
秘密复杂推演
多候选智能排序
全自动世界生成
```

---

# 22. 推荐开发顺序

```text
1. Candidate 数据结构
2. CandidateRegistry
3. CharacterGenerator
4. NPCGenerator
5. ClueGenerator
6. CandidateValidator
7. CandidateReview 页面
8. CandidateCommitService
9. generation_history
10. 批量生成 / 批量入库
```

---

# 23. 一句话总结

V4.2 的核心不是让 AI 直接替用户写完整世界，而是：

> 在页面中生成一批受约束的角色、NPC、地点、线索候选，让用户挑选、编辑、校验后再正式入库。

这能显著降低世界配置成本，同时保持系统可控。
