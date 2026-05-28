---
phase: 01-bug
verified: 2026-05-28T14:30:00Z
status: gaps_found
score: 7/8 must-haves verified
overrides_applied: 0
gaps:
  - truth: "normalize_messages 不再原地变异输入消息的 content 字段"
    status: partial
    reason: "UserMessage/AssistantMessage immutability fully fixed with model_copy. SystemMessage/ToolMessage still appended as direct references (shared with input), so a caller mutating returned objects would corrupt input. The function itself no longer mutates, but the returned list shares references for non-User/Assistant types."
    artifacts:
      - path: "framework/agent_framework/llm/transform/_normalize.py"
        issue: "Lines 33, 40, 52 use `result.append(msg)` without model_copy for SystemMessage/ToolMessage"
    missing:
      - "Apply model_copy() to SystemMessage and ToolMessage at lines 33, 40, 52"
      - "Add immutability tests for SystemMessage and ToolMessage input references"
---

# Phase 01: Bug Fix Verification Report

**Phase Goal:** 修复所有已知 Bug，确保代码正确性。
**Verified:** 2026-05-28T14:30:00Z
**Status:** gaps_found
**Re-verification:** No -- initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | AgentLoop 可用 list[Path] 类型参数 skill_dirs 实例化，不再触发 NameError | VERIFIED | `from pathlib import Path` at line 10 of agent_loop.py; test_skill_dirs_accepted_without_name_error passes |
| 2 | HITLManager.create_pending 使用 get_running_loop 而非已废弃的 get_event_loop | VERIFIED | `asyncio.get_running_loop()` at line 47 of hitl.py; no `get_event_loop` in file; test_create_pending_uses_running_loop passes |
| 3 | normalize_messages 不再原地变异输入消息的 content 字段 | PARTIAL | UserMessage/AssistantMessage use model_copy (lines 31, 45, 50). SystemMessage/ToolMessage at lines 33, 40, 52 still use bare `result.append(msg)` -- shared reference with input |
| 4 | 每个修复有对应新增测试验证 (Plan 01) | VERIFIED | 3 new tests across test_agent_loop.py, test_hitl.py, test_normalize_messages.py; all pass |
| 5 | TaskManager._apply_changes 的 pending_writes 类型注解为 list[Task] | VERIFIED | `pending_writes: list[Task] = []` at line 199; no `tuple` reference in file |
| 6 | _clear_dependency 在 lock 内批量收集所有待写变更，最后一次性写入 | VERIFIED | `pending_clears: list[Task] = []` at line 229; collection loop lines 230-237; write loop lines 238-242 |
| 7 | _clear_dependency 写入失败时 log warning 而不回滚 | VERIFIED | `logger.warning` at line 242 wrapping individual `_write` in try/except |
| 8 | 每个修复有对应新增测试验证 (Plan 02) | VERIFIED | 3 new tests in test_task_manager.py (test_apply_changes_pending_writes_type, test_clear_dependency_batch_writes_all, test_clear_dependency_partial_failure_continues); all pass |

