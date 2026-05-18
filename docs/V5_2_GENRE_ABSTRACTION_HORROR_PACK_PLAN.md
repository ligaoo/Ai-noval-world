# V5.2 开发计划：Genre Abstraction Layer + Horror Genre Pack

> 版本主题：核心引擎通用化，恐怖灵异类型插件化  
> 版本目标：将当前偏恐怖灵异的故事能力从核心引擎中抽离，建立通用 `Genre Abstraction Layer`，并实现第一个正式类型包：`Horror Genre Pack`。  
> 核心原则：核心引擎不写死恐怖灵异逻辑；恐怖灵异作为可插拔 Genre Pack 存在。

---

## 0. V5.2 背景

V5.1 已经实现：

```text
StoryQualityEvaluator
QualityReport
质量评分
质量问题识别
rewrite_recommended
质量报告页面
```

但后续如果目标是：

```text
1. 先完成 10 万字恐怖灵异
2. 后期还能扩展成通用故事系统
```

那么不能把下面这些恐怖灵异逻辑写死进核心引擎：

```text
恐怖强度
灵异规则
鬼怪出现
怪谈规则
异常空间
惊吓节奏
禁忌规则
灵异真相揭示
恐怖氛围评分
```

否则后期做悬疑、恋爱、科幻、奇幻时会非常难重构。

因此 V5.2 要做两件事：

```text
1. 建立 Genre Abstraction Layer，让核心引擎支持任意题材
2. 实现 Horror Genre Pack，把恐怖灵异能力作为第一个类型插件
```

---

## 1. V5.2 总目标

V5.2 完成后，系统应该具备：

```text
1. 核心引擎不依赖具体题材
2. 每个项目可以声明 genre_id
3. StoryQualityEvaluator 支持 base_scores + genre_scores
4. ChapterPlanner 支持 genre progression
5. NovelBlueprint 支持 genre_context
6. Prompt 构建统一通过 GenrePromptAdapter
7. 恐怖灵异逻辑迁移到 Horror Genre Pack
8. Horror Genre Pack 支持恐怖氛围、灵异规则、恐怖强度递进
9. Horror Genre Pack 能参与质量评估、章节规划、一致性检查
10. 后续可以新增 mystery / romance / scifi / fantasy 等 Genre Pack
```

一句话：

> V5.2 要让系统从“恐怖灵异小说引擎”升级为“通用故事引擎 + 恐怖灵异插件”。

---

## 2. V5.2 不做什么

V5.2 不做：

```text
1. RewriteOptimizer 自动修稿
2. 10 万字 LongRun 测试
3. 多题材完整实现
4. 恋爱 / 科幻 / 奇幻 / 推理 Genre Pack
5. 商业化模板市场
6. 复杂前端主题商店
```

V5.2 只做：

```text
Generic Genre 基础实现
Horror Genre Pack 完整实现
```

---

## 3. 推荐架构

```text
core/
  simulation/
  agent/
  environment/
  memory/
  plot/
  chapter/
  quality/
  rewrite/
  production/
  continuity/
  thread/
  npc/
  genre/
    genre_profile.py
    genre_pack.py
    genre_registry.py
    genre_rule_manager.py
    genre_quality_evaluator.py
    genre_progression_controller.py
    genre_prompt_adapter.py
    genre_context_builder.py

genre_packs/
  generic/
    generic_genre_profile.json
    generic_quality_dimensions.json
    generic_progression_curve.json
    generic_prompt_adapter.txt

  horror/
    horror_genre_profile.json
    horror_quality_dimensions.json
    horror_progression_curve.json
    horror_rule_schema.json
    horror_prompt_adapter.txt
    horror_atmosphere_controller.py
    supernatural_rule_manager.py
    horror_quality_evaluator.py
    horror_consistency_checker.py
    horror_chapter_planner_adapter.py
```

核心引擎只依赖：

```text
GenreProfile
GenrePack
GenreContext
GenreRuleManager interface
GenreQualityEvaluator interface
GenrePromptAdapter interface
GenreProgressionController interface
```

不直接依赖：

```text
HorrorAtmosphereController
SupernaturalRuleManager
GhostRule
FearIntensity
```

---

## 4. 核心抽象设计

### 4.1 GenreProfile

`GenreProfile` 是题材配置的核心。

它定义：

```text
题材 ID
题材名称
故事驱动力
张力维度
默认结构
质量评分权重
题材专属评分维度
题材推进曲线
禁用模式
Prompt 约束
```

#### Generic GenreProfile

