---
phase: 18-backend
plan: 02
subsystem: backend
tags: [aiofiles, atomic-write, async-io, session-manager, ttl-eviction]

# Dependency graph
requires: ["18-01"]
provides:
  - "Fully async SessionManager with aiofiles for all file I/O"
  - "Atomic write pattern (tempfile + os.replace) for non-append file operations"
  - "Active-session-aware TTL eviction that skips sessions with running tasks"
  - "All chat.py callers properly await async SessionManager methods"
affects: [18-03]

# Tech tracking
tech-stack:
  added: ["aiofiles>=24.1.0 (backend/pyproject.toml)"]
  patterns:
    - "aiofiles async file I/O for all SessionManager read/write operations"
    - "Atomic write via tempfile.mkstemp + aiofiles.write + os.replace"
    - "Task liveness check in TTL eviction (s.task is None or s.task.done())"

key-files:
  created: []
  modified:
    - "backend/pyproject.toml"
    - "backend/app/services/session.py"
    - "backend/app/api/v1/chat.py"

key-decisions:
  - "Extracted _cold_read_jsonl as a sync helper for TranscriptReader, wrapped via asyncio.to_thread since TranscriptReader is inherently synchronous"
  - "persist_messages simplified to direct sync Redis call (no to_thread wrapper) since _redis_set_messages is a fast in-memory Redis pipeline operation"
  - "restore_messages simplified to direct await of _get_all_messages since the async chain now handles the to_thread internally via _cold_read_jsonl"

patterns-established:
  - "Atomic writes for all non-append file operations (update_title, delete_session)"
  - "Append operations (_append_history) use aiofiles.open in append mode directly"
  - "TTL eviction respects task liveness: active sessions never evicted"

requirements-completed: [BK-LOGIC-01, BK-LOGIC-02]

# Metrics
duration: 5min
completed: 2026-06-10
---

# Phase 18 Plan 02: Async SessionManager Summary

**Convert SessionManager from synchronous to fully async file I/O with atomic writes, and fix TTL eviction race condition**

## Performance

- **Duration:** 5 min
- **Started:** 2026-06-10T08:30:22Z
- **Completed:** 2026-06-10T08:35:16Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- All SessionManager file I/O uses aiofiles async (zero sync `open()` calls remain)
- Non-append writes use atomic pattern (tempfile + aiofiles + os.replace) matching Phase 16 framework pattern
- Active sessions with running tasks are skipped during TTL eviction (BK-LOGIC-01)
- All 7 chat.py call sites properly await async SessionManager methods
- aiofiles>=24.1.0 declared in backend/pyproject.toml (D-07)
- 1002 framework tests pass (unchanged)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add aiofiles dependency + async SessionManager with atomic writes** - `be8583d` (feat)
2. **Task 2: Fix TTL eviction race + update all chat.py call sites with await** - `cabea2b` (fix)

## Files Created/Modified
- `backend/pyproject.toml` - Added `"aiofiles>=24.1.0"` to dependencies list
- `backend/app/services/session.py` - Converted all file I/O methods to async (create, get_messages, _get_all_messages, _append_history, update_title, list_sessions, delete_session, get_or_restore); added _atomic_write helper; extracted _cold_read_jsonl for sync TranscriptReader; added task liveness check in _evict_expired
- `backend/app/api/v1/chat.py` - Added await to all 7 async SessionManager call sites (create, get_or_restore, update_title x2, get_messages, list_sessions, delete_session)

## Decisions Made
- Extracted `_cold_read_jsonl` as a separate sync method wrapping TranscriptReader, called via `asyncio.to_thread` since TranscriptReader uses synchronous file I/O internally. This keeps the async boundary clean while not rewriting the framework TranscriptReader.
- Simplified `persist_messages` to call `_redis_set_messages` directly (no `asyncio.to_thread` wrapper). The Redis pipeline is a fast in-memory operation that completes in microseconds -- wrapping in to_thread adds unnecessary overhead.
- Simplified `restore_messages` to directly `await self._get_all_messages(session_id)` instead of wrapping in `asyncio.to_thread`, since `_get_all_messages` is now itself async and handles the to_thread wrapping internally where needed.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Plan 03 can now use the fully async SessionManager API
- All SessionManager methods that perform file I/O are async; sync methods (get, remove, cancel_all, replace_task) remain sync as they only touch in-memory state
- Framework test suite: 1002 tests passing (exceeds 964+ requirement)

---
*Phase: 18-backend*
*Completed: 2026-06-10*

## Self-Check: PASSED
