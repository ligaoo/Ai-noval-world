# MVP V2.2：多地点 + move 动作

> **核心目标**：验证多地点地图架构、move 动作合法性校验、地点上下文隔离，为后续 V2.3（记忆系统）和 V3（NPC 交互）打基础。

---

## 一、V2.2 范围边界

### 必做
- ✅ 3 个地点：入口区（old）、大厅（lobby）、档案室（archive）
- ✅ move 动作规则校验
- ✅ 按地点隔离 targets/topics
- ✅ EventLog 记录 location_id
- ✅ scripted/heuristic/llm 三种模式支持

### 不做（留到后续版本）
- 地点可见性动态变化（上锁/解锁）
- 多 NPC 跨地点移动
- 物品在地点间转移
- 时间对地点的影响（如午夜后地点解锁）

---

## 二、架构设计

### 2.1 地点联通规则
```json
{
  "old_hospital_entrance": {
    "connected_to": ["hospital_lobby"],
    "description": "废弃医院入口区"
  },
  "hospital_lobby": {
    "connected_to": ["old_hospital_entrance", "archive_room"],
    "description": "破旧大厅"
  },
  "archive_room": {
    "connected_to": ["hospital_lobby"],
    "description": "尘封多年的档案室"
  }
}
```

### 2.2 move 动作校验链
```
1. action_type == move
2. target 必须是 location_id（在 map.locations 中存在）
3. 当前地点.connected_to 包含 target
4. 目标地点必须可见（V2.2 默认全可见，后续可扩展）
5. 更新 WorldState 中角色.location_id
6. 生成 move 事件日志
```

### 2.3 上下文隔离
每个地点独立维护：
- **available_targets**：本地点 objects + 在场角色
- **available_topics**：与本地点线索相关的 topics
- **location_public_description**：仅当前地点的公开描述

---

## 三、数据契约变更

### 3.1 Location 模型扩展
```python
class Location(BaseModel):
    id: str
    name: str
    public_description: str
    objects: List[WorldObject] = Field(default_factory=list)
    connected_to: List[str] = Field(default_factory=list)  # 新增
    danger_level: int = 0
    locked: bool = False  # 预留，V2.2 暂不启用
```

### 3.2 ActionCommand 扩展
move 动作格式：
```json
{
  "agent_id": "char_linzho",
  "intent": "进入大厅寻找更多线索",
  "action_type": "move",
  "target": "hospital_lobby",
  "topic": null,
  "method": "推开铁门走进去",
  "dialogue": null,
  "expected_gain": "获得档案室入口位置信息",
  "risk_level": "low"
}
```

### 3.3 EventLog 新增字段
```json
{
  "event_id": "evt_0012",
  "location_id": "hospital_lobby",  # 新增
  "event_type": "move",
  "result": "林舟从入口区走进了大厅"
}
```

---

## 四、模块改造清单

### 4.1 WorldConfig 加载
- 扩展 map.json，新增 3 个地点与联通关系
- 每个地点配置独立的 objects（前台、抽屉、档案柜等）

### 4.2 ActionValidator
- 新增 move 动作校验逻辑
- 校验联通性：`target in current_location.connected_to`
- 校验目标地点存在性

### 4.3 EnvironmentEngine
- apply_action 中新增 move 分支
- 更新角色 location_id
- 生成 move 事件日志

### 4.4 CharacterAgentService
- build_context 中：
  - targets 只取当前地点 objects + 在场角色
  - topics 只取当前地点相关线索的 discover_routes 中的 topic
- ACTIONS 列表新增 "move"
- heuristic 模式下：如果当前地点无可用线索，尝试 move 到联通地点

### 4.5 SimulationRunner
- 多角色场景下：按顺序 tick，每个角色独立维护 location_id
- 事件日志中记录 location_id

---

## 五、V2.2 示例世界配置（dark_city_001）

### 地点布局
```
入口区 old_hospital_entrance
  ↓
大厅 hospital_lobby
  ↓
档案室 archive_room
```

### 地点线索分布
| 地点 | 线索 | 发现方式 |
|------|------|----------|
| 入口区 | hf_001（锁芯很新） | inspect hospital_gate_lock / ask char_guard |
| 入口区 | hf_002（老周知道夜里有人来） | ask char_guard night_visitors |
| 大厅 | hf_003（前台抽屉有划痕） | search front_desk |
| 档案室 | hf_004（十年前的事故记录） | inspect old_cabinet |

---

## 六、测试验收标准

### 6.1 单元测试
- move 到不存在地点 → 校验失败
- move 到不连通地点 → 校验失败
- move 成功后，AgentContext 的 targets/topics 更新为新地点内容

### 6.2 集成测试（scripted 模式）
- 预设动作序列：observe → inspect lock → ask guard → move lobby → search front_desk → move archive → inspect cabinet
- 验证每一步 location_id 正确变化
- 验证线索在对应地点被发现

### 6.3 一致性检查
- 章节正文中出现的地点，必须是角色实际去过的地点
- 正文中出现的线索，必须是该地点可发现的

---

## 七、开发时间估算（3 个工作日）

| 阶段 | 时间 |
|------|------|
| 1. 世界配置扩展（3 地点 + 联通关系 + 线索分布） | 0.5 天 |
| 2. move 动作校验与环境引擎实现 | 0.5 天 |
| 3. AgentContext 地点隔离 + heuristic 移动逻辑 | 0.5 天 |
| 4. EventLog location_id 字段支持 | 0.5 天 |
| 5. 测试调试：scripted / heuristic / llm 模式验证 | 1 天 |

---

## 八、风险点与应对

| 风险 | 应对 |
|------|------|
| Agent 反复在两个地点之间移动（死循环） | heuristic 模式下：如果连续 2 次 move 到同一地点，强制改为 inspect/search |
| LLM 选择 move 到不存在的地点 | ActionValidator 拦截，重试 / fallback |
| 多角色同地点交互逻辑复杂 | V2.2 只允许 POV 移动，NPC 固定在入口区 |
