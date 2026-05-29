# Phase 7: 编排引擎 + 配置化 + 搜索 — Plan

## Overview

Phase 7 adds three capabilities to the framework: (1) OrchestratorEngine that evaluates task complexity and routes to the appropriate Agent type, (2) declarative Agent configuration via `.md` files, and (3) real Tavily API search replacing the mock handler.

**Execution order:** 07-01 and 07-02 are sequential (07-02 uses patterns from 07-01). 07-03 is fully independent and can run in parallel with either.

**Requirements covered:** ORCH-01~05, CONF-01~04, SRCH-01~03

---

## Plan 07-01: OrchestratorEngine 编排引擎（ORCH-01~05）

### Requirements
- ORCH-01: OrchestratorEngine implements complexity assessment -> Agent selection -> execution -> correction/replan pipeline
- ORCH-02: Complexity assessment uses heuristic rules (no extra LLM call)
- ORCH-03: Simple tasks route directly to AgentLoop, complex tasks generate plan then execute
- ORCH-04: Execution drift triggers plan correction, max 3 Agents per chain
- ORCH-05: agent_factory pattern, creates new Agent instance per step

### Key Decisions
- **D-01:** Pure character count threshold (default 200), `_complexity_threshold` configurable. Single if statement.
- **D-02:** Complex tasks delegate to `PlanAndSolveAgent.run()`. Simple tasks create `AgentLoop` directly.
- **D-03:** agent_factory method creates top-level Agent instances. Factory receives config (adapter, router, ctx, etc.) and creates `PlanAndSolveAgent` (complex) or `AgentLoop` (simple).
- **D-04:** Drift detection relies entirely on `PlanAndSolveAgent` internal replan logic (max 2). "Max 3 Agents" is OrchestratorEngine-level creation cap.

### Files to Create/Modify

| File | Action |
|------|--------|
| `framework/agent_framework/orchestrator/engine.py` | Rewrite from scaffold to full implementation |
| `framework/agent_framework/orchestrator/__init__.py` | Add exports |
| `framework/tests/test_orchestrator_engine.py` | New test file |

### Tasks

#### Task 1: Implement OrchestratorEngine

**File:** `framework/agent_framework/orchestrator/engine.py`

**Implement:**

1. `OrchestratorEngine` class that implements the `Agent` ABC (consistent with framework pattern: AgentLoop, PlanAndSolveAgent, ReflectionAgent all implement Agent). Has `run() -> AsyncGenerator[AgentEvent, None]`.

2. `__init__` parameters:
   - `adapter: ILLMAdapter`
   - `model: str`
   - `router: ToolRouter`
   - `ctx: ToolUseContext`
   - `complexity_threshold: int = 200` (per D-01)
   - `max_steps_per_plan_item: int = 10`
   - `max_replans: int = 2`
   - Internal state: `_agent_count: int = 0` (per D-04, ORCH-04 max 3 Agents per chain)

3. `_assess_complexity(task: str) -> Literal["simple", "complex"]` (per D-01, ORCH-02) — single if statement: `return "complex" if len(task) > self._complexity_threshold else "simple"`. No keywords, no multi-signal, no LLM call.

4. `_create_agent(task: str) -> Agent` (per D-03, ORCH-05) — factory method:
   - Calls `_assess_complexity(task)`
   - Complex: creates `PlanAndSolveAgent(adapter=self.adapter, model=self.model, router=self.router, ctx=self.ctx, max_steps_per_plan_item=self.max_steps_per_plan_item, max_replans=self.max_replans)`
   - Simple: creates `AgentLoop(adapter=self.adapter, model=self.model, router=self.router, ctx=self.ctx, max_steps=self.max_steps_per_plan_item)`
   - Increments `_agent_count` after creation
   - If `_agent_count > 3`: yields error event and returns (per D-04)

