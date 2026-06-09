# Backend Code Review Report

**Audit Date:** 2026-06-09
**Scope:** `backend/app/` + `backend/main.py` (13 files, 7 scaffold empty)
**Auditor:** Automated ruff scan + manual review (Phase 13, Plan 01)
**Tools:** ruff 0.15.16 (pyflakes F / flake8-bandit S / McCabe C901 / PLR0913) + manual code inspection

---

## ruff Auto-Scan Baseline

Four ruff scan categories were run against `backend/app/` and `backend/main.py` (excluding tests/):

### F Series: Dead Code (Unused Imports / Variables / Undefined Names)

**1 pyflakes error found:**

| # | Rule | File | Line | Description |
|---|------|------|------|-------------|
| 1 | F401 | `app/models/__init__.py` | 8 | `pydantic.Field` imported but unused |

### BKND-DEAD-01: Unused import `pydantic.Field`

- **ID:** BKND-DEAD-01
- **Description:** `Field` is imported from `pydantic` but never used in the models file. The model fields use direct type annotations and `field_validator` instead.
- **File:** `app/models/__init__.py:8`
- **Impact:** Dead code, minor confusion for readers expecting Field-based validation
- **Fix:** Remove `Field` from the import: `from pydantic import BaseModel, field_validator`
- **Priority:** LOW

### S Series: Security (flake8-bandit)

**0 security warnings found.** All checks passed.

Note: ruff's S-series rules only catch pattern-based issues. Manual security review (below) covers authentication, CORS, input validation, session management, and information disclosure.

### C901: Complexity (McCabe)

**1 high-complexity function found (threshold: 10):**

| # | Complexity | File | Line | Function |
|---|-----------|------|------|----------|
| 1 | 12 | `app/api/v1/chat.py` | 79 | `create_chat` |

### PLR0913: Too Many Arguments

**0 warnings found.** All functions have reasonable parameter counts.

---

## Scaffold File Confirmation

The following 7 files are empty (0 bytes). They contain no implementation code and are skipped for detailed review:

| # | File | Status |
|---|------|--------|
| 1 | `app/__init__.py` | Empty scaffold, skipped |
| 2 | `app/api/__init__.py` | Empty scaffold, skipped |
| 3 | `app/api/v1/__init__.py` | Empty scaffold, skipped |
| 4 | `app/api/v1/agents.py` | Empty scaffold, skipped |
| 5 | `app/api/v1/tools.py` | Empty scaffold, skipped |
| 6 | `app/services/__init__.py` | Empty scaffold, skipped |
| 7 | `app/utils/__init__.py` | Empty scaffold, skipped |

---

## main.py

Manual review of `backend/main.py` (55 lines) — FastAPI application entry point.

### CRITICAL

(none)

### HIGH

(none)

### MEDIUM

#### BKND-SEC-01: CORS allows all methods and headers

- **ID:** BKND-SEC-01
- **Description:** `CORSMiddleware` is configured with `allow_methods=["*"]` and `allow_headers=["*"]`. While `allow_origins` is restricted via `APP_CORS_ORIGINS`, the wildcard methods/headers means any HTTP method (including DELETE, PUT, PATCH from any origin) and any custom header are permitted. In production, this should be tightened to only the methods and headers the API actually uses.
- **File:** `backend/main.py:52-53`
- **Impact:** Overly permissive CORS policy. Allows cross-origin requests with arbitrary headers, which could be exploited for CSRF or data exfiltration if an attacker can control a subdomain within allowed origins.
- **Fix:** Replace with `allow_methods=["GET", "POST", "DELETE", "PATCH"]` and `allow_headers=["Content-Type", "X-Session-Id"]`.
- **Priority:** MEDIUM

#### BKND-SEC-02: Redis connection failure silently swallowed

- **ID:** BKND-SEC-02
- **Description:** The `lifespan` function catches `Exception` broadly and only logs a warning when Redis is unavailable (`rdb = None`). This means the application starts with degraded functionality (no caching) and operators may not notice. The `except Exception` also catches unrelated errors (e.g., `redis_lib.Redis.from_url` could raise `ValueError` for malformed URL, which would be silently ignored).
- **File:** `backend/main.py:32-34`
- **Impact:** Silent degradation. Malformed Redis URL would be masked. Production issues with Redis go unnoticed until users report slow performance.
- **Fix:** Catch `redis_lib.ConnectionError` and `redis_lib.TimeoutError` specifically. For configuration errors (bad URL), let the exception propagate or log at ERROR level.
- **Priority:** MEDIUM

