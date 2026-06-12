---
phase: 16-framework
reviewed: 2026-06-10T13:15:00Z
depth: standard
files_reviewed: 32
files_reviewed_list:
  - framework/agent_framework/agents/agent_loop.py
  - framework/agent_framework/memory/flush.py
  - framework/agent_framework/memory/index_manager.py
  - framework/agent_framework/memory/log_manager.py
  - framework/agent_framework/memory/retriever.py
  - framework/agent_framework/memory/search.py
  - framework/agent_framework/memory/semantic_writer.py
  - framework/agent_framework/memory/store.py
  - framework/agent_framework/prompts/assembler.py
  - framework/agent_framework/tasks/runner.py
  - framework/agent_framework/teams/bus.py
  - framework/agent_framework/tools/builtin/memory_tools.py
  - framework/agent_framework/tools/context/result_truncator.py
  - framework/agent_framework/tools/executor.py
  - framework/agent_framework/tools/mcp/config.py
  - framework/agent_framework/tools/mcp/transport.py
  - framework/agent_framework/viz/ws_server.py
  - framework/pyproject.toml
  - framework/tests/test_agent_loop_flush.py
  - framework/tests/test_index_manager.py
  - framework/tests/test_log_manager.py
  - framework/tests/test_mcp_manager.py
  - framework/tests/test_mcp_transport.py
  - framework/tests/test_memory_flush.py
  - framework/tests/test_memory_retriever.py
  - framework/tests/test_memory_search.py
  - framework/tests/test_memory_store.py
  - framework/tests/test_memory_write.py
  - framework/tests/test_prompt_assembler.py
  - framework/tests/test_result_truncator.py
  - framework/tests/test_semantic_writer.py
  - framework/tests/test_ws_server.py
findings:
  critical: 2
  warning: 4
  info: 4
  total: 10
status: issues_found
---

# Phase 16: Code Review Report

**Reviewed:** 2026-06-10T13:15:00Z
**Depth:** standard
**Files Reviewed:** 32
**Status:** issues_found

## Summary

Reviewed 32 source and test files across the agent framework: agent loop, memory subsystem (flush, episodic log, semantic writer, retriever, store, search, index), prompt assembler, task runner, message bus, memory tools, result truncator, tool executor, MCP transport/config, WebSocket server, and their corresponding tests.

Two critical bugs found: an unawaited coroutine that silently drops semantic memory writes, and a missing lock in MCP transport that can corrupt wire messages under concurrent notification+request usage. Several warnings cover missing precondition checks, sync I/O in async context, and a token-auth timing-attack vector.

## Critical Issues

### CR-01: Unawaited coroutine silently drops semantic memory writes

**File:** `framework/agent_framework/agents/agent_loop.py:291`
**Issue:** `SemanticWriter(...).write_batch(drafts)` is called without `await`. `write_batch` is an `async def` method, so calling it returns a coroutine object that is never awaited. The semantic memories extracted from conversation are silently discarded -- the entire semantic extraction cascade is dead code at runtime.
**Fix:**
```python
# Line 291: add await
writer = SemanticWriter(Path(memory_dir))
await writer.write_batch(drafts)
```

### CR-02: send_notification missing lock causes wire message corruption

**File:** `framework/agent_framework/tools/mcp/transport.py:81-82`
**Issue:** `send_notification` calls `self._write(payload)` without acquiring `self._lock`, while `send` holds `self._lock` during its `_write` call. If a notification is sent concurrently with a request, their `_write` calls can interleave writes to `self._process.stdin`, producing corrupted Content-Length frames on the wire. The MCP server would then fail to parse messages or read garbage data.
**Fix:**
```python
async def send_notification(self, payload: dict) -> None:
    async with self._lock:
        await self._write(payload)
```

## Warnings

### WR-01: StdioTransport methods have no precondition check for unconnected state

**File:** `framework/agent_framework/tools/mcp/transport.py:73-82`
**Issue:** `send()`, `send_notification()`, and `_write()` all access `self._process.stdin` without checking if `self._process` is `None`. If `connect()` was never called or `close()` already ran, these methods will raise an unhelpful `AttributeError: 'NoneType' object has no attribute 'stdin'` instead of a clear error message.
**Fix:**
```python
async def send(self, payload: dict) -> dict:
    if self._process is None:
        raise RuntimeError("Transport not connected. Call connect() first.")
    async with self._lock:
        # ... rest unchanged

async def send_notification(self, payload: dict) -> None:
    if self._process is None:
        raise RuntimeError("Transport not connected. Call connect() first.")
    async with self._lock:
        await self._write(payload)
```

