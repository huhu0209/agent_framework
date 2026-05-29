---
phase: 08-a2a-protocol
plan: 02
subsystem: a2a
tags: [asgi, http, httpx, asyncio, toolspec, polling, background-execution]

requires: [08-01]

provides:
  - A2AServer pure ASGI app with 4 RESTful routes + background agent execution
  - A2AClient HTTP client with send_task/get_task/cancel_task + send_task_and_wait polling
  - A2AClient.register_as_tool() ToolSpec registration (a2a__{name} pattern)
  - asyncio.Lock concurrent task store protection
  - SecretStr API key management on both server and client

affects: [08-03-a2a-auth]

tech-stack:
  added: []
  patterns: [pure ASGI manual routing, asyncio.create_task background execution, httpx MockTransport testing, ToolSpec remote-agent registration, SecretStr API key wrapping]

key-files:
  created:
    - framework/agent_framework/a2a/server.py
    - framework/agent_framework/a2a/client.py
    - framework/tests/test_a2a_server.py
    - framework/tests/test_a2a_client.py
  modified:
    - framework/agent_framework/a2a/__init__.py

key-decisions:
  - "Pure ASGI manual routing (method + path matching) for 4 endpoints, no HTTP framework dependency"
  - "Agent.run() events consumed fully via async for, done event data['text'] collected as result"
  - "model_copy() for immutable task status updates in server (Pydantic v2 pattern)"
  - "send_task_and_wait uses time.monotonic() deadline + asyncio.sleep polling loop"
  - "ToolSpec handler catches all exceptions and returns ToolResult(is_error=True), never raises"

patterns-established:
  - "ASGI scope/receive/send manual testing via MockSend collector helper"
  - "httpx.MockTransport for client unit tests without real HTTP server"
  - "a2a__{agent_name} naming convention for remote agent tool registration"

requirements-completed: [A2A-03, A2A-04, A2A-05]

duration: 4min
completed: 2026-05-29
---

# Phase 08 Plan 02: A2AServer + A2AClient Implementation Summary

**A2AServer pure ASGI app (4 routes + background Agent.run()) and A2AClient (HTTP calls + send_task_and_wait polling + ToolSpec registration) with 30 tests**

## Performance

- **Duration:** 4 min
- **Started:** 2026-05-29T08:50:35Z
- **Completed:** 2026-05-29T08:54:48Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- A2AServer with 4 ASGI routes: agent-card discovery, task create (201), task get, task cancel
- Background agent execution via asyncio.create_task with PENDING -> RUNNING -> COMPLETED/FAILED lifecycle
- asyncio.Lock protection for concurrent task store access
- A2AClient with 3 low-level methods (send_task, get_task, cancel_task) and send_task_and_wait polling
- send_task_and_wait with time.monotonic() deadline, configurable poll_interval and timeout
- A2AClient.register_as_tool() registering as a2a__{name} ToolSpec in ToolRegistry
- _handle_tool_call returning ToolResult(is_error=True) on failure, never raising
- SecretStr API key wrapping on both server and client sides
- 30 tests (15 server + 15 client) all passing

## Task Commits

1. **Task 1: A2AServer pure ASGI app + task management (TDD)**
   - `1b4670e` (test) - RED: 15 failing tests for A2AServer ASGI routes
   - `b1521d5` (feat) - GREEN: full A2AServer implementation passing 15 tests

2. **Task 2: A2AClient HTTP calls + ToolSpec registration (TDD)**
   - `923871e` (test) - RED: 15 failing tests for A2AClient HTTP + ToolSpec
   - `7ed554c` (feat) - GREEN: full A2AClient implementation passing 15 tests

## Files Created/Modified
- `framework/agent_framework/a2a/server.py` (203 lines) - A2AServer pure ASGI app with 4 routes + background execution
- `framework/agent_framework/a2a/client.py` (138 lines) - A2AClient with HTTP calls + polling + ToolSpec registration
- `framework/agent_framework/a2a/__init__.py` - Updated exports to include A2AServer and A2AClient
- `framework/tests/test_a2a_server.py` (339 lines) - 15 tests for server routes, background execution, error handling
- `framework/tests/test_a2a_client.py` (312 lines) - 15 tests for client HTTP, polling, timeout, ToolSpec

## Decisions Made
- Pure ASGI manual routing with method+path matching avoids HTTP framework dependencies per D-01
- Agent.run() consumed via async for loop, collecting done event data["text"] as result per A1 assumption
- model_copy() used for immutable task status updates (Pydantic v2 convention matching project patterns)
- send_task_and_wait deadline-based timeout with time.monotonic() prevents infinite polling per Pitfall 5
- ToolSpec handler catches all exceptions returning ToolResult(is_error=True) per D-11

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- A2AServer ready for Plan 03 API-key authentication middleware
- A2AClient ready for Plan 03 authenticated requests with X-API-Key header
- Full A2A test suite (30 server/client tests + 26 model tests = 56) passes with no regressions

## Self-Check: PASSED

- All 5 created/modified files verified present
- All 4 commit hashes (1b4670e, b1521d5, 923871e, 7ed554c) verified in git log
- 30/30 A2A server/client tests pass

---
*Phase: 08-a2a-protocol*
*Completed: 2026-05-29*