**Score:** 7/8 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `framework/agent_framework/agents/agent_loop.py` | Path import fix | VERIFIED | `from pathlib import Path` at line 10 |
| `framework/agent_framework/safety/hitl.py` | Deprecated API fix | VERIFIED | `get_running_loop` at line 47; no `get_event_loop` |
| `framework/agent_framework/llm/transform/_normalize.py` | Immutable merge fix | PARTIAL | model_copy used for UserMessage/AssistantMessage; bare append for SystemMessage/ToolMessage |
| `framework/tests/test_normalize_messages.py` | Immutability tests | VERIFIED | 182 lines (>140 min); 3 TestImmutability tests including 2 new ones |
| `framework/agent_framework/tasks/manager.py` | Type fix + atomicity fix | VERIFIED | `pending_writes: list[Task]` at line 199; `pending_clears` at line 229; `logger.warning` at line 242 |
| `framework/tests/test_task_manager.py` | Atomicity tests | VERIFIED | 227 lines (>160 min); 3 new tests for batch writes and partial failure |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| agent_loop.py | pathlib.Path | import `from pathlib import Path` | WIRED | Line 10; used in type annotation at skill_dirs parameter |
| hitl.py | asyncio.get_running_loop | API call | WIRED | Line 47; creates future on running loop |
| _normalize.py | result list | model_copy replacement | PARTIAL | 3 of 5 append sites use model_copy; lines 33, 40, 52 use bare append for SystemMessage/ToolMessage |
| manager.py | _apply_changes | pending_writes type annotation | WIRED | `list[Task]` at line 199; appends Task objects; iterates correctly |
| manager.py | _clear_dependency | pending_clears batch collection | WIRED | Line 229 collect; line 238 write; line 242 error handling |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| _normalize.py | `result` | Input `messages` list | Yes -- model_copy creates new objects for User/Assistant; bare reference for others | PARTIAL |
| manager.py | `pending_clears` | `self._load_all()` iteration | Yes -- real Task objects loaded from file system | FLOWING |
| manager.py | `pending_writes` | `self.get(dep_id)` | Yes -- real Task objects loaded, modified via dataclasses.replace | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full test suite passes | `.venv/bin/pytest tests/ -v` | 644 passed, 0 failed in 6.33s | PASS |
| Path import test | `.venv/bin/pytest tests/test_agent_loop.py -k skill_dirs -v` | 1 passed | PASS |
| HITL deprecated API test | `.venv/bin/pytest tests/test_hitl.py::TestHITLManager::test_create_pending_uses_running_loop -v` | 1 passed | PASS |
| Immutability tests | `.venv/bin/pytest tests/test_normalize_messages.py::TestImmutability -v` | 3 passed | PASS |
| TaskManager batch write tests | `.venv/bin/pytest tests/test_task_manager.py -k "batch_writes or partial_failure or pending_writes_type" -v` | 3 passed | PASS |
| SystemMessage shared reference | Python: `result[0] is sys_msg` after normalize | True (shared reference) | FAIL |

### Probe Execution

Step 7c: SKIPPED (no probe scripts defined for this phase)

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| R2 | 01-01, 01-02 | Fix all known bugs, each with corresponding test | PARTIAL | 4 of 5 bugs fully fixed; normalize_messages immutability incomplete for SystemMessage/ToolMessage (CR-01) |

**Known bugs from REQUIREMENTS.md R2:**
- agent_loop.py missing Path import: FIXED
- TaskManager._apply_changes type annotation error: FIXED
- HITLManager.create_pending deprecated API: FIXED
- normalize_messages in-place mutation of Pydantic models: PARTIALLY FIXED (UserMessage/AssistantMessage fixed; SystemMessage/ToolMessage still share references)
- _apply_changes non-atomic dependency cleanup: FIXED

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| _normalize.py | 33, 40, 52 | Bare `result.append(msg)` without model_copy | Warning | SystemMessage/ToolMessage returned as shared references; caller mutation would corrupt input |
| test_normalize_messages.py | 140-182 | Missing immutability tests for SystemMessage/ToolMessage | Info | TestImmutability only covers UserMessage/AssistantMessage |

No TBD/FIXME/XXX markers found in any modified files.

### Human Verification Required

None -- all verification is programmatic.

### Gaps Summary

**CR-01 (from code review): Incomplete immutability fix in _normalize.py**

The normalize_messages function correctly uses `model_copy` for UserMessage and AssistantMessage types (lines 31, 45, 50), creating new objects to avoid sharing references with the input. However, SystemMessage and ToolMessage are still appended as direct references (`result.append(msg)`) at lines 33, 40, and 52. This means:

1. `result[0] is sys_msg` evaluates to `True` for SystemMessage inputs
2. `result[-1] is tool_msg` evaluates to `True` for ToolMessage inputs
3. A caller mutating the returned objects (e.g., `result[0].content = "modified"`) would corrupt the original input messages

The fix is straightforward: wrap with `model_copy()` (shallow copy suffices since SystemMessage.content is `str` and ToolMessage has no mutable content fields):
```python
# Line 33: result.append(msg) -> result.append(msg.model_copy())
# Line 40: result.append(msg) -> result.append(msg.model_copy())
# Line 52: result.append(msg) -> result.append(msg.model_copy())
```

Additionally, TestImmutability should be extended with test cases for SystemMessage and ToolMessage input reference isolation.

**Impact assessment:** The original R2 bug was "normalize_messages in-place mutation of Pydantic models." The function itself no longer performs in-place mutation -- that bug is fixed. The remaining issue is defensive: the returned list shares object identity with the input for non-User/Assistant types. This is the same class of issue but in a different location, discovered during code review.

---

_Verified: 2026-05-28T14:30:00Z_
_Verifier: Claude (gsd-verifier)_
