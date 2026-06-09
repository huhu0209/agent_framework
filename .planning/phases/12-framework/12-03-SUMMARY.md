---
phase: 12-framework
plan: 03
subsystem: framework
tags: [code-review, memory, safety, teams, tasks, race-conditions]
dependency_graph:
  requires: [12-01, 12-02]
  provides: [REVIEW-FRAMEWORK.md memory/ + safety/ + teams/ + tasks/ sections complete]
  affects: [docs/reviews/REVIEW-FRAMEWORK.md]
tech_stack:
  added: []
  patterns: [manual line-by-line code review, issue categorization FRMW-LOGIC/ARCH/SEC/DEAD]
key_files:
  created: []
  modified:
    - docs/reviews/REVIEW-FRAMEWORK.md
decisions:
  - CONCERNS.md pending_writes type annotation bug confirmed fixed (now list[Task] not list[tuple[Task]])
  - CONCERNS.md get_event_loop bug confirmed fixed (now get_running_loop)
  - CONCERNS.md _normalize.py mutation bug confirmed fixed (now uses model_copy)
  - bus.py read_inbox improved from naive write_text("") to atomic temp+replace, but read+clear gap remains
  - HITL system exists but is completely unwired -- documented as architectural gap
metrics:
  duration: 11m
  completed: 2026-06-09
  tasks: 2
  files_reviewed: 21
  issues_found: 41
  tests_passing: 964
---

# Phase 12 Plan 03: memory/ + safety/ + teams/ + tasks/ Module Review Summary

Wave 2: 逐文件审查 memory/（9 文件 944 行）+ safety/（4 文件 315 行）+ teams/（4 文件 345 行）+ tasks/（4 文件 576 行），共 21 个文件 2180 行，产出 41 个 issue 覆盖四个维度（LOGIC/ARCH/SEC/DEAD）。

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | memory/ + safety/ 模块逐文件审查 | a9a5c4e | docs/reviews/REVIEW-FRAMEWORK.md |
| 2 | teams/ + tasks/ 模块逐文件审查 | f5f5cdd | docs/reviews/REVIEW-FRAMEWORK.md |

## Key Results

### memory/ Module Review (Task 1, 9 files)

10 issues found across 4 categories:

| Category | Issues | Notable |
|----------|--------|---------|
| FRMW-ARCH-* | ARCH-20 ~ ARCH-24 | 全模块同步 I/O 阻塞、full-file scan for frontmatter |
| FRMW-LOGIC-* | LOGIC-16 ~ LOGIC-19 | flush error recovery、index truncation、overlap detection |
| FRMW-SEC-* | SEC-10 | sha1 for filename（非安全场景） |

**Key findings:**
- ARCH-20: memory/ 全模块使用同步 Path.read_text()/write_text()，在 async 框架中阻塞事件循环
- ARCH-21: retriever._scan_candidates 读取完整文件只为提取 frontmatter
- LOGIC-17: flush.py 失败时事件不可恢复（对话已被压缩）
- LOGIC-19: _detect_overlap 关键词匹配过于宽松，几乎总触发 warning

### safety/ Module Review (Task 1, 4 files)

9 issues found across 4 categories:

| Category | Issues | Notable |
|----------|--------|---------|
| FRMW-ARCH-* | ARCH-25 ~ ARCH-28 | CommandPolicy 占位、PermissionResult 非 BaseModel |
| FRMW-LOGIC-* | LOGIC-20 ~ LOGIC-22 | verification stub、HITL not wired、无注解工具默认 ASK |
| FRMW-SEC-* | SEC-19 ~ SEC-20 | _CRITICAL_TOOLS 空集合、safe_path symlink edge case |

**Key findings:**
- ARCH-25: CommandPolicy 完全是占位接口，bash 工具添加前必须先实施
- SEC-19: _CRITICAL_TOOLS 全局空集合，DENY 第一级永远不触发
- LOGIC-20: VerificationRunner 5 种检查类型只实现 regex_match，其余静默返回 None
- LOGIC-21: HITL 系统存在但未接线到 ToolRouter（CONCERNS.md 记载的 get_event_loop 已修正为 get_running_loop）

### teams/ Module Review (Task 2, 4 files)

9 issues found across 4 categories:

| Category | Issues | Notable |
|----------|--------|---------|
| FRMW-ARCH-* | ARCH-29 ~ ARCH-32 | idle timeout 无通知、AgentLoop 消息累积、TeamMessage from_ 命名 |
| FRMW-LOGIC-* | LOGIC-23 ~ LOGIC-24 | 非原子 read+clear、私有属性访问 |
| FRMW-SEC-* | SEC-09, SEC-21 | 静默跳过解析异常、可预测 inbox 路径 |
| FRMW-DEAD-* | DEAD-07 | 未使用的 Agent import |

