# Coding Conventions

**Analysis Date:** 2026-05-28

## Naming Patterns

**Files:**
- Python modules: `snake_case.py` (e.g., `agent_loop.py`, `tool_registry.py`)
- Test files: `test_{module_name}.py` (e.g., `test_agent_loop.py`, `test_tool_registry.py`)
- Private/implementation modules: leading underscore (e.g., `_anthropic.py`, `_openai.py`, `_normalize.py` in `llm/transform/`)
- TypeScript: `PascalCase.tsx` for components (`App.tsx`), `camelCase.ts` for utilities (`api.ts`, `utils.ts`)

**Classes:**
- `PascalCase` for all classes (e.g., `AgentLoop`, `ToolRegistry`, `ResilientLLMAdapter`)
- Interface classes use `I` prefix (e.g., `ILLMAdapter`)
- Error classes use `Error` suffix (e.g., `LLMAdapterError`, `RateLimitError`)
- Type-only data classes: `PascalCase` with descriptive noun (e.g., `PlanItem`, `PlanSnapshot`, `TeammateConfig`)

**Functions:**
- `snake_case` for all functions (e.g., `parse_plan_response`, `strip_plan_tags`, `handle_http_error`)
- Private helpers: leading underscore (e.g., `_calculate_delay`, `_make_mock_adapter`, `_serialize_content`)
- Factory functions: `create_` prefix (e.g., `create_adapter`, `create_builtin_registry`, `create_load_skill_spec`)
- Test helpers: `_` prefix convention (e.g., `_make_spec`, `_make_loop`, `_text_result`)

**Variables:**
- `snake_case` for all variables (e.g., `planning_state`, `tool_calls`, `breakers`)
- Private instance attributes: `_` prefix (e.g., `self._messages`, `self._breaker`, `self._compact_failures`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `_PROVIDER_MAP`, `_VALID_TRANSITIONS`, `_CRITICAL_TOOLS`)

**Types:**
- Pydantic models: `PascalCase` with descriptive noun (e.g., `TextBlock`, `CompletionConfig`, `ToolSpec`)
- Enums: `PascalCase` for enum class, `UPPER_SNAKE_CASE` for members (e.g., `StopReason.END_TURN`, `CircuitState.HALF_OPEN`)
- Type aliases: `PascalCase` (e.g., `ContentBlock = Union[...]`, `Message = Union[...]`, `ToolHandler = Callable[...]`)

## Import Organization

**Order (observed across the codebase):**
1. `from __future__ import annotations` (always first when present)
2. Standard library imports (`asyncio`, `json`, `logging`, `re`, `time`, etc.)
3. Third-party imports (`pytest`, `httpx`, `pydantic`, `unittest.mock`)
4. Framework-internal imports using full path (`from agent_framework.llm.types import ...`)

**Internal import style:**
```python
from agent_framework.llm.types import (
    CompletionConfig,
    CompletionResult,
    StopReason,
    TextBlock,
)
```
- Always use absolute imports from the `agent_framework` package root
- Never use relative imports (`from .types import ...`) in production code; relative imports appear only in `__init__.py` barrel files
- Group related imports from the same module into a single `from` statement
- For test files: import from `conftest` and `tests.helpers` directly (`from conftest import MockAdapter`)

**TYPE_CHECKING guard:**
```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agent_framework.hooks.manager import HookManager
    from agent_framework.tasks.runner import TaskRunner
```
Used in `agent_framework/agents/agent_loop.py`, `agent_framework/tools/router.py`, `agent_framework/teams/manager.py`, `agent_framework/prompts/assembler.py` to avoid circular imports.

## Type Annotation Usage

**`from __future__ import annotations`:** Present in 62 of 83 source files (~75%). Used universally to enable PEP 604 union syntax (`str | None` instead of `Optional[str]`).

