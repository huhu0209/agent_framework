---
phase: 15-framework
reviewed: 2026-06-10T00:00:00Z
depth: standard
files_reviewed: 17
files_reviewed_list:
  - framework/agent_framework/agents/agent_loop.py
  - framework/agent_framework/llm/base.py
  - framework/agent_framework/agents/config.py
  - framework/agent_framework/agents/reflection.py
  - framework/agent_framework/agents/sub_agent.py
  - framework/agent_framework/hooks/manager.py
  - framework/agent_framework/llm/providers/anthropic_provider.py
  - framework/agent_framework/llm/providers/deepseek_provider.py
  - framework/agent_framework/llm/providers/openai_provider.py
  - framework/agent_framework/llm/retry.py
  - framework/agent_framework/llm/streaming.py
  - framework/agent_framework/llm/transform/_deepseek.py
  - framework/agent_framework/llm/transform/_openai.py
  - framework/agent_framework/orchestrator/worker_agent.py
  - framework/agent_framework/tasks/runner.py
  - framework/agent_framework/teams/manager.py
  - framework/agent_framework/tools/context/token_counter.py
findings:
  critical: 1
  warning: 2
  info: 0
  total: 3
status: issues_found
---

# Phase 15: Code Review Report

**Reviewed:** 2026-06-10
**Depth:** standard
**Files Reviewed:** 17
**Status:** issues_found

## Summary

Phase 15 is a dead code cleanup that added `import logging` + `logger` to `agent_loop.py`, added `import httpx` under `TYPE_CHECKING` in `llm/base.py`, removed unused `field` from dataclasses import in `agent_loop.py`, and auto-removed 29 unused imports via `ruff --fix` across 15 other files.

The phase-15 changes themselves are correct: the logging import is used, the `field` removal is safe (only `dataclass` decorator is used), and the `httpx` import under `TYPE_CHECKING` is correct since `from __future__ import annotations` defers annotation evaluation at runtime. Python syntax validation passes on all files.

However, the review discovered one pre-existing critical bug and two warnings in the reviewed codebase.

## Critical Issues

### CR-01: str.format() crashes on LLM output containing braces in reflection.py

**File:** `framework/agent_framework/agents/reflection.py:204`
**Issue:** `_REFLECT_USER_TEMPLATE.format(task=user_message, output=output)` uses `str.format()` to interpolate `task` and `output` into a template string. The template itself contains escaped double braces `{{` for the JSON example at line 81. However, if either `user_message` or `output` contains literal `{` or `}` characters (e.g., JSON blocks, Python code, or any structured data that LLMs frequently produce), `str.format()` will raise a `KeyError` or `IndexError`, crashing the entire reflection flow.

Since `output` comes from an `AgentLoop` run (i.e., LLM-generated text), it will very frequently contain braces. This is a production crash path.

**Fix:**
```python
# In reflection.py, replace .format() with string concatenation or f-string-safe approach
async def _reflect(self, user_message: str, output: str) -> ReflectionVerdict:
    """Assess output quality, return ReflectionVerdict."""
    # Use string concatenation instead of .format() to avoid brace conflicts
    json_example = '{"satisfied": true/false, "scores": {"correctness": N, "completeness": N, "clarity": N}, "critique": "具体改进建议"}'
    user_prompt = (
        "请评估以下任务执行的输出质量。\n\n"
        f"## 原始任务\n{user_message}\n\n"
        f"## 执行输出\n{output}\n\n"
        "## 评估要求\n"
        "从三个维度评分（各 1-5 分）：\n"
        "1. 正确性：输出是否正确回答了任务\n"
        "2. 完整性：输出是否有遗漏\n"
        "3. 清晰度：输出是否清晰明了\n\n"
        "请严格按照以下 JSON 格式回复，不要包含其他内容：\n"
        f"{json_example}"
    )
    response_text = await self._call_llm(_REFLECT_SYSTEM_PROMPT, user_prompt)
    return ReflectionVerdict.from_llm_response(response_text)
```

Alternatively, use `%s` formatting or template strings that do not interpret braces in the substituted values.

## Warnings

### WR-01: asyncio.gather silently swallows flush errors in agent_loop.py

**File:** `framework/agent_framework/agents/agent_loop.py:268-274`
**Issue:** When both flush and compact run in parallel via `asyncio.gather(..., return_exceptions=True)`, the flush result is assigned to `_` and silently discarded. If the flush coroutine raises an exception, it is never logged or acknowledged. While flush is documented as "best-effort," completely silent failure of an episodic memory extraction makes debugging extremely difficult -- the operator has zero visibility into flush failures.

**Fix:**
```python
if flush_coro is not None:
    flush_result, compact_result = await asyncio.gather(
        flush_coro,
        compact(messages, self.compact_adapter, self.model, compact_config, step),
        return_exceptions=True,
    )
    if isinstance(flush_result, Exception):
        logger.debug("Episodic memory flush failed (best-effort): %s", flush_result)
    if isinstance(compact_result, Exception):
        raise compact_result
    result = compact_result
```

### WR-02: TaskRunner._run_loop iterates all events without break on terminal types

**File:** `framework/agent_framework/tasks/runner.py:63-80`
**Issue:** The `_run_loop` inner function uses `async for event in loop.run(rt.prompt)` and checks for `"done"` and `"error"` events, but does not `break` after handling them. While this works correctly today because `AgentLoop.run()` returns after yielding `"done"` or `"error"` (the generator terminates naturally), the behavior is fragile: it relies on an implementation detail of `AgentLoop.run()` rather than the documented contract. If `AgentLoop.run()` ever changes to yield additional events after `"done"`, the task status could be overwritten multiple times.

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
            break  # <-- explicit break on terminal event
        elif event.type == "error":
            rt.status = RuntimeTaskStatus.ERROR
            rt.error = event.data.get("error", "")
            await self._task_manager.update(
                rt.task_id,
                status=TaskStatus.FAILED,
                description=f"错误: {rt.error[:500]}",
            )
            break  # <-- explicit break on terminal event
```

---

_Reviewed: 2026-06-10_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
