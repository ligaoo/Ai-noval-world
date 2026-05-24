# Agent Sandbox v2.4 完整流程图

```mermaid
flowchart TD
    A[CLI 启动模拟\npython -m app.cli] --> B[加载 WorldConfig\nWorldConfig.from_directory]
    B --> C[SimulationRunner.run]
    C --> D{v2_phase 是否为 v2.4?}

    D -- 否 --> E[Legacy Loop\nCharacterAgentService + EnvironmentEngine]
    E --> F[Legacy EventLog / State 保存]
    F --> Z[章节生成 / 输出文件]

    D -- 是 --> G[启用 AgentSandboxLoop]
    G --> H[初始化 / 刷新 FactExposureMatrix]
    H --> I[ScenePresenceTracker\n构建每个 location 的 ScenePresence]

    I --> I1[同地点角色\nvisible / audible]
    I --> I2[相邻地点角色\nnearby / partially audible]
    I --> I3[当前地点对象\nstatic objects + runtime objects]

    I1 --> J[AgentPerceptionService]
    I2 --> J
    I3 --> J

    J --> J1[只注入角色可见事件]
    J --> J2[只注入角色 allowed facts]
    J --> J3[屏蔽未暴露事实 / 他人秘密 / 不可见地点]

    J1 --> K[AgentMindService]
    J2 --> K
    J3 --> K

    K --> K1{mode}
    K1 -- heuristic/scripted --> K2[规则生成 AgentIntent]
    K1 -- llm --> K3[加载外置 PromptTemplate\n生成结构化 AgentIntent]
    K3 --> K4{Schema / 身份校验通过?}
    K4 -- 否 --> K2
    K4 -- 是 --> L[AgentIntent]
    K2 --> L

    L --> M[ActionArbitrator]
    M --> N{Intent 类型}

    N -- simple action\nmove / inspect / search / observe / wait --> O[桥接 ActionCommand]
    O --> P[EnvironmentEngine.apply_action]
    P --> Q[写入普通 EventLog]
    Q --> R[更新 WorldState]

    N -- social interaction\nask / withhold / lie / challenge / share_info 等 --> S[合并 InteractionProposal]
    S --> T[MultiRoundInteractionResolver]

    T --> T1[逐轮解析行为\n表达 / 回避 / 追问 / 质疑 / 让步]
    T1 --> T2[FactExposureMatrix 限制\n只能说自己已知事实]
    T2 --> T3[PerceptionResolver\n判断观察者是否发现破绽]
    T3 --> T4[生成 InteractionResult]

    T4 --> U[DirectorRiskChecker]
    U --> U1{是否存在风险?}
    U1 -- 真相过早泄露 --> U2[confirmed fact 降级为 suspicion]
    U1 -- 关键线索断裂 / 无推进 / 不可能获知 --> U3[调整后果或创建未来机会]
    U1 -- 无风险 --> V[保留 InteractionResult]
    U2 --> V
    U3 --> V

    V --> W[WorldStateUpdater]
    W --> W1[更新 known_facts / suspicions / beliefs]
    W --> W2[更新 relationships / attitude_to]
    W --> W3[更新 chapter progress / open_threads]
    W --> W4[更新 fact_exposure / interaction_history]

    W1 --> X[SandboxEventLogWriter]
    W2 --> X
    W3 --> X
    W4 --> X

    X --> X1[visible result\n只写可感知信息]
    X --> X2[hidden_effects\n保存隐藏后果]
    X --> X3[fact_exposure_delta\n记录 revealed / suspected]
    X --> X4[source_interaction\n保存结构化交互来源]

    X1 --> Y[EventLogService.append]
    X2 --> Y
    X3 --> Y
    X4 --> Y

    Y --> YA[MemoryService\n写入角色可见 / 已知记忆]
    YA --> YB[保存 state.json]
    YB --> YC[保存 snapshot / run status]
    YC --> YD{达到 ticks 或章节目标完成?}
    YD -- 否 --> H
    YD -- 是 --> Z[章节生成 / 输出文件]

    Z --> Z1[VisibleEventFilter\n按 POV 过滤事件]
    Z1 --> Z2[NarrativeService\n生成 chapter_plan]
    Z2 --> Z3[Writer Draft\n只使用 filtered plot events]
    Z3 --> Z4[ConsistencyService\n检查 / 修订 filtered events]
    Z4 --> Z5[输出 chapter_draft.md\nchapter_plan.json\nevents.jsonl\nstate.json]
```

## 数据边界图

```mermaid
flowchart LR
    subgraph Truth[全局真实状态]
        A1[WorldConfig]
        A2[WorldState]
        A3[FactExposureMatrix]
        A4[InteractionResult.hidden_effects]
    end

    subgraph AgentView[单个角色视角]
        B1[ScenePresence]
        B2[AgentPerception]
        B3[allowed_facts]
        B4[visible_events]
    end

    subgraph WriterView[Writer / POV 视角]
        C1[VisibleEventFilter]
        C2[filtered_plot_events]
        C3[allowed_entities]
        C4[chapter_draft]
    end

    A1 --> B1
    A2 --> B1
    A3 --> B3
    B1 --> B2
    B3 --> B2
    B2 --> D[AgentMind 只生成意图]
    D --> E[Resolver / Director 判定结果]
    E --> A2
    E --> A3
    E --> F[EventLog]
    F --> C1
    A3 --> C3
    C1 --> C2
    C2 --> C4
    C3 --> C4

    A4 -. 不直接进入 .-> B2
    A4 -. 不直接进入 .-> C4
```

## 核心职责分层

```mermaid
flowchart TB
    L1[输入层\nWorldConfig / WorldState / EventLog] --> L2[感知层\nScenePresenceTracker / AgentPerceptionService]
    L2 --> L3[意图层\nAgentMindService]
    L3 --> L4[仲裁层\nActionArbitrator]
    L4 --> L5[裁判层\nEnvironmentEngine / MultiRoundInteractionResolver / PerceptionResolver]
    L5 --> L6[纠偏层\nDirectorRiskChecker]
    L6 --> L7[状态层\nWorldStateUpdater / FactExposureMatrix]
    L7 --> L8[事件层\nSandboxEventLogWriter / EventLogService]
    L8 --> L9[叙事层\nVisibleEventFilter / NarrativeService / ConsistencyService]
    L9 --> L10[输出层\nstate.json / events.jsonl / chapter_plan.json / chapter_draft.md]
```

## 关键不变量

- Agent 只决定意图，不决定交互结果。
- Resolver / EnvironmentEngine 才能裁判行为是否成功、信息是否暴露、关系如何变化。
- `known_by` 表示确认知道，`suspected_by` 表示怀疑，不可混用。
- `hidden_effects` 可以保存内部真实后果，但不能直接进入 Writer 可见输入。
- Writer 只能消费 POV 可见事件和 allowed facts，不能凭空创造剧情事实。
- Prompt / policy / writer 规则从模板或世界配置加载，不写死具体剧情信息。