**Pydantic BaseModel:** Used for LLM types and network-facing data structures in:
- `framework/agent_framework/llm/types.py` (all message/block/config/result types)
- `framework/agent_framework/tools/types.py` (`ToolCall`, `ToolResult`, `ToolSpec`, `ToolUseContext`)
- `framework/agent_framework/memory/types.py` (`SemanticMemoryDraft`)
- `framework/agent_framework/prompts/profiles.py` (`AgentProfile`, `PromptBlock`)
- `framework/agent_framework/safety/boundary.py`, `safety/verification.py`, `safety/hitl.py`

**`dataclass`:** Used for internal domain models:
- `frozen=True` for immutable value objects in `teams/types.py`, `hooks/types.py`, `tasks/types.py`, `commands/types.py`, `skills/manifest.py`, `llm/retry.py`
- Mutable dataclasses for stateful objects: `PlanningState`, `RuntimeTask`, `CircuitBreaker`, `LoopEvent`

**Convention:** Use Pydantic `BaseModel` for data that crosses module boundaries or needs serialization. Use `@dataclass(frozen=True)` for internal immutable value objects. Use mutable `@dataclass` for stateful domain objects.

**Return type annotations:** All public methods have explicit return type annotations. All function signatures use type hints. Private methods also annotated.

## Error Handling

**Strategy:** Typed exception hierarchy with structured error metadata.

**Exception hierarchy** (defined in `framework/agent_framework/llm/base.py`):
```python
LLMAdapterError          # base: message, provider, status_code, retryable
  -> RateLimitError      # 429: auto retryable=True
  -> ServiceUnavailableError  # 5xx: retryable=True
  -> InvalidRequestError     # 400: retryable=False
  -> CircuitOpenError        # breaker: retryable=False
```

**Patterns:**
- HTTP error mapping via `handle_http_error(response, provider)` in `framework/agent_framework/llm/base.py:173` -- converts status codes to typed exceptions
- Tool execution wrapping: `ToolExecutor.execute()` in `framework/agent_framework/tools/executor.py:20` catches all exceptions and returns `ToolResult(is_error=True)` instead of raising
- Retry logic in `framework/agent_framework/llm/retry.py:97` uses `retry_with_backoff()` that checks `error.retryable` flag
- Agent loop error events: `AgentLoop.run()` yields `LoopEvent(type="error", ...)` rather than propagating exceptions to the caller
- Validation errors: `ValueError` with descriptive messages for domain validation (e.g., duplicate tool registration, invalid plan transitions)

**Anti-patterns observed:** None significant. Error handling is consistently structured.

## Configuration Patterns

**Pydantic models for config:**
- `RetryConfig(frozen=True)` in `framework/agent_framework/llm/retry.py:43` -- dataclass with sensible defaults
- `CircuitBreakerConfig` in `framework/agent_framework/llm/retry.py:165`
- `CompactConfig` in `framework/agent_framework/tools/context/compactor.py`
- `McpServerConfig(BaseModel)` in `framework/agent_framework/tools/mcp/config.py:20`
- `AgentProfile(BaseModel)` in `framework/agent_framework/prompts/profiles.py:21`

**Convention:** Configuration objects use immutable dataclasses or Pydantic models with default values. Constructor parameters accept config objects rather than individual values.

**Factory pattern:** `create_adapter()` in `framework/agent_framework/llm/resilient.py:153` creates configured `ResilientLLMAdapter` instances with provider-specific setup.

**No environment variable loading in framework layer.** Environment configuration is handled at the application layer (`backend/`).

## Logging

**Framework:** Python stdlib `logging`

**Pattern:**
```python
import logging
logger = logging.getLogger(__name__)
```
Used in: `llm/retry.py`, `llm/resilient.py`, `llm/providers/*.py`, `tools/router.py`, `tools/mcp/*.py`, `tasks/runner.py`, `tasks/manager.py`

**Usage:** `logger.warning(...)` for retries and circuit breaker events. No `logger.info` or `logger.debug` observed in current codebase.

## Module Organization

**Every module has a docstring** -- a one-line Chinese description of the module's purpose:
```python
"""工具注册表 — name -> ToolSpec 的 dispatch map。"""
"""LLM Adapter 抽象基类。"""
"""Session Planning — 数据模型、状态管理、内联解析。"""
```

