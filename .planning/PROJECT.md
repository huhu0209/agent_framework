# Agent Framework — PROJECT.md

## What This Is

Python Agent 框架，Orchestrator 模式。框架层（通用、可复用）和应用层（具体业务）分离。
核心已实现：LLM Adapter（3 Provider）、Tool System、ReAct Agent Loop、Safety、Memory、Prompts、Skills、Tasks、Teams、Hooks、Commands。

## Core Value

可靠的 Agent 编排框架，提供安全、可测试、可扩展的基础设施。

## Tech Stack

- **Framework:** Python 3.11+, Pydantic v2, httpx, asyncio
- **Backend:** FastAPI（脚手架）
- **Frontend:** Vite + React + TypeScript + Tailwind（脚手架）
- **Test:** pytest, pytest-asyncio

## Requirements

### Validated

- ✓ 安全审查 + CRITICAL 修复 — v0.0.1
- ✓ Bug 修复审查（全部已知 Bug 修复 + 测试覆盖） — v0.0.1
- ✓ 架构审查报告（ARCH-REVIEW.md） — v0.0.1
- ✓ 性能审查 + 数据安全修复 — v0.0.1
- ✓ 测试覆盖补充（+57 测试，687 total） — v0.0.1

### Active

- [ ] Agent ABC 抽象基类 + AgentEvent 统一事件模型
- [ ] Plan-and-Solve Agent（先规划后执行）
- [ ] Reflection Agent（执行→反省→改进循环）
- [ ] OrchestratorEngine 编排引擎
- [ ] Agent 配置化（.md 文件定义 Agent）
- [ ] 真实搜索工具（替换 mock 数据）
- [ ] A2A 协议（同步模式 + HTTP transport）

### Out of Scope

- Backend API 开发（脚手架阶段）
- Frontend 功能开发（脚手架阶段）
- A2A 流式模式（SSE streaming）— 后续扩展
- A2A 异步模式（Webhook callback）— 后续扩展

## Current Milestone: v0.0.2 Agent 扩展与编排

**Goal:** 从单一 ReAct Agent 扩展为多类型 Agent 体系，新增编排引擎和 A2A 协议支持

**Target features:**
- Agent ABC 提取 + Plan-and-Solve Agent + Reflection Agent
- OrchestratorEngine + Agent 配置化（MD 文件）+ 真实搜索
- A2A 协议（AgentCard + Client + Server，同步模式）

## Context

**Shipped v0.0.1** — 彻底 Code Review milestone 完成（2026-05-29）。
框架层 ~7600 行源码，687 测试通过。5 个审查阶段产出 3 份结构化报告（SECURITY-REVIEW.md、ARCH-REVIEW.md、PERF-REVIEW.md），修复 3 个 Bug + 3 个安全问题。

**Tech Debt:** 14 项（all LOW），详见 v0.0.1-MILESTONE-AUDIT.md。

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
| 审查报告仅记录，不执行重构 | 本 milestone 仅审查，重构留后续 | ✓ Good |
| 保留 scaffold docstring（不删除空文件） | 标记预期功能，保留模块占位 | ✓ Good |

## Constraints

- 框架层优先，backend/frontend 暂不涉及
- 每个 milestone 有明确范围，不膨胀
- 测试必须全部通过才能关闭 milestone

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-05-29 after v0.0.2 milestone start*
