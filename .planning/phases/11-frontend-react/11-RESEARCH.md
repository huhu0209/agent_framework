# Phase 11: Frontend React 集成 - Research

**Researched:** 2026-05-31
**Domain:** React 19 + WebSocket + PixiJS 桥接
**Confidence:** HIGH

## Summary

Phase 11 的核心任务是将 Phase 10 的纯 PixiJS Canvas 渲染层与 React 19 状态管理层桥接，同时实现 WebSocket 客户端连接到 Phase 9 的后端服务。这是一个经典的 "React owns state, imperative API owns rendering" 桥接模式——React 通过 `useReducer` + `Context` 管理全局状态（连接状态、Agent 列表、事件日志），通过 `useRef` 调用 Canvas 模块的命令式 API（`init`/`updateState`/`destroy`），WebSocket 通过自定义 hook 管理。

本阶段**不引入任何新的 npm 包**。浏览器原生 `WebSocket` API 足够实现带指数退避重连的客户端。React 19 的 `useReducer` + `Context` 适合本项目的状态复杂度（中等规模、有限更新频率）。Tailwind 4 的 utility classes 覆盖所有 UI 样式需求。

**Primary recommendation:** 使用自定义 `useWebSocket` hook 管理 WebSocket 连接生命周期，通过 `dispatch` 将消息推入 `useReducer` reducer，Canvas 通过 `useRef` 直接调用 `updateState()`——数据流单向、状态集中、渲染解耦。

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** 左右分栏布局 — 左侧 Canvas 固定 800x600，右侧 React 面板自适应填充
- **D-02:** 右侧面板单列纵向排列：配置表单 → Team 控制按钮 → Agent 状态列表 → 事件日志
- **D-03:** 事件日志固定高度，最多 50 条，自动滚动到最新
- **D-04:** 按功能拆分为独立 React 组件，放在 components/{category}/ 下
- **D-05:** useReducer + Context 管理全局状态
- **D-06:** 单个 reducer 处理所有 action 类型，state 包含 connection/agents/eventLog 三块
- **D-07:** Agent 列表用 Map<name, AgentState> 存储
- **D-08:** 页面加载时自动连接 ws://localhost:8765
- **D-09:** 指数退避重连：初始 1s，x2 倍增，上限 30s，最多 10 次
- **D-10:** 连接状态指示器在页面顶部横条
- **D-11:** 折叠式表单 — Name + Role 默认展开，System Prompt 可展开
- **D-12:** 启动/停止按钮在表单下方并排，状态联动
- **D-13:** Agent 状态灯用 CSS 彩色圆点 8x8px（绿=idle, 蓝=thinking, 橙=tool_call, 灰=shutdown）

### Claude's Discretion
- 组件文件命名和具体拆分方式
- CSS 圆点的具体颜色值
- 事件日志条目的显示格式
- 折叠式表单的展开/收起动画实现方式
- 连接状态指示器的具体样式细节
- useReducer 的 action type 命名和 state 类型定义

### Deferred Ideas (OUT OF SCOPE)
None
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CNFG-01 | 用户可通过表单创建 Agent（name/role/system_prompt） | 折叠式表单组件 + reducer action |
| CNFG-02 | 用户可点击按钮启动 Team | WebSocket 发送 start_team 命令 (Phase 9 D-12) |
| CNFG-03 | 用户可点击按钮停止 Team | WebSocket 发送 stop_team 命令 (Phase 9 D-13) |
| CNFG-04 | Agent 列表展示名称和状态灯 | Map<name, AgentState> + CSS 圆点组件 |
| CONC-01 | 前端 WebSocket 指数退避自动重连 | 自定义 useWebSocket hook (D-09) |
| CONC-02 | WebSocket 消息通过 reducer 统一分发 | useReducer + Context 架构 (D-05/D-06) |
| CONC-03 | React 状态通过 ref 桥接到 PixiJS | useRef + canvas.updateState() 命令式调用 |
| CONC-04 | 连接状态指示器（绿/黄/红） | 顶部横条 + reducer 状态 (D-10) |
| CONC-05 | 事件日志实时展示 VizEvent | 固定高度列表 + 自动滚动 + 50 条上限 (D-03) |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| WebSocket 连接管理 | Browser/Client | — | 浏览器原生 WebSocket API，React hook 封装 |
| 全局状态管理 | Browser/Client | — | useReducer + Context 在 React 组件树内 |
| Canvas 渲染 | Browser/Client (PixiJS) | — | PixiJS 命令式渲染，React 不参与 |
| Agent 配置表单 | Browser/Client (React) | — | React 受控组件 + Tailwind 样式 |
| 控制命令发送 | Browser/Client | Backend (WS Server) | 前端发送 JSON 命令，后端处理 |
| VizEvent 接收 | Backend (WS Server) | Browser/Client | 后端推送，前端 reducer 消费 |

