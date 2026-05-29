---
phase: 05-test-coverage
plan: 01
subsystem: teams
tags: [testing, loop-behavior, async-mock, monkeypatch]
dependency_graph:
  requires: [TeamManager._loop, AgentLoop, MessageBus]
  provides: [TestTeamLoop coverage for _loop]
  affects: [framework/tests/test_teams_manager.py]
tech_stack:
  added: [unittest.mock.patch, unittest.mock.AsyncMock, TrackingDict pattern]
  patterns: [module-namespace patch for AgentLoop, iterator-based time.monotonic mock, TrackingDict for status observation]
key_files:
  created: []
  modified:
    - framework/tests/test_teams_manager.py
decisions:
  - D-01: Pre-seed inbox messages before spawn so _loop reads them on first iteration
  - D-02: Use TrackingDict subclass to observe status transitions (dict __setitem__ is read-only on plain dict)
  - D-03: Use fallback value in fake_monotonic to prevent StopIteration from escaping async generator
metrics:
  duration: 509s
  completed: "2026-05-29"
  tasks: 1
  files: 1
  tests_added: 5
  tests_total: 9
---

# Phase 05 Plan 01: TeamManager _loop Behavior Tests Summary

Deterministic mock-based tests covering all 5 _loop behavior branches: shutdown via inbox, idle timeout, status transitions, notification emission, and inbox prompt formatting.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add TestTeamLoop class with 5 _loop behavior tests | 6389ca3 | framework/tests/test_teams_manager.py |

## Test Details

5 new tests in `TestTeamLoop` class:

1. **test_shutdown_via_inbox** - Pre-seeds `shutdown_request` message, spawns teammate, waits for task completion. Asserts `SHUTDOWN` status.
2. **test_idle_timeout_shutdown** - Mocks `time.monotonic` with escalating values to simulate idle timeout exceeding `max_idle_seconds`. Asserts `SHUTDOWN` status.
3. **test_status_transitions** - Uses `TrackingDict(dict)` subclass to intercept `__setitem__` calls, capturing the full IDLE -> WORKING -> IDLE -> SHUTDOWN cycle.
4. **test_notification_emitted_on_shutdown** - Triggers shutdown via inbox, asserts `TeamNotification(name, status="shutdown")` in `notifications` queue.
5. **test_inbox_processing_formats_prompt** - Uses `CapturingLoop` mock to capture the prompt passed to `AgentLoop.run`. Asserts `<inbox from='lead'>` blocks with both message contents.

## Verification

```
cd framework && python -m pytest tests/test_teams_manager.py -v
# 9 passed in ~1.5s
# All 5 new tests run in < 0.005s (no real-time waits)
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] StopIteration escaping async generator in fake_monotonic**
- **Found during:** Task 1, test_idle_timeout_shutdown
- **Issue:** Iterator-based `fake_monotonic` ran out of values mid-_loop, causing `StopIteration` to escape the async generator and crash the task
- **Fix:** Added try/except fallback returning 999.0 when iterator exhausts
- **Files modified:** framework/tests/test_teams_manager.py
- **Commit:** 6389ca3

**2. [Rule 3 - Blocking] Cannot monkey-patch dict.__setitem__ for status tracking**
- **Found during:** Task 1, test_status_transitions
- **Issue:** Plain `dict.__setitem__` is a read-only C-level slot; assigning a function raises `AttributeError`
- **Fix:** Created `TrackingDict(dict)` subclass that overrides `__setitem__` to record status changes
- **Files modified:** framework/tests/test_teams_manager.py
- **Commit:** 6389ca3

**3. [Rule 3 - Blocking] Timing of inbox messages relative to _loop start**
- **Found during:** Task 1, test_shutdown_via_inbox and test_notification_emitted_on_shutdown
- **Issue:** Sending messages after spawn meant _loop might read inbox before messages arrived (race condition)
- **Fix:** Pre-seed messages before `spawn()` call; since MessageBus is file-based, messages persist until read
- **Files modified:** framework/tests/test_teams_manager.py
- **Commit:** 6389ca3

**4. [Rule 3 - Blocking] Recursive mock_sleep calling real asyncio.sleep**
- **Found during:** Task 1, initial test_inbox_processing_formats_prompt
- **Issue:** `sleep_once` side_effect called `await asyncio.sleep(0)` which resolved to the mocked sleep itself, causing infinite recursion
- **Fix:** Changed `sleep_then_shutdown` to be a simple coroutine that does not call `asyncio.sleep`; it just sends the shutdown message and returns None
- **Files modified:** framework/tests/test_teams_manager.py
- **Commit:** 6389ca3

## Self-Check: PASSED

- framework/tests/test_teams_manager.py: FOUND
- .planning/phases/05-test-coverage/05-01-SUMMARY.md: FOUND
- Commit 6389ca3: FOUND
- Commit 6740012: FOUND
