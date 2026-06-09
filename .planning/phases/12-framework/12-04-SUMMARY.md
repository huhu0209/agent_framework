---
phase: 12-framework
plan: 04
subsystem: framework
tags: [code-review, orchestrator, a2a, skills, hooks, commands, prompts, transcript, viz]
dependency_graph:
  requires: [12-01-SUMMARY.md]
  provides: [REVIEW-FRAMEWORK.md orchestrator/a2a/skills/hooks/commands/prompts/transcript/viz sections]
  affects: [docs/reviews/REVIEW-FRAMEWORK.md]
tech_stack:
  added: []
  patterns: [manual code review, security audit, architecture review]
key_files:
  created: []
  modified:
    - docs/reviews/REVIEW-FRAMEWORK.md
decisions:
  - engine.py is no longer empty (107 lines) — CONCERNS.md entry outdated
  - router.py has been deleted from codebase — CONCERNS.md entry outdated
  - A2AServer auth check covers agent-card endpoint — documented as design decision
  - EventBus publish uses lock-free snapshot iteration — documented as acceptable for single-thread asyncio
metrics:
  duration: 12m
  completed: 2026-06-09
  tasks: 2
  files_modified: 1
  issues_found: 36
  tests_passing: 964
---

# Phase 12 Plan 04: orchestrator/ + a2a/ + skills/ + hooks/ + commands/ + prompts/ + transcript/ + viz/ Review Summary

Wave 2 逐文件人工审查覆盖框架层剩余 8 个模块（共 2,883 行），产出 REVIEW-FRAMEWORK.md 的 8 个新章节，包含 36 个 FRMW-* issue（7 个安全、11 个逻辑、11 个架构、1 个死代码 + 7 个 ruff 基线已有）。

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | orchestrator/ + a2a/ + skills/ + hooks/ 逐文件审查 | 6c09bf2 | docs/reviews/REVIEW-FRAMEWORK.md |
| 2 | commands/ + prompts/ + transcript/ + viz/ 逐文件审查 | 6c09bf2 | docs/reviews/REVIEW-FRAMEWORK.md |

## Key Results

### orchestrator/ (6 issues)

| Category | Count | IDs |
|----------|-------|-----|
| FRMW-ARCH-* | 3 | ARCH-39 (lazy imports), ARCH-40 (PLR0913), ARCH-41 (SubTask dead code) |
| FRMW-DEAD-* | 1 | DEAD-08 (AgentEvent unused import) |
| FRMW-LOGIC-* | 2 | LOGIC-28 (deferred import), LOGIC-29 (send_message context loss) |

**Notable findings:**
- engine.py 已非空文件，CONCERNS.md 条目已过时
- router.py 已删除，CONCERNS.md 条目已过时
- send_message 通过 spawn 重建 Worker，不保留原始 system prompt 和对话历史

### a2a/ (6 issues)

| Category | Count | IDs |
|----------|-------|-----|
| FRMW-SEC-* | 2 | SEC-13 (timing attack on API key), SEC-14 (agent-card auth) |
| FRMW-LOGIC-* | 3 | LOGIC-30 (client leak), LOGIC-31 (timeout no cancel), LOGIC-32 (event.data access) |
| FRMW-ARCH-* | 1 | ARCH-42 (in-memory task storage) |

**Notable findings:**
- A2AServer._verify_auth 使用 `==` 比较 API key，存在时序攻击风险
- A2AClient 无 `__aenter__`/`__aexit__`，httpx.AsyncClient 可能泄漏

### skills/ (4 issues)

| Category | Count | IDs |
|----------|-------|-----|
| FRMW-SEC-* | 1 | SEC-15 (skill content injection) |
| FRMW-ARCH-* | 3 | ARCH-43 (stat scan), ARCH-44 (activate performance), ARCH-45 (Windows path) |

**Notable findings:**
- SkillRegistry 无 skill 内容验证，恶意 SKILL.md 可注入任意 system prompt
- _maybe_refresh 每次 API 调用都 stat() 所有目录

### hooks/ (4 issues)

| Category | Count | IDs |
|----------|-------|-----|
| FRMW-SEC-* | 1 | SEC-16 (bash -c execution) |
| FRMW-DEAD-* | 1 | DEAD-09 (typing.Any unused) |
| FRMW-LOGIC-* | 1 | LOGIC-33 (matcher semantics) |
| FRMW-ARCH-* | 1 | ARCH-46 (once hook removal) |

**Notable findings:**
- _execute_command 使用 bash -c 执行用户配置命令，trusted flag 是唯一防护层

### commands/ (4 issues)

