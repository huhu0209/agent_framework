# Phase 2: 安全审查与修复 - Research

**Researched:** 2026-05-28
**Domain:** Security audit and remediation for Python agent framework
**Confidence:** HIGH

## Summary

This phase addresses 6 known security issues in `framework/agent_framework/`, ordered by severity from CRITICAL to LOW. The codebase already contains the building blocks for the CRITICAL fix (`safe_path()` exists in `safety/boundary.py` but is not wired into `file_tools.py`). The HIGH issue (MCP env injection) requires a Pydantic `field_validator` on `McpServerConfig` -- a pattern not yet used in the codebase but fully supported by Pydantic v2.12. The MEDIUM issues involve `SecretStr` wrapping for API keys (trivial, but touches 3 provider files and their tests) and documentation-only items for Hook command trust and Permission ASK gaps.

**Primary recommendation:** The CRITICAL fix is a 2-line integration (call `safe_path()` in `read_file`/`write_file`), but the planner must ensure test coverage for path escape scenarios in file tools. The `SecretStr` migration requires updating `_make_provider` test helper to use `get_secret_value()`.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Call `safe_path(path, ctx.working_dir)` in `read_file` and `write_file`
- **D-02:** Return `ToolResult(is_error=True)` on path escape (not throw)
- **D-03:** Error message must not leak actual path info
- **D-04:** Blacklist strategy for sensitive env vars in MCP config
- **D-05:** Validate at `McpServerConfig` level (Pydantic validator), fail at config load time
- **D-06:** Case-insensitive keyword matching for API_KEY, TOKEN, SECRET, PASSWORD, CREDENTIAL patterns
- **D-07:** Wrap `_api_key` with `pydantic.SecretStr` in all 3 providers
- **D-08:** `__repr__`/`__str__` auto-redact, key still usable for httpx client construction
- **D-09:** Document Permission ASK gap in SECURITY-REVIEW.md only, no code fix this phase
- **D-10:** SECURITY-REVIEW.md organized by severity (CRITICAL / HIGH / MEDIUM / LOW)
- **D-11:** Each issue: description + file location + severity + fix status