### LOW

(none)

---

## config/

Manual review of `backend/app/config/__init__.py` (21 lines) — application configuration.

### CRITICAL

(none)

### HIGH

(none)

### MEDIUM

#### BKND-SEC-03: API key stored as plain string, not SecretStr

- **ID:** BKND-SEC-03
- **Description:** `llm_api_key` is stored as a plain `str` field in `Settings`. Pydantic provides `SecretStr` to prevent accidental logging or serialization of secrets. While `pydantic-settings` does not log values by default, using `SecretStr` provides defense-in-depth: it prevents the key from appearing in debug output, error messages, or any future logging that might serialize the Settings object.
- **File:** `backend/app/config/__init__.py:9`
- **Impact:** API key could leak through debugging, error reporting, or accidental serialization of the Settings object.
- **Fix:** Change `llm_api_key: str = ""` to `llm_api_key: SecretStr = SecretStr("")` and update consumers to use `settings.llm_api_key.get_secret_value()`. Ensure the validator also uses `get_secret_value()` for the empty check.
- **Priority:** MEDIUM

### LOW

(none)

---

## models/

Manual review of `backend/app/models/__init__.py` (64 lines) — request/response data models.

### CRITICAL

(none)

### HIGH

(none)

### MEDIUM

(none)

### LOW

#### BKND-DEAD-01: Unused import `pydantic.Field`

(already documented in ruff baseline section above)

#### BKND-ARCH-02: `Message` union lacks discriminated validator

- **ID:** BKND-ARCH-02
- **Description:** `Message = UserMessage | AgentMessage | ErrorMessage` is a plain union type. When deserializing from JSON (e.g., loading history from Redis or JSONL), Pydantic v2 will try each variant in order and use the first that validates. This works because each model has a unique `role` Literal, but there is no explicit discriminator configuration. If a future developer adds a new message type without a unique Literal role, silent mis-deserialization could occur.
- **File:** `app/models/__init__.py:43`
- **Impact:** Fragile deserialization contract. Currently works but lacks explicit safety guarantee.
- **Fix:** Add `model_config = ConfigDict(discriminator="role")` or define `Message` as a discriminated union using `Annotated[Union[...], Field(discriminator="role")]`.
- **Priority:** LOW

#### BKND-ARCH-03: `SESSION_ID_RE` allows only hex, no uppercase

- **ID:** BKND-ARCH-03
- **Description:** The regex `r"^[0-9a-f]{32}$"` only matches lowercase hex. `uuid.uuid4().hex` always produces lowercase, so internally generated IDs are fine. However, if an external system ever generates UUIDs with uppercase hex, they would be rejected. This is a minor inconsistency — the regex should either document the lowercase-only expectation or use `(?i)` flag.
- **File:** `app/models/__init__.py:10`
- **Impact:** No current functional impact since backend generates its own UUIDs. Future integration risk if external systems produce uppercase hex IDs.
- **Fix:** Either add a comment explaining the lowercase-only expectation, or use `re.IGNORECASE` flag.
- **Priority:** LOW

---

## services/

Manual review of `backend/app/services/` (2 files: `agent_factory.py` 40 lines + `session.py` 318 lines).

### CRITICAL

(none)

### HIGH

#### BKND-LOGIC-01: TTL eviction race condition with task cancellation

- **ID:** BKND-LOGIC-01
- **Description:** In `_evict_expired()`, `self.remove(sid)` is called which cancels `session.task` if it's still running. However, `_evict_expired` runs synchronously inside `_cleanup_loop` (an async task). If the `session.task` being cancelled is in the middle of appending messages to `session.messages`, there is a race between the task's finally block (which appends the "error" message) and the removal of the session from `self._sessions`. The `remove()` call pops the session, then cancels the task — but the task may still hold a reference to the session object and append messages to it after it's been removed from the dict. Those appended messages would be lost.
- **File:** `backend/app/services/session.py:310-318`
- **Impact:** Messages from in-progress SSE streams can be lost when sessions expire during active use. Users would see an incomplete conversation history if they reconnect.
- **Fix:** Before evicting, check if `session.task` is still running. If so, either skip eviction (extend TTL for active sessions) or await the task cancellation before removing.
- **Priority:** HIGH

