---
phase: 18-backend
plan: 01
subsystem: api
tags: [agent-loop, tool-use-context, session-manager, fastapi, pydantic]

# Dependency graph
requires: []
provides:
  - "AgentLoop.system_prompt_text @property (framework public API)"
  - "AgentFactory per-session ToolUseContext with working_dir"
  - "SessionManager.persist_messages() async public method"
  - "SessionManager.restore_messages() async public method"
  - "chat.py uses only public APIs (no private attribute access)"
affects: [18-02, 18-03]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Per-session ToolUseContext creation in AgentFactory.create_loop()"
    - "Public async wrappers for sync Redis operations via asyncio.to_thread"

key-files:
  created: []
  modified:
    - "framework/agent_framework/agents/agent_loop.py"
    - "backend/app/services/agent_factory.py"
    - "backend/app/services/session.py"
    - "backend/app/api/v1/chat.py"

key-decisions:
  - "Added storage_dir as AgentFactory constructor parameter (from_settings accepts it) rather than hardcoding relative path"
  - "persist_messages/restore_messages wrap sync Redis ops via asyncio.to_thread internally -- public API is async, internals stay sync until Plan B converts them"
  - "Removed unused asyncio import from chat.py (orphaned by replacing asyncio.to_thread calls)"

patterns-established:
  - "Per-session context: ToolUseContext() created fresh in create_loop(), never shared across sessions"
  - "Public async wrappers: persist_messages/restore_messages expose async API over sync Redis internals"
  - "No private attribute access: backend uses loop.system_prompt_text property, not getattr on _system_prompt_text"

requirements-completed: [BK-LOGIC-03, BK-LOGIC-04, BK-LOGIC-05]

# Metrics
duration: 3min
completed: 2026-06-10
---

# Phase 18 Plan 01: Framework Interface Summary

**Expose AgentLoop.system_prompt_text property, per-session ToolUseContext with working_dir, and public SessionManager persist/restore methods for backend consumption**

## Performance

- **Duration:** 3 min
- **Started:** 2026-06-10T08:22:48Z
- **Completed:** 2026-06-10T08:26:06Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- AgentLoop exposes read-only `system_prompt_text` @property (D-09)
- Each `create_loop()` call creates a fresh `ToolUseContext()` with `working_dir` set (D-08, D-10)
- SessionManager exposes public `persist_messages()` and `restore_messages()` async methods (D-11)
- chat.py eliminates all private attribute access: uses `loop.system_prompt_text` and `await sm.persist_messages()` (BK-LOGIC-05)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add system_prompt_text @property to AgentLoop + wire backend** - `7e253c2` (feat)
2. **Task 2: Per-session ToolUseContext + working_dir + public SessionManager methods** - `5d283cf` (feat)

## Files Created/Modified
- `framework/agent_framework/agents/agent_loop.py` - Added `system_prompt_text` @property exposing `_system_prompt_text` read-only
- `backend/app/services/agent_factory.py` - Moved ToolUseContext creation to `create_loop()`, added `storage_dir` parameter, set `working_dir`
- `backend/app/services/session.py` - Added public `persist_messages()` and `restore_messages()` async methods
- `backend/app/api/v1/chat.py` - Replaced `getattr(loop, '_system_prompt_text', None)` with `loop.system_prompt_text`; replaced `asyncio.to_thread(sm._redis_set_messages, ...)` with `await sm.persist_messages(...)`; removed unused `asyncio` import

## Decisions Made
- Added `storage_dir` as an explicit `AgentFactory` constructor parameter rather than hardcoding a relative path, because `storage_dir` is already computed in `main.py` and should flow through the constructor cleanly
- `persist_messages`/`restore_messages` use `asyncio.to_thread` internally to wrap the synchronous Redis operations -- this gives a clean async public API while keeping the Redis internals unchanged (Plan B handles full async conversion)
- Removed orphaned `asyncio` import from chat.py since all `asyncio.to_thread` calls were replaced

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Removed orphaned asyncio import from chat.py**
- **Found during:** Task 2 (replacing asyncio.to_thread calls)
- **Issue:** After replacing both `asyncio.to_thread(sm._redis_set_messages, ...)` calls with `await sm.persist_messages(...)`, the `import asyncio` became unused
- **Fix:** Removed the `import asyncio` line
- **Files modified:** backend/app/api/v1/chat.py
- **Verification:** grep confirms no asyncio usage remains in the file

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Minor cleanup of orphaned import. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Plans 02 and 03 can now use `AgentLoop.system_prompt_text`, `sm.persist_messages()`, `sm.restore_messages()`, and per-session `ToolUseContext`
- Plan 02 (SessionManager async conversion) will convert the sync internals that `persist_messages`/`restore_messages` currently wrap via `asyncio.to_thread`
- Plan 03 (SSE errors + security) can use the public APIs without touching private methods
- Framework test suite: 1002 tests passing (exceeds 964+ requirement)

---
*Phase: 18-backend*
*Completed: 2026-06-10*

## Self-Check: PASSED