## Standard Stack

### Core (已安装，无需新增依赖)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| react | 19.2.6 | UI 框架 | 项目已安装，useReducer + Context 满足需求 |
| react-dom | 19.2.6 | DOM 渲染 | React 配套 |
| pixi.js | 8.18.1 | Canvas 渲染 | Phase 10 已安装并实现 |
| tailwindcss | 4.3.0 | CSS 工具类 | 项目已配置 @tailwindcss/vite 插件 |
| vite | 8.0.12 | 构建工具 | 已配置 |
| typescript | ~6.0.x | 类型系统 | 已配置，含 verbatimModuleSyntax |

### 不需要安装的库
| Instead of | Reason |
|------------|--------|
| reconnecting-websocket | 浏览器原生 WebSocket + 自定义 hook 实现指数退避重连，代码量小，避免额外依赖 [VERIFIED: 项目需求分析] |
| zustand/jotai | useReducer + Context 满足本阶段状态管理需求，状态结构简单（connection/agents/eventLog） [CITED: react.dev/learn/managing-state] |
| @pixi/react | Phase 10 已实现命令式 Canvas API，React 通过 ref 桥接即可，无需 React 声明式封装层 [VERIFIED: 项目现有架构] |

**Installation:**
```bash
# 无需安装新依赖 — 所有依赖已在 Phase 10 中安装
cd frontend && npm ls react react-dom pixi.js tailwindcss vite typescript
```

## Package Legitimacy Audit

> 本阶段不引入任何新的 npm 包。所有依赖在 Phase 10 中已验证。

**Packages removed due to slopcheck [SLOP] verdict:** none (no new packages)
**Packages flagged as suspicious [SUS]:** none (no new packages)

## Architecture Patterns

### System Architecture Diagram

```
Browser (React App)
┌─────────────────────────────────────────────────────┐
│                                                     │
│  ┌─────────────────────┐  ┌──────────────────────┐  │
│  │   AppProvider        │  │   Canvas Container   │  │
│  │  (Context + Reducer) │  │   (800x600 div)      │  │
│  │                     │  │                      │  │
│  │  state: {           │  │  useRef(container)   │  │
│  │   connection,       │  │     │                │  │
│  │   agents: Map,      │  │     ▼                │  │
│  │   eventLog: [],     │  │  canvas.init()       │  │
│  │   formData          │  │  canvas.updateState()│◄─┤── reducer dispatch VizEvent
│  │  }                  │  │  canvas.destroy()    │  │   后也同步调用 ref
│  │                     │  │                      │  │
│  │  dispatch(action)   │  │  [PixiJS v8]         │  │
│  └──────┬──────────────┘  └──────────────────────┘  │
│         │                                            │
│  ┌──────▼──────────────┐  ┌──────────────────────┐  │
│  │  useWebSocket hook  │  │  React UI Components │  │
│  │                     │  │                      │  │
│  │  new WebSocket()    │  │  ConfigForm          │  │
│  │  onmessage → parse  │  │  TeamControls        │  │
│  │  → dispatch(action) │  │  AgentList           │  │
│  │                     │  │  EventLog            │  │
│  │  send(command) ─────┼──│─ ConnectionIndicator │  │
│  │  reconnect on close │  │                      │  │
│  └─────────┬───────────┘  └──────────────────────┘  │
│            │                                        │
└────────────┼────────────────────────────────────────┘
             │ ws://localhost:8765
             ▼
┌─────────────────────────┐
│  Backend (Phase 9)      │
│  WebSocket Server       │
│                         │
│  ws_server.py           │
│  ├─ _push_events() ───►│ VizEvent JSON 推送
│  └─ _handle_commands()  │ ◄── start/stop_team
│                         │
│  EventBus ← AgentRunner│
└─────────────────────────┘
```

### Recommended Project Structure
```
frontend/src/
├── canvas/                  # Phase 10 已实现，不改
│   ├── index.ts             # init/updateState/destroy API
│   ├── types.ts             # VizEvent/AnimationState 类型
│   └── ...                  # renderer, scene, cat-sprite, etc.
├── components/
│   ├── agent/               # Agent 相关组件
│   │   ├── AgentList.tsx    # Agent 列表 + 状态灯
│   │   └── AgentStatusDot.tsx # 8x8 CSS 圆点
│   ├── chat/                # 暂不使用（v0.0.4+）
│   ├── layout/              # 布局组件
│   │   ├── AppLayout.tsx    # 左右分栏布局
│   │   └── ConnectionIndicator.tsx # 顶部连接状态横条
│   └── ui/                  # 通用 UI 组件
│       ├── ConfigForm.tsx   # 折叠式 Agent 配置表单
│       ├── TeamControls.tsx # 启动/停止按钮
│       └── EventLog.tsx     # 事件日志列表
├── hooks/
│   └── useWebSocket.ts      # WebSocket 连接管理 hook
├── state/
│   ├── types.ts             # State/Action 类型定义
│   ├── reducer.ts           # 全局 reducer
│   └── context.tsx          # Context Provider + useAppState hook
├── types/
│   └── index.ts             # 全局类型（WebSocket 消息协议等）
├── App.tsx                  # 入口，完全重写
├── main.tsx                 # 不变
└── index.css                # 不变（@import "tailwindcss"）
```