**Key findings:**
- LOGIC-23: bus.py read_inbox 已改进为 atomic temp+replace 清零，但 read 和 clear 之间仍有间隙
- SEC-21: inbox JSONL 文件无完整性保护，可被外部进程篡改
- ARCH-30: 队友 AgentLoop 消息历史无限累积，可能超出 token 限制

### tasks/ Module Review (Task 2, 4 files)

13 issues found across 4 categories:

| Category | Issues | Notable |
|----------|--------|---------|
| FRMW-ARCH-* | ARCH-33 ~ ARCH-38 | _apply_changes 复杂变异、无内存索引、sync I/O in lock |
| FRMW-LOGIC-* | LOGIC-25 ~ LOGIC-27 | 类型标注已修正、_clear_dependency 部分失败、runner 忽略 max_steps |
| FRMW-SEC-* | SEC-11, SEC-22 | try-except-pass、_path 安全验证 |
| FRMW-DEAD-* | DEAD-10 | 未使用的 Agent import |

**Key findings:**
- ARCH-33: _apply_changes 一个方法承担字段更新 + 双向依赖管理 + 批量写入三项职责
- ARCH-34: 每次操作扫描所有 task JSON 文件，无内存索引
- LOGIC-25: CONCERNS.md 记载的 `list[tuple[Task]]` 类型标注错误已修正为 `list[Task]`
- LOGIC-27: runner.py 只处理 done/error 事件，忽略 max_steps 事件

## CONCERNS.md Items Verified

| CONCERNS.md Item | Status | REVIEW Issue |
|-----------------|--------|-------------|
| 同步文件 I/O 阻塞事件循环 | CONFIRMED | FRMW-ARCH-20 (memory/), FRMW-ARCH-35 (tasks/) |
| sha1 用于文件名生成 | CONFIRMED (非安全场景) | FRMW-SEC-10 |
| VerificationRunner 只实现 regex_match | CONFIRMED | FRMW-LOGIC-20 |
| HITL get_event_loop 弃用 | FIXED (now get_running_loop) | FRMW-LOGIC-21 |
| CommandPolicy 占位接口 | CONFIRMED | FRMW-ARCH-25 |
| _CRITICAL_TOOLS 空集合 | CONFIRMED | FRMW-SEC-19, FRMW-LOGIC-06 |
| bus.py 非原子读写 | PARTIALLY FIXED (atomic clear, but read+clear gap) | FRMW-LOGIC-23 |
| inbox 可预测路径 | CONFIRMED | FRMW-SEC-21 |
| pending_writes 类型标注错误 | FIXED | FRMW-LOGIC-25 |
| _apply_changes 复杂变异 | CONFIRMED | FRMW-ARCH-33 |
| runner.py try-except-pass | CONFIRMED | FRMW-SEC-11 |
| _clear_dependency 中间失败 | CONFIRMED | FRMW-LOGIC-26 |
| TaskManager 每次操作全扫描 | CONFIRMED | FRMW-ARCH-34 |

## Verification

- `grep "## memory/" docs/reviews/REVIEW-FRAMEWORK.md` -- PASS
- `grep "## safety/" docs/reviews/REVIEW-FRAMEWORK.md` -- PASS
- `grep "## teams/" docs/reviews/REVIEW-FRAMEWORK.md` -- PASS
- `grep "## tasks/" docs/reviews/REVIEW-FRAMEWORK.md` -- PASS
- Total 100 FRMW-* issues in report (41 new from this plan) -- PASS
- memory/ section: 10 issues (>= 6 required) -- PASS
- safety/ section: 9 issues (>= 4 required) -- PASS
- teams/ section: 9 issues (>= 4 required) -- PASS
- tasks/ section: 13 issues (>= 4 required) -- PASS
- `cd framework && pytest tests/ -x -q` -- 964 passed -- PASS
- No source files modified -- PASS

## Deviations from Plan

None -- plan executed exactly as written.

## Known Stubs

The following module sections are placeholder-only, pending Plan 04:
- `## orchestrator/` -- 1 ruff issue recorded, manual review pending (Plan 04)
- `## hooks/` -- 1 ruff issue recorded, manual review pending (Plan 04)
- `## skills/` -- no ruff issues, manual review pending (Plan 04)
- `## commands/` -- no ruff issues, manual review pending (Plan 04)
- `## prompts/` -- no ruff issues, manual review pending (Plan 04)
- `## a2a/` -- no ruff issues, manual review pending (Plan 04)
- `## transcript/` -- no ruff issues, manual review pending (Plan 04)
- `## viz/` -- 1 ruff issue recorded, manual review pending (Plan 04)

These stubs are intentional per the plan design: Plan 04 will fill in manual review findings for the remaining 8 modules.
