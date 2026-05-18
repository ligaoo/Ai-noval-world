# 角色专属 Temperature 功能说明

## 功能概述

V5.1 版本新增了**角色专属 LLM Temperature** 功能，允许为不同性格的角色设置不同的决策随机性，让角色行为更符合其人设。

---

## 核心原理

### 1. Temperature 优先级

角色获取 temperature 的优先级：

```
1. 角色配置中手动设置的 llm_temperature（最高优先级）
   ↓
2. 根据性格 traits 自动推导的 temperature
   ↓
3. 系统默认值（0.3）
```

### 2. 性格推导规则

系统内置了三类关键词映射：

#### 低温 traits（0.1 ~ 0.3）- 理智、稳定
```
冷静: 0.15, 理智: 0.15, 理性: 0.15, 逻辑: 0.1
克制: 0.20, 内敛: 0.20, 沉稳: 0.15, 稳重: 0.15
深思熟虑: 0.10, 严谨: 0.15, 保守: 0.20, 谨慎: 0.20
冷漠: 0.25, 冷酷: 0.20, 无情: 0.20, 平静: 0.25
专注: 0.20, 专业: 0.20, 压抑: 0.30
胆小: 0.25, 胆怯: 0.25, 懦弱: 0.25
```

#### 中温 traits（0.4 ~ 0.6）- 平衡、自然
```
外向: 0.45, 开朗: 0.40, 幽默: 0.45, 健谈: 0.40
灵活: 0.40, 变通: 0.40, 随机应变: 0.45
好奇: 0.50, 困惑: 0.50, 疑惑: 0.50, 怀疑: 0.45
犹豫: 0.50, 纠结: 0.50
神秘: 0.55, 古怪: 0.60
```

#### 高温 traits（0.7 ~ 0.9）- 情绪化、不可预测
```
冲动: 0.70, 冲动的: 0.70, 易怒: 0.70, 情绪化: 0.70, 暴躁: 0.80
鲁莽: 0.75, 大胆: 0.65, 冒险: 0.65, 激进: 0.70
疯癫: 0.85, 疯狂: 0.80
热血: 0.60, 激情: 0.60, 焦虑: 0.55, 恐慌: 0.70
```

### 3. 计算方式

如果角色有多个 traits 命中，取平均值：

```python
角色温度 = min(0.9, max(0.1, 命中 traits 温度的平均值))
```

---

## 使用方式

### 方式 1：手动设置（推荐）

在 `characters.json` 中直接设置：

```json
{
  "characters": [
    {
      "id": "char_linzho",
      "name": "林舟",
      "personality": {
        "traits": ["克制", "多疑", "压抑"]
      },
      "llm_temperature": 0.25,
      ...
    },
    {
      "id": "char_guard",
      "name": "老周",
      "personality": {
        "traits": ["警惕", "焦虑", "神经质"]
      },
      "llm_temperature": 0.55,
      ...
    }
  ]
}
```

### 方式 2：自动推导

如果不设置 `llm_temperature`，系统会根据 `personality.traits` 自动推导：

```json
{
  "characters": [
    {
      "id": "char_detective",
      "name": "冷静侦探",
      "personality": {
        "traits": ["冷静", "理智", "严谨"]
      }
      // 自动推导 → temperature ≈ 0.15
    },
    {
      "id": "char_killer",
      "name": "疯狂凶手",
      "personality": {
        "traits": ["疯狂", "冲动", "暴躁"]
      }
      // 自动推导 → temperature ≈ 0.77
    }
  ]
}
```

---

## 效果对比

| 角色 | 性格 | Temperature | 决策特点 |
|------|------|-------------|---------|
| 林舟 | 克制、多疑、压抑 | 0.25 | 行为稳定、冷静分析 |
| 老周 | 警惕、焦虑、神经质 | 0.55 | 行为多变、情绪波动 |
| 冷静侦探 | 冷静、理智、严谨 | 0.15 | 极度理性、决策一致 |
| 疯狂凶手 | 疯狂、冲动、暴躁 | 0.77 | 高度不可预测 |
| 神秘老者 | 神秘、古怪 | 0.55 | 行为难以捉摸 |

---

## 恐怖题材预设

系统内置了 12 种恐怖题材经典角色的推荐 temperature：

```python
HORROR_CHARACTER_PRESETS = {
    "冷静侦探": 0.15,    # 极度理性
    "理智医生": 0.20,    # 专业冷静
    "胆小受害者": 0.60,  # 容易恐慌
    "疯狂凶手": 0.80,    # 极度危险
    "神秘老者": 0.50,    # 难以捉摸
    "焦虑证人": 0.55,    # 紧张不安
    "怀疑论者": 0.45,    # 谨慎多疑
    "热血记者": 0.60,    # 冲动冒险
    "保守警察": 0.30,    # 按章办事
    "神秘灵媒": 0.60,    # 飘忽不定
    "失忆主角": 0.40,    # 困惑迷茫
    "看门老人": 0.30,    # 守旧谨慎
}
```

---

## 测试验证

运行测试脚本：

```bash
python test_per_char_temperature.py
```

测试输出示例：

```
测试 1: 性格特征到 temperature 的映射
  冷静侦探            -> temperature = 0.15
  冲动凶手            -> temperature = 0.77
  焦虑证人            -> temperature = 0.53
  神秘老者            -> temperature = 0.57
  普通人             -> temperature = 0.30

测试 2: 读取角色配置中的 temperature 字段
  林舟 (char_linzho): temperature = 0.25
    -> 手动设置值: 0.25
  老周 (char_guard): temperature = 0.55
    -> 手动设置值: 0.55
```

---

## 注意事项

1. **temperature 范围**: 0.1 ~ 0.9（系统自动约束）
2. **temperature = 0**: 会启用 LLM 缓存（相同输入返回相同结果）
3. **推荐配置**: 恐怖题材建议 0.2 ~ 0.6，避免过高导致角色行为脱轨
4. **手动优先**: 如果设置了 `llm_temperature`，则不会使用性格推导

---

## 技术实现

### 修改的文件

1. **app/models/world.py**
   - 新增 `CharacterProfile.llm_temperature` 字段
   - 新增 `CharactersConfig.get_llm_temperature()` 方法
   - 新增 `TraitTemperatureMapper` 类

2. **app/services/character_agent_service.py**
   - 新增 `_get_agent_temperature()` 方法
   - 修改 `_llm_action_with_retry()` 使用角色专属 temperature

3. **worlds/dark_city_001/characters.json**
   - 为林舟设置 `llm_temperature: 0.25`
   - 为老周设置 `llm_temperature: 0.55`

### 调用流程

```
SimulationRunner.run()
  └─ CharacterAgentService.decide_next_action()
      └─ _llm_action_with_retry()
          └─ _get_agent_temperature(agent_id)
              └─ world.characters.get_llm_temperature()
                  ├─ 检查 llm_temperature 字段（如果有则直接返回）
                  └─ TraitTemperatureMapper.infer_from_traits()
                      └─ 根据性格关键词匹配并计算平均值
```

---

## 常见问题

**Q: 为什么我的角色 temperature 不是预期值？**
A: 检查 traits 是否命中预设关键词，或手动设置 llm_temperature。

**Q: 可以动态修改 temperature 吗？**
A: 当前不支持运行时修改，需要在角色配置中预设。

**Q: temperature 对 heuristic 模式有效吗？**
A: 无效，heuristic 是规则驱动，不使用 LLM。

**Q: 如何调试角色的 temperature？**
A: 运行 `python test_per_char_temperature.py` 查看所有角色的 temperature 值。
