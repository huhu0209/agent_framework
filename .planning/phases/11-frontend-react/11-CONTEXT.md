# Phase 11: Frontend React 集成 - Context

**Gathered:** 2026-05-31
**Status:** Ready for planning

<domain>
## Phase Boundary

React 配置面板 + WebSocket 客户端 + 事件日志 + React-PixiJS 桥接。
用户通过 React UI 创建 Agent、启动/停止 Team、实时观察 Agent 状态变化和事件流。
依赖 Phase 9（后端 EventBus + WebSocket 服务）和 Phase 10（Canvas 渲染层）。

</domain>

<decisions>
## Implementation Decisions

### 页面布局与组件结构
- **D-01:** 左右分栏布局 — 左侧 Canvas 固定 800×600（Phase 10 D-03），右侧 React 面板自适应填充剩余宽度
- **D-02:** 右侧面板单列纵向排列：配置表单 → Team 控制按钮 → Agent 状态列表 → 事件日志。每个区域有标题分隔
- **D-03:** 事件日志固定高度，最多显示最近 50 条，自动滚动到最新。旧的被丢弃
- **D-04:** 按功能拆分为独立 React 组件，放在 components/{category}/ 下（复用现有 agent/、layout/、ui/ 目录结构）

### 状态管理与事件流
- **D-05:** useReducer + Context 管理全局状态（WebSocket 连接状态、Agent 列表、事件日志、表单数据）
- **D-06:** 单个 reducer 处理所有 action 类型（WS_CONNECTED / WS_DISCONNECTED / VIZ_EVENT / AGENT_UPDATE 等），state 包含 connection、agents、eventLog 三块
- **D-07:** Agent 列表用 Map<name, AgentState> 存储，VizEvent 的 agent 字段作为 key 更新对应 agent 状态

### WebSocket 连接策略
- **D-08:** 页面加载时自动连接 ws://localhost:8765，无需用户操作
- **D-09:** 指数退避重连：初始 1 秒，每次加倍（×2），上限 30 秒，最多尝试 10 次
- **D-10:** 连接状态指示器放在页面顶部横条，左侧显示小圆点（绿=已连接/黄=重连中/红=已断开）+ 文字说明

### 配置表单与交互流程
- **D-11:** 折叠式表单 — Name + Role 默认展开，System Prompt 可展开填写
- **D-12:** 启动/停止按钮放在配置表单下方，双按钮并排。按钮状态跟随 Team 运行状态联动（未运行→启动可用，运行中→停止可用）
- **D-13:** Agent 状态灯用 CSS 彩色圆点（8×8px）：绿色=idle，蓝色=thinking，橙色=tool_call，灰色=shutdown。无动画

### Claude's Discretion
- 组件文件命名和具体拆分方式（哪些放 agent/、layout/、ui/）
- CSS 圆点的具体颜色值（参考 DESIGN.md 暖色系统）
- 事件日志条目的显示格式（时间戳 + 事件类型 + agent 名称）
- 折叠式表单的展开/收起动画实现方式
- 连接状态指示器的具体样式细节
- useReducer 的 action type 命名和 state 类型定义

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 后端接口（Phase 9 已实现）
- `framework/agent_framework/viz/ws_server.py` — WebSocket 服务端，消息协议（start_team/stop_team 命令、command_response、VizEvent 推送）
- `framework/agent_framework/viz/viz_event.py` — VizEvent Pydantic 模型（type/agent/payload/timestamp）
- `framework/agent_framework/viz/event_bus.py` — EventBus pub-sub 实现

### Canvas 渲染层（Phase 10 已实现）
- `frontend/src/canvas/index.ts` — Canvas API：init(container, options) / updateState(vizEvent) / destroy()
- `frontend/src/canvas/types.ts` — VizEvent / AnimationState 类型定义
- `.planning/phases/10-frontend-canvas/10-CONTEXT.md` — Phase 10 完整决策（状态→动画→点位映射、帧动画方案等）

### 后端事件系统上下文
- `.planning/phases/09-backend/09-CONTEXT.md` — Phase 9 完整决策（WebSocket 消息协议、AgentRunner、控制命令格式等）

### 设计规范
- `DESIGN.md` — HTML 设计规范（parchment 暖色背景 #f5f4ed、terracotta 品牌色 #c96442、暖色调系统）

### 需求与规划
- `.planning/REQUIREMENTS.md` — CNFG-01~04（React 配置面板）、CONC-01~05（WebSocket 客户端）需求定义
- `.planning/ROADMAP.md` — Phase 11 目标、成功标准、3 个 plan 分解

### 前端基础设施
- `frontend/package.json` — 现有前端依赖（React 19, Vite 8, Tailwind 4, PixiJS v8）
- `frontend/vite.config.ts` — Vite 配置（React + Tailwind 插件）

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `frontend/src/canvas/` — Phase 10 完整的 Canvas 渲染模块，导出 init() / updateState() / destroy() API，Phase 11 直接调用
- `frontend/src/canvas/types.ts` — VizEvent 和 AnimationState 类型定义，React 组件可直接 import
- `frontend/src/types/index.ts` — 空（仅占位），可在此添加 Phase 11 的 TypeScript 类型
- `frontend/src/lib/api.ts` — 空（仅占位），可在此添加 API 调用逻辑
- `frontend/src/components/{agent,layout,ui}/` — 空目录（.gitkeep），按功能分类存放新组件
- `frontend/src/hooks/` — 空目录，存放 useWebSocket 等 custom hooks

### Established Patterns
- 前端用 TypeScript ESM 模块（"type": "module"）
- CSS 用 Tailwind 4 utility classes
- 组件放在 frontend/src/components/{category}/ 下
- DESIGN.md 定义了暖色调设计系统，所有 UI 组件应遵循

### Integration Points
- Canvas API 桥接：React 通过 useRef 获取 container div → 调用 canvas.init(container) → 后续通过 canvas.updateState(vizEvent) 驱动渲染
- WebSocket 连接：前端连接 ws://localhost:8765，接收 VizEvent JSON 推送 + 发送 start_team/stop_team 命令
- Phase 9 WebSocket 协议：控制命令格式 {"type": "start_team", "agent": {"name": "...", "role": "...", "system_prompt": "..."}}，响应格式 {"type": "command_response", "success": bool, "error": "..."}
- App.tsx 当前是 Vite 默认模板，需要完全重写为 Phase 11 的布局

</code_context>

<specifics>
## Specific Ideas

- 折叠式表单的 System Prompt 默认收起，点击展开后显示多行文本框，减少初始页面信息量
- 事件日志每条显示：时间戳（HH:MM:SS）+ 事件类型（彩色标签）+ agent 名称
- 启动按钮用 terracotta 品牌色（#c96442），停止按钮用 error crimson（#b53333），与 DESIGN.md 一致
- 连接状态指示器的圆点大小和颜色：绿色=#22c55e（idle 连接），黄色=#eab308（重连中），红色=#ef4444（断开）

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 11-Frontend React 集成*
*Context gathered: 2026-05-31*