**Barrel files (`__init__.py`):** Major modules export their public API via `__init__.py` with explicit `__all__` lists:
- `framework/agent_framework/llm/__init__.py` (82 lines, full re-exports)
- `framework/agent_framework/tools/__init__.py` (29 lines)
- `framework/agent_framework/memory/__init__.py` (37 lines)
- `framework/agent_framework/safety/__init__.py` (37 lines)

Smaller modules leave `__init__.py` empty (e.g., `agents/`, `orchestrator/`, `prompts/`).

**File size guideline:** Most source files are 100-300 lines. Largest file is `agent_loop.py` at 406 lines. Files exceeding 300 lines are usually provider implementations that must handle full API specs.

## Code Style

**Python (framework):**
- No ruff, mypy, or flake8 configuration detected
- No enforced formatting tool configuration
- Code follows PEP 8 conventions consistently despite no linter config
- Indentation: 4 spaces
- Max line length: approximately 100-110 characters (not strictly enforced)
- Trailing commas in multi-line collections
- Double quotes for strings (inconsistent -- some single quotes in tests)

**TypeScript (frontend):**
- ESLint configured in `frontend/eslint.config.js` with typescript-eslint, react-hooks, and react-refresh plugins
- TypeScript strict: `noUnusedLocals`, `noUnusedParameters`, `noFallthroughCasesInSwitch` enabled in `frontend/tsconfig.app.json`
- Module system: ESM (`"type": "module"` in package.json, `"verbatimModuleSyntax": true`)
- Build: Vite + TypeScript (`tsc -b && vite build`)

**Docstrings:**
- Modules: one-line Chinese docstring at top of every file
- Classes: one-line Chinese docstring or multi-line with `"""..."""` for complex types
- Methods: brief Chinese docstrings for public methods, Google-style `Args:`/`Returns:`/`Raises:` for abstract methods (see `ILLMAdapter` in `framework/agent_framework/llm/base.py`)

## Immutability Patterns

**`@dataclass(frozen=True)`** used for all value-type dataclasses:
- `TeammateConfig`, `TeamMessage`, `TeamNotification` in `framework/agent_framework/teams/types.py`
- `HookConfig`, `HookContext`, `HookResult` in `framework/agent_framework/hooks/types.py`
- `Task` in `framework/agent_framework/tasks/types.py`
- `RetryConfig` in `framework/agent_framework/llm/retry.py`
- `SkillManifest`, `SkillMeta` in `framework/agent_framework/skills/manifest.py`
- `CommandSpec`, `CommandRouterConfig` in `framework/agent_framework/commands/types.py`

**Pydantic models** are mutable by default but used as immutable DTOs (created once, not modified after construction).

**Convention:** Value objects and configuration objects must be `frozen=True`. Stateful objects (circuit breaker, planning state) use mutable dataclasses.

## Code Section Markers

Modules use `# ============================================================` comment blocks to separate sections:
```python
# ============================================================
# Content Block types
# ============================================================

# ============================================================
# Message types
# ============================================================
```
This pattern appears in `llm/types.py`, `llm/base.py`, `llm/retry.py`, `test_providers.py`, and other files with multiple distinct sections.

## Test Conventions (brief)

- Test files import helpers via `from conftest import MockAdapter` (pythonpath includes tests/)
- Test file naming: `test_{module_name}.py` -- one test file per source module
- Test class naming: `Test{Feature}` for grouped tests (e.g., `TestHandleHttpError`, `TestToolRegistry`)
- Standalone test functions: `test_{behavior_description}` (e.g., `test_direct_answer`, `test_register_and_get`)
- Async tests: `@pytest.mark.asyncio` decorator (156 of 630 tests)
- Chinese docstrings for test descriptions: `"""用真实的 read_file tool 执行。"""`
- See `TESTING.md` for full testing conventions

---

*Convention analysis: 2026-05-28*
