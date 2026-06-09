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

## 审查汇总

### Issue 总数

**25 个 issue** 覆盖 6 个有实质代码的文件（约 706 行），7 个 scaffold 空文件已确认跳过。

### 按严重性分布

| 严重性 | 数量 | 占比 | Issue 列表 |
|--------|------|------|-----------|
| CRITICAL | 0 | 0% | — |
| HIGH | 6 | 24% | BKND-SEC-04, BKND-SEC-05, BKND-SEC-06, BKND-LOGIC-01, BKND-LOGIC-02, BKND-ARCH-06 |
| MEDIUM | 12 | 48% | BKND-SEC-01, BKND-SEC-02, BKND-SEC-03, BKND-ARCH-01, BKND-ARCH-04, BKND-ARCH-05, BKND-ARCH-07, BKND-ARCH-09, BKND-ARCH-10, BKND-LOGIC-03, BKND-LOGIC-04, BKND-LOGIC-06 |
| LOW | 7 | 28% | BKND-DEAD-01, BKND-DEAD-02, BKND-ARCH-02, BKND-ARCH-03, BKND-ARCH-08, BKND-ARCH-11, BKND-LOGIC-05 |

### 按文件分布

| 文件 | 行数 | Issue 数 | HIGH | MEDIUM | LOW |
|------|------|----------|------|--------|-----|
| main.py | 55 | 2 | 0 | 2 | 0 |
| config/__init__.py | 21 | 1 | 0 | 1 | 0 |
| models/__init__.py | 64 | 3 | 0 | 0 | 3 |
| services/agent_factory.py | 40 | 2 | 1 | 1 | 0 |
| services/session.py | 318 | 8 | 2 | 5 | 1 |
| api/v1/chat.py | 208 | 7 | 2 | 4 | 1 |
| (ruff 基线跨文件) | — | 2 | 0 | 1 | 1 |

**注：** BKND-DEAD-01 和 BKND-ARCH-01 由 ruff 自动扫描发现，分别在 models/ 和 chat.py 中有交叉引用。BKND-SEC-04 在 services/ 和 chat.py 中均有讨论。

### 按类型分布

| 类型 | 数量 | 说明 |
|------|------|------|
| BKND-SEC-* | 6 | 安全问题（CORS、认证、信息泄露、输入验证） |
| BKND-ARCH-* | 11 | 设计问题（复杂度、SRP 违反、类型安全、耦合） |
| BKND-LOGIC-* | 6 | 逻辑漏洞（竞态条件、非原子操作、缓存一致性） |
| BKND-DEAD-* | 2 | 死代码（未使用 import、未使用模型） |

### BKND-01~05 需求追踪矩阵

| 需求 ID | 需求描述 | 对应 Issue |
|---------|---------|-----------|
| BKND-01 | 死代码检测 | BKND-DEAD-01 ~ BKND-DEAD-02 (2 个), ruff F 基线 1 个 |
| BKND-02 | 逻辑漏洞审查 | BKND-LOGIC-01 ~ BKND-LOGIC-06 (6 个) |
| BKND-03 | 设计问题审查 | BKND-ARCH-01 ~ BKND-ARCH-11 (11 个), ruff C901/PLR0913 基线 2 个 |
| BKND-04 | 安全漏洞审查 | BKND-SEC-01 ~ BKND-SEC-06 (6 个), ruff S 基线 0 个 |
| BKND-05 | 审查报告产出 | 本文件 — 含 ruff 基线 + scaffold 确认 + 5 个文件章节 + 数据流追踪 + 审查汇总 + 跨层问题 |

### CONCERNS.md 覆盖检查

CONCERNS.md 记录的两个 Backend 相关问题：

| CONCERNS.md 条目 | 报告对应 | 状态 |
|-----------------|---------|------|
| "Backend is entirely scaffold (zero implementation)" | Scaffold 文件确认章节 — 7 个空文件已确认，6 个文件有实质代码 | CONCERNS.md 过时（v0.0.3 后已有实现） |
| "No tests for backend" | 审查范围排除 tests/ (Per D-11)，但确认 backend/app/ 已有可测试代码 | 已知缺失，非本 phase 范围 |

### 优先修复建议（TOP 6 HIGH）

以下 6 个 HIGH 级 issue 涉及安全或数据完整性，建议优先修复：

1. **BKND-SEC-06**: 所有 API 端点无认证 — 当前开发阶段可接受，部署前必须添加
2. **BKND-SEC-05**: 异常消息泄露到客户端 — 用通用错误消息替换 `str(exc)`
3. **BKND-SEC-04**: `session_id` 路径参数未验证 — 添加 `SESSION_ID_RE` 校验到所有端点
4. **BKND-LOGIC-01**: TTL 驱逐竞态条件 — 活跃会话驱逐前检查 task 状态
5. **BKND-LOGIC-02**: JSONL 非原子读写 — 改用 temp file + `os.replace` 模式
6. **BKND-ARCH-06**: 共享 ToolUseContext — 每次 `create_loop()` 创建新实例

