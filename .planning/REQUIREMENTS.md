# Requirements: Agent Framework — v0.0.3

## Milestone v0.0.3: Agent 可视化平台 MVP

**Goal:** 端到端链路跑通 — config → spawn → event → WebSocket → canvas render

---

## EVNT — EventBus 事件系统

- [ ] **EVNT-01**: 开发者可通过 EventBus 发布/订阅事件，使用 asyncio.Queue 实现 pub-sub 模式
- [ ] **EVNT-02**: 开发者可订阅 EventBus 获取 asyncio.Queue，在异步循环中消费事件
- [ ] **EVNT-03**: 开发者可取消订阅，EventBus 自动清理 Queue 引用
- [ ] **EVNT-04**: VizEvent 数据模型包含 type/agent/payload/timestamp 字段，支持 JSON 序列化
- [ ] **EVNT-05**: AgentRunner 包装 AgentLoop，将 LoopEvent 映射为 VizEvent 并广播到 EventBus
- [ ] **EVNT-06**: AgentRunner 事件映射覆盖 thinking/tool_call/tool_result/done/error/max_steps 状态
- [ ] **EVNT-07**: AgentRunner yield 原始事件，不改变 AgentLoop 的外部行为

## WSRV — WebSocket 服务

- [ ] **WSRV-01**: WebSocket 服务端订阅 EventBus，将 VizEvent 实时推送到所有连接的客户端
- [ ] **WSRV-02**: WebSocket 连接断开时自动取消 EventBus 订阅，不泄漏 Queue
- [ ] **WSRV-03**: 客户端可通过 WebSocket 发送 start_team 控制命令
- [ ] **WSRV-04**: 客户端可通过 WebSocket 发送 stop_team 控制命令
- [ ] **WSRV-05**: WebSocket 服务使用 websockets 库，自带 ping/pong 心跳机制

## RNDR — Canvas 渲染层

- [ ] **RNDR-01**: PixiJS v8 应用初始化，包含背景层/agent层/效果层三个 Container
- [ ] **RNDR-02**: 办公室场景包含 4 个固定点位（2 个工位 + 茶水间 + 门口）
- [ ] **RNDR-03**: 猫精灵使用 placeholder 几何图形（圆形+三角形耳朵），32×32 像素
- [ ] **RNDR-04**: 猫精灵支持 3 种帧动画（站立/打字/喝水），对应 idle/thinking/tool_call 状态
- [ ] **RNDR-05**: Agent 状态变化时，动物自动移动到对应场景点位（线性插值平滑移动）
- [ ] **RNDR-06**: 动物到达目标点位后播放对应状态帧动画
- [ ] **RNDR-07**: Agent shutdown 时动物移动到门口并消失

## CNFG — React 配置面板

- [ ] **CNFG-01**: 用户可通过表单创建 Agent（填写 name/role/system_prompt）
- [ ] **CNFG-02**: 用户可点击按钮启动 Team（POST /api/team/start）
- [ ] **CNFG-03**: 用户可点击按钮停止 Team（POST /api/team/stop）
- [ ] **CNFG-04**: Agent 列表展示每个 agent 的名称和当前状态灯（idle/thinking/tool_call/shutdown）

## CONC — WebSocket 客户端连接

- [ ] **CONC-01**: 前端 WebSocket 客户端连接后端，连接断开时指数退避自动重连
- [ ] **CONC-02**: WebSocket 消息通过 reducer 统一分发到 React 状态
- [ ] **CONC-03**: React 状态通过 ref 桥接到 PixiJS，PixiJS ticker 每帧读取最新值渲染
- [ ] **CONC-04**: 连接状态指示器显示 WebSocket 连接状态（绿=连接/黄=重连/红=断开）
- [ ] **CONC-05**: 事件日志列表实时展示接收到的 VizEvent，按时间排序

---

## Future Requirements

| ID | Description | Target |
|----|-------------|--------|
| EVNT-F01 | EventBus topic 过滤机制 | v0.0.4+ |
| EVNT-F02 | 事件持久化到文件/数据库 | v0.0.4+ |
| RNDR-F01 | 多动物形象选择（猫/狗/兔/熊/鸟） | v0.0.4+ |
| RNDR-F02 | 消息气泡飞行动画 | v0.0.4+ |
| RNDR-F03 | 白板/讨论区区域 | v0.0.4+ |
| RNDR-F04 | Agent 走进/走出动画 | v0.0.4+ |
| CNFG-F01 | 拖拽编排 Agent 工作流 | v0.0.4+ |
| CONC-F01 | 离线消息缓冲 | v0.0.4+ |
| CONC-F02 | 消息历史面板 + 工具调用日志折叠 | v0.0.4+ |

## Out of Scope

| Feature | Reason |
|---------|--------|
| Phaser 游戏引擎 | PixiJS v8 已选型，不需要游戏框架 |
| 真实像素精灵美术资源 | 第一期用 placeholder 几何图形 |
| 多 Agent 间通信可视化 | 第一期用单 Agent 验证链路 |
| 前端单元测试 | 第一期验证端到端链路，测试以后补 |
| 移动端适配 | 第一期仅桌面浏览器 |

## Traceability

| REQ-ID | Phase | Plan | Status |
|--------|-------|------|--------|
| EVNT-01 | 9 | — | Pending |
| EVNT-02 | 9 | — | Pending |
| EVNT-03 | 9 | — | Pending |
| EVNT-04 | 9 | — | Pending |
| EVNT-05 | 9 | — | Pending |
| EVNT-06 | 9 | — | Pending |
| EVNT-07 | 9 | — | Pending |
| WSRV-01 | 9 | — | Pending |
| WSRV-02 | 9 | — | Pending |
| WSRV-03 | 9 | — | Pending |
| WSRV-04 | 9 | — | Pending |
| WSRV-05 | 9 | — | Pending |
| RNDR-01 | 10 | — | Pending |
| RNDR-02 | 10 | — | Pending |
| RNDR-03 | 10 | — | Pending |
| RNDR-04 | 10 | — | Pending |
| RNDR-05 | 10 | — | Pending |
| RNDR-06 | 10 | — | Pending |
| RNDR-07 | 10 | — | Pending |
| CNFG-01 | 11 | — | Pending |
| CNFG-02 | 11 | — | Pending |
| CNFG-03 | 11 | — | Pending |
| CNFG-04 | 11 | — | Pending |
| CONC-01 | 11 | — | Pending |
| CONC-02 | 11 | — | Pending |
| CONC-03 | 11 | — | Pending |
| CONC-04 | 11 | — | Pending |
| CONC-05 | 11 | — | Pending |

---
*Last updated: 2026-05-29 — v0.0.3 roadmap created, traceability updated*