5. `run(user_message: str) -> AsyncGenerator[AgentEvent, None]` (per ORCH-01, ORCH-03):
   - Assess complexity, yield `AgentEvent(type="step", step=0, data={"complexity": result, "task_length": len(user_message)})`
   - If `_agent_count >= 3`: yield `AgentEvent(type="error", step=0, data={"error": "Agent 实例数已达上限 3"})` and return (per ORCH-04)
   - Create agent via `_create_agent(user_message)`
   - Forward all events from the created agent's `run()`, renumbering `step` offset by 1
   - On completion, yield final events as-is

6. Imports: `Agent`, `AgentEvent` from `agents.base`, `AgentLoop` from `agents.agent_loop`, `PlanAndSolveAgent` from `agents.plan_and_solve`, `ILLMAdapter` from `llm.base`, `ToolRouter` from `tools.router`, `ToolUseContext` from `tools.types`, `Literal` from `typing`.

**File:** `framework/agent_framework/orchestrator/__init__.py`

Update exports to include `OrchestratorEngine`.

**Verify:**
```bash
cd /Users/huhu/project/agent_framework/framework && python -c "from agent_framework.orchestrator.engine import OrchestratorEngine; print('Import OK')"
```

#### Task 2: Write OrchestratorEngine Tests

**File:** `framework/tests/test_orchestrator_engine.py`

**Test cases:**

1. `test_assess_complexity_simple` — task under 200 chars returns "simple"
2. `test_assess_complexity_complex` — task over 200 chars returns "complex"
3. `test_assess_complexity_threshold_configurable` — custom threshold respected
4. `test_simple_task_routes_to_agent_loop` — mock adapter, short task (under 200 chars), verify AgentLoop events flow through (yielding "done" event)
5. `test_complex_task_routes_to_plan_and_solve` — mock adapter returning a `<plan>...</plan>` response, long task (over 200 chars), verify PlanAndSolveAgent events flow through
6. `test_agent_count_limit_at_three` — call `run()` 3 times (each increments `_agent_count`), verify 4th call yields error event with "上限" message
7. `test_implements_agent_abc` — `assert issubclass(OrchestratorEngine, Agent)`

Use existing test helpers from `test_plan_and_solve.py` as reference for mock adapter construction: `_make_mock_adapter_with_plan`, `_make_mock_adapter_with_text` with `AsyncMock(spec=ILLMAdapter)`.

**Verify:**
```bash
cd /Users/huhu/project/agent_framework/framework && pytest tests/test_orchestrator_engine.py -v
```

#### Task 3: Verify Zero Regression

**Action:** Run full test suite to confirm no regressions from OrchestratorEngine addition.

**Verify:**
```bash
cd /Users/huhu/project/agent_framework/framework && pytest tests/ -v --tb=short
```

All existing tests must pass (687+ tests).

### Dependencies
- Task 1 -> Task 2 -> Task 3 (sequential)

---

## Plan 07-02: Agent 配置化（CONF-01~04）

### Requirements
- CONF-01: AgentConfig dataclass parsed from .md files (name, description, system_prompt, tools, model, max_steps)
- CONF-02: `load_agent_configs()` scans directory, parses all .md files, reuses `parse_frontmatter()` pattern
- CONF-03: `agent_from_config()` creates AgentLoop instance from AgentConfig with tool filtering
- CONF-04: Validate system_prompt safety (non-empty check)

### Key Decisions
- **D-05:** .md config structure: frontmatter for metadata (name, description, model, max_steps, tools), body for system_prompt. Reuse `parse_frontmatter()`.
- **D-06:** `tools` field is a comma-separated name list matching `ToolRegistry.register()` name field.
- **D-07:** system_prompt validation (CONF-04) is non-empty check only. Trust config file authors.

### Files to Create/Modify

| File | Action |
|------|--------|
| `framework/agent_framework/agents/config.py` | New file — AgentConfig, parse_agent_config(), load_agent_configs(), agent_from_config() |
| `framework/agent_framework/agents/__init__.py` | Add exports |
| `framework/tests/test_agent_config.py` | New test file |
| `framework/tests/fixtures/agents/` | Test fixture directory with sample .md files |

