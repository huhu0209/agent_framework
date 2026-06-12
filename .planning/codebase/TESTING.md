# Testing Patterns

**Analysis Date:** 2026-05-28

## Test Framework

**Runner:**
- pytest >= 8.0.0
- pytest-asyncio >= 0.24.0
- Config: `framework/pyproject.toml` -> `[tool.pytest.ini_options]`

**Configuration:**
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
pythonpath = ["tests"]
```
- `asyncio_mode = "auto"`: all `async def test_*` functions are automatically treated as async tests without needing explicit `@pytest.mark.asyncio` (though many tests still include the decorator)
- `pythonpath = ["tests"]`: allows direct imports like `from conftest import MockAdapter` and `from tests.helpers import create_skill`

**Assertion Library:**
- Plain `assert` statements (no assertpy or similar)
- `pytest.raises` for exception testing

**Run Commands:**
```bash
cd framework && pytest tests/ -v                # Run all tests
cd framework && pytest tests/test_agent_loop.py -v  # Single file
cd framework && pytest tests/ -k "test_direct"  # By name pattern
```

## Test File Organization

**Location:**
- Co-located in `framework/tests/` directory (separate from source)
- Source code lives in `framework/agent_framework/`
- One test file per source module (nearly 1:1 mapping)

**Naming:**
- Test files: `test_{module_name}.py` (e.g., `test_agent_loop.py` for `agent_loop.py`)
- Test functions: `test_{behavior_description}` (e.g., `test_direct_answer`, `test_register_and_get`)
- Test classes: `Test{Feature}` (e.g., `TestHandleHttpError`, `TestToolRegistry`, `TestCircuitBreakerState`)

**Statistics:**
- 57 test files
- 630 test functions
- 156 async tests (~25% of all tests)

**Structure:**
```
framework/tests/
    __init__.py
    conftest.py           # Shared fixtures: MockAdapter, memory_dir
    helpers.py            # Shared helpers: create_skill()
    test_agent_loop.py    # ~671 lines, 24 tests
    test_providers.py     # ~703 lines, 33 tests
    test_transform.py     # ~638 lines, ~30 tests
    test_resilient.py     # ~503 lines, ~20 tests
    test_tool_router.py   # ~508 lines
    ... (53 more test files)
```

## Test Structure

**Suite Organization:**
Two patterns are used. For simple test suites, standalone test functions:

```python
"""ToolRegistry tests."""

import pytest
from agent_framework.tools.registry import ToolRegistry
from agent_framework.tools.types import ToolResult, ToolSpec

async def _fake_handler(args, ctx):
    return ToolResult(content="ok")

def test_register_and_get():
    registry = ToolRegistry()
    spec = _make_spec("read_file")
    registry.register(spec)
    assert registry.get("read_file") is spec
```

For grouped/related tests, class-based organization:

```python
class TestHandleHttpError:
    """HTTP error code to typed LLM exception mapping."""

    def test_429_raises_rate_limit_error(self) -> None:
        resp = _make_httpx_response(429, json_body={"error": {"message": "Too many requests"}})
        with pytest.raises(RateLimitError) as exc_info:
            handle_http_error(resp, "openai")
        assert exc_info.value.provider == "openai"

    def test_500_raises_service_unavailable(self) -> None:
        ...
```

**Pattern observed:**
- Type-only tests (e.g., `test_teams_types.py`) use standalone functions
- Behavior/feature tests use `class Test{Feature}` with method-per-scenario
- Integration tests with complex setup use standalone functions with helper factories

## Mocking

**Framework:** `unittest.mock` (stdlib)

**Patterns:**

Mock adapter creation (most common pattern across test suite):
```python
from unittest.mock import AsyncMock

def _make_mock_adapter() -> AsyncMock:
    adapter = AsyncMock(spec=ILLMAdapter)
    adapter.get_provider_info.return_value = ProviderInfo(
        name="mock", base_url="https://mock", default_model="mock-model",
    )
    return adapter
