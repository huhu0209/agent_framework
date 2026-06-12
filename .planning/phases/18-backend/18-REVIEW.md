---
phase: 18-backend
reviewed: 2026-06-10T12:00:00Z
depth: standard
files_reviewed: 7
files_reviewed_list:
  - backend/app/api/v1/chat.py
  - backend/app/config/__init__.py
  - backend/app/services/agent_factory.py
  - backend/app/services/session.py
  - backend/main.py
  - backend/pyproject.toml
  - framework/agent_framework/agents/agent_loop.py
findings:
  critical: 3
  warning: 7
  info: 2
  total: 12
status: issues_found
---

# Phase 18: Code Review Report

**Reviewed:** 2026-06-10T12:00:00Z
**Depth:** standard
**Files Reviewed:** 7
**Status:** issues_found

## Summary

Reviewed 7 source files spanning the backend FastAPI application (config, routes, session management, agent factory) and the core AgentLoop framework module. Three critical issues were found: a synchronous Redis call that blocks the event loop, an unprotected directory traversal via session IDs, and an error classification bug that mislabels timeouts. Seven warnings cover unvalidated user input, non-atomic file operations, missing thread safety, and other robustness concerns.

## Critical Issues

### CR-01: Synchronous Redis calls block the async event loop

**File:** `backend/app/services/session.py:244-267`
**Issue:** `_redis_set_messages` and `_redis_get_messages` use the synchronous `redis.Redis` client (blocking I/O: `pipeline().execute()`, `exists()`, `zrange()`, `delete()`). These methods are called directly from async contexts -- `_redis_set_messages` is called from `persist_messages` (awaited in `chat.py:146,172`) and `_cold_read_jsonl` (called via `to_thread`, but the Redis call inside it runs synchronously on the thread -- this is fine). However, `_redis_set_messages` is also called directly from `persist_messages` on the main async event loop (session.py:271), meaning every chat message persistence call blocks the entire event loop while waiting for Redis I/O. Similarly, `_redis_get_messages` at session.py:129 is called from the async `_get_all_messages` without `to_thread`.

**Fix:**
```python
# Option A: Use redis.asyncio instead of redis sync client
import redis.asyncio as redis_lib

# Option B: Wrap sync Redis calls in to_thread
async def persist_messages(self, session_id: str, messages: list[dict]) -> None:
    await asyncio.to_thread(self._redis_set_messages, session_id, messages)

async def _get_all_messages(self, session_id: str) -> list[dict] | None:
    # ...
    cached = await asyncio.to_thread(self._redis_get_messages, session_id)
    # ...
```

### CR-02: Directory traversal via session_id in file operations

**File:** `backend/app/services/session.py:135,183,233,286,317`
**Issue:** Multiple methods construct file paths directly from `session_id` without sanitization: `self._storage_dir / f"{session_id}.jsonl"`. While `SESSION_ID_RE` validation exists in the FastAPI route layer (`chat.py:204`), the `SessionManager` itself has no validation. Any caller of `SessionManager` methods (e.g., `get_or_restore`, `delete_session`, `_get_all_messages`) bypasses the route-level regex check. A `session_id` like `../../etc/passwd` (32 hex chars via `aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa00`) would be valid per the regex but cause path traversal. More critically, `_cold_read_jsonl` is called from `_get_all_messages` which receives session_id from Redis cache or JSONL paths -- if the history.jsonl were tampered with, the session_id inside it would never be validated.

**Fix:**
```python
def _resolve_transcript_path(self, session_id: str) -> Path:
    """Resolve session_id to transcript path, preventing traversal."""
    if not SESSION_ID_RE.match(session_id):
        raise ValueError(f"Invalid session_id: {session_id}")
    path = (self._storage_dir / f"{session_id}.jsonl").resolve()
    if not str(path).startswith(str(self._storage_dir.resolve())):
        raise ValueError("Path traversal detected")
    return path
```
Use this method everywhere session_id is interpolated into a path.

### CR-03: asyncio.TimeoutError misclassified as TOOL_ERROR