```json
{
  "genre_id": "generic",
  "genre_name": "通用故事",
  "description": "适用于大多数剧情类故事的基础通用类型。",
  "base_dimensions": [
    "plot_progress",
    "conflict_strength",
    "character_depth",
    "emotional_curve",
    "pacing",
    "dialogue_quality",
    "chapter_hook",
    "readability",
    "style_consistency"
  ],
  "story_drivers": [
    "goal",
    "conflict",
    "choice",
    "change",
    "consequence"
  ],
  "tension_axes": [
    "external_obstacle",
    "relationship_tension",
    "inner_conflict",
    "stakes",
    "uncertainty"
  ],
  "default_arc_structure": [
    "setup",
    "development",
    "crisis",
    "climax",
    "resolution"
  ],
  "quality_weights": {
    "plot_progress": 0.18,
    "conflict_strength": 0.15,
    "character_depth": 0.15,
    "emotional_curve": 0.12,
    "pacing": 0.12,
    "dialogue_quality": 0.08,
    "chapter_hook": 0.08,
    "readability": 0.07,
    "style_consistency": 0.05
  },
  "thread_policy": {
    "max_open_threads": 8,
    "max_new_threads_per_chapter": 2,
    "stale_chapter_threshold": 2
  }
}
```

#### Horror GenreProfile

```json
{
  "genre_id": "horror",
  "extends": "generic",
  "genre_name": "恐怖灵异",
  "description": "以未知威胁、异常现象、灵异规则和心理恐惧为核心驱动力的故事类型。",
  "story_drivers": [
    "suspense",
    "fear",
    "mystery",
    "survival",
    "truth_reveal",
    "taboo_violation"
  ],
  "tension_axes": [
    "unknown_threat",
    "environment_pressure",
    "psychological_fear",
    "supernatural_rule",
    "truth_reveal",
    "isolation"
  ],
  "genre_dimensions": [
    "horror_atmosphere",
    "uncanny_effect",
    "fear_escalation",
    "supernatural_rule_consistency",
    "taboo_pressure",
    "unknown_threat_strength"
  ],
  "quality_weights_override": {
    "suspense": 0.16,
    "horror_atmosphere": 0.16,
    "uncanny_effect": 0.12,
    "plot_progress": 0.12,
    "character_depth": 0.10,
    "pacing": 0.10,
    "supernatural_rule_consistency": 0.10,
    "chapter_hook": 0.08,
    "readability": 0.06
  },
  "forbidden_patterns": [
    "过早解释灵异规则",
    "无铺垫出现鬼怪正面攻击",
    "用大段说明替代恐惧体验",
    "突然转为热血打怪",
    "主角用嘴炮解释所有真相",
    "恐怖来源过早具象化",
    "鬼怪能力没有边界"
  ]
}
```

---

### 4.2 GenrePack 接口

Python 示例：

```python
class GenrePack:
    genre_id: str

    def load_profile(self) -> dict:
        pass

    def build_genre_context(self, state, chapter_plan) -> dict:
        pass

    def get_progression_target(self, novel_progress) -> dict:
        pass

    def evaluate_genre_quality(self, quality_context) -> dict:
        pass

    def validate_genre_rules(self, event_or_chapter) -> dict:
        pass

    def adapt_prompt_context(self, base_prompt_context) -> dict:
        pass
```

Java 示例：

```java
public interface GenrePack {
    String genreId();
    GenreProfile loadProfile();
    GenreContext buildGenreContext(WorldState state, ChapterPlan chapterPlan);
    GenreProgressionTarget getProgressionTarget(NovelProgress progress);
    GenreQualityResult evaluateGenreQuality(QualityContext context);
    GenreValidationResult validateGenreRules(GenreValidationInput input);
    PromptContext adaptPromptContext(PromptContext baseContext);
}
```

---

### 4.3 GenreRegistry

职责：

```text
1. 注册所有 GenrePack
2. 根据 genre_id 获取 GenrePack
3. 提供默认 generic pack
4. 校验项目声明的 genre_id 是否存在
5. 支持后续动态加载新 genre
```

示例：

```json
{
  "registered_genres": [
    {
      "genre_id": "generic",
      "enabled": true,
      "path": "genre_packs/generic"
    },
    {
      "genre_id": "horror",
      "enabled": true,
      "path": "genre_packs/horror"
    }
  ],
  "default_genre": "generic"
}
```

---

### 4.4 GenreContext

GenreContext 是章节生成、质量评估、规则检查时注入的类型上下文。

