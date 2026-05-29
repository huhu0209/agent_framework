---
status: issues-found
phase: 08-a2a-protocol
reviewer: gsd-code-reviewer
depth: standard
files_reviewed: 7
started: "2026-05-29T08:50:00Z"
updated: "2026-05-29T08:50:00Z"

findings:
  critical: 2
  warning: 5
  info: 3
  total: 10
---

# Code Review: Phase 08 — A2A Protocol

## Critical

### CR-01: Timing side-channel in API key comparison
**File:** `framework/agent_framework/a2a/server.py:91`
**Category:** Security

`_verify_auth` uses `==` for API key comparison instead of `hmac.compare_digest`. This exposes a timing side-channel attack vector.

**Fix:** Replace `value == expected` with `hmac.compare_digest(value, expected)`.

### CR-02: asyncio.Lock() instantiated outside event loop
**File:** `framework/agent_framework/a2a/server.py:41`
**Category:** Bug

`asyncio.Lock()` in `__init__` emits `DeprecationWarning` on Python 3.10+ and will become `RuntimeError` in future versions. ASGI servers that instantiate the app before entering async context will break.

**Fix:** Create lock lazily on first use, or in an async init method.

## Warnings

### WR-01: Race condition on canceled task overwrite
**File:** `framework/agent_framework/a2a/server.py:168-203`
**Category:** Bug

Canceled task can be overwritten to COMPLETED by background executor because lock is released while agent runs.

### WR-02: Empty message silently accepted
**File:** `framework/agent_framework/a2a/server.py:114`
**Category:** Bug

Missing or empty `message` field silently accepted as empty string and dispatched as a real task.

### WR-03: Fire-and-forget background tasks
**File:** `framework/agent_framework/a2a/server.py:28-41`
**Category:** Quality

`asyncio.create_task` calls have no tracking or graceful shutdown mechanism.

### WR-04: A2AClient missing async context manager
**File:** `framework/agent_framework/a2a/client.py:25-39`
**Category:** Quality

`aclose()` exists but no `__aenter__`/`__aexit__`, so `async with` cannot guarantee cleanup.

### WR-05: Hardcoded Chinese error message
**File:** `framework/agent_framework/a2a/client.py:93`
**Category:** Quality

Error message contains hardcoded Chinese text in an English codebase.

## Info

### IN-01: Timing-dependent test assertions
Tests use `asyncio.sleep(0.1)` assertions that may be flaky on slow CI.

### IN-02: No body size limit
`_read_body` has no size limit. ASGI servers usually cap this, but explicit limit would be safer.

### IN-03: Dual import paths
Minor note about potential dual import paths (no action needed).