### Pattern 1: useReducer + Context 全局状态

**What:** 集中管理 WebSocket 连接状态、Agent 列表、事件日志和表单数据。

**When to use:** 多个组件需要访问同一份状态（连接状态影响 TeamControls 和 Indicator，Agent 列表影响 AgentList 和 Canvas）。

**Example:**
```typescript
// Source: [CITED: react.dev/reference/react/useReducer]

// state/types.ts — TypeScript discriminated union
// 注意: tsconfig 设置了 verbatimModuleSyntax: true，type 导入必须用 'import type'
// 注意: tsconfig 设置了 erasableSyntaxOnly: true，不能用 enum，只能用 as const 或 union type

import type { VizEvent } from '../canvas/types';

export type ConnectionStatus = 'connected' | 'reconnecting' | 'disconnected';

export interface AgentState {
  name: string;
  status: 'idle' | 'thinking' | 'tool_call' | 'shutdown';
  lastEvent: VizEvent | null;
}

export interface AppState {
  connection: {
    status: ConnectionStatus;
    retryCount: number;
  };
  agents: Map<string, AgentState>;
  eventLog: VizEvent[];
  formData: {
    name: string;
    role: string;
    systemPrompt: string;
  };
  isTeamRunning: boolean;
}

// Discriminated union action types — TypeScript 可以在 switch 中自动窄化
export type AppAction =
  | { type: 'WS_CONNECTED' }
  | { type: 'WS_DISCONNECTED' }
  | { type: 'WS_RECONNECTING'; retryCount: number }
  | { type: 'VIZ_EVENT'; event: VizEvent }
  | { type: 'COMMAND_RESPONSE'; success: boolean; error?: string }
  | { type: 'UPDATE_FORM'; field: string; value: string }
  | { type: 'TEAM_STARTED' }
  | { type: 'TEAM_STOPPED' };
```

```typescript
// state/reducer.ts — 纯函数，不可变更新
// 关键: 每个 case 都要 spread ...state，不要 mutate

import type { AppState, AppAction } from './types';

const MAX_LOG_ENTRIES = 50;

export function appReducer(state: AppState, action: AppAction): AppState {
  switch (action.type) {
    case 'WS_CONNECTED':
      return {
        ...state,
        connection: { status: 'connected', retryCount: 0 },
      };
    case 'WS_DISCONNECTED':
      return {
        ...state,
        connection: { ...state.connection, status: 'disconnected' },
        isTeamRunning: false,
      };
    case 'WS_RECONNECTING':
      return {
        ...state,
        connection: { status: 'reconnecting', retryCount: action.retryCount },
      };
    case 'VIZ_EVENT': {
      const event = action.event;
      const newAgents = new Map(state.agents);
      const existing = newAgents.get(event.agent);
      newAgents.set(event.agent, {
        name: event.agent,
        status: mapEventTypeToAgentStatus(event.type),
        lastEvent: event,
      });

      // 事件日志：追加新事件，超过上限丢弃最旧
      const newLog = [...state.eventLog, event].slice(-MAX_LOG_ENTRIES);

      return { ...state, agents: newAgents, eventLog: newLog };
    }
    case 'COMMAND_RESPONSE':
      // command_response 处理 — 可用于错误提示
      return state;
    case 'UPDATE_FORM':
      return {
        ...state,
        formData: { ...state.formData, [action.field]: action.value },
      };
    case 'TEAM_STARTED':
      return { ...state, isTeamRunning: true };
    case 'TEAM_STOPPED':
      return { ...state, isTeamRunning: false };
  }
}

function mapEventTypeToAgentStatus(
  type: string,
): AgentState['status'] {
  switch (type) {
    case 'idle':
      return 'idle';
    case 'thinking':
      return 'thinking';
    case 'tool_call':
      return 'tool_call';
    case 'shutdown':
      return 'shutdown';
    default:
      return 'idle';
  }
}
```

### Pattern 2: useWebSocket 自定义 Hook

**What:** 封装浏览器原生 WebSocket + 指数退避重连逻辑。

**When to use:** 唯一的 WebSocket 连接入口。

