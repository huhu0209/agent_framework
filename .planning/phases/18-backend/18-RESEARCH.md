# Phase 18: Backend 全面试修 - Research

**Researched:** 2026-06-10
**Domain:** Backend security & logic fixes (FastAPI + aiofiles + Pydantic + Redis)
**Confidence:** HIGH

## Summary

Phase 18 fixes 10 backend issues (BK-SEC-01~05, BK-LOGIC-01~05) across 6 source files and 2 test files. The fixes are well-scoped: they modify existing code patterns without introducing new architectural layers. Three groups (Plans A/B/C) are defined by dependency ordering -- Plan A exposes framework interfaces that Plans B and C consume.

The core technical challenges are: (1) converting SessionManager from synchronous to async file I/O via aiofiles while maintaining backward compatibility with existing test infrastructure, (2) implementing ErrorCategory-based SSE error sanitization without breaking the `session.messages` diagnostic trail, and (3) adding a `@property` to AgentLoop without breaking 964+ framework tests.

**Primary recommendation:** Follow the Plan A -> Plan B -> Plan C ordering strictly. Plan A is small (4 targeted changes) but unlocks Plans B and C. Plan B is the highest-risk due to the full async conversion of SessionManager -- it requires updating every call site and all test mocks.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** SSE error events return categorized messages via ErrorCategory enum + user-friendly message mapping (not `str(exc)`)
- **D-02:** SSE transport-layer only -- `session.messages` still stores raw `str(exc)` for server-side debugging
- **D-03:** Known error types: LLM timeout, LLM rate limit, Tool execution error, Session not found, Unknown. Mapping via isinstance checks
- **D-04:** All file I/O to aiofiles async -- `update_title`, `delete_session`, `_append_history`, `list_sessions`, `_get_all_messages`
- **D-05:** SessionManager ALL methods become async (including internal methods)
- **D-06:** Atomic writes via aiofiles + temp file + os.replace (matching Phase 16 pattern)
- **D-07:** Add `aiofiles` to `backend/pyproject.toml` dependencies
- **D-08:** Each `create_loop()` call creates new `ToolUseContext()` instance (move from `__init__` to `create_loop`)
- **D-09:** `AgentLoop` adds `system_prompt_text` @property -- framework layer only adds one property
- **D-10:** `ctx.working_dir = str(storage_dir / "shared_workspace")` -- shared workspace directory
- **D-11:** Add `SessionManager` public methods `persist_messages()` / `restore_messages()`
- **D-12:** `session_id` path params use FastAPI `Path(pattern=SESSION_ID_RE)` validation
- **D-13:** Redis exception handling: ConnectionError/TimeoutError -> ERROR log + degrade; ValueError -> raise
- **D-14:** `Settings.llm_api_key` -> `SecretStr`, `AgentFactory.from_settings` calls `get_secret_value()`
- **D-15:** CORS `allow_methods=["GET","POST","DELETE","PATCH"]`, `allow_headers=["Content-Type","X-Session-Id"]`
- **D-16:** `_evict_expired` checks `session.task` still running -- skip eviction for active sessions
- **D-17:** Plan grouping: Plan A (framework interface), Plan B (async + atomic), Plan C (SSE + security)
- **D-18:** Full pytest verification after each plan (964+ tests)
- **D-19:** Backend manual verification for SSE, session_id, atomic writes

### Claude's Discretion
- ErrorCategory enum specific definition and naming
- User-friendly message specific wording
- SessionManager async method decomposition and call-chain updates
- persist/restore method API design
- FastAPI Path() pattern specific syntax
- Fix ordering within each plan

