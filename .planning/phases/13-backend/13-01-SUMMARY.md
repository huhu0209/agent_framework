---
phase: 13-backend
plan: 01
subsystem: backend
tags: [code-review, ruff, security, data-flow]
dependency_graph:
  requires: []
  provides: [REVIEW-BACKEND.md]
  affects: []
tech_stack:
  added: []
  patterns: [ruff F/S/C901/PLR0913, manual code review, data flow tracing]
key_files:
  created:
    - docs/reviews/REVIEW-BACKEND.md
  modified: []
decisions:
  - CORS wildcard methods/headers flagged as SEC-01 MEDIUM (not CRITICAL since origins are restricted)
  - Shared ToolUseContext across AgentLoop instances flagged as ARCH-06 MEDIUM (could be HIGH depending on framework mutation behavior)
  - No authentication on any endpoint flagged as SEC-06 HIGH (acknowledged as expected for current single-user development phase)
  - Exception message leak flagged as SEC-05 HIGH (should be fixed before production deployment)
metrics:
  duration: 420s
  completed: "2026-06-09"
  tasks: 2
  files_reviewed: 6
  issues_found: 25
  lines_reviewed: 706
---

# Phase 13 Plan 01: Backend Code Review Summary

ruff auto-scan + manual file-by-file review + data flow tracing for all backend source files (6 files, 706 lines). Found 25 issues across 4 severity levels and 4 categories (SEC/LOGIC/ARCH/DEAD).

## What Was Done

1. **ruff auto-scan baseline** — Ran 4 scan categories (F401/F811/F841/F821, S, C901, PLR0913) against backend/app/ and backend/main.py. Found 1 dead code issue (unused Field import) and 1 complexity issue (create_chat McCabe 12).

2. **Scaffold file confirmation** — Verified 7 empty files (0 bytes) are scaffold placeholders, skipped detailed review.

3. **Manual file-by-file review** — Reviewed all 6 files with substantial code (main.py 55 lines, config 21 lines, models 64 lines, agent_factory 40 lines, session.py 318 lines, chat.py 208 lines). Checked logic correctness, race conditions, error handling, design patterns, security, framework API usage, and dead code.

4. **Data flow tracking** — Traced complete request-to-response path for all 5 API endpoints (POST /chat, GET /chat/{id}, GET /sessions, DELETE /sessions/{id}, PATCH /sessions/{id}).

## Key Findings

### HIGH Priority (5 issues)

| ID | Category | Description |
|----|----------|-------------|
| BKND-SEC-06 | Security | No authentication on any API endpoint — any client can access any session |
| BKND-SEC-05 | Security | Exception `str(exc)` leaked to client in SSE error event |
| BKND-SEC-04 | Security | `session_id` path parameter not validated (no SESSION_ID_RE check) |
| BKND-LOGIC-01 | Logic | TTL eviction race condition — active task's messages lost on eviction |
| BKND-LOGIC-02 | Logic | Non-atomic JSONL read-write in `update_title` and `delete_session` |

### MEDIUM Priority (12 issues)

| ID | Category | Description |
|----|----------|-------------|
| BKND-SEC-01 | Security | CORS allows wildcard methods and headers |
| BKND-SEC-02 | Security | Redis connection failure silently swallowed |
| BKND-SEC-03 | Security | API key stored as plain string, not SecretStr |
| BKND-ARCH-01 | Architecture | `create_chat` McCabe complexity 12 (threshold 10) |
| BKND-ARCH-04 | Architecture | SessionManager mixes I/O with state management (SRP violation) |
| BKND-ARCH-05 | Architecture | `redis_client: Any` lacks type safety |
| BKND-ARCH-06 | Architecture | Shared ToolUseContext across all AgentLoop instances |
| BKND-ARCH-07 | Architecture | Missing working_dir configuration on ToolUseContext |
| BKND-LOGIC-03 | Logic | Cache invalidation not safe under concurrent access |
| BKND-LOGIC-04 | Logic | Lazy import of TranscriptReader in method body |
| BKND-LOGIC-06 | Logic | Accessing private method `_redis_set_messages` from chat.py |
| BKND-ARCH-09 | Architecture | Silent drop of step events with non-tool-use stop reasons |
| BKND-ARCH-10 | Architecture | Accessing framework private attribute `_system_prompt_text` |

### LOW Priority (6 issues)

| ID | Category | Description |
|----|----------|-------------|
| BKND-DEAD-01 | Dead Code | Unused `pydantic.Field` import |
| BKND-ARCH-02 | Architecture | Message union lacks discriminated validator |
| BKND-ARCH-03 | Architecture | SESSION_ID_RE only matches lowercase hex |
| BKND-ARCH-08 | Architecture | Synchronous I/O in async context (_append_history) |
| BKND-ARCH-11 | Architecture | `before` parameter type mismatch (str vs float) |
| BKND-DEAD-02 | Dead Code | Message Pydantic models not used for internal handling |
| BKND-LOGIC-05 | Logic | TTL refreshed on every get() access, sessions never expire if polled |

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

No stubs found. All reviewed code is functional implementation.

## Threat Flags

No new threat surfaces introduced beyond those documented in the plan's threat model. The review report itself documents security vulnerabilities but does not contain exploits.

## Self-Check

## Self-Check: PASSED

- FOUND: docs/reviews/REVIEW-BACKEND.md
- FOUND: .planning/phases/13-backend/13-01-SUMMARY.md
- FOUND: d8d5f26 (Task 1 commit)
- FOUND: ebda7dd (Task 2 commit)
- Framework tests: 964 passed (no source code modified)
