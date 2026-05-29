# Agent Framework — PROJECT.md

## What This Is

Python Agent 框架，Orchestrator 模式。框架层（通用、可复用）和应用层（具体业务）分离。
核心已实现：LLM Adapter（3 Provider）、Tool System、ReAct Agent Loop、Safety、Memory、Prompts、Skills、Tasks、Teams、Hooks、Commands。
v0.0.2 新增：多类型 Agent（Plan-and-Solve、Reflection）、编排引擎、声明式配置、真实搜索、A2A 协议。

## Core Value

可靠的 Agent 编排框架，提供安全、可测试、可扩展的基础设施。

## Tech Stack

- **Framework:** Python 3.11+, Pydantic v2, httpx, asyncio
- **Backend:** FastAPI（脚手架）
- **Frontend:** Vite + React + TypeScript + Tailwind（脚手架）
- **Test:** pytest, pytest-asyncio
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

### Active

(None — ready for next milestone)

### Out of Scope

| Feature | Reason |
|---------|--------|
| LangGraph / CrewAI / AutoGen 集成 | 竞争架构，与现有 Tool System 冲突 |
| Backend API 功能开发 | 脚手架阶段，非框架核心 |
| Frontend 功能开发 | 脚手架阶段，非框架核心 |
| A2A 流式模式（SSE） | Phase 8 只做同步 HTTP，流式留后续 |
| A2A 异步模式（Webhook） | 需要外部回调基础设施 |
| pyyaml 依赖 | flat frontmatter 足够 |

## Context

**Shipped v0.0.1** — 彻底 Code Review milestone（2026-05-29）。687 测试通过。

**Shipped v0.0.2** — Agent 扩展与编排 milestone（2026-05-29）。812 测试通过。
框架层 ~12,500 行源码 + ~9,000 行测试。新增 125 个测试。
9 个 plan 全部通过验证（5/5 must-haves per plan）。

**Architecture Evolution (v0.0.2):**
```
framework/agent_framework/
├── agents/
│   ├── base.py          ← Agent ABC + AgentEvent (NEW)
│   ├── agent_loop.py    ← LoopEvent(AgentEvent), AgentLoop(Agent)
│   ├── plan_solve.py    ← PlanAndSolveAgent (NEW)
│   ├── reflection.py    ← ReflectionAgent (NEW)
│   └── sub_agent.py
├── orchestrator/
│   └── engine.py        ← OrchestratorEngine (NEW)
├── config/
│   └── agent_config.py  ← AgentConfig + agent_from_config (NEW)
├── tools/
│   └── search_tools.py  ← Tavily real search (UPDATED)
├── a2a/                 ← A2A Protocol (NEW)
│   ├── models.py        ← AgentCard, A2ATask, A2AMessage
│   ├── server.py        ← A2AServer (pure ASGI)
│   └── client.py        ← A2AClient (httpx)
```

**Tech Debt:** v0.0.1 遗留 14 项（all LOW）+ v0.0.2 新增（Orchestrator 复杂度评估启发式可升级）

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

## Constraints

- 框架层优先，backend/frontend 暂不涉及
- 每个 milestone 有明确范围，不膨胀
- 测试必须全部通过才能关闭 milestone
- 硬上限防止无限循环：replan ≤ 2, reflection ≤ 2, agent chain ≤ 3

## Evolution

This document evolves at phase transitions and milestone boundaries.

---
*Last updated: 2026-05-29 after v0.0.2 milestone completion*