### Deferred Ideas (OUT OF SCOPE)
- BKND-SEC-06 (API authentication) -- separate milestone required
- BKND-ARCH-04 (SessionManager mixed responsibilities) -- larger refactor
- BKND-ARCH-05 (redis_client: Any | None -> Protocol)
- BKND-ARCH-01 (create_chat C901=12 complexity)
- BKND-LOGIC-05 (get() refreshes TTL)
- BKND-ARCH-11 (before parameter type)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| BK-SEC-01 | SSE error messages leak internal info to client | ErrorCategory enum + isinstance mapping (D-01~03). LLM exception hierarchy verified: RateLimitError, ServiceUnavailableError, CircuitOpenError, InvalidRequestError all inherit LLMAdapterError |
| BK-SEC-02 | session_id path parameter unvalidated | FastAPI `Path(pattern=...)` verified on v0.133.1 -- both `pattern` and `regex` params accepted. SESSION_ID_RE already defined in models/__init__.py |
| BK-SEC-03 | CORS methods/headers too permissive | CORSMiddleware config in main.py:52-53. Tightened to actual API usage: GET/POST/DELETE/PATCH + Content-Type/X-Session-Id |
| BK-SEC-04 | Redis connection failure silently swallowed | redis lib exception types verified: `redis.exceptions.ConnectionError`, `redis.exceptions.TimeoutError`. ValueError confirmed for malformed URLs |
| BK-SEC-05 | API key stored as plain string | Pydantic SecretStr verified: `repr()` masks value, `get_secret_value()` extracts. Validator pattern tested: `field_validator` works with `SecretStr` input (Pydantic auto-converts empty string to `SecretStr('')`) |
| BK-LOGIC-01 | TTL eviction race condition | `_evict_expired` in session.py:310-318. Fix: check `session.task` and `not session.task.done()` before evicting |
| BK-LOGIC-02 | JSONL non-atomic read/write | aiofiles 25.1.0 available. Atomic write pattern from framework `memory/index_manager.py:_atomic_write()` ready to reuse |
| BK-LOGIC-03 | Shared ToolUseContext across sessions | ToolUseContext() has mutable list/dict fields. Verified: `ToolUseContext()` takes no required args. Fix: create new instance per `create_loop()` |
| BK-LOGIC-04 | AgentFactory missing working_dir | ToolUseContext.working_dir defaults to ".". Fix: set to `str(storage_dir / "shared_workspace")` |
| BK-LOGIC-05 | chat.py accesses framework private attributes | `getattr(loop, '_system_prompt_text', None)` at chat.py:115. Fix: AgentLoop gets `system_prompt_text` @property |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| SSE error sanitization | API / Backend | -- | HTTP response layer owns what leaves the server |
| session_id validation | API / Backend | -- | FastAPI path parameter validation is a routing concern |
| CORS policy | API / Backend | -- | Middleware configuration at application entry point |
| Redis exception handling | API / Backend | -- | Application startup lifecycle owns service initialization |
| API key protection | API / Backend (config) | -- | Pydantic Settings model owns secret management |
| Async file I/O | Backend (SessionManager) | -- | SessionManager owns all file operations |
| Atomic writes | Backend (SessionManager) | -- | Same -- file integrity is SessionManager's responsibility |
| TTL eviction safety | Backend (SessionManager) | -- | SessionManager owns session lifecycle |
| ToolUseContext isolation | Backend (AgentFactory) | -- | Factory owns AgentLoop assembly |
| working_dir config | Backend (AgentFactory) | -- | Factory sets up context before creating loops |
| AgentLoop @property | Framework (agents/) | -- | Framework owns its own public API surface |
| Public persist/restore | Backend (SessionManager) | -- | Encapsulation fix -- SessionManager exposes its own API |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| aiofiles | >=24.1.0 (installed 25.1.0) | Async file I/O | Already in framework deps; Phase 16 pattern established [VERIFIED: pip registry] |
| pydantic SecretStr | 2.x (bundled with pydantic) | API key protection | Standard Pydantic secret type [VERIFIED: runtime test] |
| FastAPI Path(pattern=...) | 0.133.1 | Path parameter validation | Built-in FastAPI feature [VERIFIED: runtime test] |
| redis exceptions | 8.0.0 | Connection error handling | Standard redis lib exception hierarchy [VERIFIED: runtime test] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| tempfile + os.replace | stdlib | Atomic write pattern | All non-append file writes in SessionManager |
| enum.Enum | stdlib | ErrorCategory enum | SSE error classification |

### Installation
```bash
# aiofiles needs explicit addition to backend/pyproject.toml (D-07)
# All other dependencies are already available (stdlib or existing deps)
```