```json
{
  "genre_id": "horror",
  "genre_stage": "subtle_anomaly",
  "genre_tension_level": 3,
  "genre_progression_target": {
    "target": "subtle_anomaly",
    "description": "轻微异常，制造不安但不解释原因。"
  },
  "genre_constraints": [
    "不能直接解释灵异规则",
    "不能出现正面鬼怪攻击",
    "异常应通过环境细节呈现"
  ],
  "genre_allowed_devices": [
    "声音异常",
    "旧物反常",
    "空间细节不一致"
  ],
  "genre_forbidden_devices": [
    "鬼正面现身",
    "主角直接理解全部规则"
  ]
}
```

---

# 5. 核心引擎需要改造的点

## 5.1 Project / World 配置增加 genre_id

项目配置增加：

```json
{
  "project_id": "dark_hospital_001",
  "genre_id": "horror",
  "genre_pack_version": "1.0.0"
}
```

world_bible 增加：

```json
{
  "world_id": "dark_city_001",
  "genre_id": "horror",
  "title": "旧医院真相",
  "tone": "克制、压抑、现实中透出诡异"
}
```

---

## 5.2 NovelBlueprint 增加 genre_context

不要写死恐怖字段。

推荐：

```json
{
  "novel_id": "novel_hospital_ghost_001",
  "genre_id": "horror",
  "target_words": 100000,
  "target_chapters": 30,
  "act_structure": [
    {
      "act_id": "act_1",
      "chapter_range": [1, 8],
      "function": "setup",
      "genre_context": {
        "genre_stage": "subtle_anomaly",
        "genre_target": "建立轻微异常与不安"
      }
    },
    {
      "act_id": "act_2",
      "chapter_range": [9, 20],
      "function": "development",
      "genre_context": {
        "genre_stage": "clear_threat_and_rule_discovery",
        "genre_target": "威胁显形，灵异规则逐渐出现"
      }
    },
    {
      "act_id": "act_3",
      "chapter_range": [21, 30],
      "function": "climax_and_resolution",
      "genre_context": {
        "genre_stage": "truth_and_resolution",
        "genre_target": "真相揭示，完成终局选择"
      }
    }
  ]
}
```

---

## 5.3 ChapterPlan 增加 genre_context

```json
{
  "chapter_id": "ch_006",
  "chapter_function": "推进主线并强化恐怖压力",
  "genre_context": {
    "genre_id": "horror",
    "genre_stage": "clear_threat",
    "genre_tension_level": 5,
    "allowed_devices": [
      "空间错位",
      "远处脚步声",
      "旧物位置变化"
    ],
    "forbidden_devices": [
      "正面鬼怪攻击",
      "直接解释四楼来源"
    ]
  }
}
```

核心 ChapterPlanner 只处理 `genre_context`，不关心里面是否是恐怖字段。

---

## 5.4 StoryQualityEvaluator 改造成 base + genre

V5.1 当前可能是固定维度：

```text
plot_progress
conflict_strength
character_depth
...
```

V5.2 改成：

```json
{
  "base_scores": {
    "plot_progress": 8,
    "conflict_strength": 6,
    "character_depth": 7,
    "emotional_curve": 7,
    "pacing": 7,
    "dialogue_quality": 7,
    "chapter_hook": 8,
    "readability": 8,
    "style_consistency": 8
  },
  "genre_scores": {
    "horror_atmosphere": 8,
    "uncanny_effect": 7,
    "fear_escalation": 6,
    "supernatural_rule_consistency": 8,
    "taboo_pressure": 5,
    "unknown_threat_strength": 7
  },
  "overall_score": 7.6
}
```

要求：

```text
base_scores 所有题材都有
genre_scores 由 GenrePack 提供
overall_score 根据 GenreProfile 权重计算
```

---

## 5.5 Prompt 构建改造

所有 Prompt 不再写死：

```text
请生成恐怖灵异章节
请强化恐怖氛围
请让鬼怪压迫感增强
```

改成：

```text
请根据 GenreProfile、GenreContext 和 StyleBible 生成章节。
当前 genre_id = horror。
当前 genre_constraints = ...
```

PromptContext 增加：

```json
{
  "genre_profile": {},
  "genre_context": {},
  "genre_prompt_instructions": []
}
```

---

## 5.6 ConsistencyCheck 增加 GenreRuleCheck

一致性检查拆成：

```text
BaseConsistencyCheck
GenreConsistencyCheck
```

Base 检查：

```text
新增事实
POV 泄露
角色位置
物品拥有权
线索阶段锁
```

Genre 检查：

```text
由当前 GenrePack 决定
```

恐怖 Genre 检查：

```text
灵异规则是否提前解释
鬼怪是否越权
恐怖强度是否不符合阶段
异常现象是否违反 SupernaturalRule
是否使用 forbidden horror devices
```

---

# 6. Horror Genre Pack 详细设计

## 6.1 Horror Genre Pack 模块