**Example:**
```typescript
// Source: [VERIFIED: browser WebSocket API + WebSearch patterns]

// hooks/useWebSocket.ts
import { useEffect, useRef, useCallback } from 'react';
import type { AppAction } from '../state/types';

interface UseWebSocketOptions {
  url: string;
  dispatch: React.Dispatch<AppAction>;
  maxRetries?: number;
  initialDelay?: number;
  maxDelay?: number;
}

export function useWebSocket({
  url,
  dispatch,
  maxRetries = 10,
  initialDelay = 1000,
  maxDelay = 30000,
}: UseWebSocketOptions) {
  const wsRef = useRef<WebSocket | null>(null);
  const retryCountRef = useRef(0);
  const retryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const connect = useCallback(() => {
    // 清理旧连接
    if (wsRef.current) {
      wsRef.current.onopen = null;
      wsRef.current.onclose = null;
      wsRef.current.onmessage = null;
      wsRef.current.onerror = null;
      if (wsRef.current.readyState === WebSocket.OPEN ||
          wsRef.current.readyState === WebSocket.CONNECTING) {
        wsRef.current.close();
      }
    }

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      retryCountRef.current = 0;
      dispatch({ type: 'WS_CONNECTED' });
    };

    ws.onclose = () => {
      dispatch({ type: 'WS_DISCONNECTED' });
      attemptReconnect();
    };

    ws.onerror = () => {
      // onclose 会在 onerror 之后触发，重连逻辑放在 onclose
    };

    ws.onmessage = (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data as string);
        if (data.type === 'command_response') {
          dispatch({
            type: 'COMMAND_RESPONSE',
            success: data.success,
            error: data.error,
          });
        } else {
          // VizEvent 推送
          dispatch({ type: 'VIZ_EVENT', event: data });
        }
      } catch {
        // 忽略无法解析的消息
      }
    };
  }, [url, dispatch]);

  const attemptReconnect = useCallback(() => {
    if (retryCountRef.current >= maxRetries) return;

    const delay = Math.min(
      initialDelay * Math.pow(2, retryCountRef.current),
      maxDelay,
    );
    retryCountRef.current += 1;
    dispatch({
      type: 'WS_RECONNECTING',
      retryCount: retryCountRef.current,
    });

    retryTimerRef.current = setTimeout(() => {
      connect();
    }, delay);
  }, [connect, maxRetries, initialDelay, maxDelay, dispatch]);

  // 发送消息的辅助函数
  const sendMessage = useCallback((data: Record<string, unknown>) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  }, []);

  // 自动连接 — useEffect cleanup 处理 StrictMode 双重挂载
  useEffect(() => {
    connect();
    return () => {
      // 清理重连定时器
      if (retryTimerRef.current) {
        clearTimeout(retryTimerRef.current);
      }
      // 清理 WebSocket
      if (wsRef.current) {
        wsRef.current.onclose = null; // 防止触发重连
        wsRef.current.close();
      }
    };
  }, [connect]);

  return { sendMessage };
}
```

### Pattern 3: React-PixiJS 命令式桥接

**What:** React 通过 `useRef` 持有 Canvas 容器 DOM 节点，命令式调用 Phase 10 的 `init`/`updateState`/`destroy` API。

**When to use:** 渲染引擎（PixiJS）有自己的渲染循环，不需要 React re-render 驱动。

**Example:**
```typescript
// Source: [VERIFIED: Phase 10 canvas/index.ts API]

// components/layout/AppLayout.tsx 关键片段
import { useEffect, useRef } from 'react';
import { init as canvasInit, updateState as canvasUpdateState, destroy as canvasDestroy } from '../../canvas/index';
import type { VizEvent } from '../../canvas/types';

function CanvasContainer({ events }: { events: readonly VizEvent[] }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const lastProcessedIndex = useRef(0);
  const isInitialized = useRef(false);

  // 初始化 Canvas — 只运行一次
  useEffect(() => {
    if (!containerRef.current || isInitialized.current) return;
    isInitialized.current = true;

    canvasInit(containerRef.current, { width: 800, height: 600 });

    return () => {
      canvasDestroy();
      isInitialized.current = false;
    };
  }, []);

  // 处理新事件 — 使用 ref 追踪已处理索引，避免重复
  useEffect(() => {
    for (let i = lastProcessedIndex.current; i < events.length; i++) {
      canvasUpdateState(events[i]);
    }
    lastProcessedIndex.current = events.length;
  }, [events]);

  return (
    <div
      ref={containerRef}
      style={{ width: 800, height: 600 }}
      className="flex-shrink-0"
    />
  );
}
```

### Pattern 4: 消息协议 — 前端视角

**What:** 前端与后端的 WebSocket 消息格式约定。

**When to use:** 解析接收消息、构建发送消息。

**消息协议（基于 Phase 9 ws_server.py 实现）:**

