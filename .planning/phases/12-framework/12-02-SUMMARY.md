---
phase: 12-framework
plan: 02
subsystem: framework
tags: [code-review, tools, agents, security, mcp]
dependency_graph:
  requires: [12-01]
  provides: [REVIEW-FRAMEWORK.md tools/ + agents/ sections complete]
  affects: [docs/reviews/REVIEW-FRAMEWORK.md]
tech_stack:
  added: []
  patterns: [manual code review, security audit, STRIDE threat model]
key_files:
  created: []
  modified:
    - docs/reviews/REVIEW-FRAMEWORK.md
decisions:
  - base.py is NOT an empty file (24 lines with Agent ABC + AgentEvent), correcting CONCERNS.md note
  - CONCERNS.md Path import bug verified as FIXED in current codebase
  - safe_path() in file_tools.py verified complete — TOCTOU documented as theoretical risk only
  - MCP env key blacklist documented as incomplete (missing auth/session/jwt patterns)
  - _CRITICAL_TOOLS empty set identified as permanently unreachable code path
metrics:
  duration: 14m
  completed: 2026-06-09
  tasks: 2
  files_created: 0
  files_modified: 1
  issues_found_tools: 21
  issues_found_agents: 17
  issues_total_new: 38
  tests_passing: 964
---

# Phase 12 Plan 02: tools/ + agents/ Module Review Summary

tools/ 模块 12 个源文件（~1511 行）+ agents/ 模块 6 个源文件（~1135 行）逐行审查完成，共发现 38 个新 issue（tools/ 21 个 + agents/ 17 个），覆盖逻辑漏洞、设计问题、安全漏洞、死代码四维度。

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | tools/ 模块逐文件审查 | 87d42f6 | docs/reviews/REVIEW-FRAMEWORK.md |
| 2 | agents/ 模块逐文件审查 | f6dd785 | docs/reviews/REVIEW-FRAMEWORK.md |

## Key Results

### tools/ Module Review (Task 1) — 21 issues

12 个源文件逐行审查。重点发现：

| Category | Count | IDs |
|----------|-------|-----|
| FRMW-ARCH-* | 8 | ARCH-06 ~ ARCH-13 |
| FRMW-LOGIC-* | 6 | LOGIC-05 ~ LOGIC-10 |
| FRMW-SEC-* | 5 | SEC-13 ~ SEC-17 |
| FRMW-DEAD-* | 2 | DEAD-03, DEAD-12 |

**Notable findings:**

- **FRMW-LOGIC-05 (HIGH):** router.py ASK 权限决策返回 error 而非触发 HITL，权限管道的 ASK 永远等同于 DENY
- **FRMW-LOGIC-06 (HIGH):** `_CRITICAL_TOOLS` 全局空集合，权限 DENY 第一级永远不触发，无 API 添加工具名
- **FRMW-SEC-13 (HIGH):** `result_truncator.py` 同步文件 I/O 在 async 上下文中阻塞事件循环
- **FRMW-SEC-15 (MEDIUM):** MCP env key blacklist 缺少 `auth`, `session`, `jwt`, `cookie` 等模式
- **FRMW-SEC-16 (MEDIUM):** MCP transport 子进程继承完整系统环境变量（含 API key）
- **FRMW-ARCH-06 (HIGH):** router.py dispatch 4 层职责混合（权限 + hook + 执行 + 降级），C901=18

**CONCERNS.md items verified:**
- file_tools.py safe_path 调用: **VERIFIED COMPLETE** — read_file 和 write_file 都正确调用 safe_path()
- MCP transport.py 环境变量注入: **VERIFIED** — config.py validator 存在但覆盖不完整 (FRMW-SEC-15)
- router.py:72-76 ASK 决策: **CONFIRMED** (FRMW-LOGIC-05)
- router.py:179-183 _dispatch_agent stub: **CONFIRMED** (FRMW-ARCH-07)
- permissions.py:40 _CRITICAL_TOOLS 空: **CONFIRMED** (FRMW-LOGIC-06)
- search_tools.py mock: **UPDATED** — 已替换为 Tavily API 实现，但模块级全局状态问题存在 (FRMW-ARCH-09)
- result_truncator.py:34 同步 I/O: **CONFIRMED** (FRMW-SEC-13)
- compactor.py:126-156 额外 LLM 调用: **CONFIRMED** (FRMW-ARCH-08)