```text
genre_packs/horror/
  horror_genre_profile.json
  horror_progression_curve.json
  horror_quality_dimensions.json
  horror_rule_schema.json
  horror_prompt_adapter.txt

  horror_genre_pack.py
  horror_atmosphere_controller.py
  supernatural_rule_manager.py
  horror_quality_evaluator.py
  horror_consistency_checker.py
  horror_progression_controller.py
  horror_device_selector.py
```

---

## 6.2 Horror Progression Curve

恐怖灵异长篇需要恐怖强度递进。

```json
{
  "genre_id": "horror",
  "progression_curve": [
    {
      "stage_id": "subtle_anomaly",
      "chapter_ratio_range": [0.0, 0.20],
      "horror_intensity_range": [1, 3],
      "function": "制造轻微异常和不安",
      "allowed_devices": [
        "声音异常",
        "旧物位置变化",
        "温度异常",
        "视线错觉",
        "梦境片段"
      ],
      "forbidden_devices": [
        "鬼怪正面攻击",
        "灵异规则解释",
        "真相揭露",
        "大规模死亡"
      ]
    },
    {
      "stage_id": "clear_threat",
      "chapter_ratio_range": [0.20, 0.45],
      "horror_intensity_range": [3, 6],
      "function": "威胁显形，但仍保留未知感",
      "allowed_devices": [
        "空间错位",
        "重复声音",
        "无法解释的监控画面",
        "短暂目击",
        "人际关系中的不可信"
      ],
      "forbidden_devices": [
        "完整解释灵异来源",
        "主角掌握全部规则"
      ]
    },
    {
      "stage_id": "rule_discovery",
      "chapter_ratio_range": [0.45, 0.75],
      "horror_intensity_range": [5, 8],
      "function": "灵异规则逐渐显形，代价出现",
      "allowed_devices": [
        "规则验证",
        "禁忌触发",
        "错误尝试带来后果",
        "重要角色受影响",
        "过去事件回声"
      ],
      "forbidden_devices": [
        "最终真相完整揭露",
        "机械解释所有异常"
      ]
    },
    {
      "stage_id": "truth_and_resolution",
      "chapter_ratio_range": [0.75, 1.0],
      "horror_intensity_range": [7, 10],
      "function": "真相揭示、终局选择、恐惧收束",
      "allowed_devices": [
        "核心规则揭示",
        "主角面对过去",
        "终局禁忌",
        "空间与记忆重叠",
        "代价选择"
      ],
      "forbidden_devices": [
        "新增无关大坑",
        "引入全新核心反派",
        "结尾机械解释"
      ]
    }
  ]
}
```

---

## 6.3 HorrorAtmosphereController

职责：

```text
1. 根据 NovelProgress 判断当前恐怖阶段
2. 计算当前章 horror_intensity
3. 提供 allowed_horror_devices
4. 提供 forbidden_horror_devices
5. 给 ChapterPlanner 提供恐怖氛围目标
6. 给 QualityEvaluator 提供评分标准
```

输入：

```json
{
  "chapter_no": 8,
  "target_chapters": 30,
  "plot_arc_stage": "investigation",
  "recent_horror_intensity": [2, 3, 3, 4],
  "open_threads": []
}
```

输出：

```json
{
  "genre_stage": "clear_threat",
  "target_horror_intensity": 5,
  "allowed_devices": [
    "空间错位",
    "短暂目击",
    "重复声音"
  ],
  "forbidden_devices": [
    "完整解释灵异来源",
    "鬼怪正面攻击"
  ],
  "atmosphere_goal": "让主角确认异常不是心理错觉，但仍不知道来源。"
}
```

---

## 6.4 SupernaturalRuleManager

灵异故事必须有规则边界，否则会崩。

### 6.4.1 Rule 数据结构

```json
{
  "rule_id": "rule_fourth_floor",
  "name": "午夜后的四楼",
  "surface_rule": "午夜后旧医院会出现四楼。",
  "true_rule": "四楼是十年前事故记忆的空间化残留。",
  "rule_type": "space_anomaly",
  "status": "partially_revealed",
  "reveal_schedule": {
    "surface_reveal_stage": "clear_threat",
    "partial_reveal_stage": "rule_discovery",
    "truth_reveal_stage": "truth_and_resolution"
  },
  "allowed_manifestations": [
    {
      "stage": "subtle_anomaly",
      "manifestations": [
        "楼梯数目不对",
        "电梯按钮短暂闪过 4"
      ]
    },
    {
      "stage": "clear_threat",
      "manifestations": [
        "角色短暂进入不存在的楼层",
        "监控画面出现四楼走廊"
      ]
    },
    {
      "stage": "rule_discovery",
      "manifestations": [
        "角色发现四楼只在特定时间出现",
        "进入四楼会遗忘一段时间"
      ]
    },
    {
      "stage": "truth_and_resolution",
      "manifestations": [
        "四楼与主角过去记忆重叠",
        "真相场景重演"
      ]
    }
  ],
  "forbidden_before_reveal": [
    "不能直接说明四楼是记忆空间",
    "不能让 NPC 解释全部规则",
    "不能让主角立刻理解规则来源"
  ],
  "cost": {
    "entering_fourth_floor": "失去一段近期记忆",
    "breaking_rule": "被过去事件的幻象追逐"
  }
}
```

