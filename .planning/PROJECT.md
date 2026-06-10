# Agent Framework — PROJECT.md

## What This Is

Python Agent 框架，Orchestrator 模式。框架层（通用、可复用）和应用层（具体业务）分离。
核心已实现：LLM Adapter（3 Provider）、Tool System、ReAct Agent Loop、Safety、Memory、Prompts、Skills、Tasks、Teams、Hooks、Commands。
v0.0.2 新增：多类型 Agent（Plan-and-Solve、Reflection）、编排引擎、声明式配置、真实搜索、A2A 协议。
v0.0.3 新增：EventBus 事件总线、WebSocket 实时推送、AgentRunner 包装层、PixiJS v8 Canvas 渲染、React 可视化面板。

## Core Value

可靠的 Agent 编排框架，提供安全、可测试、可扩展的基础设施。端到端可视化能力验证。

## Tech Stack

- **Framework:** Python 3.11+, Pydantic v2, httpx, asyncio
- **Viz Backend:** EventBus (asyncio.Queue pub-sub), websockets 16, AgentRunner
- **Frontend:** Vite + React + TypeScript + Tailwind + PixiJS v8
- **Backend:** FastAPI
- **Test:** pytest, pytest-asyncio (964 tests passing)
- **Search:** Tavily API (AsyncTavilyClient)
- **A2A:** 纯 ASGI (httpx + asyncio), 无额外 Web 框架依赖

## Requirements

### Validated

- ✓ 安全审查 + CRITICAL 修复 — v0.0.1
- ✓ Bug 修复审查（全部已知 Bug 修复 + 测试覆盖） — v0.0.1
- ✓ 架构审查报告（ARCH-REVIEW.md） — v0.0.1
- ✓ 性能审查 + 数据安全修复 — v0.0.1
- ✓ 测试覆盖补充（+57 测试，687 total） — v0.0.1
- ✓ Agent ABC + AgentEvent 统一事件模型（AGENT-01~05） — v0.0.2
- ✓ Plan-and-Solve Agent（PLAN-01~05） — v0.0.2
- ✓ Reflection Agent（REFL-01~04） — v0.0.2
- ✓ OrchestratorEngine 编排引擎（ORCH-01~05） — v0.0.2
- ✓ Agent 配置化（CONF-01~04） — v0.0.2
- ✓ 真实搜索工具 Tavily（SRCH-01~03） — v0.0.2
- ✓ A2A 协议同步模式 + API-key 认证（A2A-01~06） — v0.0.2
- ✓ EventBus 事件总线（EVNT-01~07） — v0.0.3
- ✓ WebSocket 实时推送（WSRV-01~05） — v0.0.3
- ✓ Canvas 渲染层（RNDR-01~07） — v0.0.3
- ✓ React 配置面板 + WebSocket 客户端（CNFG-01~04, CONC-01~05） — v0.0.3
- ✓ 框架层全面代码审查（FRMW-01~05, 133 issues） — v0.0.4
- ✓ 后端全面代码审查（BKND-01~05, 25 issues） — v0.0.4
- ✓ 前端全面代码审查（FRNT-01~05, 31 issues） — v0.0.4

### Active

**v0.0.5 — Review 问题修复**
- 修复 v0.0.4 全面代码审查中发现的 HIGH 和关键 MEDIUM 级别 issue
- 来源: docs/reviews/REVIEW-FRAMEWORK.md (133 issues), REVIEW-BACKEND.md (25 issues), REVIEW-FRONTEND.md (31 issues)
- 范围: 64 HIGH + 关键 MEDIUM（共 189 issues 中筛选）

### Out of Scope

| Feature | Reason |
|---------|--------|
| LangGraph / CrewAI / AutoGen 集成 | 竞争架构，与现有 Tool System 冲突 |
| A2A 流式模式（SSE） | 同步 HTTP 已实现，流式留后续 |
| A2A 异步模式（Webhook） | 需要外部回调基础设施 |
| 前端单元测试 | 第一期验证端到端链路，测试以后补 |
| 移动端适配 | 第一期仅桌面浏览器 |
| 真实像素精灵美术资源 | 第一期用 placeholder 几何图形 |
| 多 Agent 间通信可视化 | 第一期用单 Agent 验证链路 |

## Context

**Shipped v0.0.1** — 彻底 Code Review milestone（2026-05-29）。687 测试通过。

**Shipped v0.0.2** — Agent 扩展与编排 milestone（2026-05-29）。812 测试通过。
框架层 ~12,500 行源码 + ~9,000 行测试。新增 125 个测试。
9 个 plan 全部通过验证（5/5 must-haves per plan）。

**Shipped v0.0.3** — Agent 可视化平台 MVP（2026-05-31）。845 测试通过（当前 964）。
新增 EventBus + WebSocket + AgentRunner 后端事件系统。
新增 PixiJS v8 Canvas 渲染 + React 可视化面板前端。
端到端链路验证：config → spawn → event → WebSocket → canvas render。

**Shipped v0.0.4** — 全面代码审查（2026-06-09）。964 测试通过，零源码修改。
三份审查报告：REVIEW-FRAMEWORK.md（133 issues）、REVIEW-BACKEND.md（25 issues）、REVIEW-FRONTEND.md（31 issues）。
总计 189 个 issue（0 CRITICAL, 64 HIGH, 90 MEDIUM, 35 LOW），含跨层交叉参照。
CONCERNS.md "Backend entirely scaffold" 条目确认过时。

