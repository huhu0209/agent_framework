---
phase: 16-framework
plan: 02
subsystem: tools/mcp
tags: [security, env-whitelist, sensitive-key-filter, tdd]
dependency_graph:
  requires: []
  provides: [FW-SEC-03, FW-SEC-08]
  affects: [transport.py, config.py]
tech_stack:
  added: [frozenset-whitelist-env]
  patterns: [env-whitelist, sensitive-pattern-blocking]
key_files:
  created: []
  modified:
    - framework/agent_framework/tools/mcp/transport.py
    - framework/agent_framework/tools/mcp/config.py
    - framework/tests/test_mcp_transport.py
    - framework/tests/test_mcp_manager.py
decisions:
  - Whitelist approach (not blacklist) for env var inheritance -- whitelist is safer by default
  - File-based env dump in tests to avoid subprocess stdout timing issues
metrics:
  duration: ~3min
  completed: "2026-06-10"
  tasks: 2
  files: 4
  tests_added: 10
  tests_total: 975
---

# Phase 16 Plan 02: MCP Env Whitelist + Sensitive Key Filter Summary

MCP subprocess environment variable inheritance replaced with whitelist mechanism; sensitive key patterns expanded from 7 to 13.

## Changes Made

### Task 1: transport.py whitelist env construction

**Commit:** aba7c27

- Added `_ALLOWED_ENV_KEYS` frozenset constant containing: PATH, HOME, TEMP, TMP, TMPDIR, USER, LANG, SYSTEMROOT
- Replaced `env = {**os.environ, **(self._env or {})}` with whitelist-based construction:
  ```python
  base_env = {k: v for k, v in os.environ.items() if k in _ALLOWED_ENV_KEYS}
  env = {**base_env, **(self._env or {})}
  ```
- Added 4 tests: frozenset type check, essential keys check, whitelist enforcement, config env merge

### Task 2: config.py expanded sensitive key filter + shutdown logger

**Commit:** 4752ec3

- Expanded `_BLOCKED_ENV_PATTERNS` from 7 to 13 patterns, adding: auth, session, cookie, bearer, refresh, jwt
- Changed `McpManager.shutdown()` loop from `.values()` to `.items()` for server name access
- Replaced `except Exception: pass` with `logger.debug("MCP client '%s' close failed", name)`
- Added 7 tests: 6 new pattern rejection tests + shutdown logging test

## Verification Results

- Full test suite: 975 passed in 8.02s
- `_ALLOWED_ENV_KEYS` constant exists in transport.py
- `os.environ` used exactly once (for whitelist filtering only)
- All 6 new blocked patterns present in config.py

## Deviations from Plan

None - plan executed exactly as written.

## TDD Gate Compliance

Both tasks followed TDD RED/GREEN cycle:
- Task 1: RED (ImportError for `_ALLOWED_ENV_KEYS`) -> GREEN (14 tests pass)
- Task 2: RED (4 tests fail for new patterns + logging) -> GREEN (21 tests pass)

## Self-Check: PASSED

- framework/agent_framework/tools/mcp/transport.py: EXISTS
- framework/agent_framework/tools/mcp/config.py: EXISTS
- framework/tests/test_mcp_transport.py: EXISTS
- framework/tests/test_mcp_manager.py: EXISTS
- Commit aba7c27: FOUND
- Commit 4752ec3: FOUND