```
前端接收（服务端推送）:
├── VizEvent: { type: "idle"|"thinking"|"tool_call"|"done"|"error"|"shutdown",
│               agent: string, payload: {}, timestamp: number }
└── command_response: { type: "command_response", success: boolean, error?: string }

前端发送:
├── start_team: { type: "start_team",
│                 agent: { name: string, role: string, system_prompt: string } }
└── stop_team:  { type: "stop_team", name: string }
```

### Anti-Patterns to Avoid

- **不要用 React re-render 驱动 PixiJS 渲染：** PixiJS 有自己的 Ticker 渲染循环，React re-render 不应触发 Canvas 重绘。通过 `useRef` + 命令式调用桥接，不要用 state 映射到 PixiJS 属性。
- **不要在 reducer 中调用 canvas API：** reducer 必须是纯函数。Canvas 更新在组件的 `useEffect` 中处理，通过比较 eventLog 长度增量来驱动。
- **不要忽略 StrictMode 双重挂载：** React 19 StrictMode 会 mount → unmount → mount。WebSocket 和 Canvas init 必须在 cleanup 中正确清理，否则产生双重连接和双重渲染器。[CITED: react.dev/reference/react/useReducer — Strict Mode caveats]
- **不要在 WebSocket onclose 中直接递归重连：** 使用 setTimeout 延迟重连，否则在服务器宕机时可能导致无限循环栈溢出。
- **不要用 enum：** `erasableSyntaxOnly: true` 不允许 TypeScript enum。用 `as const` 对象或 union type 替代。[VERIFIED: tsconfig.app.json 设置]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| WebSocket 重连库 | 自定义 ReconnectingWebSocket 类 | useWebSocket hook (50 行代码) | 场景简单，hook 封装足够，避免引入外部库的版本维护成本 |
| 事件节流 | 自定义 throttle/debounce 工具 | reducer 内 slice(-50) 丢弃 | 50 条上限 + reducer 不可变更新，不需要额外节流逻辑 |
| 表单验证库 | zod/joi 验证 | HTML5 required + 受控组件 | 3 个字段，required 足够，不需要 schema 验证 |
| 日期格式化库 | date-fns/dayjs | Date.toLocaleTimeString() | 只需 HH:MM:SS 格式，浏览器原生 API 足够 |

**Key insight:** 本阶段的核心复杂度在于数据流设计（WebSocket → reducer → React UI + Canvas 桥接），不在于单个工具函数。每个外部库都会增加构建体积和维护成本，而这个项目的状态管理需求完全在 React 内置 API 的能力范围内。

## Common Pitfalls

### Pitfall 1: StrictMode 双重 WebSocket 连接
**What goes wrong:** React 19 StrictMode 在开发模式下 mount → unmount → mount。如果 useEffect cleanup 不关闭旧 WebSocket，会产生两个并行连接。
**Why it happens:** StrictMode 故意触发双重 effect 以检测缺少的 cleanup 逻辑。
**How to avoid:** useEffect cleanup 中 (1) 清除重连定时器，(2) 设置 `ws.onclose = null`（防止 cleanup 的 close 触发重连），(3) 调用 `ws.close()`。
**Warning signs:** 后端日志显示同一客户端 IP 有两个活跃 WebSocket 连接。

### Pitfall 2: eventLog 导致频繁 re-render
**What goes wrong:** 每个 VizEvent 都触发 dispatch → 全局 state 更新 → 所有 Context consumer re-render。高频事件下可能产生性能问题。
**Why it happens:** Context 没有细粒度订阅，所有 consumer 都会在 state 变化时 re-render。
**How to avoid:** (1) Canvas 桥接组件使用 `React.memo`；(2) 事件日志组件用 `useMemo` 处理显示数据；(3) MVP 阶段事件频率低（几十个/任务），实际不会是瓶颈。
**Warning signs:** Chrome DevTools Profiler 显示每个 VizEvent 触发 >50ms 的 JS 执行。

### Pitfall 3: Map 序列化陷阱
**What goes wrong:** `useReducer` 的 reducer 中 `new Map(state.agents).set(...)` 返回的是同一个 Map 引用（set 返回 Map 自身），React 的 `Object.is` 比较可能认为 state 没变。
**Why it happens:** Map.set() 是 mutation + 返回 this。`new Map(oldMap)` 创建新 Map，但 `.set()` 仍然修改这个新 Map 并返回它——这里实际上没问题，因为 Map 是 new 出来的。但如果不 new 直接 `.set()`，就会 mutation 原来的 Map。
**How to avoid:** 始终用 `new Map(state.agents)` 创建新 Map，然后 `.set()` 修改新 Map。**不要**在 reducer 中直接调用 `state.agents.set()`。
**Warning signs:** Agent 列表 UI 不更新，但 console.log 显示数据已变。