---

### 6.4.2 SupernaturalRuleManager 职责

```text
1. 加载 supernatural_rules.json
2. 判断当前阶段允许哪些规则表现
3. 阻止规则过早解释
4. 阻止鬼怪能力越界
5. 给 EnvironmentEngine 提供灵异事件合法性判断
6. 给 NarrativeWriter 提供可写的异常表现
7. 给 ConsistencyCheck 提供规则检查
```

---

### 6.4.3 规则检查示例

输入：

```json
{
  "event_type": "supernatural_manifestation",
  "rule_id": "rule_fourth_floor",
  "manifestation": "主角意识到四楼是十年前事故记忆的空间化残留",
  "chapter_no": 8,
  "genre_stage": "clear_threat"
}
```

输出：

```json
{
  "allowed": false,
  "reason": "truth_reveal_not_allowed_in_current_genre_stage",
  "safe_alternative": "主角发现四楼只在午夜后出现，但无法解释原因。"
}
```

---

## 6.5 HorrorDeviceSelector

根据当前阶段选择恐怖手法。

设备类型：

```text
sound_anomaly：声音异常
object_displacement：物品位置变化
temperature_drop：温度下降
space_mismatch：空间错位
time_gap：时间断层
mirror_or_reflection：镜像异常
recording_anomaly：录音/监控异常
dream_fragment：梦境碎片
body_sensation：身体感知异常
social_uncanny：熟人行为反常
rule_violation：禁忌触发
```

输出示例：

```json
{
  "selected_devices": [
    {
      "device_type": "space_mismatch",
      "description": "楼梯比记忆中多出一段。",
      "intensity": 4,
      "allowed": true
    },
    {
      "device_type": "recording_anomaly",
      "description": "监控画面出现主角没有走过的走廊。",
      "intensity": 5,
      "allowed": true
    }
  ]
}
```

---

## 6.6 HorrorQualityEvaluator

在 V5.1 QualityEvaluator 基础上增加 genre_scores。

评分维度：

```text
horror_atmosphere：恐怖氛围
uncanny_effect：异常感
fear_escalation：恐怖递进
supernatural_rule_consistency：灵异规则一致性
taboo_pressure：禁忌压力
unknown_threat_strength：未知威胁强度
```

HorrorQualityReport 片段：

```json
{
  "genre_scores": {
    "horror_atmosphere": 8,
    "uncanny_effect": 7,
    "fear_escalation": 6,
    "supernatural_rule_consistency": 8,
    "taboo_pressure": 5,
    "unknown_threat_strength": 7
  },
  "genre_problems": [
    {
      "type": "fear_escalation_flat",
      "message": "本章恐怖强度与前两章接近，没有形成递进。",
      "severity": "medium"
    },
    {
      "type": "over_explained_supernatural",
      "message": "正文中过早解释了四楼异常的来源。",
      "severity": "high"
    }
  ],
  "genre_suggestions": [
    {
      "type": "increase_uncanny_detail",
      "message": "可通过空间细节不一致增强异常感，而不是直接解释。"
    }
  ]
}
```

---

## 6.7 HorrorConsistencyChecker

检查：

```text
1. 是否过早解释灵异规则
2. 是否使用当前阶段禁止的恐怖设备
3. 鬼怪能力是否越界
4. 恐怖强度是否跳跃过大
5. 是否从心理恐怖突然变成热血战斗
6. 是否新增未注册的灵异规则
7. 是否违反 SupernaturalRuleManager
```

输出：

```json
{
  "passed": false,
  "violations": [
    {
      "type": "supernatural_rule_revealed_too_early",
      "rule_id": "rule_fourth_floor",
      "message": "当前阶段为 clear_threat，但正文直接解释了四楼真实来源。",
      "severity": "error"
    }
  ]
}
```

---

# 7. Prompt Adapter 设计

## 7.1 Generic Prompt Adapter

通用故事 Prompt 注入：