### Claude's Discretion
- Hook command execution security (#4) documentation depth
- MessageBus predictable path (#6) documentation recommendations
- Blacklist keyword list specifics
- Test organization (new file vs append to existing)

### Deferred Ideas (OUT OF SCOPE)
- None
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SEC-01 | Path sandbox for file tools (CRITICAL) | `safe_path()` exists, needs wiring into `file_tools.py` |
| SEC-02 | MCP env variable injection (HIGH) | Pydantic `field_validator` on `McpServerConfig.env` |
| SEC-03 | API key plaintext storage (MEDIUM) | `SecretStr` wrapping in 3 providers |
| SEC-04 | Hook command execution docs (MEDIUM) | `trusted` flag exists, needs documentation |
| SEC-05 | Permission ASK HITL gap (MEDIUM) | Document only, no code change |
| SEC-06 | MessageBus predictable paths (LOW) | Document only |
| SEC-07 | Produce SECURITY-REVIEW.md | Template from decisions D-10/D-11 |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Path sandbox enforcement | API / Backend (tools layer) | -- | File tools must validate before I/O; this is a backend concern, not client-side |
| Env var injection prevention | API / Backend (config layer) | -- | `McpServerConfig` is loaded server-side; validation belongs at config parse time |
| API key protection | API / Backend (LLM layer) | -- | Provider instances live server-side; `SecretStr` wrapping is server-side protection |
| Hook trust documentation | API / Backend (hooks layer) | -- | Trust model is a server-side configuration concern |
| Permission ASK gap documentation | API / Backend (tools layer) | -- | HITL is a server-side orchestration concern |

## Standard Stack

### Core (already installed, no new packages needed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pydantic | 2.12.5 | `SecretStr` for API keys, `field_validator` for MCP env | Already a framework dependency; provides exactly what's needed [VERIFIED: pip show] |
| pytest | 9.0.3 | Test framework for all security tests | Already in use, `@pytest.mark.asyncio` for async tests [VERIFIED: pytest --version] |
| pathlib | stdlib | `Path.resolve()`, `is_relative_to()` used by `safe_path()` | Already used in `boundary.py` [VERIFIED: codebase read] |

### No New Dependencies Required

This phase requires zero new package installations. All security fixes use existing dependencies.

**Installation:** None needed.

## Package Legitimacy Audit

> No new packages are installed in this phase. All fixes use existing dependencies (pydantic, pytest, pathlib stdlib).

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```text
                    Agent Framework Security Layer

  ┌──────────────────────────────────────────────────────────────┐
  │                     Tool Dispatch Pipeline                    │
  │                                                              │
  │  ToolCall ──► PermissionPipeline ──► PreHooks ──► Route      │
  │                   │                             │            │
  │                   │ DENY/ASK                     │ builtin   │
  │                   ▼                             ▼            │
  │             ToolResult(error)           ┌──────────────┐     │
  │                                         │  file_tools   │     │
  │                                         │  read_file    │◄──── SEC-01: safe_path() gate
  │                                         │  write_file   │     │
  │                                         └──────┬───────┘     │
  │                                                │             │
  │                                         ┌──────▼───────┐     │
  │                                         │  MCP Tools   │     │
  │                                         │  McpConfig   │◄──── SEC-02: env blacklist validator
  │                                         │  StdioTransport│   │
  │                                         └──────────────┘     │
  └──────────────────────────────────────────────────────────────┘

  ┌──────────────────────────────────────────────────────────────┐
  │                      LLM Provider Layer                       │
  │                                                              │
  │  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
  │  │ OpenAIProvider   │  │ AnthropicProv.  │  │ DeepSeekProv.│ │
  │  │ _api_key:        │  │ _api_key:       │  │ _api_key:    │ │
  │  │ SecretStr ◄──────│──│ SecretStr ◄─────│──│ SecretStr    │ │
  │  │ SEC-03           │  │ SEC-03          │  │ SEC-03       │ │
  │  └─────────────────┘  └─────────────────┘  └──────────────┘ │
  └──────────────────────────────────────────────────────────────┘
```

### Recommended Project Structure (changes only)

```text
framework/agent_framework/
├── safety/boundary.py          # UNCHANGED (safe_path already exists)
├── tools/builtin/file_tools.py # MODIFIED: add safe_path() calls
├── tools/mcp/config.py         # MODIFIED: add field_validator on env
├── llm/providers/
│   ├── openai_provider.py      # MODIFIED: SecretStr wrap _api_key
│   ├── anthropic_provider.py   # MODIFIED: SecretStr wrap _api_key
│   └── deepseek_provider.py    # MODIFIED: SecretStr wrap _api_key

framework/tests/
├── test_builtin_tools.py       # EXTENDED: path escape tests
├── test_mcp_manager.py         # EXTENDED: env blacklist tests
├── test_providers.py           # MODIFIED: update _make_provider helper

docs/reviews/
└── SECURITY-REVIEW.md          # NEW: structured security report
```

### Pattern 1: safe_path() Integration in Tool Handlers

**What:** Call `safe_path()` before file I/O, return `ToolResult(is_error=True)` on escape.
**When to use:** Every file tool that resolves user-supplied paths.
**Example:**
```python
# Source: [VERIFIED: codebase read of boundary.py + file_tools.py]
from agent_framework.safety.boundary import safe_path, PathEscapesWorkspace

async def read_file(args: dict, ctx: ToolUseContext) -> ToolResult:
    path = args["path"]

    # Path sandbox check (SEC-01)
    try:
        full_path = safe_path(path, Path(ctx.working_dir))
    except PathEscapesWorkspace:
        return ToolResult(content="路径访问被拒绝: 不允许访问工作目录外的文件", is_error=True)

    if not full_path.exists():
        return ToolResult(content=f"文件不存在: {path}", is_error=True)
    # ... rest unchanged
```

### Pattern 2: Pydantic field_validator for Env Blacklist

**What:** Add `@field_validator("env")` to `McpServerConfig` to reject sensitive keys at config load time.
**When to use:** On any Pydantic model that accepts user-supplied environment variable dicts.
**Example:**
```python
# Source: [VERIFIED: Pydantic v2.12 field_validator tested locally]
from pydantic import BaseModel, field_validator

_BLOCKED_PATTERNS = ("api_key", "token", "secret", "password", "credential", "private_key")

class McpServerConfig(BaseModel):
    env: dict[str, str] = {}

    @field_validator("env")
    @classmethod
    def _reject_sensitive_env_keys(cls, v: dict[str, str]) -> dict[str, str]:
        for key in v:
            lower = key.lower()
            if any(pattern in lower for pattern in _BLOCKED_PATTERNS):
                raise ValueError(
                    f"MCP 配置不允许覆盖敏感环境变量: '{key}'"
                )
        return v
```

### Pattern 3: SecretStr for API Key Storage

**What:** Wrap `_api_key` with `SecretStr`, use `get_secret_value()` for HTTP header construction.
**When to use:** Any field that stores credentials or tokens.
**Example:**
```python
# Source: [VERIFIED: Pydantic v2.12 SecretStr tested locally]
from pydantic import SecretStr

class OpenAIProvider(ILLMAdapter):
    def __init__(self, *, api_key: str | None = None, ...) -> None:
        raw_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        if not raw_key:
            raise ValueError("...")
        self._api_key = SecretStr(raw_key)
        self._client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {self._api_key.get_secret_value()}",
                ...
            },
        )
```

**Critical note:** `str(secret_str)` and `f"{secret_str}"` both produce `**********` [VERIFIED: local test]. The code MUST call `.get_secret_value()` for header construction.

### Anti-Patterns to Avoid

- **Throwing PathEscapesWorkspace from tool handlers:** The codebase convention is `ToolResult(is_error=True)`, not exceptions. The `safe_path()` function raises `PathEscapesWorkspace`, but tools must catch it and return error results (per D-02).
- **Leaking path information in error messages:** Per D-03, use generic "access denied" messages, not the actual resolved path.
- **Using `str()` or f-string interpolation on SecretStr:** This produces `**********`, not the actual value. Must use `.get_secret_value()`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Path traversal protection | Custom `..` checking | `safe_path()` in `safety/boundary.py` | Already handles symlinks, `..`, absolute paths [VERIFIED: codebase read] |
| Secret value masking | Custom `__repr__` override | `pydantic.SecretStr` | Handles repr, str, JSON serialization automatically [VERIFIED: Pydantic docs] |
| Config field validation | Manual `if` checks in `__init__` | Pydantic `@field_validator` | Runs automatically on model instantiation, integrates with error reporting [VERIFIED: Pydantic v2 docs] |

## Common Pitfalls

### Pitfall 1: SecretStr in f-strings produces masked output

**What goes wrong:** `f"Bearer {self._api_key}"` produces `Bearer **********`, silently breaking authentication.
**Why it happens:** `SecretStr.__str__()` returns `**********` by design.
**How to avoid:** Always use `self._api_key.get_secret_value()` when constructing HTTP headers.
**Warning signs:** Provider tests pass but real API calls fail with 401 Unauthorized.

### Pitfall 2: Test helper `_make_provider` breaks after SecretStr migration

**What goes wrong:** `test_providers.py` line 193 does `provider._api_key = api_key` (a plain string). After migration, `_api_key` is `SecretStr`, so string assignment breaks type expectations.
**Why it happens:** Test helper bypasses `__init__` and sets private attributes directly.
**How to avoid:** Update `_make_provider` to wrap: `provider._api_key = SecretStr(api_key)`.
**Warning signs:** `test_providers.py` tests fail with `AttributeError` or `AssertionError` on key comparisons.

### Pitfall 3: safe_path() exception not caught in file tools

**What goes wrong:** Calling `safe_path()` raises `PathEscapesWorkspace` exception. If not caught, it propagates up and crashes the tool dispatch pipeline.
**Why it happens:** `safe_path()` is designed as a guard that raises; tools expect to return `ToolResult`.
**How to avoid:** Wrap `safe_path()` in try/except `PathEscapesWorkspace`, return `ToolResult(is_error=True)`.
**Warning signs:** Agent loop receives unhandled exception instead of graceful error result.

### Pitfall 4: Blacklist too aggressive (blocking legitimate env vars)

**What goes wrong:** An MCP server legitimately needs `DATABASE_URL` which contains no sensitive keywords but the word "password" might appear in a legitimate var like `MY_APP_NOT_PASSWORD_FILE`.
**Why it happens:** Keyword matching is imprecise.
**How to avoid:** Match patterns that are clearly sensitive: `api_key`, `token`, `secret`, `password`, `credential`, `private_key`. Use `in` matching on lowercase, not exact match.
**Warning signs:** Legitimate MCP server configs fail to load with validation errors.

### Pitfall 5: Existing test `test_has_three_tools` expects 4 tools

**What goes wrong:** `test_builtin_tools.py` line 19 asserts `set(registry.list_tools()) == {"read_file", "write_file", "web_search", "update_plan_status"}`. This is unrelated to security but any test changes must not break this.
**Why it happens:** The registry has exactly 4 built-in tools.
**How to avoid:** Don't modify the registry, only the handlers.

## Code Examples

### Example 1: Complete read_file with safe_path integration

```python
# Source: [VERIFIED: codebase read + boundary.py API]
from pathlib import Path

from agent_framework.safety.boundary import safe_path, PathEscapesWorkspace
from agent_framework.tools.types import ToolResult, ToolUseContext


async def read_file(args: dict, ctx: ToolUseContext) -> ToolResult:
    path = args["path"]

    try:
        full_path = safe_path(path, Path(ctx.working_dir))
    except PathEscapesWorkspace:
        return ToolResult(
            content="路径访问被拒绝: 不允许访问工作目录外的文件",
            is_error=True,
        )

    if not full_path.exists():
        return ToolResult(content=f"文件不存在: {path}", is_error=True)

    try:
        content = full_path.read_text(encoding="utf-8")
        return ToolResult(content=content)
    except Exception as e:
        return ToolResult(content=f"读取文件失败: {e}", is_error=True)
```

### Example 2: MCP env blacklist validator

```python
# Source: [VERIFIED: Pydantic v2.12 field_validator tested locally]
from pydantic import BaseModel, field_validator

_BLOCKED_ENV_PATTERNS = (
    "api_key",
    "token",
    "secret",
    "password",
    "credential",
    "private_key",
    "access_key",
    "auth",
)


class McpServerConfig(BaseModel):
    name: str
    transport: Literal["stdio"] = "stdio"
    command: str = ""
    args: list[str] = []
    env: dict[str, str] = {}
    timeout_ms: int = 30_000
    url: str = ""
    headers: dict[str, str] = {}

    @field_validator("env")
    @classmethod
    def _reject_sensitive_env_keys(cls, v: dict[str, str]) -> dict[str, str]:
        for key in v:
            lower = key.lower()
            if any(pattern in lower for pattern in _BLOCKED_ENV_PATTERNS):
                raise ValueError(
                    f"MCP 配置不允许覆盖敏感环境变量: '{key}'"
                )
        return v
```

### Example 3: Test for path escape in file tools

```python
# Source: [VERIFIED: test_builtin_tools.py pattern]
import pytest
from agent_framework.tools.builtin import create_builtin_registry
from agent_framework.tools.types import ToolUseContext


class TestPathSandbox:
    """SEC-01: 文件工具路径沙箱测试。"""

    @pytest.mark.asyncio
    async def test_read_file_rejects_traversal(self, registry, ctx):
        spec = registry.get("read_file")
        result = await spec.handler({"path": "../../../etc/passwd"}, ctx)
        assert result.is_error is True
        assert "拒绝" in result.content or "不允许" in result.content
        # Must NOT contain actual resolved path
        assert "etc" not in result.content

    @pytest.mark.asyncio
    async def test_write_file_rejects_traversal(self, registry, ctx):
        spec = registry.get("write_file")
        result = await spec.handler(
            {"path": "../../tmp/evil.txt", "content": "hack"}, ctx,
        )
        assert result.is_error is True

    @pytest.mark.asyncio
    async def test_read_file_rejects_absolute_path(self, registry, ctx):
        spec = registry.get("read_file")
        result = await spec.handler({"path": "/etc/shadow"}, ctx)
        assert result.is_error is True
```

### Example 4: Test for MCP env blacklist

```python
# Source: [VERIFIED: test_mcp_manager.py pattern]
import pytest
from pydantic import ValidationError
from agent_framework.tools.mcp.config import McpServerConfig


class TestMcpEnvBlacklist:
    """SEC-02: MCP 环境变量注入黑名单测试。"""

    def test_rejects_api_key(self):
        with pytest.raises(ValidationError, match="敏感"):
            McpServerConfig(name="test", command="echo", env={"OPENAI_API_KEY": "sk-xxx"})

    def test_rejects_token(self):
        with pytest.raises(ValidationError, match="敏感"):
            McpServerConfig(name="test", command="echo", env={"GITHUB_TOKEN": "ghp_xxx"})

    def test_rejects_case_insensitive(self):
        with pytest.raises(ValidationError, match="敏感"):
            McpServerConfig(name="test", command="echo", env={"My_Secret_Key": "xxx"})

    def test_allows_normal_env(self):
        cfg = McpServerConfig(name="test", command="echo", env={"PATH": "/usr/bin", "HOME": "/root"})
        assert cfg.env["PATH"] == "/usr/bin"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Plain string for API keys | `SecretStr` wrapping | Pydantic v2 (2023) | repr/str/log auto-redaction |
| Manual `if` validation in `__init__` | `@field_validator` | Pydantic v2 (2023) | Declarative, auto-run on instantiation |
| Manual `..` path checking | `Path.resolve()` + `is_relative_to()` | Python 3.9+ | Handles symlinks, edge cases |

**Deprecated/outdated:**
- `@validator` (Pydantic v1): Replaced by `@field_validator` in v2. Not used in this codebase.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Blacklist keywords `api_key, token, secret, password, credential, private_key, access_key, auth` are sufficient coverage | MCP env blacklist | False positives block legitimate vars; false negatives miss sensitive vars |
| A2 | `SecretStr` does not need to be persisted (providers are reconstructed each session) | SecretStr migration | If providers are serialized/deserialized, SecretStr handling needs extra care |
| A3 | The `_make_provider` helper is the only test code that directly sets `_api_key` | SecretStr migration | Other test files may also set it and break |

**Risk mitigation for A1:** The keyword list is Claude's discretion per CONTEXT.md. Planner can expand/reduce. The `auth` pattern is the most aggressive -- could match `AUTH_TYPE=simple` which is not sensitive. Consider removing `auth` or using exact suffix matching.

## Open Questions

1. **Blacklist keyword `auth` is potentially too broad**
   - What we know: "auth" as a substring appears in many non-sensitive env vars (`AUTH_TYPE`, `AUTH_MECHANISM`, `SQL_AUTH_TYPE`)
   - What's unclear: Whether the codebase or its users commonly use such env vars
   - Recommendation: Keep `auth` out of the initial blacklist, or use more specific patterns like `_auth` (with underscore prefix/suffix)

2. **Should `_BLOCKED_ENV_PATTERNS` be configurable?**
   - What we know: Hardcoded patterns are simpler but inflexible
   - What's unclear: Whether users need to override the blacklist
   - Recommendation: Hardcoded for this phase; note in SECURITY-REVIEW.md as future improvement

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11+ | Framework runtime | Yes | 3.11.14 | -- |
| pytest | Test execution | Yes | 9.0.3 | -- |
| pydantic v2 | SecretStr, field_validator | Yes | 2.12.5 | -- |
| uv | Package installation | Yes | 0.9.24 | -- |

**Missing dependencies with no fallback:** None

**Missing dependencies with fallback:** None

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 + pytest-asyncio |
| Config file | None (conftest.py only) |
| Quick run command | `cd framework && pytest tests/test_builtin_tools.py tests/test_mcp_manager.py tests/test_providers.py tests/test_boundary.py -v` |
| Full suite command | `cd framework && pytest tests/ -v --timeout=60` |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SEC-01 | Path traversal rejected in read_file | unit | `cd framework && pytest tests/test_builtin_tools.py::TestPathSandbox -v` | Wave 0 (new class in existing file) |
| SEC-01 | Path traversal rejected in write_file | unit | `cd framework && pytest tests/test_builtin_tools.py::TestPathSandbox -v` | Wave 0 (new class in existing file) |
| SEC-01 | Absolute path rejected | unit | `cd framework && pytest tests/test_builtin_tools.py::TestPathSandbox -v` | Wave 0 |
| SEC-02 | MCP config rejects sensitive env keys | unit | `cd framework && pytest tests/test_mcp_manager.py::TestMcpEnvBlacklist -v` | Wave 0 (new class in existing file) |
| SEC-02 | MCP config accepts normal env keys | unit | `cd framework && pytest tests/test_mcp_manager.py::TestMcpEnvBlacklist -v` | Wave 0 |
| SEC-03 | Provider _api_key is SecretStr | unit | `cd framework && pytest tests/test_providers.py -v` | Wave 0 (modify existing) |
| SEC-03 | Provider repr masks key | unit | `cd framework && pytest tests/test_providers.py -v` | Wave 0 (new test) |
| SEC-07 | SECURITY-REVIEW.md exists | manual | `test -f docs/reviews/SECURITY-REVIEW.md` | Wave 0 (new file) |

### Sampling Rate
- **Per task commit:** `cd framework && pytest tests/test_<affected>.py -v`
- **Per wave merge:** `cd framework && pytest tests/ -v --timeout=60`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `TestPathSandbox` class in `framework/tests/test_builtin_tools.py` -- covers SEC-01
- [ ] `TestMcpEnvBlacklist` class in `framework/tests/test_mcp_manager.py` -- covers SEC-02
- [ ] `test_api_key_is_secret_str` and `test_api_key_repr_masks` in `framework/tests/test_providers.py` -- covers SEC-03
- [ ] Update `_make_provider` helper in `framework/tests/test_providers.py` -- must wrap `SecretStr`
- [ ] `docs/reviews/SECURITY-REVIEW.md` -- covers SEC-07

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Not in scope (no user auth) |
| V3 Session Management | no | Not in scope |
| V4 Access Control | yes | Path sandbox via `safe_path()` -- restricts file access to working directory |
| V5 Input Validation | yes | `field_validator` for MCP env keys; `safe_path()` for file paths |
| V6 Cryptography | no | No cryptographic operations in this phase |
| V8 Data Protection | yes | `SecretStr` for API key protection against logging/serialization leaks |

### Known Threat Patterns for Agent Framework

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal via `../../` in file tools | Tampering | `safe_path()` with `resolve()` + `is_relative_to()` |
| Env var injection via MCP config | Elevation of Privilege | Blacklist sensitive keyword patterns at config validation |
| API key leakage via logging/repr | Information Disclosure | `pydantic.SecretStr` auto-redaction |
| Arbitrary command execution via hooks | Elevation of Privilege | `trusted` flag gates execution; documentation of trust model |
| Permission bypass via ASK not wired | Elevation of Privilege | Documented gap, future HITL integration |

## Sources

### Primary (HIGH confidence)
- Codebase source files: `file_tools.py`, `boundary.py`, `config.py`, `transport.py`, `openai_provider.py`, `anthropic_provider.py`, `deepseek_provider.py`, `router.py`, `hooks/manager.py`, `hitl.py`, `bus.py` -- all read and analyzed in this session
- `CONCERNS.md` -- 6 security issues documented with file locations and impact analysis
- `test_boundary.py`, `test_builtin_tools.py`, `test_mcp_manager.py`, `test_providers.py`, `test_hook_manager.py`, `test_permissions.py` -- existing test patterns verified

### Secondary (MEDIUM confidence)
- [Pydantic SecretStr docs](https://docs.pydantic.dev/latest/concepts/types/#secret-types) -- SecretStr API behavior
- [Pydantic field_validator docs](https://docs.pydantic.dev/latest/concepts/validators/) -- validator pattern for MCP config

### Tertiary (LOW confidence)
- [OWASP Secure Coding Practices](https://owasp.org/www-project-secure-coding-practices-quick-reference-guide/) -- general security guidance for blacklist approach
- [CyberArk: Environment Variables Don't Keep Secrets](https://developer.cyberark.com/blog/environment-variables-dont-keep-secrets-best-practices-for-plugging-application-credential-leaks/) -- env var security best practices

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all dependencies already installed, verified versions
- Architecture: HIGH - all source files read, integration points identified precisely
- Pitfalls: HIGH - pitfalls discovered through direct code analysis (SecretStr f-string behavior, _make_provider test helper)
- Security patterns: HIGH - verified with local Python execution (SecretStr behavior, field_validator)

**Research date:** 2026-05-28
**Valid until:** 2026-06-28 (stable -- no fast-moving dependencies)