**File:** `backend/app/api/v1/chat.py:62-63`
**Issue:** The `_classify_error` function maps `asyncio.TimeoutError` to `ErrorCategory.TOOL_ERROR` with the message "工具执行出错，请检查输入。" But `asyncio.TimeoutError` is a generic timeout that can occur during LLM calls (e.g., when `asyncio.wait_for` wraps the adapter call), not just tool execution. The user-facing error message is misleading -- it tells the user their input is wrong when the real issue is an LLM timeout. This is a correctness bug that will confuse users and misdirect debugging.

**Fix:**
```python
def _classify_error(exc: Exception) -> ErrorCategory:
    if isinstance(exc, RateLimitError):
        return ErrorCategory.LLM_RATE_LIMIT
    if isinstance(exc, (ServiceUnavailableError, CircuitOpenError)):
        return ErrorCategory.LLM_TIMEOUT
    if isinstance(exc, LLMAdapterError):
        return ErrorCategory.LLM_TIMEOUT
    if isinstance(exc, asyncio.TimeoutError):
        return ErrorCategory.LLM_TIMEOUT  # not TOOL_ERROR
    return ErrorCategory.UNKNOWN_ERROR
```

## Warnings

### WR-01: `before` query parameter in GET /chat/{id} is unvalidated user input parsed as float

**File:** `backend/app/api/v1/chat.py:209`
**Issue:** The `before` query parameter is a raw string that gets converted to `float` without error handling. If a user passes `before=abc`, the `float(before)` call raises `ValueError` which becomes an unhandled 500 Internal Server Error instead of a proper 400 Bad Request.

**Fix:**
```python
before_ts = None
if before:
    try:
        before_ts = float(before)
    except ValueError:
        raise HTTPException(400, "invalid 'before' parameter: must be a numeric timestamp")
```

### WR-02: `update_title` performs non-atomic read-rewrite on history.jsonl

**File:** `backend/app/services/session.py:192-215`
**Issue:** `update_title` reads the entire history.jsonl, parses all lines, modifies one entry, then overwrites the file via `_atomic_write`. Between the read and the write, another concurrent request could append a new session entry to history.jsonl (via `_append_history`), which would be lost when `update_title` writes back the stale snapshot. This is a classic TOCTOU race.

**Fix:** Either use file-level locking, or serialize all history.jsonl mutations through a single async task/lock:
```python
self._history_lock = asyncio.Lock()

async def update_title(self, session_id: str, title: str) -> bool:
    async with self._history_lock:
        # ... existing logic ...
```
Note: `_append_history` must also acquire the same lock.

### WR-03: `TranscriptWriter` uses synchronous blocking file I/O

**File:** `framework/agent_framework/transcript/writer.py:14`
**Issue:** `TranscriptWriter.__init__` opens a file with synchronous `open()`, and `write()` does synchronous `self._file.write()` + `self._file.flush()`. This writer is called from `TranscriptConsumer.wrap()` which runs inside the async generator `event_stream()` in `chat.py`. Every transcript write blocks the event loop, degrading SSE streaming latency. For long conversations with many tool calls, this accumulates.

**Fix:** Use `aiofiles.open()` for the writer, or run writes via `asyncio.to_thread()` / `asyncio.get_event_loop().run_in_executor()`.

### WR-04: `_atomic_write` mixes sync `os.replace` with async `aiofiles.write`

**File:** `backend/app/services/session.py:47-61`
**Issue:** The method uses `aiofiles.open` for the write (correct for async) but then calls synchronous `os.replace()` and `os.unlink()` which block the event loop. While these syscalls are fast on local filesystems, they are still blocking I/O from the perspective of the event loop. The method name `_atomic_write` suggests it is used for data integrity, so consistency matters.

**Fix:** Wrap `os.replace` and `os.unlink` in `await asyncio.to_thread(...)`:
```python
async def _atomic_write(self, path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix=".tmp", prefix=".sess_")
    try:
        os.close(fd)
        async with aiofiles.open(tmp_path, "w", encoding="utf-8") as f:
            await f.write(content)
        await asyncio.to_thread(os.replace, tmp_path, path)
    except BaseException:
        try:
            await asyncio.to_thread(os.unlink, tmp_path)
        except OSError:
            pass
        raise
```

