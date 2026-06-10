---
phase: 16-framework
plan: 04
subsystem: [viz, teams, tasks]
tags: [security, websocket, auth, logging, try-except-pass]
dependency_graph:
  requires: []
  provides: [ws-token-auth, logger-debug-replacement]
  affects: [ws_server.py, bus.py, runner.py]
tech_stack:
  added: []
  patterns: [token-auth-handshake, logger-debug-replace-pass]
key_files:
  created: []
  modified:
    - framework/agent_framework/viz/ws_server.py
    - framework/agent_framework/teams/bus.py
    - framework/agent_framework/tasks/runner.py
    - framework/tests/test_ws_server.py
decisions:
  - Token auth at handler level (post-handshake close) rather than process_request hook — simpler, websockets 16 compatible
  - websockets Request.path attribute (not .uri) for URL query parsing in websockets 16
  - Tests use recv() to detect server-initiated close since websockets client context manager does not raise on post-handshake close
metrics:
  duration: 5m
  completed: "2026-06-10"
  tasks: 2
  tests_added: 4
  tests_total: 968
  files_modified: 3
---

# Phase 16 Plan 04: WebSocket Token Auth + Try-Except-Pass Fix Summary

Configurable token authentication for WebSocket handshake; 4 try-except-pass replaced with logger.debug across 3 files.

## Changes

### Task 1: WebSocket Token Authentication (TDD)

**Files:** `framework/agent_framework/viz/ws_server.py`, `framework/tests/test_ws_server.py`

- `serve_ws()` accepts optional `token: str | None = None` keyword argument
- When token is set, `_handler()` validates `?token=xxx` URL query parameter against it
- Auth failure closes connection with code 4001, reason "Unauthorized"
- When token is None, no auth check (backward compatible — existing tests unchanged)
- Startup logs auth status: "(auth enabled)" or "(no auth, development mode)"
- `_handler()` task cleanup try-except-pass replaced with `logger.debug("Task cleanup error", exc_info=True)`
- 4 new tests: valid token connects, invalid token rejected, missing token rejected, no-auth mode accepts all

**TDD gate compliance:**
- RED commit: `5e22296` — failing tests added
- GREEN commit: `c0aa81e` — implementation passes all 11 tests

### Task 2: Fix bus.py + runner.py try-except-pass

**Files:** `framework/agent_framework/teams/bus.py`, `framework/agent_framework/tasks/runner.py`

- `bus.py` line 50: `except Exception: continue` changed to `logger.debug("跳过无法解析的消息行: %s", line[:200])` + continue
- `runner.py` line 93: `except Exception: pass` changed to `logger.debug("任务超时状态更新失败: %s", rt.task_id)`
- `runner.py` line 104: `except Exception: pass` changed to `logger.debug("任务异常状态更新失败: %s", rt.task_id)`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] websockets Request.uri does not exist in websockets 16**
- **Found during:** Task 1 GREEN phase
- **Issue:** Plan referenced `ws.request.uri` but websockets 16 uses `ws.request.path`
- **Fix:** Changed `urlparse(websocket.request.uri)` to `urlparse(websocket.request.path)`
- **Files modified:** ws_server.py
- **Commit:** c0aa81e

**2. [Rule 1 - Bug] Token rejection tests did not raise on connect**
- **Found during:** Task 1 GREEN phase
- **Issue:** websockets client context manager succeeds on handshake; server-initiated close only detected on recv()
- **Fix:** Tests now use `await ws.recv()` inside the connected context to detect the 4001 close
- **Files modified:** test_ws_server.py
- **Commit:** c0aa81e

## Verification Results

- 968 tests passed (964 existing + 4 new)
- `grep "token" framework/agent_framework/viz/ws_server.py` — 6 matches (token auth present)
- `grep "logger.debug" framework/agent_framework/teams/bus.py` — 1 match
- `grep "logger.debug" framework/agent_framework/tasks/runner.py` — 2 matches
- `grep -A1 "except Exception" framework/agent_framework/viz/ws_server.py` — shows logger.debug (not pass)

## Threat Model Compliance

| Threat ID | Mitigation | Status |
|-----------|-----------|--------|
| T-16-06 | Token auth on handshake | Implemented |
| T-16-07 | Token gate prevents unauthorized subscription | Implemented |
| T-16-08 | DoS — localhost-only binding accepted | Acknowledged |

## Self-Check: PASSED

All files verified present, all commits verified in git log.