---

## 跨层问题

以下 Backend 审查发现的问题与 Framework 层（`agent_framework/`）存在关联。每个主题列出 Backend issue 和对应的 Framework issue（来自 `REVIEW-FRAMEWORK.md`），说明跨层关联的具体表现。

参照方向：BKND → FRMW（仅标注 Backend 发现中与 Framework 有关的问题，不反向扩展）。

### 主题 1：API Key 管理策略不一致

Backend 的 `config/__init__.py` 将 API key 存储为普通 `str`，而 Framework 的 provider 层已在内部处理 key 的使用方式。两层之间缺少统一的密钥保护策略。

| 层 | Issue | 描述 | 严重性 |
|----|-------|------|--------|
| Backend | BKND-SEC-03 | `llm_api_key` 存储为 plain `str`，未使用 `SecretStr` | MEDIUM |
| Framework | FRMW-SEC-02~06 (patterns) | 多个 provider 导入未使用符号，但 `_api_key` 以 plain string 存储在 provider 实例中 | MEDIUM (pattern) |

**跨层表现：** Backend 的 `Settings.llm_api_key` (str) 通过 `AgentFactory` 传递给 Framework 的 `create_adapter()`，最终以 `self._api_key` 存储在 provider 实例中。两层都以 plain string 形式持有密钥，无统一的 `SecretStr` 或 secret reference 模式。如果在任何一层意外序列化或日志记录 Settings/Provider 对象，密钥都会泄露。

**修复建议：** Backend 改用 `SecretStr`，Framework 的 `create_adapter` 接受 `SecretStr` 并在内部调用 `get_secret_value()` 传给 provider。

### 主题 2：错误处理策略不匹配

Backend SSE 层直接将异常信息发送给客户端，而 Framework 层使用结构化的 `LoopEvent(type="error")` 进行错误传播。两层之间缺少统一的错误边界。

| 层 | Issue | 描述 | 严重性 |
|----|-------|------|--------|
| Backend | BKND-SEC-05 | SSE error event 中 `str(exc)` 直接泄露给客户端 | HIGH |
| Backend | BKND-SEC-02 | Redis 连接失败被静默吞掉（`except Exception` + warning only） | MEDIUM |
| Framework | FRMW-SEC-09, FRMW-SEC-11, FRMW-SEC-12, FRMW-SEC-17 | 多处 `try-except-pass` 静默吞异常（teams/, tasks/, viz/, tools/） | HIGH/MEDIUM |

**跨层表现：** Framework 的 `AgentLoop.run()` 在异常时 yield `LoopEvent(type="error", ...)` 结构化事件。Backend 的 `event_stream()` generator 捕获 `Exception` 并用 `str(exc)` 构建客户端响应——这会绕过 Framework 的结构化错误处理，直接暴露内部实现细节。同时，Framework 层多处 `try-except-pass` 模式意味着某些异常在 Framework 内部就被静默，永远不会传播到 Backend 层。

**修复建议：** Backend 的 `event_stream()` 应区分已知异常类型（LLM 超时、Tool 执行错误等）和未知异常。对已知异常返回用户友好的错误消息，对未知异常返回通用错误 + correlation ID。Framework 层的 `try-except-pass` 应改为 log + re-raise 或 log + 返回结构化错误事件。

### 主题 3：同步 I/O 在 async 上下文中

Backend 和 Framework 都存在同步文件 I/O 阻塞事件循环的问题，但表现形式不同。

| 层 | Issue | 描述 | 严重性 |
|----|-------|------|--------|
| Backend | BKND-ARCH-08 | `_append_history` 同步写 JSONL，在 async 端点中阻塞事件循环 | LOW |
| Backend | BKND-LOGIC-02 | `update_title` / `delete_session` 同步读写 JSONL（非原子 + 阻塞） | HIGH |
| Framework | FRMW-ARCH-20 | memory/ 全模块使用同步 I/O 阻塞事件循环 | HIGH |
| Framework | FRMW-SEC-13 | `result_truncator.py` 同步文件 I/O | HIGH |
| Framework | FRMW-ARCH-35 | `TaskManager._write` 同步 JSON 写入在 async lock 内 | MEDIUM |

