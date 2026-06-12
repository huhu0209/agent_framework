---
phase: 06-agent-types
reviewed: 2026-05-29T00:00:00Z
depth: standard
files_reviewed: 11
files_reviewed_list:
  - framework/agent_framework/agents/__init__.py
  - framework/agent_framework/agents/agent_loop.py
  - framework/agent_framework/agents/base.py
  - framework/agent_framework/agents/plan_and_solve.py
  - framework/agent_framework/agents/reflection.py
  - framework/agent_framework/agents/sub_agent.py
  - framework/agent_framework/tasks/runner.py
  - framework/agent_framework/teams/manager.py
  - framework/tests/test_agent_base.py
  - framework/tests/test_plan_and_solve.py
  - framework/tests/test_reflection.py
findings:
  critical: 2
  warning: 6
  info: 4
  total: 12
status: issues_found
---

# Phase 6: Code Review Report

**Reviewed:** 2026-05-29
**Depth:** standard
**Files Reviewed:** 11
**Status:** issues_found

## Summary

Reviewed 11 source files implementing the Agent type system: ABC base (`Agent`/`AgentEvent`), `AgentLoop` (ReAct), `PlanAndSolveAgent`, `ReflectionAgent`, `SubAgent` tool, `TaskRunner`, `TeamManager`, and their tests. The architecture is sound with a clean ABC contract and consistent event model. However, two critical bugs were found: `TaskRunner` silently drops `max_steps` events leaving tasks in a perpetually "running" state, and `TeamManager._loop` never resets `idle_start` after processing inbox messages causing premature idle-timeout shutdowns. Several warnings cover dead code, incomplete drift detection, and missing module exports.

## Critical Issues

### CR-01: TaskRunner silently drops max_steps events, leaving tasks permanently stuck in RUNNING state

**File:** `framework/agent_framework/tasks/runner.py:64-81`
**Issue:** The `_run_loop` inner function only handles `event.type == "done"` and `event.type == "error"`. When `AgentLoop` emits a `max_steps` event (line 406 of `agent_loop.py`), the `_run_loop` coroutine completes without ever setting `rt.status` or calling `self._task_manager.update()`. The `RuntimeTask` remains in `RUNNING` status, the `finally` block in `_execute` fires a notification with the stale status, and the task entry in `TaskManager` is never updated from `IN_PROGRESS`. Callers polling `TaskManager` will never see this task complete.

**Fix:**
```python
async def _run_loop():
    async for event in loop.run(rt.prompt):
        if event.type == "done":
            rt.status = RuntimeTaskStatus.COMPLETED
            rt.output = event.data.get("content", "")
            await self._task_manager.update(
                rt.task_id,
                status=TaskStatus.COMPLETED,
                description=f"输出: {rt.output[:500]}",
            )
        elif event.type == "error":
            rt.status = RuntimeTaskStatus.ERROR
            rt.error = event.data.get("error", "")
            await self._task_manager.update(
                rt.task_id,
                status=TaskStatus.FAILED,
                description=f"错误: {rt.error[:500]}",
            )
        elif event.type == "max_steps":
            rt.status = RuntimeTaskStatus.TIMEOUT
            rt.error = "达到最大步数限制"
            await self._task_manager.update(
                rt.task_id,
                status=TaskStatus.FAILED,
                description="达到最大步数限制",
            )
```

### CR-02: TeamManager._loop never resets idle_start after processing inbox, causing premature shutdown

**File:** `framework/agent_framework/teams/manager.py:83-112`
**Issue:** `idle_start` is set to `time.monotonic()` on line 83, and reset to `time.monotonic()` on line 101 only when inbox messages are found. However, after processing messages (line 108), execution falls through to line 112 where `self._statuses[config.name]` is set back to `IDLE`. The loop then re-iterates to line 86, reads inbox (now empty since `read_inbox` atomically clears), and on line 94 checks `time.monotonic() - idle_start > config.max_idle_seconds`. The problem is that `idle_start` was set when the teammate first went idle (line 83 on first iteration) or when it finished work (line 101), but if the teammate just completed work and the inbox is immediately empty, `idle_start` was correctly reset. Wait -- re-reading: `idle_start` IS reset on line 101 when inbox is non-empty. The bug is more subtle. On line 108, `loop.run(prompt, resume=True)` is called. The `resume=True` path appends messages to the existing `self._messages` list. But a **new** `AgentLoop` is created on line 75, so `self._messages` starts empty. The first `resume=True` call after creation will hit the `else` branch (line 259 of `agent_loop.py`), initializing messages fresh, which is fine. The real issue: after `_loop` processes inbox messages, the AgentLoop persists across iterations (created once on line 75). With `resume=True`, old conversation history accumulates. But if the loop processes a message and yields `done`, the next inbox read creates a **new** run with `resume=True`, appending to the existing message history. This is intentional for context continuity. The actual shutdown logic appears correct. **Retracting this finding.**