```text
【Genre】
当前题材：{genre_name}
故事驱动力：{story_drivers}
当前题材阶段：{genre_stage}
题材约束：{genre_constraints}

请遵守 GenreProfile，不要使用未允许的题材元素。
```

---

## 7.2 Horror Prompt Adapter

恐怖灵异 Prompt 注入：

```text
【Horror Genre Constraints】
当前恐怖阶段：{genre_stage}
目标恐怖强度：{target_horror_intensity}
允许的恐怖手法：{allowed_devices}
禁止的恐怖手法：{forbidden_devices}

写作要求：
1. 恐怖来自细节异常、未知和心理压力，而不是直接解释。
2. 不要提前说明灵异规则的真实来源。
3. 不要让鬼怪能力突破 SupernaturalRuleManager 的限制。
4. 当前阶段只允许表现 {allowed_rule_reveals}。
5. 禁止使用：{forbidden_patterns}。
6. 恐怖氛围应服务于剧情推进，不要纯堆氛围。
```

---

# 8. 数据文件设计

## 8.1 项目配置

```text
worlds/dark_city_001/
  world_bible.json
  genre_config.json
  plot_arcs.json
  characters.json
  npcs.json
  clues.json
  style_bible.json

  genre/
    horror/
      supernatural_rules.json
      horror_devices.json
      horror_progression_override.json
```

---

## 8.2 genre_config.json

```json
{
  "genre_id": "horror",
  "genre_pack_version": "1.0.0",
  "enabled_features": {
    "horror_atmosphere_controller": true,
    "supernatural_rule_manager": true,
    "horror_quality_evaluator": true,
    "horror_consistency_checker": true
  },
  "fallback_genre": "generic"
}
```

---

## 8.3 supernatural_rules.json

```json
{
  "rules": [
    {
      "rule_id": "rule_fourth_floor",
      "name": "午夜后的四楼",
      "surface_rule": "午夜后旧医院会出现四楼。",
      "true_rule": "四楼是十年前事故记忆的空间化残留。",
      "rule_type": "space_anomaly",
      "reveal_schedule": {
        "surface_reveal_stage": "clear_threat",
        "partial_reveal_stage": "rule_discovery",
        "truth_reveal_stage": "truth_and_resolution"
      },
      "allowed_manifestations": [],
      "forbidden_before_reveal": []
    }
  ]
}
```

---

## 8.4 horror_devices.json

```json
{
  "devices": [
    {
      "device_id": "space_mismatch",
      "name": "空间错位",
      "min_stage": "subtle_anomaly",
      "max_safe_intensity": 7,
      "description": "通过地点结构、楼层、门窗位置异常制造不安。"
    },
    {
      "device_id": "recording_anomaly",
      "name": "录音/监控异常",
      "min_stage": "clear_threat",
      "max_safe_intensity": 8,
      "description": "通过设备记录到角色未经历的画面或声音。"
    }
  ]
}
```

---

# 9. API 设计

## 9.1 Genre 管理

```text
GET  /genres
GET  /genres/{genreId}
GET  /projects/{projectId}/genre
PUT  /projects/{projectId}/genre
```

---

## 9.2 Genre Profile

```text
GET /genres/{genreId}/profile
GET /genres/{genreId}/quality-dimensions
GET /genres/{genreId}/progression-curve
```

---

## 9.3 Horror Pack 专属 API

```text
GET  /projects/{projectId}/horror/rules
POST /projects/{projectId}/horror/rules
PUT  /projects/{projectId}/horror/rules/{ruleId}
GET  /projects/{projectId}/horror/devices
GET  /simulations/{simulationId}/horror/context
POST /simulations/{simulationId}/horror/validate-event
POST /simulations/{simulationId}/horror/validate-chapter
```

---

## 9.4 Quality API 增强

V5.1 已有：

```text
GET /simulations/{simulationId}/chapters/{chapterId}/quality-report
```

V5.2 增强后返回：

```json
{
  "base_scores": {},
  "genre_scores": {},
  "overall_score": 7.6,
  "genre_id": "horror",
  "genre_problems": [],
  "genre_suggestions": []
}
```

---

# 10. 前端页面设计

## 10.1 Genre Settings 页面

路径建议：

```text
/projects/{projectId}/genre
```

功能：

```text
查看当前 genre_id
切换 genre
查看 GenreProfile
查看题材评分维度
查看题材推进曲线
启用/禁用题材功能
```

---

## 10.2 Horror Rules 页面

路径：

```text
/projects/{projectId}/genre/horror/rules
```

功能：

```text
新增灵异规则
编辑 surface_rule / true_rule
设置 reveal_schedule
设置 allowed_manifestations
设置 forbidden_before_reveal
校验规则完整性
```

---