#### BKND-LOGIC-02: Non-atomic JSONL read-write in `update_title` and `delete_session`

- **ID:** BKND-LOGIC-02
- **Description:** Both `update_title()` and `delete_session()` read `history.jsonl`, parse all lines, modify in memory, then write back by opening the file in write mode (`"w"`). This is not atomic — if the process crashes or another coroutine interleaves between read and write, data can be lost or corrupted. Additionally, since both methods are synchronous and called from async endpoints, they block the event loop during the file read and write operations.
- **File:** `backend/app/services/session.py:167-191` (`update_title`), `backend/app/services/session.py:245-275` (`delete_session`)
- **Impact:** Data loss on crash during write. Event loop blocking during file I/O (both read and write).
- **Fix:** Use atomic write pattern (write to temp file, then `os.replace`). Wrap file I/O in `asyncio.to_thread()` at the call site (chat.py) to avoid event loop blocking.
- **Priority:** HIGH

#### BKND-SEC-04: `session_id` not validated for existence before Redis/JSONL operations

- **ID:** BKND-SEC-04
- **Description:** While `SESSION_ID_RE` validates the format of `session_id` (32 hex chars) in `ChatRequest`, the `session_id` path parameter in `get_history`, `delete_session`, and `rename_session` endpoints is not validated at all. Any string can be passed as `session_id` in these endpoints. Although the `SESSION_ID_RE` pattern check in the model only applies to `ChatRequest`, the path parameters in other endpoints accept arbitrary strings, which are then used to construct file paths (`self._storage_dir / f"{session_id}.jsonl"`). While the UUID hex format limits path traversal, there is no explicit validation.
- **File:** `backend/app/api/v1/chat.py:154-208` (all endpoints with `{session_id}`)
- **Impact:** No path traversal risk currently (UUIDs are hex-only), but future changes could introduce vulnerabilities if session_id format changes. Inconsistent validation across endpoints.
- **Fix:** Add `session_id: str` path parameter validation using the same `SESSION_ID_RE` pattern. Apply via a FastAPI `Path()` validator or a dependency.
- **Priority:** HIGH

### MEDIUM

#### BKND-ARCH-01: `create_chat` complexity exceeds threshold

(already documented in ruff baseline section above)

#### BKND-ARCH-04: `SessionManager` mixes I/O responsibilities with in-memory state management

- **ID:** BKND-ARCH-04
- **Description:** `SessionManager` (318 lines) handles five distinct concerns: (1) in-memory session lifecycle, (2) TTL-based eviction, (3) JSONL file I/O for history, (4) Redis caching, (5) session listing with caching. The JSONL history management alone (`_append_history`, `update_title`, `delete_session`, `list_sessions`) is ~120 lines of file I/O logic mixed with session management. This makes the class difficult to test in isolation and violates Single Responsibility Principle.
- **File:** `backend/app/services/session.py` (entire class)
- **Impact:** Hard to unit test file I/O without Redis or storage directory. Changes to history format require modifying the session manager. Mocking is complex due to mixed concerns.
- **Fix:** Extract JSONL history management into a separate `HistoryStore` class. Extract Redis caching into a separate `SessionCache` class. `SessionManager` would compose these two and focus on lifecycle management.
- **Priority:** MEDIUM

#### BKND-ARCH-05: `redis_client: Any | None` lacks type safety

- **ID:** BKND-ARCH-05
- **Description:** `SessionManager.__init__` accepts `redis_client: Any | None = None`. This bypasses type checking entirely — any object can be passed. The code calls `.pipeline()`, `.delete()`, `.exists()`, `.zadd()`, `.zrange()`, `.expire()`, `.execute()` on it. If a non-Redis object is passed, these would fail at runtime with confusing errors.
- **File:** `backend/app/services/session.py:35`
- **Impact:** No compile-time safety for Redis client. Bugs from passing wrong type would only surface at runtime.
- **Fix:** Define a `Protocol` with the required methods (`pipeline`, `delete`, `exists`, `zadd`, `zrange`, `expire`, `execute`, `ping`, `close`) and use that as the type annotation. Or use `redis_lib.Redis | None`.
- **Priority:** MEDIUM