```

Mock HTTP responses for provider tests:
```python
def _make_httpx_response(status_code: int, json_body: dict | None = None, text: str = "") -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.headers = {}
    if json_body is not None:
        resp.json.return_value = json_body
    else:
        resp.json.side_effect = Exception("not json")
        resp.text = text
    return resp
```

Side-effect sequences for multi-step flows:
```python
adapter.complete.side_effect = [
    _tool_use_result(_make_tool("read_file", path="a.txt")),
    _text_result("answer"),
]
```

`monkeypatch` for environment/module patching (rare):
```python
async def test_fire_subprocess_error_returns_blocked(monkeypatch):
    monkeypatch.setattr(asyncio, "create_subprocess_exec", _fail)
```

**What to Mock:**
- LLM adapters: Always mock with `AsyncMock(spec=ILLMAdapter)` -- never call real APIs
- HTTP clients: Mock `httpx.Response` for provider tests
- File system: Use `tmp_path` pytest fixture for real filesystem operations (not mock)

**What NOT to Mock:**
- Tool execution: Tests use real `ToolRouter`, `ToolRegistry`, and builtin tools (`create_builtin_registry()`)
- File operations: Tests write to `tmp_path` and read back (e.g., `test_single_tool_call_read_file`)
- Pydantic models: Construct real instances, never mock data models

## Fixtures

**Shared fixtures in `framework/tests/conftest.py`:**

```python
class MockAdapter:
    """Minimal mock LLM adapter that returns preset text."""
    def __init__(self, response_text: str) -> None:
        self._response = response_text

    async def complete(self, config: CompletionConfig) -> CompletionResult:
        return CompletionResult(
            id="test-id", model=config.model,
            content=[TextBlock(text=self._response)],
            stop_reason=StopReason.END_TURN,
            usage=UsageStats(input_tokens=100, output_tokens=50),
        )

@pytest.fixture
def memory_dir(tmp_path):
    d = tmp_path / "memory"
    d.mkdir()
    return d
```

**File-scoped fixtures (21 total across test files):**

Typical pattern -- fixtures defined in the test file that uses them:
```python
# test_resilient.py
@pytest.fixture
def mock_config() -> CompletionConfig:
    return CompletionConfig(model="mock-model", messages=[])

@pytest.fixture
def mock_result() -> CompletionResult:
    return CompletionResult(id="test-id", content=[], model="mock-model", ...)
```

```python
# test_task_manager.py
@pytest.fixture
def task_dir(tmp_path):
    return tmp_path / "tasks"
```

**Convention:** Define fixtures in the test file that uses them, not in `conftest.py`, unless shared across multiple test files. Only `MockAdapter` and `memory_dir` are shared via conftest.

## Test Helpers

**`framework/tests/helpers.py`:**
```python
def create_skill(
    skills_dir: Path,
    name: str,
    description: str,
    body: str = "",
    **meta_extra: str,
) -> Path:
    """Create a SKILL.md file in skills_dir/name/."""
    ...
```

Used by `test_skills_registry.py` and `test_command_router.py`.

**Inline helper factories (common pattern):**

Most test files define private factory functions at module level:
```python
def _make_spec(name: str = "test_tool", **kwargs) -> ToolSpec: ...
def _make_mock_adapter() -> AsyncMock: ...
def _text_result(text: str, stop_reason=StopReason.END_TURN) -> CompletionResult: ...
def _tool_use_result(*tool_calls: ToolUseBlock) -> CompletionResult: ...
def _make_loop(adapter, **kwargs) -> AgentLoop: ...
async def _collect_events(loop: AgentLoop, message: str) -> list[LoopEvent]: ...
```

**Convention:** Use `_` prefix for test helper functions. Group helpers at the top of the test file, after imports, before test classes/functions.

## Parametrize

**Usage:** Minimal -- only 2 parametrized tests found:
```python
# test_skills_manifest.py
@pytest.mark.parametrize("value", ["true", "True", "TRUE", "yes", "1"])
def test_meta_bool_true(self, value): ...

