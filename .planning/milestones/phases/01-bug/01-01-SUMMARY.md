---
phase: 01-bug
plan: 01
subsystem: framework
tags: [bugfix, pathlib, asyncio, pydantic, immutability]
dependency_graph:
  requires: []
  provides: [R2-complete]
  affects: [agent_loop, hitl, normalize_messages]
tech_stack:
  added: []
  patterns: [model_copy for Pydantic immutability, get_running_loop for async]
key_files:
  created: []
  modified:
    - framework/agent_framework/agents/agent_loop.py
    - framework/agent_framework/safety/hitl.py
    - framework/agent_framework/llm/transform/_normalize.py
    - framework/tests/test_agent_loop.py
    - framework/tests/test_hitl.py
    - framework/tests/test_normalize_messages.py
decisions:
  - Used model_copy(update={...}) per CONVENTIONS.md Pydantic v2 immutability pattern
  - Used unittest.mock.patch to verify get_event_loop is not called after fix
metrics:
  duration: 1627s
  completed: "2026-05-28"
  tasks: 3
  files: 6
---

# Phase 01-bug Plan 01: Bug Fix Summary

3 independent single-file bug fixes with corresponding tests: missing Path import, deprecated asyncio API, Pydantic model in-place mutation.

## Completed Tasks

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Fix agent_loop.py missing Path import | 22498e9 | agent_loop.py, test_agent_loop.py |
| 2 | Fix HITLManager.create_pending deprecated API | 81cb4d2 | hitl.py, test_hitl.py |
| 3 | Fix normalize_messages in-place mutation | d7148c5 | _normalize.py, test_normalize_messages.py |

## Changes Made

### Task 1: Path import fix
- Added `from pathlib import Path` to `framework/agent_framework/agents/agent_loop.py` imports
- Added `test_skill_dirs_accepted_without_name_error` to verify AgentLoop accepts `skill_dirs=[Path("/tmp")]` and creates a SkillRegistry

### Task 2: Deprecated asyncio API fix
- Replaced `asyncio.get_event_loop()` with `asyncio.get_running_loop()` in `HITLManager.create_pending`
- Added `test_create_pending_uses_running_loop` that verifies the deprecated `get_event_loop` is not called and the future resolves correctly

### Task 3: Pydantic immutability fix
- Replaced in-place `last.content = [...]` mutation with `model_copy(update={"content": [...]})` creating a new object
- Added `test_merged_message_is_new_object` and `test_merged_assistant_not_mutated` to `TestImmutability` class

## Deviations from Plan

### Auto-fixed Issues

**1. [Observation] Task 1 RED phase test passed without fix**
- **Found during:** Task 1 TDD RED phase
- **Issue:** The test_skill_dirs_accepted_without_name_error test passed before applying the Path import fix, because `from __future__ import annotations` on line 6 defers all type annotations to strings, preventing NameError at runtime
- **Fix:** Still applied the import as planned -- it is correct practice for type-checking tools, IDE support, and any code that evaluates annotations at runtime
- **Commit:** 22498e9

None otherwise -- plan executed exactly as written.

## Verification Results

- All 641 tests pass (0 failures), up from 630 baseline (11 new tests added)
- `from pathlib import Path` confirmed in agent_loop.py
- `get_running_loop` confirmed in hitl.py (no `get_event_loop` remaining)
- `model_copy` confirmed in _normalize.py (no direct content assignment)

## Self-Check: PASSED

- framework/agent_framework/agents/agent_loop.py: FOUND (contains `from pathlib import Path`)
- framework/agent_framework/safety/hitl.py: FOUND (contains `get_running_loop`)
- framework/agent_framework/llm/transform/_normalize.py: FOUND (contains `model_copy`)
- framework/tests/test_agent_loop.py: FOUND (contains `test_skill_dirs_accepted_without_name_error`)
- framework/tests/test_hitl.py: FOUND (contains `test_create_pending_uses_running_loop`)
- framework/tests/test_normalize_messages.py: FOUND (contains `test_merged_message_is_new_object`)
- Commit 22498e9: FOUND
- Commit 81cb4d2: FOUND
- Commit d7148c5: FOUND