#### BKND-LOGIC-03: `_invalidate_list_cache` not thread-safe but called from async context

- **ID:** BKND-LOGIC-03
- **Description:** `_invalidate_list_cache()` sets `self._session_list_cache = None`. It is called from `create()`, `update_title()`, and `delete_session()`. While asyncio is single-threaded, these methods are synchronous and can be called from `asyncio.to_thread()`. If `list_sessions()` is called concurrently (e.g., from a different coroutine while `update_title` is running in a thread), the cache could be in an inconsistent state. Under pure asyncio (no threads), this is safe due to the GIL and cooperative scheduling, but the design is fragile.
- **File:** `backend/app/services/session.py:216-218`
- **Impact:** Potential stale cache reads under high concurrency with `asyncio.to_thread()` usage. Currently low risk since `list_sessions()` is synchronous.
- **Fix:** Document the assumption that all SessionManager methods run on the same event loop. If `asyncio.to_thread` is used more broadly, add explicit synchronization.
- **Priority:** MEDIUM

#### BKND-LOGIC-04: `_get_all_messages` triggers lazy import on every JSONL cold read

- **ID:** BKND-LOGIC-04
- **Description:** Line 118 does `from agent_framework.transcript import TranscriptReader` inside the method body. This is a lazy import to avoid startup cost, but it is executed every time a JSONL cold read occurs. Python caches module imports after the first load, so the performance impact is minimal, but the pattern is unusual and makes the dependency less visible.
- **File:** `backend/app/services/session.py:118` (also line 288 in `get_or_restore`)
- **Impact:** Negligible performance impact. Code readability issue — dependencies are hidden.
- **Fix:** Move to top-level import with a comment explaining why it's acceptable (or add to `TYPE_CHECKING` guard if circular import risk exists).
- **Priority:** MEDIUM

#### BKND-ARCH-06: Shared `ToolUseContext` across all AgentLoop instances

- **ID:** BKND-ARCH-06
- **Description:** `AgentFactory.__init__` creates a single `ToolUseContext()` instance and reuses it for all `AgentLoop` instances via `create_loop()`. The `ToolUseContext` has mutable fields: `message_history: list`, `mcp_clients: dict`, `app_state: dict`, `extra: dict`. If `AgentLoop.run()` modifies `ctx.message_history` (which it does — it appends messages), all concurrent sessions would share the same list, causing cross-session message leakage.
- **File:** `backend/app/services/agent_factory.py:22,39`
- **Impact:** HIGH if AgentLoop mutates the shared context. AgentLoop does use `self.ctx` during execution and appends to `ctx.message_history`. Concurrent sessions would see each other's messages.
- **Fix:** Create a new `ToolUseContext()` instance per `create_loop()` call, or deep-copy the context.
- **Priority:** MEDIUM → could be HIGH depending on framework behavior

#### BKND-ARCH-07: `AgentFactory.create_loop` omits working_dir and other context parameters

- **ID:** BKND-ARCH-07
- **Description:** `create_loop()` creates `AgentLoop` with only `adapter`, `model`, `router`, and `ctx`. It does not set `working_dir` on the `ToolUseContext` (defaults to `"."`), which means file tools would operate relative to the process CWD, not a sandboxed directory. It also does not configure `hook_manager`, `task_runner`, `team_manager`, `skill_dirs`, or `enable_subagent`, which means all advanced framework features are disabled.
- **File:** `backend/app/services/agent_factory.py:34-40`
- **Impact:** `working_dir` defaults to `"."` — file tools could access any file relative to CWD. Missing hook/task/team configuration is expected (not yet needed), but should be documented.
- **Fix:** Set `ctx.working_dir` to an explicit sandbox directory. Document which framework features are intentionally omitted.
- **Priority:** MEDIUM

### LOW

#### BKND-LOGIC-05: `get()` silently refreshes TTL on every access

