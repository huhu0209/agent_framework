---
phase: 01-bug
reviewed: 2026-05-28T11:15:00Z
depth: standard
files_reviewed: 8
files_reviewed_list:
  - framework/agent_framework/agents/agent_loop.py
  - framework/agent_framework/llm/transform/_normalize.py
  - framework/agent_framework/safety/hitl.py
  - framework/agent_framework/tasks/manager.py
  - framework/tests/test_agent_loop.py
  - framework/tests/test_hitl.py
  - framework/tests/test_normalize_messages.py
  - framework/tests/test_task_manager.py
findings:
  critical: 1
  warning: 3
  info: 3
  total: 7
status: issues_found
---

# Phase 01: Code Review Report

**Reviewed:** 2026-05-28T11:15:00Z
**Depth:** standard
**Files Reviewed:** 8
**Status:** issues_found

## Summary

Reviewed 8 files (4 source, 4 test) from Phase 01 bug fixes. All 67 tests pass. The five bug fixes are correct and well-targeted:

1. `from pathlib import Path` import in agent_loop.py -- correct fix, verified by `test_skill_dirs_accepted_without_name_error`
2. `get_event_loop()` -> `get_running_loop()` in hitl.py -- correct, eliminates deprecation
3. In-place Pydantic mutation -> `model_copy(update={...})` in _normalize.py -- correct immutability fix
4. `pending_writes` type annotation `list[tuple[Task]]` -> `list[Task]` in manager.py -- correct
5. `_clear_dependency` batch-collect-then-write with per-item error handling in manager.py -- correct

However, one critical issue remains in `_normalize.py` (incomplete immutability fix), and several test quality issues were found.

## Critical Issues

### CR-01: Incomplete immutability fix in _normalize.py -- SystemMessage and ToolMessage passed by reference

**File:** `framework/agent_framework/llm/transform/_normalize.py:33,40`
**Issue:** The immutability bug fix (replacing direct reference with `model_copy`) was only applied to `UserMessage` and `AssistantMessage` (lines 31, 45, 50). `SystemMessage` and `ToolMessage` are still appended as direct references to the original input objects (lines 33, 40). Since all message types are non-frozen Pydantic `BaseModel` subclasses, a caller that mutates a `SystemMessage.content` or `ToolMessage` attribute in the returned list will silently corrupt the original input messages.

This is the same class of bug that was fixed for `UserMessage`/`AssistantMessage`, but incompletely applied to the remaining message types. The existing immutability test (`TestImmutability`) only covers `UserMessage` merging, so this gap went undetected by tests.
**Fix:**
```python
# Line 33 -- replace:
    result.append(msg)
# with:
    result.append(msg.model_copy())

# Line 40 -- replace:
    result.append(msg)
# with:
    result.append(msg.model_copy())
```

Note: `SystemMessage.content` is `str` (not a list), so `model_copy(update={"content": ...})` is unnecessary -- a shallow `model_copy()` suffices. For `ToolMessage`, there is no mutable content field to deep-copy either.

## Warnings

### WR-01: Fragile conftest import in test_agent_loop.py

**File:** `framework/tests/test_agent_loop.py:8`
**Issue:** `from conftest import MockAdapter` relies on pytest's implicit `conftest.py` discovery adding the test directory to `sys.path`. This fails if the test file is executed directly (e.g., `python tests/test_agent_loop.py`) or imported by a non-pytest runner. The standard practice is to either (a) import via the package path or (b) use pytest fixtures defined in conftest rather than importing from it.
**Fix:** Use a relative import or restructure `MockAdapter` into a shared test utility module:
```python
# Option A: Import via package path (if framework/tests is a package with conftest accessible)
# Option B: Move MockAdapter to a test_helpers.py module
from tests.test_helpers import MockAdapter
```

### WR-02: Transitive import of RiskLevel in test_hitl.py

**File:** `framework/tests/test_hitl.py:13`
**Issue:** `from agent_framework.safety.hitl import ... RiskLevel` works only because `hitl.py` happens to import `RiskLevel` from `permissions.py`. This is a transitive import -- `RiskLevel` is not part of `hitl.py`'s public API. If `hitl.py` removes or refactors its internal import, this test breaks with no obvious cause.
**Fix:**
```python
# Replace:
from agent_framework.safety.hitl import (
    HITLManager,
    PermissionOption,
    PermissionRequest,
    PermissionResponse,
    RiskLevel,  # <- transitive
)
# With:
from agent_framework.safety.hitl import (
    HITLManager,
    PermissionOption,
    PermissionRequest,
    PermissionResponse,
)
from agent_framework.safety.permissions import RiskLevel
```

### WR-03: Silent ignore of non-existent dependency IDs in manager.py

**File:** `framework/agent_framework/tasks/manager.py:204-205`
**Issue:** When `add_blocked_by` or `add_blocks` references a task ID that does not exist, `self.get(dep_id)` returns `None` and the code silently skips the bidirectional link. The requesting task still gets the dependency ID in its `blocked_by` list, but the reverse link is never created. This creates an inconsistent DAG state: task A claims to be blocked by task B, but task B has no record of blocking A. No warning is logged.
**Fix:** Either validate that the dependency exists and raise an error, or at minimum log a warning:
```python
dep_task = self.get(dep_id)
if dep_task is None:
    logger.warning("依赖任务 %s 不存在，跳过反向链接", dep_id)
    continue
if task.id not in dep_task.blocks:
    pending_writes.append(...)
```

## Info

### IN-01: Missing immutability test coverage for SystemMessage and ToolMessage

**File:** `framework/tests/test_normalize_messages.py`
**Issue:** The `TestImmutability` class only tests `UserMessage` and `AssistantMessage` merging. No test verifies that `SystemMessage` or `ToolMessage` objects in the input are not shared by reference with the output. This is why CR-01 was not caught by existing tests.
**Fix:** Add test cases that pass a `SystemMessage` and a `ToolMessage` through `normalize_messages`, then verify that mutating the result does not affect the original input.

### IN-02: HITL test uses indirect assertion pattern for get_running_loop

**File:** `framework/tests/test_hitl.py:113-115`
**Issue:** `test_create_pending_uses_running_loop` patches `get_event_loop` and asserts it was not called. This is an indirect way to verify `get_running_loop` is used. A more direct test would patch `get_running_loop` and assert it IS called. The current approach is valid but could miss a scenario where neither function is called (e.g., if the code was changed to use a pre-created loop).
**Fix:** Consider also patching `asyncio.get_running_loop` and asserting it is called, for more complete coverage.

### IN-03: test_clear_dependency_partial_failure_continues uses fragile mock pattern

**File:** `framework/tests/test_task_manager.py:204-219`
**Issue:** The partial-failure test captures `original_write = mgr._write` and then uses `patch.object(mgr, "_write", side_effect=flaky_write)` where `flaky_write` delegates to `original_write` for non-target IDs. This is a correct pattern but relies on the `_write` method being a regular method (not a classmethod or staticmethod). If `_write` is ever refactored, this test will silently break.
**Fix:** No change needed currently; this is a low-risk note for future maintenance awareness.

---

_Reviewed: 2026-05-28T11:15:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