**Version verification:**
```
aiofiles: 25.1.0 (installed)
FastAPI: 0.133.1
redis: 8.0.0
pydantic SecretStr: available (bundled)
Python: 3.11.14
```

## Package Legitimacy Audit

> No new packages installed in this phase. `aiofiles` is already a dependency of the framework package (`framework/pyproject.toml:10`). D-07 adds it to `backend/pyproject.toml` for explicitness only.

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| aiofiles | PyPI | 8+ yrs | 50M+/mo | github.com/Tinche/aiofiles | N/A (existing dep) | Approved |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
HTTP Client
    |
    v
FastAPI (main.py)
    |-- CORSMiddleware (tightened methods/headers)
    |-- Lifespan:
    |     |-- Settings (SecretStr for llm_api_key)
    |     |-- AgentFactory (per-session ToolUseContext + working_dir)
    |     |-- Redis (differentiated exception handling)
    |     |-- SessionManager (async + atomic writes)
    |
    v
chat.py (SSE + REST endpoints)
    |-- Path(pattern=SESSION_ID_RE) validation
    |-- ErrorCategory-based SSE error messages
    |-- await sm.persist_messages() / sm.restore_messages()
    |
    v
SessionManager (async)
    |-- aiofiles for all file I/O
    |-- tempfile + os.replace for atomic writes
    |-- TTL eviction skips active tasks
    |
    v
AgentLoop (framework layer)
    |-- @property system_prompt_text (public accessor)
    |-- ToolUseContext (per-session instance)
    |-- working_dir (sandboxed)
```

### Recommended Project Structure

No structural changes needed. All modifications are within existing files:

```
backend/
├── main.py                        # CORS tighten + Redis exception handling
├── app/
│   ├── config/__init__.py         # SecretStr migration
│   ├── models/__init__.py         # Remove unused Field import (opportunistic)
│   ├── services/
│   │   ├── agent_factory.py       # Per-session ctx + working_dir + SecretStr
│   │   └── session.py             # Full async + atomic writes + TTL fix + public API
│   └── api/v1/chat.py             # SSE errors + session_id validation + await async + public methods
└── tests/
    ├── test_chat_api.py           # Update for async SessionManager + SSE error changes
    └── test_session_redis.py      # Update for async SessionManager

framework/
└── agent_framework/agents/
    └── agent_loop.py              # Add system_prompt_text @property
```

### Pattern 1: ErrorCategory SSE Error Sanitization

**What:** Replace `str(exc)` in SSE error events with categorized user-friendly messages.
**When to use:** SSE event_stream() exception handler.
**Example:**

```python
# Source: [DESIGNED for this phase -- LLM exception hierarchy from framework/agent_framework/llm/base.py]
import enum

class ErrorCategory(enum.Enum):
    LLM_TIMEOUT = "llm_timeout"
    LLM_RATE_LIMIT = "llm_rate_limit"
    TOOL_ERROR = "tool_error"
    SESSION_NOT_FOUND = "session_not_found"
    UNKNOWN_ERROR = "unknown_error"

_ERROR_MESSAGES: dict[ErrorCategory, str] = {
    ErrorCategory.LLM_TIMEOUT: "AI 服务响应超时，请稍后重试。",
    ErrorCategory.LLM_RATE_LIMIT: "AI 服务繁忙，请稍后重试。",
    ErrorCategory.TOOL_ERROR: "工具执行出错，请检查输入。",
    ErrorCategory.SESSION_NOT_FOUND: "会话不存在或已过期。",
    ErrorCategory.UNKNOWN_ERROR: "服务内部错误，请稍后重试。",
}

def _classify_error(exc: Exception) -> ErrorCategory:
    """Map exception type to ErrorCategory via isinstance."""
    from agent_framework.llm.base import (
        LLMAdapterError,
        RateLimitError,
        ServiceUnavailableError,
        CircuitOpenError,
    )
    if isinstance(exc, RateLimitError):
        return ErrorCategory.LLM_RATE_LIMIT
    if isinstance(exc, (ServiceUnavailableError, CircuitOpenError)):
        return ErrorCategory.LLM_TIMEOUT
    if isinstance(exc, LLMAdapterError):
        return ErrorCategory.LLM_TIMEOUT
    # asyncio.TimeoutError for tool timeouts
    if isinstance(exc, asyncio.TimeoutError):
        return ErrorCategory.TOOL_ERROR
    return ErrorCategory.UNKNOWN_ERROR