- **ID:** BKND-LOGIC-05
- **Description:** `SessionManager.get()` unconditionally resets `session.created_at = time.time()`, effectively refreshing the TTL on every access. This means a session that is actively polled (e.g., `GET /chat/{id}` to fetch history) will never expire, even if no new messages are sent. The TTL mechanism only evicts sessions that are never accessed.
- **File:** `backend/app/services/session.py:63-67`
- **Impact:** Sessions with frequent history queries never expire, potentially leaking memory over time. This may be intentional behavior but is not documented.
- **Fix:** Either document the behavior as intentional, or use a separate `last_accessed_at` field for TTL that is independent of `created_at`.
- **Priority:** LOW

#### BKND-ARCH-08: `_append_history` uses synchronous I/O in potentially async context

- **ID:** BKND-ARCH-08
- **Description:** `_append_history()` opens and writes to `history.jsonl` synchronously. It is called from `create()`, which is called from the async `create_chat` endpoint handler. This blocks the event loop during file I/O. The file is small (append-only), so the blocking duration is minimal, but it violates the async design principle.
- **File:** `backend/app/services/session.py:154-165`
- **Impact:** Brief event loop blocking during session creation. Negligible in practice but inconsistent with the `asyncio.to_thread()` pattern used elsewhere in chat.py.
- **Fix:** Either wrap in `asyncio.to_thread()` at the call site, or use aiofiles.
- **Priority:** LOW

---

## api/v1/chat.py

Manual review of `backend/app/api/v1/chat.py` (208 lines) — Chat API routes.

### CRITICAL

(none)

### HIGH

#### BKND-SEC-05: Exception message leaked to client in SSE error event

- **ID:** BKND-SEC-05
- **Description:** In the `event_stream()` generator's except block (line 134), `str(exc)` is sent directly to the client as `_sse("error", {"error": str(exc)})`. If the exception contains sensitive information (e.g., API keys in connection errors, file paths in I/O errors, or internal implementation details), it would be exposed to the client. This is an information disclosure vulnerability.
- **File:** `backend/app/api/v1/chat.py:134`
- **Impact:** Sensitive internal information (API keys, file paths, stack traces) could be leaked to the HTTP client. An attacker could probe for internal details by triggering different exception types.
- **Fix:** Replace `str(exc)` with a generic error message like "An internal error occurred". Log the full exception server-side (which is already done on line 133). Optionally return a correlation ID for debugging.
- **Priority:** HIGH

#### BKND-SEC-06: No authentication or authorization on any API endpoint

- **ID:** BKND-SEC-06
- **Description:** All 5 API endpoints (POST /chat, GET /chat/{id}, GET /sessions, DELETE /sessions/{id}, PATCH /sessions/{id}) have no authentication or authorization checks. Any HTTP client that can reach the server can read, modify, or delete any session. Specifically:
  - `GET /chat/{session_id}` — any user can read any session's messages
  - `DELETE /sessions/{session_id}` — any user can delete any session
  - `PATCH /sessions/{session_id}` — any user can rename any session
  - `POST /chat` with `session_id` — any user can send messages to any session
- **File:** `backend/app/api/v1/chat.py:79,154,180,189,202` (all route handlers)
- **Impact:** Complete lack of access control. In a multi-user deployment, users can access each other's conversations. Session IDs (UUID hex) provide obscurity but not security.
- **Fix:** Add authentication middleware (e.g., API key header, JWT token, session cookie). For authorization, bind sessions to authenticated users and verify ownership on all endpoints.
- **Priority:** HIGH

#### BKND-SEC-04: `session_id` not validated for existence before Redis/JSONL operations

(already documented in services/ section above — the root cause is in endpoints that pass unvalidated session_id to SessionManager)

### MEDIUM

#### BKND-LOGIC-06: `await asyncio.to_thread(sm._redis_set_messages, ...)` accesses private method from another module