### WR-05: `_evict_expired` may not evict sessions with active streaming tasks

**File:** `backend/app/services/session.py:342-351`
**Issue:** The eviction check at line 347 requires `s.task is None or s.task.done()`. However, the `task` field on `ChatSession` is never set by any code path in these files. The `create_chat` route in `chat.py` creates a `StreamingResponse` but never assigns its internal task to `session.task`. The `replace_task` method exists but is never called. This means `s.task` is always `None`, so sessions are evicted even while their SSE stream is actively generating output. The TTL eviction will `remove()` the session (closing the transcript writer, clearing from memory) while the `event_stream()` generator still holds a reference and tries to use `session.agent_loop` and `session.messages`.

**Fix:** Either track the streaming task on the session, or verify the current behavior is acceptable and remove the dead `task` field and `replace_task` method to avoid confusion.

### WR-06: `_session_list_cache` has no invalidation on TTL eviction

**File:** `backend/app/services/session.py:240-242`
**Issue:** `_evict_expired` calls `self.remove(sid)` which does not call `_invalidate_list_cache()`. If sessions are evicted by the cleanup loop, the cached session list becomes stale (includes deleted sessions). The cache is only invalidated on explicit `create`, `update_title`, or `delete_session` calls.

**Fix:** Add `self._invalidate_list_cache()` inside `_evict_expired`:
```python
def _evict_expired(self) -> None:
    now = time.time()
    expired = [
        sid for sid, s in self._sessions.items()
        if now - s.created_at > self._ttl
        and (s.task is None or s.task.done())
    ]
    if expired:
        for sid in expired:
            self.remove(sid)
            logger.info("Evicted expired session %s", sid)
        self._invalidate_list_cache()
```

### WR-07: Redis `delete` and `exists` calls in async context are synchronous

**File:** `backend/app/services/session.py:214,262,281`
**Issue:** `update_title` at line 214 calls `self._redis.delete(...)` synchronously from an async method. `delete_session` at line 281 does the same. `_redis_get_messages` at line 262 calls `self._redis.exists(key)` synchronously. All of these block the event loop. This is the same class of issue as CR-01 but in different code paths.

**Fix:** Same as CR-01 -- migrate to `redis.asyncio` or wrap all Redis calls in `asyncio.to_thread`.

## Info

### IN-01: Unused `storage_dir` parameter in `AgentFactory.__init__`

**File:** `backend/app/services/agent_factory.py:20`
**Issue:** The `storage_dir` parameter is accepted but never actually used by `AgentFactory` itself. `from_settings` at line 27 accepts `storage_dir` and passes it to `__init__`, and `create_loop` uses it indirectly via `self._storage_dir` to set `ctx.working_dir`. However, in `main.py:29`, `from_settings` is called without `storage_dir`, so it is `None`. The `storage_dir` used by `SessionManager` is a separate value constructed independently at `main.py:41`. This is not a bug per se, but the `AgentFactory._storage_dir` machinery appears to be dead code in the current configuration.

**Fix:** Either wire the `storage_dir` through `main.py` (pass `storage_dir` to `factory = AgentFactory.from_settings(settings, storage_dir=storage_dir)`) or remove the unused parameter if it serves no purpose.

### IN-02: `AgentLoop.run` does not match `Agent` abstract base class signature

**File:** `framework/agent_framework/agents/agent_loop.py:433-439`
**Issue:** The `Agent` ABC in `base.py` declares `run(self, user_message: str) -> AsyncGenerator[AgentEvent, None]`. But `AgentLoop.run` has signature `run(self, user_message: str, plan=None, *, resume=False)` with extra parameters and yields `LoopEvent` (a subclass). This works at runtime because Python's ABC does not enforce signature compatibility, and `LoopEvent` is a subclass of `AgentEvent`. However, any code using `Agent` as a type hint and calling `run(user_message)` would miss the additional keyword arguments. This is a design inconsistency rather than a runtime bug.

**Fix:** Consider updating the `Agent` ABC to accept `**kwargs` or making the interface more explicit about optional parameters.

---

_Reviewed: 2026-06-10T12:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
