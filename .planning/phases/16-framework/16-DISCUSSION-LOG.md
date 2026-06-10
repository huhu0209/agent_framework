# Phase 16: Framework 安全修复 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-10
**Phase:** 16-Framework 安全修复
**Areas discussed:** 异步 I/O 策略, 注入防御深度, Plan 分组策略

---

## 异步 I/O 策略

| Option | Description | Selected |
|--------|-------------|----------|
| aiofiles | 引入新依赖，更原生 async。memory/ ~10 个文件 + result_truncator 全部改用 aiofiles | ✓ |
| asyncio.to_thread() | 标准库包装器，每个调用点都要包装，代码笨重 | |
| 你决定 | Claude 判断哪种更合适 | |

**User's choice:** aiofiles（推荐）
**Notes:** 无额外备注

---

## 注入防御深度

| Option | Description | Selected |
|--------|-------------|----------|
| 基础边界标记 | XML 标签包裹 PromptBlock，让 LLM 区分来源。不检测内容，只标记边界。实现简单 | ✓ |
| 内容扫描 + 边界标记 | 扫描 Skill 内容检测 injection 模式（如 "ignore previous instructions"）。误报风险 | |
| 你决定 | Claude 判断 | |

**User's choice:** 基础边界标记（推荐）
**Notes:** 无额外备注

---

## Plan 分组策略

| Option | Description | Selected |
|--------|-------------|----------|
| 2 plans 按模块分 | Plan A: I/O + try-except，Plan B: MCP + 注入 + WebSocket。均衡 | |
| 4+ plans 按问题类型分 | Plan per problem type。每个 plan 小而独立 | ✓ |
| 1 plan 全部完成 | 全部 8 个 requirement 在一个 plan | |

**User's choice:** 4+ plans 按问题类型分
**Notes:** 确认分为 4 个 plan：同步 I/O / MCP 环境 / 注入防护 / WebSocket + try-except

---

## Claude's Discretion

- aiofiles 具体调用方式
- XML 标签命名和格式
- MCP 白名单最小环境变量列表
- WebSocket token 验证实现细节
- 每个 plan 内部修复顺序

## Deferred Ideas

None — discussion stayed within phase scope