## 10.3 Horror Progression 页面

显示：

```text
章节比例
恐怖阶段
恐怖强度范围
允许手法
禁止手法
当前章节所处阶段
```

---

## 10.4 Quality Report 页面增强

显示：

```text
Base Scores
Genre Scores
Horror Atmosphere Score
Uncanny Effect Score
Supernatural Rule Consistency
Genre Problems
Genre Suggestions
```

---

## 10.5 ChapterPlan 页面增强

显示：

```text
genre_context
当前恐怖阶段
目标恐怖强度
允许恐怖手法
禁止恐怖手法
关联灵异规则
```

---

# 11. 与现有模块集成

## 11.1 ChapterPlanner

新增：

```text
GenreProgressionController.get_current_target()
GenreContextBuilder.build()
```

ChapterPlanner 生成计划时注入：

```json
{
  "genre_context": {}
}
```

---

## 11.2 NarrativeWriter

Prompt 输入增加：

```text
genre_profile
genre_context
genre_prompt_instructions
```

---

## 11.3 StoryQualityEvaluator

流程变成：

```text
Base quality evaluation
↓
Genre quality evaluation
↓
Score merge by GenreProfile weights
↓
QualityReport output
```

---

## 11.4 ConsistencyCheck

流程变成：

```text
BaseConsistencyCheck
↓
PlotArcStageLockCheck
↓
POVCheck
↓
GenreConsistencyCheck
```

---

## 11.5 DynamicNPCIntroductionService

RoleSpec 生成时增加 genre constraints：

```json
{
  "genre_constraints": [
    "新 NPC 不能直接知道灵异规则真相",
    "setup 阶段 NPC 只能描述异常现象，不能解释原因"
  ]
}
```

---

## 11.6 Project Template Generator

生成模板时根据 genre_id 选择 GenrePack。

恐怖模板额外生成：

```text
supernatural_rules.json
horror progression curve
horror devices
horror-specific clues
```

---

# 12. 测试计划

## 12.1 GenreRegistry 测试

```text
能加载 generic
能加载 horror
未知 genre_id 回退到 generic
禁用的 genre 不能使用
```

---

## 12.2 GenreProfile 测试

```text
horror extends generic
base_dimensions 继承成功
genre_dimensions 加载成功
quality_weights_override 生效
```

---

## 12.3 ChapterPlanner 集成测试

```text
horror 项目生成 chapter_plan 时包含 genre_context
chapter 1 处于 subtle_anomaly
chapter 中段处于 rule_discovery
chapter 后段处于 truth_and_resolution
```

---

## 12.4 HorrorAtmosphereController 测试

```text
根据 chapter_no / target_chapters 返回正确 horror stage
返回目标恐怖强度
返回 allowed_devices / forbidden_devices
```

---

## 12.5 SupernaturalRuleManager 测试

```text
setup 阶段不能 reveal true_rule
clear_threat 阶段允许 surface manifestation
rule_discovery 阶段允许 partial reveal
truth_and_resolution 阶段允许 truth reveal
```

---

## 12.6 HorrorConsistencyChecker 测试

```text
提前解释灵异规则会被拦截
使用 forbidden horror device 会被拦截
新增未注册 supernatural_rule 会被拦截
恐怖强度跳跃过大会 warning
```

---

## 12.7 QualityEvaluator 测试

```text
horror 项目 quality_report 包含 genre_scores
generic 项目没有 horror 专属分数
overall_score 使用 genre weights
genre_problems 能被输出
```

---

## 12.8 Prompt Adapter 测试

```text
horror Prompt 包含 genre constraints
generic Prompt 不包含 horror 专属词
Prompt 不写死恐怖逻辑
```

---

# 13. 配置项

## 13.1 genre_system_config.json

```json
{
  "genre_system": {
    "enabled": true,
    "default_genre": "generic",
    "allow_project_genre_override": true,
    "fail_to_generic_if_missing": true,
    "store_genre_context_in_chapter_plan": true
  }
}
```

---

## 13.2 horror_pack_config.json

```json
{
  "horror_pack": {
    "enabled": true,
    "atmosphere_controller_enabled": true,
    "supernatural_rule_manager_enabled": true,
    "horror_quality_enabled": true,
    "horror_consistency_check_enabled": true,
    "max_horror_intensity_jump_per_chapter": 2,
    "forbid_truth_rule_reveal_before_stage": "truth_and_resolution"
  }
}
```

---

# 14. 输出文件

```text
outputs/sim_xxx/
  genre_contexts/
    ch_001_genre_context.json
    ch_002_genre_context.json

  quality_reports/
    ch_001_quality.json

  genre_reports/
    ch_001_horror_report.json

  consistency_reports/
    ch_001_consistency.json
```