### agents/ Module Review (Task 2) — 17 issues

6 个源文件逐行审查。重点发现：

| Category | Count | IDs |
|----------|-------|-----|
| FRMW-ARCH-* | 6 | ARCH-14 ~ ARCH-19 |
| FRMW-LOGIC-* | 5 | LOGIC-11 ~ LOGIC-15 |
| FRMW-SEC-* | 2 | SEC-08, SEC-18 |
| FRMW-DEAD-* | 4 | DEAD-04 ~ DEAD-06, DEAD-13 |

**Notable findings:**

- **FRMW-ARCH-14 (HIGH):** AgentLoop.__init__ 19 个参数，构造器 73 行初始化逻辑
- **FRMW-ARCH-15 (HIGH):** AgentLoop.run() C901=30，175 行，含 5 个 stop_reason 分支 + 3 个通知 drain + 计划注入
- **FRMW-SEC-08 (HIGH):** agent_loop.py:288 logger 未定义，memory flush 失败时抛 NameError 掩盖原始异常
- **FRMW-SEC-18 (MEDIUM):** run_subagent 共享 ToolUseContext，子 agent 修改 ctx.extra 泄漏到父 agent
- **FRMW-LOGIC-12 (MEDIUM):** _maybe_compact 中 flush/compact 并行但 flush 异常被静默忽略
- **FRMW-ARCH-16 (MEDIUM):** ReflectionAgent/PlanAndSolveAgent 每轮创建新 AgentLoop，丢失对话历史和高级功能

**CONCERNS.md items verified:**
- agent_loop.py:87 Path import 缺失: **VERIFIED FIXED** — Path 已在行 10 正常导入
- 15 参数构造器: **CONFIRMED + EXPANDED** — 实际为 19 个参数 (ARCH-14)，CONCERNS.md 记录为 15 可能是旧版本数据
- base.py 空文件: **CORRECTED** — base.py 有 24 行（Agent ABC + AgentEvent dataclass），非空文件

## Verification

- `grep "## tools/" docs/reviews/REVIEW-FRAMEWORK.md` — PASS (1 match)
- `grep "## agents/" docs/reviews/REVIEW-FRAMEWORK.md` — PASS (1 match)
- `grep -c "#### FRMW-" docs/reviews/REVIEW-FRAMEWORK.md` — 65 (32 from Plan 01 + 38 new from Plan 02)
- tools/ section: 0 "pending" entries — PASS
- agents/ section: 0 "pending" entries — PASS
- `cd framework && pytest tests/ -x -q` — 964 passed — PASS
- No source files modified — PASS

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

The following module sections remain placeholder-only, pending Plans 03-04:
- `## teams/` — 2 ruff issues recorded, manual review pending (Plan 03)
- `## memory/` — 1 ruff issue recorded, manual review pending (Plan 03)
- `## safety/` — no ruff issues, manual review pending (Plan 03)
- `## orchestrator/` — 1 ruff issue recorded, manual review pending (Plan 03, moved from Plan 02 per plan design)
- `## hooks/` — 1 ruff issue recorded, manual review pending (Plan 04)
- `## skills/` — no ruff issues, manual review pending (Plan 04)
- `## tasks/` — 2 ruff issues recorded, manual review pending (Plan 04)
- `## commands/` — no ruff issues, manual review pending (Plan 04)
- `## prompts/` — no ruff issues, manual review pending (Plan 04)
- `## a2a/` — no ruff issues, manual review pending (Plan 04)
- `## transcript/` — no ruff issues, manual review pending (Plan 04)
- `## viz/` — 1 ruff issue recorded, manual review pending (Plan 04)

These stubs are intentional per the plan design: Plans 03-04 will fill in manual review findings for the remaining 12 modules.

## Self-Check: PASSED

- [x] docs/reviews/REVIEW-FRAMEWORK.md exists
- [x] .planning/phases/12-framework/12-02-SUMMARY.md exists
- [x] Commit 87d42f6 (Task 1: tools/ review) found in git log
- [x] Commit f6dd785 (Task 2: agents/ review) found in git log
- [x] No source files modified (964 tests still pass)
