# Roadmap: Agent Framework

## Milestones

- ✅ **v0.0.1 彻底 Code Review** — Phases 1-5 (shipped 2026-05-29)
- ✅ **v0.0.2 Agent 扩展与编排** — Phases 6-8 (shipped 2026-05-29)
- 🚧 **v0.0.3 Agent 可视化平台 MVP** — Phases 9-11 (in progress)

## Phases

<details>
<summary>✅ v0.0.1 彻底 Code Review (Phases 1-5) — SHIPPED 2026-05-29</summary>

- [x] Phase 1: Bug 修复审查 (3/3 plans) — completed
- [x] Phase 2: 安全审查与修复 (2/2 plans) — completed
- [x] Phase 3: 架构与代码质量审查 (2/2 plans) — completed
- [x] Phase 4: 性能与数据安全审查 (1/1 plan) — completed
- [x] Phase 5: 测试覆盖补充 (4/4 plans) — completed

</details>

<details>
<summary>✅ v0.0.2 Agent 扩展与编排 (Phases 6-8) — SHIPPED 2026-05-29</summary>

- [x] Phase 6: Agent 类型扩展 (3/3 plans) — completed 2026-05-29
- [x] Phase 7: 编排引擎 + 配置化 + 搜索 (3/3 plans) — completed 2026-05-29
- [x] Phase 8: A2A 协议 (3/3 plans) — completed 2026-05-29

</details>

### 🚧 v0.0.3 Agent 可视化平台 MVP (In Progress)

**Milestone Goal:** 端到端链路跑通 — config → spawn → event → WebSocket → canvas render

- [ ] **Phase 9: Backend 事件系统** — EventBus pub-sub + VizEvent 模型 + AgentRunner + WebSocket 推送
- [x] **Phase 10: Frontend Canvas 渲染** — PixiJS v8 办公室场景 + 猫精灵 + 状态动画 (completed 2026-05-30)
- [ ] **Phase 11: Frontend React 集成** — 配置面板 + WebSocket 客户端 + 事件日志 + React-PixiJS 桥接

## Phase Details

### Phase 9: Backend 事件系统

**Goal**: 开发者可通过 EventBus 发布/订阅 Agent 事件，WebSocket 客户端可实时接收 VizEvent 流并控制 Team 生命周期
**Depends on**: Nothing (v0.0.2 framework layer is the foundation)
**Requirements**: EVNT-01, EVNT-02, EVNT-03, EVNT-04, EVNT-05, EVNT-06, EVNT-07, WSRV-01, WSRV-02, WSRV-03, WSRV-04, WSRV-05
**Success Criteria** (what must be TRUE):

  1. 开发者可创建 EventBus 实例，发布事件后订阅者通过 asyncio.Queue 收到该事件
  2. 订阅者取消订阅后，Queue 引用被清理，不再收到事件
  3. AgentRunner 运行 AgentLoop 时，LoopEvent（thinking/tool_call/tool_result/done/error/max_steps）被正确映射为 VizEvent 并广播到 EventBus
  4. WebSocket 客户端连接后可实时收到 VizEvent JSON 推送；连接断开后 EventBus 订阅自动清理
  5. WebSocket 客户端可发送 start_team / stop_team 控制命令，服务端正确接收

**Plans**: 3 plans

Plans:
**Wave 1**

- [ ] 09-01: EventBus + VizEvent 模型 + 订阅管理

**Wave 2** *(blocked on Wave 1 completion)*

- [ ] 09-02: AgentRunner 包装层（LoopEvent → VizEvent 映射）

**Wave 3** *(blocked on Wave 2 completion)*

- [ ] 09-03: WebSocket 服务端（EventBus 订阅 + 推送 + 控制命令）

### Phase 10: Frontend Canvas 渲染