### Tasks

#### Task 1: Implement Agent Config System

**File:** `framework/agent_framework/agents/config.py`

**Implement:**

1. `AgentConfig` dataclass (per D-05, CONF-01):
   - `name: str` — required
   - `system_prompt: str` — required
   - `description: str = ""`
   - `model: str = "claude-sonnet-4-6-20250514"`
   - `max_steps: int = 10`
   - `tools: list[str] | None = None` — None means all tools

2. Helper `_extract_body(text: str) -> str`:
   - Split on `---`, the body is everything after the second `---` separator
   - Strip leading/trailing whitespace
   - Return the body text

3. `parse_agent_config(text: str, filename: str = "<unknown>") -> AgentConfig` (per CONF-01):
   - Call `parse_frontmatter(text)` from `memory/frontmatter.py` to get metadata dict
   - Extract `name` (required, raise `ValueError` if missing)
   - Extract `model` (str, default "claude-sonnet-4-6-20250514")
   - Extract `max_steps` (int via `int()`, default 10)
   - Extract `description` (str, default "")
   - Extract `tools` (comma-separated string -> `list[str]` if present and non-empty, else `None`)
   - Call `_extract_body(text)` for `system_prompt` (per D-07, CONF-04: raise `ValueError` if empty)
   - Return `AgentConfig(...)`

4. `load_agent_configs(directory: Path) -> dict[str, AgentConfig]` (per CONF-02):
   - `directory.glob("*.md")` to find all .md files
   - For each file: `read_text()`, call `parse_agent_config(text, filename=f.name)`
   - Collect into `dict[str, AgentConfig]` keyed by `config.name`
   - Raise `ValueError` on duplicate names
   - Return the dict

5. `agent_from_config(config: AgentConfig, adapter: ILLMAdapter, router: ToolRouter, ctx: ToolUseContext) -> AgentLoop` (per CONF-03, D-06):
   - If `config.tools` is not None: `filtered_router = router.derive(router.registry.subset(set(config.tools)))`
   - If `config.tools` is None: use `router` directly (all tools)
   - Create and return `AgentLoop(adapter=adapter, model=config.model, router=filtered_router, ctx=ctx, max_steps=config.max_steps, system_prompt=config.system_prompt)`

6. Update `framework/agent_framework/agents/__init__.py` to export `AgentConfig`, `parse_agent_config`, `load_agent_configs`, `agent_from_config`.

**Verify:**
```bash
cd /Users/huhu/project/agent_framework/framework && python -c "from agent_framework.agents.config import AgentConfig, load_agent_configs, agent_from_config; print('Import OK')"
```

#### Task 2: Write Agent Config Tests

**File:** `framework/tests/test_agent_config.py`

**Test fixture directory:** `framework/tests/fixtures/agents/` — create sample .md files:

`research-agent.md`:
```
---
name: research-agent
description: 研究分析助手
model: claude-sonnet-4-6-20250514
max_steps: 15
tools: read_file, web_search
---
你是一个专业的分析师，擅长搜索和整理信息。
```

`minimal-agent.md`:
```
---
name: minimal-agent
---
你是一个简单的助手。
```

**Test cases:**

1. `test_parse_agent_config_full` — parse `research-agent.md`, verify name, description, model, max_steps=15, tools=["read_file", "web_search"], system_prompt content
2. `test_parse_agent_config_minimal` — parse `minimal-agent.md`, verify name="minimal-agent", default model, default max_steps=10, tools=None
3. `test_parse_agent_config_missing_name` — frontmatter without `name` field -> ValueError
4. `test_parse_agent_config_empty_system_prompt` — .md with `---\nname: test\n---\n` (empty body) -> ValueError (per D-07, CONF-04)
5. `test_load_agent_configs_from_directory` — load from fixtures dir, returns dict keyed by name, has both agents
6. `test_load_agent_configs_duplicate_names` — two files with same `name` field -> ValueError
7. `test_load_agent_configs_empty_directory` — empty dir returns empty dict
8. `test_agent_from_config_with_tool_filter` — create AgentLoop with tools=["read_file","web_search"], verify `agent.router.registry.list_tools()` == ["read_file", "web_search"]
9. `test_agent_from_config_all_tools` — tools=None, verify agent has all tools from parent router
10. `test_agent_from_config_is_agent_loop` — verify return is `isinstance(result, AgentLoop)` and `isinstance(result, Agent)`