**跨层表现：** Backend 的 `SessionManager` 直接调用同步文件读写（`open()`, `Path.read_text()`, `Path.write_text()`），部分调用已通过 `asyncio.to_thread()` 包装（chat.py 中的 Redis 操作），但 `_append_history` 和 `update_title`/`delete_session` 未包装。Framework 层的 memory 子系统、teams/bus.py、tools/context/result_truncator.py 也有同样的同步 I/O 问题。这形成了一个从 Framework 到 Backend 的连续同步 I/O 链条——Backend 通过 `TranscriptReader`/`TranscriptWriter` 调用 Framework 的 transcript 模块，而 transcript 模块本身也使用同步 I/O（参见 FRMW-ARCH-20 相关的 memory 层问题）。

**修复建议：** 两层统一使用 `asyncio.to_thread()` 包装文件 I/O，或引入 `aiofiles`。Backend 应优先修复 `update_title` 和 `delete_session`（HIGH），Framework 应优先修复 memory 层（FRMW-ARCH-20）。

### 主题 4：AgentLoop 参数传递不完整

Backend 的 `AgentFactory.create_loop()` 仅传递 4 个参数给 `AgentLoop.__init__`，而 Framework 的 `AgentLoop` 支持 19 个参数（参见 FRMW-ARCH-14 PLR0913）。

| 层 | Issue | 描述 | 严重性 |
|----|-------|------|--------|
| Backend | BKND-ARCH-07 | `create_loop` 未设置 `working_dir` 和其他框架特性配置 | MEDIUM |
| Backend | BKND-ARCH-06 | 共享 `ToolUseContext` 实例导致潜在跨会话状态泄漏 | MEDIUM → HIGH |
| Framework | FRMW-ARCH-14 | `AgentLoop.__init__` 19 个参数，构造器过于复杂 | HIGH |
| Framework | FRMW-SEC-18 | `run_subagent` 共享 `ToolUseContext` 导致状态泄漏 | HIGH |

**跨层表现：** Backend 的 `AgentFactory.create_loop()` 只传 `adapter`, `model`, `router`, `ctx` 四个参数。未配置的参数包括：`working_dir`（默认 `"."` — 文件工具可访问任意路径）、`hook_manager`、`task_runner`、`team_manager`、`skill_dirs`、`enable_subagent` 等。同时，所有 `create_loop()` 调用共享同一个 `ToolUseContext` 实例（BKND-ARCH-06），Framework 层的 `run_subagent` 也有同样的共享上下文问题（FRMW-SEC-18）。

`working_dir` 默认值 `"."` 尤其值得关注：Framework 的 `file_tools.py` 虽然有 `safe_path()` 函数，但 CONCERNS.md 和 Phase 12 审查均确认 `file_tools.py` 未调用 `safe_path()`（参见 FRMW-SEC-14 相关讨论）。这意味着 Backend 未设置 `working_dir` + Framework 未调用 `safe_path()` = 文件工具可访问进程 CWD 下的任意文件。

**修复建议：** Backend 应在 `create_loop()` 中设置 `ctx.working_dir` 为显式沙箱目录。Framework 应引入 builder 模式或 config dataclass 替代 19 参数构造器（FRMW-ARCH-14 修复建议），并确保 `file_tools.py` 调用 `safe_path()`。

### 主题 5：私有属性跨层访问

Backend 直接访问 Framework 的私有方法和属性，形成脆弱的跨层耦合。

| 层 | Issue | 描述 | 严重性 |
|----|-------|------|--------|
| Backend | BKND-ARCH-10 | `getattr(loop, '_system_prompt_text', None)` 访问 Framework 私有属性 | MEDIUM |
| Backend | BKND-LOGIC-06 | `sm._redis_set_messages` 从 api 层访问 SessionManager 私有方法 | MEDIUM |
| Framework | FRMW-LOGIC-24 | teams/tools.py `_broadcast` 访问 manager 私有属性 `_configs` | MEDIUM |
| Framework | FRMW-LOGIC-34 | commands/help.py 直接访问 registry 私有属性 `_documents` | HIGH |

**跨层表现：** Backend 的 `chat.py` 使用 `getattr(loop, '_system_prompt_text', None)` 读取 Framework `AgentLoop` 的私有属性，用于 `TranscriptConsumer` 的初始化。这种访问方式在属性被重命名时会静默降级为 `None`，不会报错但会导致 transcript 缺少 system prompt 信息。Framework 内部也存在同样的私有属性访问模式（`_configs`, `_documents`），说明这是一个系统性的封装边界问题。

**修复建议：** Framework 应在 `AgentLoop` 上暴露公共 `system_prompt_text` 属性（property），或通过工厂方法的返回值传递。Backend 应调用 SessionManager 的公共方法而非私有方法 `_redis_set_messages`。

---

*Report completed: 2026-06-09 — Phase 13, Plan 01 (file review) + Plan 02 (summary + cross-layer)*