@pytest.mark.parametrize("value", ["false", "False", "no", "0"])
def test_meta_bool_false(self, value): ...
```

**Convention:** Prefer explicit test functions over parametrize for most cases. Parametrize only for data-driven variations of the same assertion.

## Coverage

**Requirements:** No coverage threshold enforced in config. No `pytest-cov` dependency configured.

**Coverage configuration:** Not configured. No `[tool.coverage]` or `.coveragerc` found.

**Test-to-source ratio:** 57 test files covering ~60 source modules (~95% module coverage). 630 test functions for ~7600 lines of source code.

## Test Types

**Unit Tests (majority):**
- Scope: Individual functions, classes, data models
- Approach: Mock external dependencies, test logic in isolation
- Examples: `test_tool_registry.py`, `test_teams_types.py`, `test_task_types.py`, `test_resilient.py`
- Pattern: construct inputs -> call function -> assert outputs/raises

**Integration Tests (significant):**
- Scope: Multi-component interactions (agent loop + tool system + LLM adapter)
- Approach: Mock only the LLM adapter, use real tool execution and routing
- Examples: `test_agent_loop.py` (real `ToolRouter` + real builtin tools + mock adapter), `test_providers.py` (mock HTTP, real parsing pipeline)
- Pattern: set up mock adapter with side_effect sequence -> run loop -> collect events -> assert event sequence

**End-to-End Tests:**
- Not present in current test suite
- No Playwright or similar framework configured

## Common Patterns

**Async Testing:**
```python
@pytest.mark.asyncio
async def test_complete_success(mock_config, mock_result):
    provider = _make_mock_provider()
    provider.complete.return_value = mock_result
    adapter = ResilientLLMAdapter(provider=provider)
    result = await adapter.complete(mock_config)
    assert result == mock_result
```

**Error Testing:**
```python
def test_register_duplicate_raises():
    registry = ToolRegistry()
    registry.register(_make_spec("dup"))
    with pytest.raises(ValueError, match="already registered"):
        registry.register(_make_spec("dup"))
```

**Multi-step Flow Testing (agent loop):**
```python
@pytest.mark.asyncio
async def test_write_then_read(tmp_path):
    adapter = _make_mock_adapter()
    adapter.complete.side_effect = [
        _tool_use_result(_make_tool("write_file", path="output.txt", content="written content")),
        _tool_use_result(_make_tool("read_file", path="output.txt")),
        _text_result("answer"),
    ]
    registry = create_builtin_registry()
    router = ToolRouter(registry)
    ctx = ToolUseContext(working_dir=str(tmp_path))
    loop = AgentLoop(adapter, model="mock", router=router, ctx=ctx)
    events = await _collect_events(loop, "write and read file")

    tool_events = [e for e in events if e.type == "tool_result"]
    assert len(tool_events) == 2
    assert "written content" in tool_events[1].data["tool_results"][0]
```

**Async Generator Collection:**
```python
async def _collect_events(loop: AgentLoop, message: str) -> list[LoopEvent]:
    return [event async for event in loop.run(message)]
```

**Filesystem Testing with tmp_path:**
```python
def test_send_and_read(tmp_path):
    bus = MessageBus(tmp_path)
    bus.send("alice", "hello")
    messages = bus.read_inbox("alice")
    assert len(messages) == 1
```

## Adding New Tests

**For a new module `framework/agent_framework/foo/bar.py`:**
1. Create `framework/tests/test_bar.py`
2. Add module docstring: `"""Bar tests."""`
3. Import from `agent_framework.foo.bar`
4. For async tests: use `@pytest.mark.asyncio` decorator
5. For filesystem tests: use `tmp_path` fixture parameter
6. For LLM-dependent tests: mock adapter via `AsyncMock(spec=ILLMAdapter)` or `conftest.MockAdapter`
7. Run: `cd framework && pytest tests/test_bar.py -v`

**For a new test in an existing file:**
1. Follow existing pattern (class-based or standalone function)
2. Use same helper functions defined at module top
3. Chinese docstring for test description

---

*Testing analysis: 2026-05-28*