**Verify:**
```bash
cd /Users/huhu/project/agent_framework/framework && pytest tests/test_agent_config.py -v
```

#### Task 3: Verify Zero Regression

**Action:** Run full test suite.

**Verify:**
```bash
cd /Users/huhu/project/agent_framework/framework && pytest tests/ -v --tb=short
```

### Dependencies
- Task 1 -> Task 2 -> Task 3 (sequential)
- Plan 07-02 has no hard code dependency on Plan 07-01 (different files), but logically follows since both extend the agents/orchestrator layer

---

## Plan 07-03: 真实搜索工具（SRCH-01~03）

### Requirements
- SRCH-01: search_tools.py handler switches from mock to Tavily `AsyncTavilyClient` HTTP calls
- SRCH-02: Async concurrency control (asyncio.Semaphore to prevent rate limit)
- SRCH-03: API key via environment variable (SecretStr pattern)

### Key Decisions
- **D-08:** Tavily API unavailable -> `ToolResult(is_error=True, content="搜索失败：...")`. No degradation to empty, no fallback to mock.

### Files to Create/Modify

| File | Action |
|------|--------|
| `framework/agent_framework/tools/builtin/search_tools.py` | Rewrite: mock -> Tavily AsyncTavilyClient |
| `framework/pyproject.toml` | Add `tavily-python>=0.5.0` dependency |
| `framework/tests/test_search_tools.py` | New test file |

### Tasks

#### Task 1: Add tavily-python Dependency and Implement Search Handler

**File:** `framework/pyproject.toml`

Add `tavily-python>=0.5.0` to the `dependencies` list (after `httpx>=0.27.0`). Then run `uv pip install -e ".[test]"` to install.

**File:** `framework/agent_framework/tools/builtin/search_tools.py`

Rewrite the entire file. Current content is a 17-line mock — replace with:

1. Module-level state:
   - `_semaphore: asyncio.Semaphore = asyncio.Semaphore(5)` — concurrency limit (per SRCH-02, Claude's discretion: 5)
   - `_client: AsyncTavilyClient | None = None` — lazy singleton

2. `_get_client() -> AsyncTavilyClient`:
   - Lazy init: check `_client is None`, if so create `AsyncTavilyClient(api_key=os.environ.get("TAVILY_API_KEY", ""))`
   - If `TAVILY_API_KEY` is empty/missing, raise `ValueError("TAVILY_API_KEY 未配置")`
   - Return `_client`

3. `reset_client() -> None` — for testing: sets `_client = None`

4. Rewrite `web_search(args: dict, ctx: ToolUseContext) -> ToolResult` (per SRCH-01, D-08):
   - Extract `query` from args
   - `try: async with _semaphore:` (per SRCH-02)
   - Call `_get_client().search(query=query, max_results=5)`
   - Format results: for each result in `response.get("results", [])`, extract `title`, `url`, `content`, build numbered list string
   - Return `ToolResult(content=formatted_string)`
   - `except ValueError as e`: missing API key -> `ToolResult(is_error=True, content=f"搜索失败：{e}")` (per D-08)
   - `except Exception as e`: network/rate-limit/other -> `ToolResult(is_error=True, content=f"搜索失败：{e}")` (per D-08)

5. Imports: `os`, `asyncio`, `AsyncTavilyClient` from `tavily`, `ToolResult`, `ToolUseContext` from `tools.types`.

6. Handler signature unchanged: `(args: dict, ctx: ToolUseContext) -> ToolResult` — no changes to `__init__.py` registration.

**Verify:**
```bash
cd /Users/huhu/project/agent_framework/framework && uv pip install -e ".[test]" && python -c "from agent_framework.tools.builtin.search_tools import web_search, reset_client; print('Import OK')"
```

#### Task 2: Write Search Tool Tests

**File:** `framework/tests/test_search_tools.py`

**Test cases:**

1. `test_search_returns_results_on_success` — mock `AsyncTavilyClient` to return `{"results": [{"title": "Test", "url": "https://example.com", "content": "Test content"}]}`, verify formatted output contains title, url, content
2. `test_search_returns_error_on_missing_api_key` — delete `TAVILY_API_KEY` from env (`monkeypatch.delenv`), call `reset_client()`, verify `ToolResult(is_error=True, content="搜索失败：...")` (per D-08)
3. `test_search_returns_error_on_network_failure` — mock `AsyncTavilyClient.search` to raise `ConnectionError("timeout")`, verify `ToolResult(is_error=True, content="搜索失败：timeout")`
4. `test_search_semaphore_limits_concurrency` — verify `_semaphore._value == 5` (internal check), or more robustly: launch 10 concurrent searches with a mock that records max concurrency, verify it never exceeds 5
5. `test_search_result_format` — with 3 mock results, verify output has numbered items 1/2/3, each containing title and url

**Mock strategy:** Use `unittest.mock.patch("agent_framework.tools.builtin.search_tools.AsyncTavilyClient")` to mock the client class. Tests must NOT require a real Tavily API key. Each test should call `reset_client()` in setup to ensure clean state.

**Verify:**
```bash
cd /Users/huhu/project/agent_framework/framework && pytest tests/test_search_tools.py -v
```

#### Task 3: Verify Zero Regression

**Action:** Run full test suite.

**Verify:**
```bash
cd /Users/huhu/project/agent_framework/framework && pytest tests/ -v --tb=short
```

### Dependencies
- Task 1 -> Task 2 -> Task 3 (sequential)
- Plan 07-03 is **independent** of Plans 07-01 and 07-02 (different files, no shared code)

---

## Dependency Graph

```
Wave 1:  07-01 (OrchestratorEngine)  |  07-03 (Search Tools)
         [engine.py, __init__.py]    |  [search_tools.py, pyproject.toml]
         [test_orchestrator_engine]  |  [test_search_tools.py]
                                      
Wave 2:  07-02 (Agent Config)
         [config.py, __init__.py]
         [test_agent_config.py, fixtures/]
```

**File overlap check:**
- 07-01 touches: `orchestrator/engine.py`, `orchestrator/__init__.py`, `tests/test_orchestrator_engine.py`
- 07-02 touches: `agents/config.py`, `agents/__init__.py`, `tests/test_agent_config.py`, `tests/fixtures/agents/`
- 07-03 touches: `tools/builtin/search_tools.py`, `pyproject.toml`, `tests/test_search_tools.py`

Zero overlap between plans in any wave. Safe for parallel execution.

---

## Success Criteria

1. OrchestratorEngine evaluates task complexity via character count heuristic (no LLM call), routes simple tasks to AgentLoop and complex tasks to PlanAndSolveAgent (ORCH-01~03)
2. agent_factory creates new Agent instances per execution, capped at 3 total per OrchestratorEngine (ORCH-04~05)
3. Agent configuration can be defined in .md files with frontmatter metadata + body system_prompt, `agent_from_config()` creates runnable AgentLoop instances with tool filtering (CONF-01~04)
4. web_search handler calls Tavily API, returns real results, handles errors via `ToolResult(is_error=True)`, concurrency controlled by Semaphore(5) (SRCH-01~03)
5. All existing tests pass (zero regression)
6. New test files cover all requirements: `test_orchestrator_engine.py`, `test_agent_config.py`, `test_search_tools.py`