**Revised CR-02:** `TeamManager._loop` reads inbox with `read_inbox` which atomically clears the file. If the teammate's `AgentLoop.run()` takes longer than `config.max_idle_seconds` to complete, the loop re-checks `idle_start` only when inbox is empty. The idle timeout is only checked when inbox is empty (line 92-98). This means: after a teammate finishes processing and goes back to IDLE (line 112), `idle_start` was set when inbox was found non-empty (line 101). The idle timeout clock starts from when work began, not when the teammate returned to idle. This causes premature shutdown -- if processing took 50s and `max_idle_seconds=60`, the teammate only has 10s of idle time before shutdown.

**Fix:**
```python
self._statuses[config.name] = TeammateStatus.IDLE
idle_start = time.monotonic()  # Reset idle timer after work completes
```

Move the `idle_start = time.monotonic()` reset to after the status is set back to IDLE on line 112, so the idle clock starts from when the teammate actually becomes idle, not from when it started working.

## Warnings

### WR-01: Dead code -- _DRIFT_SYSTEM_PROMPT and _llm_check_drift in PlanAndSolveAgent are never called

**File:** `framework/agent_framework/agents/plan_and_solve.py:28-33,169-186`
**Issue:** `_DRIFT_SYSTEM_PROMPT` (line 28) is defined but never used. `_llm_check_drift` (line 169) is defined with a docstring saying "保留供外部使用" but is never called from `run()` or `_detect_drift()`. The `_detect_drift` method (line 154) only calls `_rule_check_drift` and returns `False` if the rule check returns `None`. The LLM-based drift detection is completely dead code. The `import json` on line 171 is also only reachable through this dead method. This dead code adds maintenance burden and confuses readers about the actual drift detection strategy.

**Fix:** Either remove the dead code or integrate `_llm_check_drift` into `_detect_drift` as the fallback when `_rule_check_drift` returns `None`. The method's signature is `async` but `_detect_drift` is synchronous, so integration would require making `_detect_drift` async and `run` would need `await self._detect_drift(...)`.

### WR-02: Missing exports in agents/__init__.py for new Agent types

**File:** `framework/agent_framework/agents/__init__.py:1-11`
**Issue:** `PlanAndSolveAgent` (in `plan_and_solve.py`) and `ReflectionAgent` (in `reflection.py`) are not listed in `__all__` or imported in `__init__.py`. Users must know the internal module structure to import them (`from agent_framework.agents.plan_and_solve import PlanAndSolveAgent`). The `__init__.py` only exports `Agent`, `AgentEvent`, `AgentLoop`, and `LoopEvent`, which was appropriate before these new types were added.

**Fix:**
```python
"""agents -- Agent type system."""

from agent_framework.agents.base import Agent, AgentEvent
from agent_framework.agents.agent_loop import AgentLoop, LoopEvent
from agent_framework.agents.plan_and_solve import PlanAndSolveAgent
from agent_framework.agents.reflection import ReflectionAgent

__all__ = [
    "Agent",
    "AgentEvent",
    "AgentLoop",
    "LoopEvent",
    "PlanAndSolveAgent",
    "ReflectionAgent",
]
```

### WR-03: ReflectionAgent._collect_loop_output silently drops text when multiple text blocks exist in done event

**File:** `framework/agent_framework/agents/reflection.py:186-198`
**Issue:** On line 192, when iterating over content blocks in a "done" event, the code does `output_text = block.get("text", "")` with plain assignment (not `+=`). If multiple text blocks exist, only the last one is kept. This differs from `PlanAndSolveAgent._collect_loop_output` (line 196 of `plan_and_solve.py`) which uses `+=` to concatenate. The inconsistency means `ReflectionAgent` may lose output text when the LLM returns multiple text blocks.

**Fix:** Change line 192 from:
```python
output_text = block.get("text", "")
```
to:
```python
output_text += block.get("text", "")
```

### WR-04: AgentLoop.run mutates self._messages in-place between yield points, risking corruption if consumer modifies events

**File:** `framework/agent_framework/agents/agent_loop.py:243-406`
**Issue:** The `run` method appends to `self._messages` (a mutable list) throughout the generator's lifetime. If `run()` is called with `resume=True` while a previous generator is still being consumed, the two generators share the same `self._messages` list, causing interleaved message corruption. This is a latent risk since `TeamManager._loop` calls `loop.run(prompt, resume=True)` in a loop on the same `AgentLoop` instance, but always awaits full consumption before the next call.