### WR-02: MessageBus.send uses synchronous blocking I/O in potentially async context

**File:** `framework/agent_framework/teams/bus.py:31`
**Issue:** `send()` uses `with open(path, "a") as f: f.write(...)` -- synchronous blocking file I/O. The rest of the codebase uses `aiofiles` for all file operations (see `log_manager.py`, `semantic_writer.py`, `retriever.py`, `index_manager.py`). If `send` is called from async code (which is the expected usage in an orchestrator/agent system), it blocks the event loop. `read_inbox` at line 42 similarly uses `path.read_text()` synchronously.
**Fix:** Convert to `aiofiles.open(..., "a")` with `await f.write(...)` for `send`, and `aiofiles.open(..., "r")` for `read_inbox`.

### WR-03: WebSocket token authentication uses timing-unsafe string comparison

**File:** `framework/agent_framework/viz/ws_server.py:42`
**Issue:** `client_token != token` performs a standard Python string comparison, which short-circuits on the first differing byte. An attacker can measure response time to guess the token character-by-character (timing side-channel). While this is a development/localhost WebSocket server, the token auth feature was explicitly added as a security measure and should use constant-time comparison.
**Fix:**
```python
import hmac
# Line 42:
if not hmac.compare_digest(client_token or "", token):
```

### WR-04: flush error in asyncio.gather silently swallowed by return_exceptions

**File:** `framework/agent_framework/agents/agent_loop.py:268-274`
**Issue:** When `flush_coro` is not None, the code uses `asyncio.gather(flush_coro, compact(...), return_exceptions=True)`. Only the `result` (second item = compact) is checked for `isinstance(result, Exception)`. If `flush_coro` raises, the exception is silently captured in the first tuple element and never inspected or logged. The flush failure is completely invisible.
**Fix:**
```python
flush_res, compact_res = await asyncio.gather(
    flush_coro,
    compact(messages, self.compact_adapter, self.model, compact_config, step),
    return_exceptions=True,
)
if isinstance(flush_res, Exception):
    logger.debug("Flush failed (best-effort): %s", flush_res)
if isinstance(compact_res, Exception):
    raise compact_res
```

## Info

### IN-01: Dead code -- _make_long_messages never called

**File:** `framework/tests/test_agent_loop_flush.py:42-47`
**Issue:** The helper function `_make_long_messages` is defined but never used in any test. Additionally, line 47 contains a confusing expression: `TextBlock(text=...) and UserMessage(...)` which always returns the `UserMessage` (because `TextBlock(...)` is truthy), making the `TextBlock` creation dead code within the helper.
**Fix:** Either remove the unused helper or fix its logic if tests are planned that would use it.

### IN-02: MCP config logger uses f-string instead of % formatting

**File:** `framework/agent_framework/tools/mcp/config.py:78`
**Issue:** `logger.warning(f"MCP server '{cfg.name}' 启动失败，跳过: {e}")` uses f-string formatting. The rest of the codebase consistently uses `%`-style formatting for logging (e.g., `logger.warning("MEMORY.md 索引超 %d 行", _MAX_LINES)`). This inconsistency is minor but could cause issues with structured logging handlers.
**Fix:** `logger.warning("MCP server '%s' 启动失败，跳过: %s", cfg.name, e)`

### IN-03: test_memory_flush unused fixture parameter

**File:** `framework/tests/test_memory_flush.py:16,31`
**Issue:** `test_extract_events_with_results` and `test_extract_no_events` both accept `memory_dir: Path` as a parameter but the `FlushExtractor` does not use it -- it only needs an adapter and model. The fixture creates an unused directory.
**Fix:** Remove the `memory_dir` parameter from these two tests, or suppress the unused fixture warning.

### IN-04: result_truncator does not sanitize tool_call_id for filesystem safety

**File:** `framework/agent_framework/tools/context/result_truncator.py:31`
**Issue:** `dump_filename = f"{tool_call_id}.txt"` uses the tool call ID directly as a filename. Currently `tool_call_id` comes from `spec.name` in the executor (line 53), which is a registered tool name. However, MCP tool names come from external servers via `f"mcp__{cfg.name}__{tool_def['name']}"` and could theoretically contain path separators. No sanitization is applied.
**Fix:** Sanitize the filename: `safe_name = re.sub(r'[^\w\-.]', '_', tool_call_id)` before using it as a filename.

---

_Reviewed: 2026-06-10T13:15:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
