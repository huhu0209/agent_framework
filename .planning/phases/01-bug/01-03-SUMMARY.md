---
phase: 01-bug
plan: 03
subsystem: llm/transform
tags: [bug-fix, immutability, tdd]
dependency_graph:
  requires: []
  provides: [normalize_messages-immutability-guarantee]
  affects: [framework/agent_framework/llm/transform/_normalize.py]
tech_stack:
  added: []
  patterns: [pydantic-model_copy]
key_files:
  created: []
  modified:
    - framework/agent_framework/llm/transform/_normalize.py
    - framework/tests/test_normalize_messages.py
decisions:
  - Used model_copy() without update kwarg for SystemMessage/ToolMessage since their content fields are immutable strings
metrics:
  duration: 165s
  completed: "2026-05-28"
  tasks: 1
  files: 2
---

# Phase 01 Plan 03: Normalize Messages Immutability Fix Summary

Fixed VERIFICATION.md CR-01: 3 bare `result.append(msg)` calls for SystemMessage/ToolMessage in `_normalize.py` shared object references with callers, violating the immutability contract that UserMessage/AssistantMessage already enforced via `model_copy()`.

## Changes

### framework/agent_framework/llm/transform/_normalize.py
- Line 33: `result.append(msg)` changed to `result.append(msg.model_copy())` -- first message in result (SystemMessage/ToolMessage branch)
- Line 40: `result.append(msg)` changed to `result.append(msg.model_copy())` -- non-merge SystemMessage/ToolMessage path
- Line 52: `result.append(msg)` changed to `result.append(msg.model_copy())` -- else branch SystemMessage/ToolMessage path

### framework/tests/test_normalize_messages.py
- Added `test_system_message_not_shared_reference` to TestImmutability
- Added `test_tool_message_not_shared_reference` to TestImmutability

## TDD Gate Compliance

- RED commit: `62f2616` -- 2 failing immutability tests added
- GREEN commit: `41f1c8f` -- 3 bare appends replaced with model_copy(), all 646 tests pass

## Verification Results

- No bare `result.append(msg)` in _normalize.py (grep confirmed)
- 5 `model_copy()` calls cover all append sites (3 new + 2 existing)
- `pytest tests/test_normalize_messages.py -v` -- 15/15 passed
- `pytest tests/ -v` -- 646/646 passed, no regressions

## Deviations from Plan

None - plan executed exactly as written.

## Commits

| Commit | Type | Message |
|--------|------|---------|
| 62f2616 | test | Add failing immutability tests for SystemMessage/ToolMessage |
| 41f1c8f | fix | Add model_copy() to SystemMessage/ToolMessage in normalize_messages |