### Pitfall 4: verbatimModuleSyntax 导入错误
**What goes wrong:** TypeScript 编译报错 "This import is never used" 或 "Type-only import used in value position"。
**Why it happens:** `verbatimModuleSyntax: true` 要求 type-only imports 使用 `import type { X }` 语法，不能和 value imports 混合。
**How to avoid:** 类型导入一律用 `import type { X } from '...'`。如果同时需要 value 和 type，分开两条 import 语句。
**Warning signs:** `tsc --noEmit` 报 TS 错误。

### Pitfall 5: Canvas init 在 DOM 节点挂载前执行
**What goes wrong:** `canvasInit(container, options)` 时 container 为 null，PixiJS 创建失败。
**Why it happens:** `useRef` 在首次渲染后才指向 DOM 节点。如果 init 在渲染前调用，ref.current 还是 null。
**How to avoid:** 使用 `useEffect`（不是 `useLayoutEffect`）调用 `canvasInit`，因为 useEffect 在 DOM 更新后执行，ref.current 已指向真实节点。
**Warning signs:** PixiJS 报错 "Cannot read properties of null" 或 Canvas 区域空白。

### Pitfall 6: WebSocket 消息类型区分错误
**What goes wrong:** 前端把 `command_response` 当成 VizEvent 处理，导致 Agent 状态列表出现名为 "command_response" 的假 Agent。
**Why it happens:** 后端 WebSocket 发送两种消息格式，前端需要通过 `type` 字段区分。
**How to avoid:** onmessage 处理中首先检查 `data.type === 'command_response'`，走单独的 dispatch 分支。只有非 command_response 的消息才走 VIZ_EVENT 分支。
**Warning signs:** Agent 列表出现名称为 "command_response" 的条目。

## Code Examples

### 连接状态指示器样式 (DESIGN.md 暖色系)
```typescript
// Source: [CITED: DESIGN.md — Warm color palette]
// 绿色=#22c55e, 黄色=#eab308, 红色=#ef4444 来自 11-CONTEXT.md specifics

const STATUS_COLORS: Record<ConnectionStatus, string> = {
  connected: '#22c55e',    // 绿色 — 活跃连接
  reconnecting: '#eab308', // 黄色 — 重连中
  disconnected: '#ef4444', // 红色 — 已断开
} as const;

// Tailwind 类名: w-2 h-2 rounded-full (8x8px)
```

### Agent 状态灯颜色
```typescript
// Source: [CITED: 11-CONTEXT.md D-13]
// 绿=idle, 蓝=thinking, 橙=tool_call, 灰=shutdown

const AGENT_STATUS_COLORS: Record<string, string> = {
  idle: '#22c55e',       // 绿色
  thinking: '#3b82f6',   // 蓝色
  tool_call: '#f97316',  // 橙色
  shutdown: '#9ca3af',   // 灰色
} as const;
```

### 折叠式表单
```typescript
// Source: [CITED: 11-CONTEXT.md D-11]
// Name + Role 默认展开, System Prompt 可展开

import { useState } from 'react';

function ConfigForm() {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="space-y-3">
      {/* Name 输入 */}
      <div>
        <label className="block text-sm font-medium text-olive-gray">Name</label>
        <input
          type="text"
          required
          className="mt-1 w-full rounded-xl border border-cream px-3 py-1.5 text-sm"
          style={{ borderColor: '#f0eee6' }}
        />
      </div>
      {/* Role 输入 */}
      <div>
        <label className="block text-sm font-medium text-olive-gray">Role</label>
        <input
          type="text"
          required
          className="mt-1 w-full rounded-xl border border-cream px-3 py-1.5 text-sm"
        />
      </div>
      {/* System Prompt 折叠区域 */}
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="text-sm text-terracotta"
      >
        {expanded ? 'Hide' : 'Show'} System Prompt
      </button>
      {expanded && (
        <textarea
          className="w-full rounded-xl border px-3 py-1.5 text-sm"
          rows={4}
          placeholder="Optional system prompt..."
        />
      )}
    </div>
  );
}
```