**Goal**: 浏览器中展示办公室场景，猫精灵根据 Agent 状态切换位置和帧动画，可视化反映 Agent 内部状态
**Depends on**: Nothing (纯前端渲染层，可与 Phase 9 并行开发)
**Requirements**: RNDR-01, RNDR-02, RNDR-03, RNDR-04, RNDR-05, RNDR-06, RNDR-07
**Success Criteria** (what must be TRUE):

  1. 浏览器中显示 PixiJS v8 办公室场景，包含 4 个固定点位（2 工位 + 茶水间 + 门口）
  2. 场景中出现猫精灵（placeholder 几何图形：圆形+三角耳朵），可被程序化控制移动到任意点位
  3. 猫精灵在 idle/thinking/tool_call 三种状态下播放对应帧动画（站立/打字/喝水）
  4. Agent 状态变化时猫精灵平滑移动到对应点位，到达后播放对应动画
  5. Agent shutdown 时猫精灵移动到门口并消失

**Plans**: 3 plans
**UI hint**: yes

Plans:
**Wave 1**

- [x] 10-01: PixiJS v8 应用初始化 + 办公室场景 + 点位系统

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 10-02: 猫精灵 + 帧动画（idle/thinking/tool_call）+ 状态切换

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 10-03: 精灵移动系统（线性插值）+ shutdown 消失动画

### Phase 11: Frontend React 集成

**Goal**: 用户可通过 React 界面创建 Agent、启动/停止 Team、实时观察 Agent 状态变化和事件流
**Depends on**: Phase 9 (后端 EventBus + WebSocket), Phase 10 (Canvas 渲染层)
**Requirements**: CNFG-01, CNFG-02, CNFG-03, CNFG-04, CONC-01, CONC-02, CONC-03, CONC-04, CONC-05
**Success Criteria** (what must be TRUE):

  1. 用户可通过表单填写 name/role/system_prompt 创建 Agent，Agent 出现在列表中
  2. 用户可点击按钮启动/停止 Team，操作触发后端 API 调用
  3. Agent 列表中每个 agent 显示名称和当前状态灯（idle/thinking/tool_call/shutdown）
  4. WebSocket 连接状态指示器正确显示连接状态（绿/黄/红），断开后自动重连
  5. 事件日志列表实时展示接收到的 VizEvent，按时间排序；Canvas 中猫精灵同步更新状态

**Plans**: 3 plans
**UI hint**: yes

Plans:

- [x] 11-01: React 配置面板（创建 Agent 表单 + Team 控制 + Agent 状态列表）
- [x] 11-02: WebSocket 客户端 + reducer 状态管理 + 连接状态指示器
- [ ] 11-03: React-PixiJS ref 桥接 + 事件日志列表 + 端到端集成

## Progress

**Execution Order:**
Phase 9 和 Phase 10 可并行执行。Phase 11 依赖两者完成。

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Bug 修复审查 | v0.0.1 | 3/3 | Complete | 2026-05-28 |
| 2. 安全审查与修复 | v0.0.1 | 2/2 | Complete | 2026-05-28 |
| 3. 架构与代码质量审查 | v0.0.1 | 2/2 | Complete | 2026-05-28 |
| 4. 性能与数据安全审查 | v0.0.1 | 1/1 | Complete | 2026-05-29 |
| 5. 测试覆盖补充 | v0.0.1 | 4/4 | Complete | 2026-05-29 |
| 6. Agent 类型扩展 | v0.0.2 | 3/3 | Complete | 2026-05-29 |
| 7. 编排引擎 + 配置化 + 搜索 | v0.0.2 | 3/3 | Complete | 2026-05-29 |
| 8. A2A 协议 | v0.0.2 | 3/3 | Complete | 2026-05-29 |
| 9. Backend 事件系统 | v0.0.3 | 3/3 | Complete | 2026-05-29 |
| 10. Frontend Canvas 渲染 | v0.0.3 | 3/3 | Complete    | 2026-05-31 |
| 11. Frontend React 集成 | v0.0.3 | 2/3 | In Progress | - |