```

### Pattern 2: aiofiles Async File I/O + Atomic Write

**What:** All SessionManager file operations use aiofiles + temp file + os.replace.
**When to use:** Any file write that must not lose data on crash.
**Example:**

```python
# Source: [VERIFIED pattern from framework/agent_framework/memory/index_manager.py:_atomic_write]
import os
import tempfile
import aiofiles

async def _atomic_write(self, path: Path, content: str) -> None:
    """Atomic write: write-to-temp + os.replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix=".tmp", prefix=".sess_")
    try:
        os.close(fd)
        async with aiofiles.open(tmp_path, "w", encoding="utf-8") as f:
            await f.write(content)
        os.replace(tmp_path, path)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
```

### Pattern 3: FastAPI Path Parameter Validation

**What:** Validate session_id format at the routing level using FastAPI's built-in `Path()`.
**When to use:** All endpoints accepting `{session_id}` path parameter.
**Example:**

```python
# Source: [VERIFIED on FastAPI 0.133.1 -- both 'pattern' and 'regex' params accepted]
from fastapi import Path

SESSION_ID_RE = r"^[0-9a-f]{32}$"

@router.get("/chat/{session_id}", response_model=HistoryResponse)
async def get_history(
    session_id: str = Path(pattern=SESSION_ID_RE),
    request: Request,
    ...
) -> HistoryResponse:
    # FastAPI auto-returns 422 if pattern doesn't match
```

### Pattern 4: SecretStr in Pydantic Settings

**What:** Protect API key from accidental logging/serialization.
**When to use:** Any secret field in configuration models.
**Example:**

```python
# Source: [VERIFIED via runtime test -- Pydantic v2 auto-converts str input to SecretStr]
from pydantic import SecretStr, field_validator

class Settings(BaseSettings):
    llm_api_key: SecretStr = SecretStr("")

    @field_validator("llm_api_key")
    @classmethod
    def api_key_must_not_be_empty(cls, v: SecretStr) -> SecretStr:
        if not v.get_secret_value().strip():
            raise ValueError("APP_LLM_API_KEY is required")
        return v

# Consumer:
api_key = settings.llm_api_key.get_secret_value()
```

### Pattern 5: Per-Session ToolUseContext

**What:** Create fresh ToolUseContext per AgentLoop to prevent cross-session state leakage.
**When to use:** In AgentFactory.create_loop().
**Example:**

```python
# Source: [VERIFIED -- ToolUseContext() has no required args, creates fresh mutable defaults]
class AgentFactory:
    def __init__(self, adapter, model, storage_dir):
        self._adapter = adapter
        self._model = model
        self._router = ToolRouter(create_builtin_registry())
        self._storage_dir = storage_dir

    def create_loop(self) -> AgentLoop:
        ctx = ToolUseContext()  # Fresh instance per session
        ctx.working_dir = str(self._storage_dir / "shared_workspace")
        return AgentLoop(
            adapter=self._adapter,
            model=self._model,
            router=self._router,
            ctx=ctx,
        )
```

### Anti-Patterns to Avoid

- **Don't use `asyncio.to_thread()` for new SessionManager methods** -- the methods themselves should be `async def` using aiofiles. `asyncio.to_thread` was a workaround in chat.py for the sync methods; once methods are async, the call sites just `await` them directly.
- **Don't change `session.messages` error content** -- D-02 explicitly preserves raw `str(exc)` in `session.messages` for server debugging. Only the SSE transport layer uses ErrorCategory.
- **Don't pass `SecretStr` to `create_adapter()`** -- it accepts `api_key: str`. The conversion `get_secret_value()` happens in `AgentFactory.from_settings`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SSE error sanitization | Custom string filtering on `str(exc)` | ErrorCategory enum + isinstance mapping | Comprehensive coverage of known error types; extensible |
| Atomic file writes | Custom locking or append-only schemes | tempfile + os.replace | OS-level atomicity guarantee; same pattern as Phase 16 |
| API key protection | Custom masking/redaction | Pydantic SecretStr | Prevents repr/str/serialization leaks automatically |
| session_id validation | Manual regex check in each handler | FastAPI Path(pattern=...) | Declarative, auto-422, consistent with FastAPI patterns |
| Redis exception classification | Broad `except Exception` | Specific `ConnectionError`/`TimeoutError`/`ValueError` catch | Correct behavior per error type (degrade vs fail-fast) |

## Common Pitfalls

### Pitfall 1: Sync Test Client with Async SessionManager Methods

**What goes wrong:** `test_chat_api.py` uses `TestClient` (synchronous) which calls endpoints that now `await` async SessionManager methods. If SessionManager methods are `async def`, they work fine inside FastAPI's async handlers via `TestClient`. However, tests that call SessionManager methods directly (e.g., `sm.get_messages(sid)`, `sm.remove(sid)`) must become `async def` tests.
**Why it happens:** `asyncio_mode = "auto"` in backend `pyproject.toml` makes this seamless -- pytest-asyncio auto-detects `async def test_*` functions.
**How to avoid:** Tests that call async SessionManager methods directly must be `async def`. Tests using `TestClient` remain synchronous (TestClient handles the event loop internally).
**Warning signs:** `RuntimeError: coroutine was never awaited` in test output.

### Pitfall 2: aiofiles Not in Backend pyproject.toml

**What goes wrong:** `aiofiles` is a dependency of the *framework* package, so it's transitively available. But D-07 explicitly requires adding it to `backend/pyproject.toml`. If forgotten, the backend still works during development (transitive dep) but fails in isolated installs.
**Why it happens:** The backend imports `aiofiles` directly in `session.py` -- this creates a direct dependency that should be declared.
**How to avoid:** Add `"aiofiles>=24.1.0"` to `backend/pyproject.toml` dependencies.
**Warning signs:** `ModuleNotFoundError: No module named 'aiofiles'` when installing backend alone.

### Pitfall 3: SecretStr Validator Receives String Input

**What goes wrong:** When Pydantic loads from env vars, the input is always a `str`. The `field_validator` for `SecretStr` fields receives the *raw string* (Pydantic converts after validation). The validator must handle `str` input, not `SecretStr`.
**Why it happens:** Pydantic v2 runs validators before type coercion in some configurations.
**How to avoid:** Verified: with `pydantic-settings`, the validator receives `SecretStr` (Pydantic coerces first). Use `v.get_secret_value()` in the validator.
**Warning signs:** `AttributeError: 'str' object has no attribute 'get_secret_value'`.

### Pitfall 4: AgentLoop @property Conflicts with Existing Tests

**What goes wrong:** Framework has 964+ tests. Adding `system_prompt_text` as a `@property` could theoretically shadow a setter or conflict with existing attribute access. However, the attribute `_system_prompt_text` already exists as a private attribute -- the @property just exposes it read-only.
**Why it happens:** Test code may reference `_system_prompt_text` directly (unlikely given it's private to the module).
**How to avoid:** D-18 mandates running full framework test suite after Plan A.
**Warning signs:** `pytest tests/ -v` failures after adding the @property.

### Pitfall 5: TTL Eviction Skipping Extends Sessions Indefinitely

**What goes wrong:** D-16 says skip eviction if `session.task` is running. If a session's SSE stream never closes (buggy client), the task never completes, and the session is never evicted -- memory leak.
**Why it happens:** The task is the SSE `event_stream()` generator task, which runs until the LLM responds or errors. Under normal operation, tasks complete within seconds to minutes. But edge cases (infinite loop in agent, hung connection) could prevent eviction.
**How to avoid:** The TTL check should still have an upper bound. Consider adding a maximum TTL (e.g., 3x normal TTL = 3 hours) beyond which sessions are forcefully evicted regardless of task state. Alternatively, document that task completion timeout is handled by `max_steps` in AgentLoop.
**Warning signs:** Growing `_sessions` dict over time in production.

### Pitfall 6: `_get_all_messages` Async Chain Breaks Sync Callers

**What goes wrong:** `_get_all_messages` is called by `get_messages` (which is called by endpoints). If `get_messages` becomes `async def`, all callers must `await` it. The existing test `sm.get_messages(sid)` in `test_chat_api.py` calls it synchronously.
**Why it happens:** D-05 says ALL SessionManager methods become async.
**How to avoid:** All direct test calls to `sm.get_messages()`, `sm.remove()`, etc. must become `await sm.get_messages()` inside `async def test_*` functions.
**Warning signs:** `TypeError: object coroutine can't be used in 'await' expression` or `RuntimeError: coroutine was never awaited`.

## Code Examples

### AgentLoop @property Addition (D-09)

```python
# File: framework/agent_framework/agents/agent_loop.py
# Add after __init__ method, before load_messages:

@property
def system_prompt_text(self) -> str:
    """The assembled system prompt text (read-only)."""
    return self._system_prompt_text
```

### Redis Exception Differentiation (D-13)

```python
# File: backend/main.py
# Replace the broad except block:

try:
    rdb = redis_lib.Redis.from_url(settings.redis_url, decode_responses=True)
    rdb.ping()
except (redis_lib.ConnectionError, redis_lib.TimeoutError) as exc:
    logger.error("Redis connection failed: %s. Caching disabled.", exc)
    rdb = None
# ValueError (malformed URL) propagates -> app fails to start (correct)
```

### SessionManager Async Conversion (D-04, D-05, D-06)

```python
# File: backend/app/services/session.py
# Key method conversions:

async def _append_history(self, session_id: str, title: str) -> None:
    if not self._storage_dir:
        return
    history_path = self._storage_dir / "history.jsonl"
    history_path.parent.mkdir(parents=True, exist_ok=True)
    entry = json.dumps({
        "session_id": session_id,
        "title": title,
        "created_at": time.time(),
    }, ensure_ascii=False)
    async with aiofiles.open(history_path, "a", encoding="utf-8") as f:
        await f.write(entry + "\n")

async def update_title(self, session_id: str, title: str) -> bool:
    """Atomic update with aiofiles + tempfile + os.replace."""
    if not self._storage_dir:
        return False
    history_path = self._storage_dir / "history.jsonl"
    if not history_path.exists():
        return False
    # Read
    async with aiofiles.open(history_path, "r", encoding="utf-8") as f:
        content = await f.read()
    # Process
    lines = []
    updated = False
    for line in content.strip().split("\n"):
        if not line.strip():
            continue
        entry = json.loads(line)
        if entry["session_id"] == session_id:
            entry["title"] = title
            updated = True
        lines.append(json.dumps(entry, ensure_ascii=False))
    # Atomic write
    await self._atomic_write(history_path, "\n".join(lines) + "\n")
    self._invalidate_list_cache()
    if self._redis:
        self._redis.delete(f"session:{session_id}:meta")
    return updated

async def persist_messages(self, session_id: str, messages: list[dict]) -> None:
    """Public method: persist messages to Redis cache."""
    self._redis_set_messages(session_id, messages)

async def restore_messages(self, session_id: str) -> list[dict] | None:
    """Public method: restore messages from cache/storage."""
    return self._get_all_messages(session_id)
```

### TTL Eviction Active Session Check (D-16)

```python
# File: backend/app/services/session.py
# In _evict_expired:

def _evict_expired(self) -> None:
    now = time.time()
    expired = [
        sid for sid, s in self._sessions.items()
        if now - s.created_at > self._ttl
        and (s.task is None or s.task.done())  # Skip active sessions
    ]
    for sid in expired:
        self.remove(sid)
        logger.info("Evicted expired session %s", sid)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `str(exc)` in SSE errors | ErrorCategory enum + user-friendly messages | This phase | Prevents info disclosure |
| Sync `open()` in SessionManager | aiofiles async I/O | Phase 16 (framework), this phase (backend) | No event loop blocking |
| `open()` + write back | tempfile + os.replace atomic writes | Phase 16 (framework), this phase (backend) | No data loss on crash |
| `str` for API keys | Pydantic `SecretStr` | This phase | Prevents accidental logging |
| `allow_methods=["*"]` CORS | Explicit method whitelist | This phase | Reduced attack surface |
| Broad `except Exception` for Redis | Specific exception types | This phase | Correct failure modes |

**Deprecated/outdated:**
- `getattr(loop, '_system_prompt_text', None)`: Replaced by `loop.system_prompt_text` @property
- `sm._redis_set_messages(...)`: Replaced by `await sm.persist_messages(...)`
- `asyncio.to_thread(sm._redis_set_messages, ...)`: Replaced by direct `await sm.persist_messages(...)`

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | TestClient (sync) correctly handles async endpoint handlers that await async SessionManager methods | Common Pitfalls | Tests would need restructuring |
| A2 | Framework 964+ tests pass after adding `system_prompt_text` @property | Architecture Patterns | Needs Plan A verification step |
| A3 | `_system_prompt_text` is always set in `AgentLoop.__init__` (all code paths assign it) | Architecture Patterns | @property could raise AttributeError |
| A4 | pytest-asyncio `asyncio_mode = "auto"` handles mixed sync/async tests in the same file | Common Pitfalls | Test file restructuring needed |
| A5 | aiofiles transitively available from framework dep is sufficient for development; D-07 adds explicit declaration | Common Pitfalls | Minor -- aiofiles already installed |

**If this table is empty:** All claims in this research were verified or cited -- no user confirmation needed.

## Open Questions

1. **`X-Session-Id` in allow_headers (D-15)**
   - What we know: D-15 specifies `allow_headers=["Content-Type", "X-Session-Id"]`. In the current code, `X-Session-Id` is a *response* header (set by the server in SSE responses), not a *request* header sent by the client.
   - What's unclear: Whether the frontend ever sends `X-Session-Id` as a request header. CORS `allow_headers` controls which *request* headers are permitted.
   - Recommendation: Check frontend code. If `X-Session-Id` is only a response header, it doesn't need to be in `allow_headers`. The planner should verify this before implementation.

2. **`persist_messages` async vs Redis sync**
   - What we know: `_redis_set_messages` uses synchronous Redis operations. Currently called via `asyncio.to_thread()`.
   - What's unclear: Should `persist_messages()` also be async and use `asyncio.to_thread()` internally for the Redis operations? Or should Redis operations remain sync within the now-async method?
   - Recommendation: Since `persist_messages()` is async, wrap the Redis call in `asyncio.to_thread()` internally. This keeps the public API clean while not blocking the event loop.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Runtime | YES | 3.11.14 | -- |
| FastAPI | Backend | YES | 0.133.1 | -- |
| redis (lib) | Optional caching | YES | 8.0.0 | Degrade to file-only |
| aiofiles | Async file I/O | YES | 25.1.0 | -- |
| Pydantic SecretStr | Secret protection | YES | (bundled) | -- |
| pytest | Testing | YES | 9.0.3 | -- |
| pytest-asyncio | Async tests | YES | 1.4.0 | -- |
| Redis server | Integration tests | UNKNOWN | -- | Tests auto-skip via `pytestmark` |

**Missing dependencies with no fallback:**
- None -- all required libraries are installed.

**Missing dependencies with fallback:**
- Redis server: Integration tests (`test_session_redis.py`) auto-skip when Redis is unavailable. This is acceptable for unit test execution.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 + pytest-asyncio 1.4.0 |
| Config file | backend/pyproject.toml (`[tool.pytest.ini_options]`) |
| Quick run command | `cd backend && pytest tests/test_chat_api.py -v` |
| Full suite command | `cd framework && pytest tests/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BK-SEC-01 | SSE errors use ErrorCategory, not str(exc) | unit | `cd backend && pytest tests/test_chat_api.py::test_agent_error_sends_error_event -v` | YES -- needs update |
| BK-SEC-02 | Invalid session_id in path returns 422 | unit | `cd backend && pytest tests/test_chat_api.py -v -k "invalid_session"` | NO -- Wave 0 |
| BK-SEC-03 | CORS only allows specified methods | unit | manual (curl -X OPTIONS) | NO -- manual only |
| BK-SEC-04 | Redis ConnectionError logs ERROR, not WARNING | unit | `cd backend && pytest tests/ -v -k "redis_connection"` | NO -- Wave 0 |
| BK-SEC-05 | API key not in repr/str of Settings | unit | `cd backend && pytest tests/ -v -k "secret"` | NO -- Wave 0 |
| BK-LOGIC-01 | Active sessions not evicted by TTL | unit | `cd backend && pytest tests/ -v -k "evict"` | NO -- Wave 0 |
| BK-LOGIC-02 | Atomic writes survive crash simulation | unit | `cd backend && pytest tests/ -v -k "atomic"` | NO -- Wave 0 |
| BK-LOGIC-03 | Each create_loop gets fresh ToolUseContext | unit | `cd backend && pytest tests/ -v -k "tool_use_context"` | NO -- Wave 0 |
| BK-LOGIC-04 | working_dir set on ToolUseContext | unit | `cd backend && pytest tests/ -v -k "working_dir"` | NO -- Wave 0 |
| BK-LOGIC-05 | chat.py uses loop.system_prompt_text, not getattr | unit | Verified via framework test suite (D-18) | YES -- framework tests |

### Sampling Rate
- **Per task commit:** `cd backend && pytest tests/ -v`
- **Per wave merge:** `cd framework && pytest tests/ -v`
- **Phase gate:** Both backend + framework test suites green

### Wave 0 Gaps
- [ ] Test for BK-SEC-02: session_id path validation returns 422
- [ ] Test for BK-SEC-04: Redis exception differentiation
- [ ] Test for BK-SEC-05: SecretStr repr masking
- [ ] Test for BK-LOGIC-01: TTL eviction skips active sessions
- [ ] Test for BK-LOGIC-02: Atomic write integrity
- [ ] Test for BK-LOGIC-03: Per-session ToolUseContext
- [ ] Test for BK-LOGIC-04: working_dir set on context

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Out of scope (BKND-SEC-06 deferred) |
| V3 Session Management | yes | TTL + session_id validation + SSE error sanitization |
| V4 Access Control | no | Out of scope (no auth) |
| V5 Input Validation | yes | FastAPI Path(pattern=) + Pydantic validators |
| V6 Cryptography | no | Not applicable |

### Known Threat Patterns for Backend Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Information disclosure via error messages | Information Disclosure | ErrorCategory enum (D-01) |
| Path traversal via session_id | Tampering | SESSION_ID_RE regex via Path(pattern=) (D-12) |
| API key leak via logging/serialization | Information Disclosure | Pydantic SecretStr (D-14) |
| CORS policy exploitation | Spoofing | Explicit methods/headers whitelist (D-15) |
| Cross-session state leakage | Information Disclosure | Per-session ToolUseContext (D-08) |
| Redis config error masking | Denial of Service | Specific exception handling (D-13) |

## Sources

### Primary (HIGH confidence)
- Framework source: `framework/agent_framework/llm/base.py` -- LLM exception hierarchy verified
- Framework source: `framework/agent_framework/tools/types.py` -- ToolUseContext structure verified
- Framework source: `framework/agent_framework/memory/index_manager.py` -- Atomic write pattern reference
- Backend source: `backend/app/services/session.py` -- Current sync implementation verified
- Backend source: `backend/app/api/v1/chat.py` -- SSE error handling verified
- Runtime verification: FastAPI 0.133.1 Path(pattern=) parameter accepted
- Runtime verification: SecretStr validator pattern works with pydantic-settings
- Runtime verification: redis.exceptions.ConnectionError/TimeoutError types confirmed

### Secondary (MEDIUM confidence)
- `docs/reviews/REVIEW-BACKEND.md` -- Issue descriptions, severity, fix suggestions
- `.planning/codebase/CONVENTIONS.md` -- Project coding standards

### Tertiary (LOW confidence)
- None -- all findings verified against source code or runtime tests

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries verified via runtime tests and existing codebase usage
- Architecture: HIGH -- all source files read and understood; patterns from Phase 16 directly applicable
- Pitfalls: HIGH -- test infrastructure verified; async conversion risks identified and mitigated

**Research date:** 2026-06-10
**Valid until:** 2026-07-10 (stable -- no fast-moving dependencies)