- **ID:** BKND-LOGIC-06
- **Description:** `chat.py:102` calls `await asyncio.to_thread(sm._redis_set_messages, session.session_id, session.messages)`, accessing a private method (`_redis_set_messages`) of `SessionManager` from outside the class. This violates encapsulation and creates tight coupling between the API layer and the session manager's internal caching strategy. If the caching implementation changes, this call site must also change.
- **File:** `backend/app/api/v1/chat.py:102` and `backend/app/api/v1/chat.py:128`
- **Impact:** Fragile coupling. Changes to SessionManager's caching require updates to chat.py. Private method access signals incorrect abstraction boundary.
- **Fix:** Add a public method to SessionManager (e.g., `persist_messages(session_id, messages)`) that handles the Redis caching internally, including the `asyncio.to_thread` wrapping if needed.
- **Priority:** MEDIUM

#### BKND-ARCH-01: `create_chat` complexity exceeds threshold

(already documented in ruff baseline section above)

#### BKND-ARCH-09: SSE `_map_to_sse` silently drops `step` events with non-tool-use stop reasons

- **ID:** BKND-ARCH-09
- **Description:** In `_map_to_sse`, when `event_type == "step"` and `stop_reason` is neither `"tool_use"` nor `"end_turn"/"stop_sequence"`, the function returns an empty list (`[]`). This means step events with other stop reasons (e.g., `"max_tokens"`) are silently dropped. The client never receives a notification that the LLM stopped for an unexpected reason.
- **File:** `backend/app/api/v1/chat.py:37-43`
- **Impact:** Client may hang waiting for a response if the LLM stops with an unhandled stop reason. No error feedback to the user.
- **Fix:** Add a fallback case for unknown stop reasons that emits an SSE error event or at least logs a warning.
- **Priority:** MEDIUM

#### BKND-ARCH-10: `getattr(loop, '_system_prompt_text', None)` accesses framework private attribute

- **ID:** BKND-ARCH-10
- **Description:** Line 115 uses `getattr(loop, '_system_prompt_text', None)` to read a private attribute of `AgentLoop` for the `TranscriptConsumer`. This creates a hidden dependency on the framework's internal implementation. If `AgentLoop` renames or removes `_system_prompt_text`, this would silently degrade to `None`.
- **File:** `backend/app/api/v1/chat.py:115`
- **Impact:** Fragile coupling with framework internals. Silent failure if attribute is renamed.
- **Fix:** Add a public property `system_prompt_text` to `AgentLoop`, or pass the system prompt explicitly through the factory/session layer.
- **Priority:** MEDIUM

### LOW

#### BKND-DEAD-02: `UserMessage` and `ErrorMessage` models defined but only used as union types

- **ID:** BKND-DEAD-02
- **Description:** `UserMessage`, `AgentMessage`, and `ErrorMessage` models are defined in `models/__init__.py` and composed into `Message = UserMessage | AgentMessage | ErrorMessage`. However, in the actual code, messages are stored as plain `dict` objects throughout (`session.messages` is `list[dict]`, and all append operations use dict literals). The Pydantic models are only used in the `HistoryResponse` response model. The models serve as documentation but are not used for input validation.
- **File:** `backend/app/models/__init__.py:25-43`
- **Impact:** No functional impact. The models provide type safety for the API response but are bypassed in internal message handling.
- **Fix:** Either use the models for internal message handling (replacing dict literals), or document that they are response-only types.
- **Priority:** LOW

#### BKND-ARCH-11: `before` parameter in `get_history` is `str` but interpreted as float timestamp

- **ID:** BKND-ARCH-11
- **Description:** The `before` query parameter in `get_history` is typed as `str | None` and manually converted to float via `float(before)`. This could raise `ValueError` for non-numeric input, which would result in an unhandled 500 error. FastAPI's type coercion would handle `float` automatically if the parameter were typed as `float | None`.
- **File:** `backend/app/api/v1/chat.py:159,162`
- **Impact:** Unhandled `ValueError` (500 response) if client sends non-numeric `before` parameter.
- **Fix:** Change parameter type to `float | None` and let FastAPI handle validation, or wrap the conversion in a try/except with a 400 response.
- **Priority:** LOW

---

## Data Flow Tracking

### POST /api/v1/chat

