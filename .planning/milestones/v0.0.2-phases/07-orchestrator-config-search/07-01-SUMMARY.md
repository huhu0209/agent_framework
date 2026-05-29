---
phase: "07"
plan: "01"
subsystem: orchestrator
tags: [orchestrator-engine, agent-routing, complexity-assessment]
dependency_graph:
  requires: [agents-base, plan-and-solve-agent, agent-loop]
  provides: [orchestrator-engine]
  affects: [orchestrator-engine]
tech_stack:
  added: []
  patterns: [complexity-threshold-routing, agent-factory, local-import-avoid-circular]
key_files:
  created:
    - framework/tests/test_orchestrator_engine.py
  modified:
    - framework/agent_framework/orchestrator/engine.py
    - framework/agent_framework/orchestrator/__init__.py
decisions:
  - Local imports for AgentLoop/PlanAndSolveAgent to avoid circular import with orchestrator/__init__.py
metrics:
  duration: "338s"
  completed: "2026-05-29"
  tasks: 3
  files: 3
---

# Phase 7 Plan 01: OrchestratorEngine Summary

OrchestratorEngine that assesses task complexity via character count heuristic and routes simple tasks to AgentLoop, complex tasks to PlanAndSolveAgent, with a 3-agent creation cap per engine instance.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Implement OrchestratorEngine | d23bf63 | engine.py, __init__.py |
| 2 | Write OrchestratorEngine Tests | 5c5865a | test_orchestrator_engine.py |
| 3 | Verify Zero Regression | (verified) | -- |

## Key Decisions

1. **Local imports for AgentLoop/PlanAndSolveAgent**: Moved imports inside `_create_agent()` to avoid circular import between `orchestrator/__init__.py` -> `engine.py` -> `agents.agent_loop` -> `orchestrator.planner` -> `orchestrator/__init__.py`.

2. **Mock pattern for async generators**: Used `MagicMock` (not `AsyncMock`) for mock agent instances in tests, since `AsyncMock.run()` returns a coroutine but `run()` is an async generator.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Circular import between orchestrator and agents**
- **Found during:** Task 1 verification
- **Issue:** `orchestrator/__init__.py` exports `OrchestratorEngine`, which imports `AgentLoop` from `agents.agent_loop`, which imports `orchestrator.planner`, triggering `orchestrator/__init__.py` -> circular.
- **Fix:** Moved `AgentLoop` and `PlanAndSolveAgent` imports to local scope inside `_create_agent()`, added `TYPE_CHECKING` guard for type hints.
- **Files modified:** engine.py
- **Commit:** d23bf63

**2. [Rule 1 - Bug] Test mock pattern mismatch for async generators**
- **Found during:** Task 2 test execution
- **Issue:** `AsyncMock().run` returns a coroutine, but `run()` is an async generator. `async for` requires `__aiter__`, not a coroutine.
- **Fix:** Used `MagicMock` with explicit `run = MagicMock(return_value=_async_iter([...]))` pattern.
- **Files modified:** test_orchestrator_engine.py
- **Commit:** 5c5865a

## Test Results

- **New tests:** 7 (all passing)
- **Full suite:** 724 passed, 0 failed
- **Regression:** None

## Known Stubs

None.

## Threat Flags

None. No new network endpoints, auth paths, or file access patterns introduced.

## Self-Check: PASSED

- FOUND: framework/agent_framework/orchestrator/engine.py
- FOUND: framework/agent_framework/orchestrator/__init__.py
- FOUND: framework/tests/test_orchestrator_engine.py
- FOUND: .planning/phases/07-orchestrator-config-search/07-01-SUMMARY.md
- FOUND: commit d23bf63
- FOUND: commit 5c5865a
