---
phase: 12-framework
plan: 01
subsystem: framework
tags: [code-review, ruff, dead-code, security, llm]
dependency_graph:
  requires: []
  provides: [REVIEW-FRAMEWORK.md skeleton with ruff baseline + llm/ review]
  affects: [docs/reviews/REVIEW-FRAMEWORK.md]
tech_stack:
  added: []
  patterns: [ruff static analysis, manual code review]
key_files:
  created:
    - docs/reviews/REVIEW-FRAMEWORK.md
  modified: []
decisions:
  - ruff scan results organized as FRMW-DEAD-* and FRMW-SEC-* issues in module sections
  - _normalize.py mutation bug already fixed in current codebase (uses model_copy)
  - Shallow copy concern documented as MEDIUM rather than HIGH since ContentBlocks are Pydantic models
metrics:
  duration: 13m
  completed: 2026-06-09
  tasks: 2
  files_created: 1
  issues_found: 32
  tests_passing: 964
---

# Phase 12 Plan 01: ruff Baseline + llm/ Module Review Summary

ruff 全量自动扫描（F/S/C901/PLR0913）+ llm/ 模块 10 个源文件逐文件人工审查，产出 REVIEW-FRAMEWORK.md 报告骨架（32 个 ruff 基线 issue + 19 个 llm/ 人工审查 issue）。

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | ruff 自动扫描 + 报告骨架 | 00a66d9 | docs/reviews/REVIEW-FRAMEWORK.md |
| 2 | llm/ 模块逐文件人工审查 | b29e888 | docs/reviews/REVIEW-FRAMEWORK.md |

## Key Results

### ruff Auto-Scan Baseline (Task 1)

- **F series (dead code):** 32 errors (30 unused imports + 2 undefined names)
- **S series (security):** 7 warnings (S311, S324, 3x S110, S112)
- **C901 (complexity):** 10 functions exceeding complexity threshold
- **PLR0913 (parameters):** 7 functions with too many parameters

All 56 ruff findings recorded as FRMW-DEAD-* or FRMW-SEC-* issues in corresponding module sections.

### llm/ Module Manual Review (Task 2)

10 source files reviewed (2,765 lines). 19 issues found across 4 categories:

| Category | Count | Range |
|----------|-------|-------|
| FRMW-SEC-* (security) | 7 | SEC-01 ~ SEC-07 |
| FRMW-LOGIC-* (logic) | 4 | LOGIC-01 ~ LOGIC-04 |
| FRMW-ARCH-* (design) | 5 | ARCH-01 ~ ARCH-05 |
| FRMW-DEAD-* (dead code) | 3 | DEAD-01 ~ DEAD-11 |

**Notable findings:**

- FRMW-SEC-01: `base.py:173` httpx TYPE_CHECKING guard issue (HIGH)
- FRMW-LOGIC-01: `_normalize.py` shallow copy violates immutability (MEDIUM)
- FRMW-LOGIC-03: `resilient.py` stream retry only covers connection phase (MEDIUM)
- FRMW-ARCH-01: OpenAI/DeepSeek providers share ~160 lines duplicate code (LOW)
- FRMW-ARCH-05: `_PROVIDER_MAP` uses fragile string-path dynamic imports (MEDIUM)

**Known CONCERNS.md items verified:**
- `_normalize.py:45` in-place mutation: **ALREADY FIXED** (now uses `model_copy`)
- `base.py:173` httpx reference: **CONFIRMED** (recorded as FRMW-SEC-01)
- Provider API keys: **CONFIRMED FIXED** (using `SecretStr`)

## Verification

- `test -f docs/reviews/REVIEW-FRAMEWORK.md` -- PASS
- Report contains `## ruff` baseline section -- PASS
- All 16 module placeholder sections exist -- PASS
- llm/ section has 19 FRMW-* issues -- PASS
- Issues span all 4 categories (LOGIC/ARCH/SEC/DEAD) -- PASS
- Each issue has ID, description, file:line, impact, fix, priority -- PASS
- `cd framework && pytest tests/ -x -q` -- 964 passed -- PASS
- No source files modified -- PASS

## Deviations from Plan

None -- plan executed exactly as written.

## Known Stubs

The following module sections are placeholder-only, pending Plans 02-04:
- `## tools/` -- 1 ruff issue recorded, manual review pending (Plan 02)
- `## agents/` -- 5 ruff issues recorded, manual review pending (Plan 02)
- `## orchestrator/` -- 1 ruff issue recorded, manual review pending (Plan 02)
- `## teams/` -- 2 ruff issues recorded, manual review pending (Plan 03)
- `## memory/` -- 1 ruff issue recorded, manual review pending (Plan 03)
- `## safety/` -- no ruff issues, manual review pending (Plan 03)
- `## hooks/` -- 1 ruff issue recorded, manual review pending (Plan 04)
- `## skills/` -- no ruff issues, manual review pending (Plan 04)
- `## tasks/` -- 2 ruff issues recorded, manual review pending (Plan 04)
- `## commands/` -- no ruff issues, manual review pending (Plan 04)
- `## prompts/` -- no ruff issues, manual review pending (Plan 04)
- `## a2a/` -- no ruff issues, manual review pending (Plan 04)
- `## transcript/` -- no ruff issues, manual review pending (Plan 04)
- `## viz/` -- 1 ruff issue recorded, manual review pending (Plan 04)

These stubs are intentional per the plan design: Plans 02-04 will fill in manual review findings for the remaining 15 modules.