**Fix:** Add a guard in `run()` to prevent concurrent iteration:
```python
if self._running:
    raise RuntimeError("AgentLoop.run() is already in progress")
self._running = True
# ... at the end or on exception:
self._running = False
```

### WR-05: PlanAndSolveAgent passes non-PlanItem plan to AgentLoop.run() in _run_fallback

**File:** `framework/agent_framework/agents/plan_and_solve.py:218-229`
**Issue:** The `_run_fallback` method yields events directly from `AgentLoop.run()` without transformation. `AgentLoop.run()` yields `LoopEvent` objects (subclass of `AgentEvent`), while `PlanAndSolveAgent.run()` is typed as `AsyncGenerator[AgentEvent, None]`. This works because `LoopEvent` is a subclass, but the fallback path yields `LoopEvent` with a `plan` field always set to `None`, which is semantically inconsistent with the plan-and-solve domain. More importantly, the fallback path does not wrap events in `PlanAndSolveAgent`'s own event schema, so consumers expecting `data["text"]` (as produced by the plan execution path on line 97) will instead find `data["content"]` (as produced by `AgentLoop`). This data shape mismatch will cause downstream consumers to fail or produce empty output.

**Fix:** Wrap the AgentLoop events in PlanAndSolveAgent's own event format:
```python
async def _run_fallback(self, user_message: str) -> AsyncGenerator[AgentEvent, None]:
    filtered_router = create_filtered_router(self.router, None)
    loop = AgentLoop(...)
    async for event in loop.run(user_message):
        if event.type == "done":
            content = event.data.get("content", [])
            text = "".join(
                b.get("text", "") for b in content
                if isinstance(b, dict) and b.get("type") == "text"
            )
            yield AgentEvent(type="done", step=event.step, data={"text": text})
        elif event.type == "error":
            yield AgentEvent(type="error", step=event.step, data={"error_message": event.data.get("error", "")})
        else:
            yield event
```

### WR-06: TaskRunner does not cancel running asyncio.Task on shutdown, potential resource leak

**File:** `framework/agent_framework/tasks/runner.py:41,107-109`
**Issue:** The `_running` dict stores `asyncio.Task` objects but there is no `shutdown()` or `cancel_all()` method. If the `TaskRunner` is discarded while tasks are running, the `asyncio.Task` objects continue executing in the background with no way to cancel them. The `_running.pop()` in the `finally` block only removes tasks after they complete. Long-running or hung tasks will never be cleaned up.

**Fix:** Add a shutdown method:
```python
async def shutdown(self) -> None:
    for task_id, atask in list(self._running.items()):
        atask.cancel()
    if self._running:
        await asyncio.gather(*self._running.values(), return_exceptions=True)
    self._running.clear()
```

## Info

### IN-01: Dead import -- `Agent` in tasks/runner.py

**File:** `framework/agent_framework/tasks/runner.py:9`
**Issue:** `Agent` is imported from `agent_framework.agents.base` but never used in the file. The only class used is `AgentLoop`.

**Fix:** Remove `Agent` from the import line:
```python
from agent_framework.agents.agent_loop import AgentLoop
```

### IN-02: Dead import -- `Agent` in teams/manager.py

**File:** `framework/agent_framework/teams/manager.py:10`
**Issue:** `Agent` is imported from `agent_framework.agents.base` but never used in the file.

**Fix:** Remove `Agent` from the import line:
```python
from agent_framework.agents.agent_loop import AgentLoop
```

### IN-03: Dead import -- `Any` in plan_and_solve.py

**File:** `framework/agent_framework/agents/plan_and_solve.py:6`
**Issue:** `Any` is imported from `typing` but never used in the file.

**Fix:** Remove `Any` from the import:
```python
from typing import AsyncGenerator
```

### IN-04: PlanAndSolveAgent replan resets to step i=0 but does not reset global_step

**File:** `framework/agent_framework/agents/plan_and_solve.py:117`
**Issue:** When replanning (line 114-118), `i` is reset to 0 and `step_outputs` is cleared, but `global_step` continues incrementing from its previous value. This means after a replan, step events will have non-sequential step numbers (e.g., 1, 2, 3, 4, 5, ... instead of restarting at 1). This is not a bug since `global_step` represents total steps across all plan iterations, but it could confuse consumers expecting sequential numbering.

**Fix:** Document the semantics of `global_step` in the method docstring, or reset it to 0 on replan if sequential numbering is desired.

---

_Reviewed: 2026-05-29_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
