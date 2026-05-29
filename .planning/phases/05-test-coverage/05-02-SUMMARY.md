---
phase: 05-test-coverage
plan: 02
subsystem: safety
tags: [integration-test, path-safety, security]
dependency_graph:
  requires: [safe_path, AgentLoop, ToolRouter, file_tools]
  provides: [test_safety_integration.py]
  affects: [framework/agent_framework/tools/builtin/file_tools.py]
tech_stack:
  added: [pytest-asyncio]
  patterns: [integration-test-with-real-chain]
key_files:
  created:
    - framework/tests/test_safety_integration.py
  modified:
    - framework/agent_framework/tools/builtin/file_tools.py
decisions:
  - "Wired safe_path() into file_tools read_file/write_file to enforce path sandbox at execution time"
metrics:
  duration: 3m
  completed: "2026-05-29"
  tasks: 1
  files: 2
---

# Phase 5 Plan 2: Safety Boundary Integration Tests Summary

Full-chain integration tests for AgentLoop -> ToolRouter -> safe_path path sandbox, with safe_path wired into file_tools handlers.

## Completed Tasks

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create test_safety_integration.py with 3 full-chain tests | ed93f03 | test_safety_integration.py, file_tools.py |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical Functionality] Wired safe_path into file_tools handlers**
- **Found during:** Task 1 (reading source files before writing tests)
- **Issue:** Plan assumed `read_file` already called `safe_path()`, but `file_tools.py` used raw `Path(ctx.working_dir) / path` without any sandbox check. Path traversal and absolute paths were not blocked.
- **Fix:** Imported `safe_path` and `PathEscapesWorkspace` from `agent_framework.safety.boundary`, wrapped path resolution in both `read_file` and `write_file` to call `safe_path()` and return `ToolResult(content="路径访问被拒绝: 不允许访问工作目录外的文件", is_error=True)` on `PathEscapesWorkspace`.
- **Files modified:** `framework/agent_framework/tools/builtin/file_tools.py`
- **Commit:** ed93f03

## Test Results

```
tests/test_safety_integration.py::test_path_traversal_rejected PASSED
tests/test_safety_integration.py::test_absolute_path_rejected PASSED
tests/test_safety_integration.py::test_normal_file_access_allowed PASSED
3 passed in 0.06s
```

Regression check: all 26 existing `test_agent_loop.py` tests pass.

## Verification

- [x] `test_safety_integration.py` exists with 3 tests
- [x] Path traversal (`../../../etc/passwd`) is rejected through the full chain
- [x] Absolute path (`/etc/passwd`) is rejected through the full chain
- [x] Normal file access within `working_dir` succeeds
- [x] Tests use real `create_builtin_registry()` and `ToolRouter` (no mocks on these)

## Self-Check: PASSED

All files and commits verified present.