---

# 15. 迁移策略

## 15.1 从现有恐怖项目迁移

步骤：

```text
1. world_bible.json 增加 genre_id = horror
2. 新增 genre_config.json
3. 把恐怖相关规则迁移到 supernatural_rules.json
4. 把恐怖强度/阶段迁移到 horror_progression_curve.json
5. 修改 ChapterPlanner 使用 genre_context
6. 修改 NarrativeWriter Prompt 使用 GenrePromptAdapter
7. 修改 QualityReport 为 base_scores + genre_scores
```

---

## 15.2 Prompt 迁移

旧 Prompt：

```text
请保持恐怖灵异氛围。
```

新 Prompt：

```text
请遵守 GenreProfile 和 GenreContext。
当前 genre_id = horror。
具体约束由 GenrePromptAdapter 注入。
```

---

## 15.3 质量报告迁移

旧结构：

```json
{
  "scores": {
    "plot_progress": 8,
    "suspense": 8
  }
}
```

新结构：

```json
{
  "base_scores": {},
  "genre_scores": {},
  "scores": {},
  "overall_score": 7.6
}
```

其中 `scores` 可以保留为兼容字段。

---

# 16. V5.2 DoD

```text
1. 项目支持 genre_id 配置
2. GenreRegistry 能加载 generic 和 horror
3. 核心引擎不直接依赖 horror 类
4. ChapterPlan 支持 genre_context
5. NarrativeWriter 通过 GenrePromptAdapter 注入题材约束
6. QualityReport 支持 base_scores + genre_scores
7. Horror Genre Pack 实现 HorrorAtmosphereController
8. Horror Genre Pack 实现 SupernaturalRuleManager
9. Horror Genre Pack 实现 HorrorQualityEvaluator
10. Horror Genre Pack 实现 HorrorConsistencyChecker
11. setup/subtle_anomaly 阶段不能直接解释灵异真相
12. horror 项目能输出 horror genre_scores
13. generic 项目能正常运行且不出现 horror 专属字段
14. 前端能查看 Genre Settings
15. 前端能编辑 Horror Supernatural Rules
16. 测试覆盖 GenreRegistry、GenreProfile、HorrorRule、HorrorQuality、HorrorConsistency
```

---

# 17. MVP 范围

如果要控制范围，V5.2 MVP 只做：

```text
1. GenreProfile
2. GenreRegistry
3. GenreContext
4. GenrePromptAdapter
5. QualityReport base_scores + genre_scores 改造
6. HorrorAtmosphereController
7. SupernaturalRuleManager
8. HorrorQualityEvaluator
9. HorrorConsistencyChecker
```

暂不做：

```text
复杂 Genre Pack 动态加载
多题材模板市场
其他题材完整实现
复杂前端图形化规则编辑器
```

---

# 18. 推荐开发顺序

```text
1. 定义 GenreProfile / GenrePack / GenreContext 接口
2. 实现 GenreRegistry
3. 实现 generic Genre Pack
4. 改造项目配置，增加 genre_id
5. 改造 ChapterPlan，增加 genre_context
6. 改造 Prompt 构建，接入 GenrePromptAdapter
7. 改造 StoryQualityEvaluator，支持 base_scores + genre_scores
8. 实现 horror_genre_profile.json
9. 实现 HorrorAtmosphereController
10. 实现 SupernaturalRuleManager
11. 实现 HorrorQualityEvaluator
12. 实现 HorrorConsistencyChecker
13. 前端增加 Genre Settings / Horror Rules 简版
14. 写迁移脚本或迁移说明
15. 补齐测试
```

---

# 19. 与后续版本关系

V5.2 完成后，后续版本可以这样走：

```text
V5.3 RewriteOptimizer
- 修稿时读取 GenreContext
- 恐怖项目修稿时保持恐怖氛围和规则边界

V5.4 NovelBlueprint + ProductionOrchestrator
- 全书规划基于 GenreProgressionCurve

V5.5 LongRun 100k Test
- 测试 horror genre progression 是否稳定

V5.6 新 Genre Pack
- mystery
- romance
- scifi
- fantasy
```

---

# 20. 一句话总结

V5.2 的核心是：

> 核心引擎只懂“故事”，不懂“恐怖”；恐怖灵异作为 Genre Pack 提供自己的规则、氛围、质量维度和 Prompt 约束。

最终结构：

```text
Generic Story Engine
↓
Genre Abstraction Layer
↓
Horror Genre Pack
↓
10 万字恐怖灵异故事
```

这样既能完成当前恐怖灵异目标，又不会堵死后续通用故事扩展路线。