| Category | Count | IDs |
|----------|-------|-----|
| FRMW-SEC-* | 1 | SEC-17 ($ARGUMENTS injection) |
| FRMW-ARCH-* | 1 | ARCH-47 (config no-op) |
| FRMW-LOGIC-* | 2 | LOGIC-34 (private attribute access), LOGIC-35 (special chars) |

**Notable findings:**
- help.py 直接访问 SkillRegistry._documents 私有属性
- /config 命令只返回消息不实际修改配置

### prompts/ (3 issues)

| Category | Count | IDs |
|----------|-------|-----|
| FRMW-SEC-* | 1 | SEC-18 (prompt injection via profile) |
| FRMW-ARCH-* | 2 | ARCH-48 (file size), ARCH-49 (format collision) |

**Notable findings:**
- PromptAssembler 不转义用户注入的 profile 内容
- DRIFT_WARN_TEMPLATE 使用 str.format()，plan_text 中花括号会导致 KeyError

### transcript/ (4 issues)

| Category | Count | IDs |
|----------|-------|-----|
| FRMW-SEC-* | 1 | SEC-19 (sensitive data plaintext) |
| FRMW-LOGIC-* | 2 | LOGIC-36 (file handle leak), LOGIC-37 (JSONL corruption) |
| FRMW-ARCH-* | 1 | ARCH-50 (LoopEvent coupling) |

**Notable findings:**
- 转录文件包含完整对话内容，可能泄露 API key 等敏感信息
- TranscriptWriter 不实现上下文管理器，文件句柄可能泄漏

### viz/ (5 issues)

| Category | Count | IDs |
|----------|-------|-----|
| FRMW-SEC-* | 3 | SEC-12 (silent catch), SEC-20 (WebSocket no auth), SEC-21 (input validation) |
| FRMW-LOGIC-* | 1 | LOGIC-38 (EventBus race window) |
| FRMW-ARCH-* | 1 | ARCH-51 (global _active_runners) |

**Notable findings:**
- WebSocket 无认证，任何本地客户端可连接并接收所有事件
- _active_runners 模块级全局变量，多实例场景下共享

## Verification

- All 8 module sections present in REVIEW-FRAMEWORK.md -- PASS
- orchestrator/ has 6 FRMW-* issues (>= 3 required) -- PASS
- a2a/ has 6 FRMW-* issues (>= 2 required, includes error handling) -- PASS
- skills/ has 4 FRMW-* issues (>= 2 required, includes directory scan) -- PASS
- hooks/ has 4 FRMW-* issues (>= 2 required, includes shell execution) -- PASS
- commands/ has 4 FRMW-* issues (>= 3 required) -- PASS
- prompts/ has 3 FRMW-* issues (>= 2 required, includes prompt security) -- PASS
- transcript/ has 4 FRMW-* issues (>= 2 required, includes file I/O) -- PASS
- viz/ has 5 FRMW-* issues (>= 3 required, includes WebSocket security) -- PASS
- Each issue contains: ID, Description, File Location, Impact, Fix Suggestion, Priority, Related -- PASS
- Issues sorted by priority: CRITICAL > HIGH > MEDIUM > LOW -- PASS
- `cd framework && pytest tests/ -x -q` -- 964 passed -- PASS
- No source files modified -- PASS

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] CONCERNS.md entries outdated**
- **Found during:** Task 1 (orchestrator/ review)
- **Issue:** Plan referenced CONCERNS.md entries for engine.py (empty file) and router.py. Both entries are outdated: engine.py now has 107 lines of implementation, router.py has been deleted.
- **Fix:** Documented in orchestrator/ section header that CONCERNS.md entries are outdated. Reviewed engine.py as a normal source file (not as an empty file).
- **Files modified:** docs/reviews/REVIEW-FRAMEWORK.md
- **Commit:** 6c09bf2

**2. [Rule 3 - Blocking] Duplicate a2a/ section**
- **Found during:** Task 1 edit
- **Issue:** Replacing the old placeholder sections for orchestrator/hooks/skills left a duplicate a2a/ placeholder section (from the original file layout where a2a/ was listed between tasks/ and commands/).
- **Fix:** Combined Task 1 and Task 2 into a single commit, replacing all 8 module placeholder sections in one edit to avoid structural issues.
- **Files modified:** docs/reviews/REVIEW-FRAMEWORK.md
- **Commit:** 6c09bf2

## Known Stubs

None -- all 8 module sections contain substantive review findings.

## Threat Flags

No new threat surface introduced beyond what was documented in the plan's threat_model. All findings are documentation-only (review report additions).

## Self-Check: PASSED

- FOUND: docs/reviews/REVIEW-FRAMEWORK.md
- FOUND: .planning/phases/12-framework/12-04-SUMMARY.md
- FOUND: commit 6c09bf2
- No framework/ source modifications in commit