```
HTTP Request (POST /api/v1/chat)
  -> FastAPI routing -> chat_router
  -> Pydantic validation: ChatRequest (message: str, session_id: str | None)
    -> session_id validated via SESSION_ID_RE if provided
    -> empty message rejected via `.strip()` check
  -> Request.app.state: session_manager, agent_factory
  -> if session_id provided:
    -> AgentFactory.create_loop() -> new AgentLoop instance
    -> SessionManager.get_or_restore(session_id, agent_loop)
      -> SessionManager.get(session_id) -> check _sessions dict
        -> if found: refresh TTL (created_at = now), return
      -> if not in memory:
        -> SessionManager._get_all_messages(session_id) via storage_dir
          -> TranscriptReader reads {session_id}.jsonl
          -> TranscriptReader.to_messages() -> list of messages
        -> AgentLoop.load_messages(messages) -> restore conversation state
        -> create new TranscriptWriter for append
        -> store in _sessions dict
      -> if transcript not found: return None -> HTTP 404
  -> else (new session):
    -> AgentFactory.create_loop() -> new AgentLoop instance
    -> SessionManager.create(agent_loop)
      -> uuid.uuid4().hex -> session_id
      -> TranscriptWriter(path) for new JSONL file
      -> _append_history(session_id, "新会话")
      -> store in _sessions dict
  -> Append user message dict to session.messages
  -> asyncio.to_thread(sm._redis_set_messages, ...) -> cache to Redis
  -> StreamingResponse with event_stream() generator:
    -> AgentLoop.run(message, resume=is_resume) -> async generator
      -> framework: system prompt assembly, LLM call, tool dispatch loop
    -> TranscriptConsumer.wrap(gen) -> intercepts events for JSONL
    -> For each LoopEvent:
      -> _map_to_sse(event) -> SSE event string(s)
      -> yield to client
    -> On "done" event:
      -> append agent response to session.messages
      -> asyncio.to_thread(sm._redis_set_messages, ...) -> update Redis cache
      -> if first exchange: update_title with first 50 chars
    -> On exception:
      -> yield SSE error with str(exc) [SEC-05: info leak]
      -> append error dict to session.messages
    -> Finally: yield SSE "shutdown"
  -> Response: SSE stream, X-Session-Id header
```

### GET /api/v1/chat/{session_id}

```
HTTP Request (GET /api/v1/chat/{session_id}?limit=N&before=timestamp)
  -> FastAPI routing -> chat_router
  -> Path parameter: session_id (str, NO validation applied)
  -> Query parameters: limit (int | None), before (str | None)
  -> Convert before to float (potential ValueError on invalid input)
  -> Request.app.state.session_manager
  -> SessionManager.get_messages(session_id, limit, before_ts)
    -> SessionManager._get_all_messages(session_id)
      -> Layer 1: check _sessions dict (in-memory)
        -> if found: return session.messages (list[dict])
      -> Layer 2: Redis lookup via _redis_get_messages
        -> check redis.exists(key)
        -> redis.zrange(key, 0, -1) -> deserialize JSON
      -> Layer 3: JSONL cold read from storage_dir
        -> TranscriptReader reads {session_id}.jsonl
        -> Parse events: user -> content, assistant -> blocks, skip tool_result
        -> Backfill Redis via _redis_set_messages
    -> Pagination (if limit provided):
      -> sort by timestamp descending, take limit+1
      -> filter by before_ts if provided
      -> has_more = len > limit
      -> reverse to restore chronological order
      -> next_cursor = earliest timestamp in page
    -> if session not found: return None -> HTTP 404
  -> Build HistoryResponse(session_id, messages, has_more, next_cursor)
  -> Response: JSON HistoryResponse
```

### GET /api/v1/sessions

```
HTTP Request (GET /api/v1/sessions)
  -> FastAPI routing -> chat_router
  -> Request.app.state.session_manager
  -> SessionManager.list_sessions()
    -> Check _session_list_cache (in-memory cache)
      -> if cached: return immediately
    -> Read storage_dir/history.jsonl
      -> Open file, parse each JSON line
      -> For each entry: check transcript file exists
      -> Filter out entries with missing transcript files
    -> Reverse list (most recent first)
    -> Cache result in _session_list_cache
  -> Response: JSON array of session objects [{session_id, title, created_at}]
```

### DELETE /api/v1/sessions/{session_id}