**Architecture Evolution (v0.0.3):**
```
framework/agent_framework/
├── viz/                    ← NEW in v0.0.3
│   ├── event_bus.py        ← EventBus pub-sub (asyncio.Queue)
│   ├── viz_event.py        ← VizEvent Pydantic model
│   ├── agent_runner.py     ← AgentRunner (AgentLoop → EventBus bridge)
│   └── ws_server.py        ← WebSocket server (websockets 16)
frontend/src/
├── canvas/                 ← NEW in v0.0.3
│   ├── types.ts            ← VizEvent/AnimationState types
│   ├── constants.ts        ← Positions, colors, mappings
│   ├── renderer.ts         ← PixiJS v8 Application + 3 Container layers
│   ├── scene.ts            ← Office scene drawing
│   ├── cat-sprite.ts       ← Geometric cat sprite
│   ├── animations.ts       ← 4 Ticker-driven animations
│   └── movement.ts         ← lerp movement system
├── state/                  ← NEW in v0.0.3
│   ├── types.ts            ← AppState/AppAction types
│   ├── reducer.ts          ← Pure reducer
│   └── context.tsx         ← AppProvider + useAppState
└── components/             ← NEW in v0.0.3
    ├── agent/              ← AgentStatusDot, AgentList
    ├── layout/             ← AppLayout, ConnectionIndicator
    └── ui/                 ← ConfigForm, TeamControls, EventLog
```

**Tech Debt:** v0.0.1 遗留 14 项 (all LOW) + v0.0.2 Orchestrator 启发式可升级 + v0.0.3 前端测试缺失

**Codebase Intelligence:**
- `.planning/codebase/ARCHITECTURE.md` — 架构分析
- `.planning/codebase/CONCERNS.md` — 已知问题清单
- `.planning/codebase/CONVENTIONS.md` — 编码规范
- `.planning/codebase/TESTING.md` — 测试规范
- `.planning/codebase/STRUCTURE.md` — 文件结构
- `.planning/codebase/STACK.md` — 技术栈
- `.planning/codebase/INTEGRATIONS.md` — 依赖关系

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Immutability via model_copy() | Pydantic v2 保证不可变性 | ✓ Good |
| safe_path() 路径沙箱 | 防止路径遍历攻击 | ✓ Good |
| SecretStr 保护 API Key | 防止信息泄露 | ✓ Good |
| os.replace 原子写入 MessageBus | 防止数据丢失 | ✓ Good |
| 审查报告仅记录，不执行重构 | 本 milestone 仅审查 | ✓ Good |
| 保留 scaffold docstring | 标记预期功能 | ✓ Good |
| Agent ABC 不约束 __init__ | 子类灵活定义构造函数 | ✓ Good |
| LoopEvent 继承 AgentEvent | 向后兼容 + 统一事件模型 | ✓ Good |
| replan 硬上限 2 次 | 防止无限循环 | ✓ Good |
| Reflection 硬上限 2 轮 | 不让 LLM 自行决定是否继续 | ✓ Good |
| Orchestrator 启发式复杂度评估 | 无额外 LLM 调用成本 | ✓ Good |
| A2A 纯 ASGI 实现 | 不依赖 FastAPI，轻量级 | ✓ Good |
| flat frontmatter Agent 配置 | 不引入 pyyaml 依赖 | ✓ Good |
| PixiJS v8 (非 Phaser) | 纯渲染引擎无游戏框架开销 | ✓ Good — v0.0.3 |
| websockets 库 (非 FastAPI WS) | 独立于 FastAPI，纯 asyncio | ✓ Good — v0.0.3 |
| useRef 命令式桥接 (非 React-PixiJS) | 零依赖，单向数据流 | ✓ Good — v0.0.3 |
| 有界队列 drop-oldest | 防止慢消费者内存溢出 | ✓ Good — v0.0.3 |
| 内联样式 (非 Tailwind) | DESIGN.md 自定义颜色更自然 | ✓ Good — v0.0.3 |
| useReducer+Context (非 Redux) | MVP 范围不需要复杂状态管理 | ✓ Good — v0.0.3 |
| Phase 9 和 Phase 10 并行开发 | 前后端解耦，加速交付 | ✓ Good — v0.0.3 |

## Constraints

- 框架层优先，v0.0.3 开始引入前端可视化
- 每个 milestone 有明确范围，不膨胀
- 测试必须全部通过才能关闭 milestone
- 硬上限防止无限循环：replan ≤ 2, reflection ≤ 2, agent chain ≤ 3
- PixiJS 只管渲染，React 拥有数据状态
- 第一期 MVP 只用 1 种动物（猫），验证端到端链路

## Current State

**Shipped v0.0.4** — 964 测试通过，189 个审查 issue 已记录待修复。

**Current: v0.0.5** — Review 问题修复。修复 HIGH + 关键 MEDIUM 级别 issue（64 HIGH, ~90 MEDIUM 中筛选）。

## Evolution

This document evolves at phase transitions and milestone boundaries.

---
*Last updated: 2026-06-10 after v0.0.5 milestone initiated*
