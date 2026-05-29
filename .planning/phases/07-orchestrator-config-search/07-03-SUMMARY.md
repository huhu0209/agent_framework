---
phase: "07"
plan: "03"
subsystem: "tools/search"
tags: ["tavily", "search", "async", "semaphore"]
dependency_graph:
  requires: ["framework/tools/types"]
  provides: ["web_search_real_handler"]
  affects: ["search_tools.py", "test_builtin_tools.py"]
tech_stack:
  added: ["tavily-python>=0.5.0"]
  patterns: ["asyncio.Semaphore concurrency control", "lazy singleton client"]
key_files:
  created:
    - framework/tests/test_search_tools.py
  modified:
    - framework/agent_framework/tools/builtin/search_tools.py
    - framework/pyproject.toml
    - framework/tests/test_builtin_tools.py
decisions:
  - "D-08: Tavily unavailable returns ToolResult(is_error=True), no fallback to mock"
  - "Semaphore(5) chosen as concurrency limit for Tavily rate limiting"
metrics:
  duration: "3m 28s"
  completed: "2026-05-29"
  tasks: 3
  files_modified: 3
  files_created: 1
---

# Phase 7 Plan 03: 真实搜索工具 Summary

Tavily AsyncTavilyClient replaces mock web_search handler with real HTTP calls, asyncio.Semaphore(5) concurrency control, and proper error handling via ToolResult(is_error=True).

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add tavily-python dependency and implement search handler | a7972aa | search_tools.py, pyproject.toml |
| 2 | Write search tool tests with mocked AsyncTavilyClient | c01df5a | test_search_tools.py |
| 3 | Fix builtin test regression and verify zero regression | b45b339 | test_builtin_tools.py |

## Implementation Details

### search_tools.py Rewrite

- Lazy `_get_client()` initializes `AsyncTavilyClient` on first call, reads `TAVILY_API_KEY` from environment
- `reset_client()` sets module-level `_client` to None for test isolation
- `web_search()` acquires `_semaphore` before calling Tavily API, formats results as numbered list with title/url/content
- Error handling: `ValueError` (missing key) and generic `Exception` both return `ToolResult(is_error=True, content="搜索失败：...")`

### Test Coverage (7 tests)

- `test_search_returns_results_on_success` -- happy path with mock results
- `test_search_returns_error_on_missing_api_key` -- env var deleted, reset client, error returned
- `test_search_returns_error_on_network_failure` -- ConnectionError propagated as error ToolResult
- `test_semaphore_limits_concurrency` -- verifies `_semaphore._value == 5`
- `test_semaphore_enforces_max_5_concurrent` -- 10 concurrent calls, max active never exceeds 5
- `test_search_result_format` -- 3 results produce numbered items 1/2/3 with titles and URLs
- `test_search_empty_results` -- empty results array returns "未找到结果" message

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated test_builtin_tools.py regression**
- **Found during:** Task 3 (regression check)
- **Issue:** `TestWebSearch::test_mock_search` failed because it tested the old mock handler which no longer exists
- **Fix:** Rewrote the test to mock `_get_client()` and verify the handler works through the registry integration
- **Files modified:** framework/tests/test_builtin_tools.py
- **Commit:** b45b339

## Test Results

- search_tools tests: 7/7 passed
- Full suite: 644/644 passed (zero regression)

## Self-Check: PASSED

```
FOUND: framework/agent_framework/tools/builtin/search_tools.py
FOUND: framework/pyproject.toml
FOUND: framework/tests/test_search_tools.py
FOUND: framework/tests/test_builtin_tools.py
FOUND: a7972aa feat(07-03): implement Tavily AsyncTavilyClient search handler
FOUND: c01df5a test(07-03): add search_tools tests with mocked AsyncTavilyClient
FOUND: b45b339 fix(07-03): update builtin tools test for real Tavily handler
```