### 启动/停止按钮 (DESIGN.md 色系)
```typescript
// Source: [CITED: 11-CONTEXT.md specifics]
// 启动 = terracotta (#c96442), 停止 = error crimson (#b53333)

function TeamControls({ isRunning, onSendCommand }: TeamControlsProps) {
  return (
    <div className="flex gap-3">
      <button
        type="button"
        disabled={isRunning}
        onClick={() => onSendCommand('start_team')}
        className="rounded-lg px-4 py-2 text-sm font-medium text-ivory"
        style={{
          backgroundColor: '#c96442',  // Terracotta brand
          opacity: isRunning ? 0.5 : 1,
        }}
      >
        Start Team
      </button>
      <button
        type="button"
        disabled={!isRunning}
        onClick={() => onSendCommand('stop_team')}
        className="rounded-lg px-4 py-2 text-sm font-medium text-ivory"
        style={{
          backgroundColor: '#b53333',  // Error crimson
          opacity: !isRunning ? 0.5 : 1,
        }}
      >
        Stop Team
      </button>
    </div>
  );
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Tailwind 3 @tailwindcss directive | Tailwind 4 @import "tailwindcss" | Tailwind 4 (2025) | 不需要 tailwind.config.js，配置在 CSS 中完成 |
| React 18 useEffect fire-once pattern | React 19 cleanup-first StrictMode | React 19 (2024) | useEffect cleanup 必须完整，StrictMode 更严格 |
| PixiJS v7 new Application({...}) | PixiJS v8 new Application() + await app.init() | PixiJS v8 (2024) | 构造函数无参数，init() 异步配置 |
| TypeScript enum | union type + as const | TS 5.8+ erasableSyntaxOnly | 不能用 enum，只能用类型推断 |

**Deprecated/outdated:**
- Tailwind 3 配置文件 (tailwind.config.js): Tailwind 4 不使用，配置在 CSS `@import "tailwindcss"` 中完成 [VERIFIED: 项目 vite.config.ts 使用 @tailwindcss/vite 插件]
- PixiJS v7 `beginFill()` / `lineStyle()`: v8 使用链式 API `.circle().fill()` [VERIFIED: Phase 10 代码已使用 v8 API]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | 浏览器原生 WebSocket API 在所有目标浏览器中支持 | Standard Stack | 极低 — 现代浏览器全部支持 |
| A2 | Date.toLocaleTimeString() 输出 HH:MM:SS 格式 | Don't Hand-Roll | 低 — locale 相关，可能需要 toLocaleTimeString('en-GB') 强制 24h 格式 |
| A3 | React 19 StrictMode 双重挂载行为与 React 18 一致 | Common Pitfalls | 低 — React 19 文档确认 StrictMode 仍双重调用 effects [CITED: react.dev] |
| A4 | Canvas updateState() 可以从 useEffect 中高频调用无性能问题 | Architecture Patterns | 低 — PixiJS 内部有 movement 缓冲，且 MVP 事件频率低 |

## Open Questions

1. **事件日志事件去重**
   - What we know: 后端可能连续推送相同 type 的 VizEvent（如多个 tool_call）
   - What's unclear: 事件日志是否应该对连续相同 type 的事件合并显示
   - Recommendation: MVP 不做合并，每条 VizEvent 独立显示。v0.0.4+ 考虑折叠

2. **stop_team 后 Agent 状态清理**
   - What we know: stop_team 发送 name 参数，后端取消 task
   - What's unclear: 后端是否会主动发送 shutdown VizEvent，还是前端需要在 command_response 后手动设置
   - Recommendation: 前端在收到 stop_team 的 command_response 后 dispatch TEAM_STOPPED，不假设后端发 shutdown

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node.js | Vite 构建/开发 | ✓ | 22.22.0 | — |
| npm | 包管理 | ✓ | 10.9.4 | — |
| React 19 | UI 框架 | ✓ | 19.2.6 | — |
| PixiJS v8 | Canvas 渲染 | ✓ | 8.18.1 | — |
| Tailwind 4 | CSS | ✓ | 4.3.0 | — |
| TypeScript 6 | 类型检查 | ✓ | ~6.0.x | — |
| Vite 8 | 构建工具 | ✓ | 8.0.12 | — |
| Backend WebSocket (ws://localhost:8765) | 实时数据 | ✗ | — | 开发时手动启动后端 |
| 浏览器 WebSocket API | 通信 | ✓ | Native | — |

**Missing dependencies with no fallback:**
- Backend WebSocket 服务需要手动启动（Phase 9 实现的后端）。前端开发时可不依赖后端进行 UI 开发，WebSocket 连接失败时 UI 显示 "disconnected" 状态。

**Missing dependencies with fallback:**
- None

## Validation Architecture

> workflow.nyquist_validation 未在 config.json 中设置，视为启用。

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Vitest (待安装) — Vite 原生测试框架 |
| Config file | 待创建 vitest.config.ts |
| Quick run command | `cd frontend && npx vitest run --reporter=verbose` |
| Full suite command | `cd frontend && npx vitest run` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CNFG-01 | 表单创建 Agent | unit | `vitest run src/__tests__/ConfigForm.test.tsx` | ❌ Wave 0 |
| CNFG-02 | 启动按钮发送 start_team | unit | `vitest run src/__tests__/TeamControls.test.tsx` | ❌ Wave 0 |
| CNFG-03 | 停止按钮发送 stop_team | unit | `vitest run src/__tests__/TeamControls.test.tsx` | ❌ Wave 0 |
| CNFG-04 | Agent 列表 + 状态灯 | unit | `vitest run src/__tests__/AgentList.test.tsx` | ❌ Wave 0 |
| CONC-01 | WebSocket 指数退避重连 | unit | `vitest run src/__tests__/useWebSocket.test.ts` | ❌ Wave 0 |
| CONC-02 | reducer 统一分发 | unit | `vitest run src/__tests__/reducer.test.ts` | ❌ Wave 0 |
| CONC-03 | React ref 桥接 PixiJS | integration | 手动验证 | N/A |
| CONC-04 | 连接状态指示器 | unit | `vitest run src/__tests__/ConnectionIndicator.test.tsx` | ❌ Wave 0 |
| CONC-05 | 事件日志列表 | unit | `vitest run src/__tests__/EventLog.test.tsx` | ❌ Wave 0 |

**注意:** REQUIREMENTS.md 的 Out of Scope 明确标注 "前端单元测试 — 第一期验证端到端链路，测试以后补"。本 Phase 的 Wave 0 gap 列出但**不阻塞实现**。CONC-03（React-PixiJS 桥接）为手动验证，因为 PixiJS 需要真实 DOM + Canvas 环境。

### Sampling Rate
- **Per task commit:** 无（前端测试框架待搭建）
- **Per wave merge:** `cd frontend && npx tsc -b && npx vite build`（类型检查 + 构建验证）
- **Phase gate:** 构建通过 + 手动验证端到端链路（启动后端 → 打开前端 → 创建 Agent → 观察动画）

### Wave 0 Gaps
- [ ] `vitest` 安装 + `vitest.config.ts` 配置 — 覆盖所有 unit test
- [ ] 注意: 根据项目 REQUIREMENTS.md Out of Scope "前端单元测试"，测试框架搭建可推迟到 v0.0.4+

## Security Domain

> Phase 11 是纯前端 React 应用，安全面较窄。

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | 无认证需求（MVP 本地开发） |
| V3 Session Management | no | 无 session |
| V4 Access Control | no | 无权限控制 |
| V5 Input Validation | yes | HTML5 required + TypeScript 类型约束 |
| V6 Cryptography | no | 无加密需求 |

### Known Threat Patterns for React + WebSocket

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| XSS via VizEvent payload | Tampering | React 自动转义 JSX，不使用 dangerouslySetInnerHTML |
| WebSocket 消息注入 | Tampering | JSON.parse 在 try-catch 中，无效消息静默丢弃 |
| CSRF via WebSocket | — | WebSocket 不受 CSRF 影响（无 HTTP cookie） |
| WebSocket 连接劫持 | Spoofing | MVP 阶段 ws://localhost，无跨域风险 |

## Sources

### Primary (HIGH confidence)
- [react.dev/reference/react/useReducer](https://react.dev/reference/react/useReducer) — useReducer API、StrictMode caveats、不可变更新要求
- [react.dev/learn/managing-state](https://react.dev/learn/managing-state) — 状态管理策略选择
- Phase 10 实现代码: `frontend/src/canvas/index.ts`, `types.ts`, `constants.ts`, `renderer.ts` — Canvas API 接口
- Phase 9 实现代码: `framework/agent_framework/viz/ws_server.py`, `viz_event.py` — WebSocket 消息协议
- `DESIGN.md` — 暖色调设计系统、组件样式规范

### Secondary (MEDIUM confidence)
- [DEV Community: Using WebSockets with React.js](https://dev.to/itays123/using-websockets-with-react-js-the-right-way-no-library-needed-15d0) — useWebSocket hook 模式 + 指数退避
- [Medium: Elegantly Type React's useReducer with Discriminated Unions](https://medium.com/@mohsentaleb/elegantly-type-reacts-usereducer-and-context-api-with-discriminated-union-of-typescript-855ff475cafe) — TypeScript discriminated union action types
- [GitConnected: React 18/19 Strict Mode Double WebSocket Fix](https://levelup.gitconnected.com/react-18-19-strict-mode-is-opening-two-websocket-connections-fix-it-like-this-45492db347e4) — StrictMode WebSocket cleanup 模式

### Tertiary (LOW confidence)
- [Medium: React Declarative-Imperative Bridge Pattern](https://betterprogramming.pub/react-declarative-imperative-bridge-pattern-483d8ab63559) — React-命令式API 桥接模式

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — 所有依赖已安装并验证版本，无需新增包
- Architecture: HIGH — 数据流设计基于 React 官方推荐模式 + 已验证的 Phase 9/10 API
- Pitfalls: HIGH — StrictMode 双重挂载、Map mutation、verbatimModuleSyntax 均有明确规避方案

**Research date:** 2026-05-31
**Valid until:** 2026-06-30 (React/PixiJS 稳定 API)