```
HTTP Request (DELETE /api/v1/sessions/{session_id})
  -> FastAPI routing -> chat_router
  -> Path parameter: session_id (str, NO validation applied)
  -> Request.app.state.session_manager
  -> SessionManager.delete_session(session_id)
    -> _invalidate_list_cache() -> clear session list cache
    -> Redis: delete session:{id}:messages and session:{id}:meta
    -> SessionManager.remove(session_id)
      -> pop from _sessions dict
      -> close TranscriptWriter
      -> cancel running asyncio.Task if any
    -> Delete transcript file: {session_id}.jsonl.unlink()
    -> Rewrite history.jsonl (remove matching session_id line)
      -> Non-atomic: read all lines, filter, write back
    -> Return True if transcript was deleted, False otherwise
  -> if not deleted: HTTP 404
  -> Response: {"status": "ok"}
```

### PATCH /api/v1/sessions/{session_id}

```
HTTP Request (PATCH /api/v1/sessions/{session_id})
  -> FastAPI routing -> chat_router
  -> Path parameter: session_id (str, NO validation applied)
  -> Pydantic validation: RenameRequest (title: str)
    -> title validated: non-empty after strip, max 100 chars
  -> Request.app.state.session_manager
  -> SessionManager.update_title(session_id, title)
    -> Read history.jsonl, find matching session_id
    -> Update title field in the entry
    -> Rewrite history.jsonl (non-atomic)
    -> _invalidate_list_cache()
    -> Redis: delete session:{id}:meta
    -> Return True if updated, False if not found
  -> if not updated: HTTP 404
  -> Response: {"status": "ok"}
```

---

## Issue Summary

| Count | Severity | Category |
|-------|----------|----------|
| 0 | CRITICAL | — |
| 5 | HIGH | SEC-04, SEC-05, SEC-06, LOGIC-01, LOGIC-02 |
| 8 | MEDIUM | SEC-01, SEC-02, SEC-03, ARCH-01, ARCH-04, ARCH-05, ARCH-06, ARCH-07 |
| 4 | MEDIUM (continued) | LOGIC-03, LOGIC-04, LOGIC-06, ARCH-09, ARCH-10 |
| 5 | LOW | DEAD-01, ARCH-02, ARCH-03, ARCH-08, ARCH-11, LOGIC-05, DEAD-02 |

### By Category

**Security (SEC):** 6 issues
- SEC-01 (MEDIUM): CORS wildcard methods/headers
- SEC-02 (MEDIUM): Redis connection error silently swallowed
- SEC-03 (MEDIUM): API key stored as plain string
- SEC-04 (HIGH): session_id path parameter not validated
- SEC-05 (HIGH): Exception message leaked to client
- SEC-06 (HIGH): No authentication on any endpoint

**Logic (LOGIC):** 6 issues
- LOGIC-01 (HIGH): TTL eviction race condition with task cancellation
- LOGIC-02 (HIGH): Non-atomic JSONL read-write
- LOGIC-03 (MEDIUM): Cache invalidation under concurrent access
- LOGIC-04 (MEDIUM): Lazy import in method body
- LOGIC-05 (LOW): TTL refresh on every get() access
- LOGIC-06 (MEDIUM): Accessing private method from another module

**Architecture (ARCH):** 11 issues
- ARCH-01 (MEDIUM): create_chat complexity (ruff C901)
- ARCH-02 (LOW): Message union lacks discriminator
- ARCH-03 (LOW): SESSION_ID_RE lowercase-only
- ARCH-04 (MEDIUM): SessionManager mixes I/O with state management
- ARCH-05 (MEDIUM): redis_client typed as Any
- ARCH-06 (MEDIUM): Shared ToolUseContext across AgentLoop instances
- ARCH-07 (MEDIUM): Missing working_dir configuration
- ARCH-08 (LOW): Synchronous I/O in async context
- ARCH-09 (MEDIUM): Silent drop of non-tool-use step events
- ARCH-10 (MEDIUM): Accessing framework private attribute
- ARCH-11 (LOW): before parameter type mismatch

**Dead Code (DEAD):** 2 issues
- DEAD-01 (LOW): Unused Field import (ruff F401)
- DEAD-02 (LOW): Message models not used for internal handling
