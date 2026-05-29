# Phase 7 Plan Verification

## Requirement Coverage

| Req | Covered By | Plan | Task | Status |
|-----|-----------|------|------|--------|
| ORCH-01 | OrchestratorEngine class: assess -> select -> execute pipeline | 07-01 | 1 | ✅ |
| ORCH-02 | `_assess_complexity()` single if-statement, character count threshold | 07-01 | 1 | ✅ |
| ORCH-03 | `_create_agent()` routes simple->AgentLoop, complex->PlanAndSolveAgent | 07-01 | 1 | ✅ |
| ORCH-04 | `_agent_count` cap at 3, drift via PlanAndSolve internal replan (max 2) | 07-01 | 1 | ✅ |
| ORCH-05 | `_create_agent()` factory method creates new Agent per call | 07-01 | 1 | ✅ |
| CONF-01 | `AgentConfig` dataclass + `parse_agent_config()` from .md frontmatter | 07-02 | 1 | ✅ |
| CONF-02 | `load_agent_configs()` with `directory.glob("*.md")`, reuses `parse_frontmatter()` | 07-02 | 1 | ✅ |
| CONF-03 | `agent_from_config()` creates `AgentLoop` with tool filtering via `router.derive(subset())` | 07-02 | 1 | ✅ |
| CONF-04 | Non-empty system_prompt check in `parse_agent_config()` (raises ValueError) | 07-02 | 1 | ✅ |
| SRCH-01 | Rewrite `search_tools.py` to use Tavily `AsyncTavilyClient` | 07-03 | 1 | ✅ |
| SRCH-02 | `asyncio.Semaphore(5)` wrapping the API call | 07-03 | 1 | ✅ |
| SRCH-03 | API key via `os.environ.get("TAVILY_API_KEY")`, ValueError if missing | 07-03 | 1 | ✅ |

**All 12 requirements covered. No gaps.**

## Success Criteria Check

| # | Criterion | Achievable | Notes |
|---|-----------|-----------|-------|
| 1 | OrchestratorEngine evaluates task complexity (heuristic, no LLM call), routes simple->ReAct, complex->Plan-and-Solve | ✅ | `_assess_complexity()` uses `len(task) > threshold`. `_create_agent()` creates AgentLoop or PlanAndSolveAgent. Task 2 tests verify routing. |
| 2 | Execution drift triggers plan correction, max 3 Agents per chain | ✅ | Drift detection delegated to PlanAndSolveAgent internal replan (max_replans=2, D-04). `_agent_count` cap at 3 in OrchestratorEngine. Task 2 test case 6 verifies 3-agent cap. |
| 3 | Agent config via .md files, `agent_from_config()` creates runnable Agent instance | ✅ | parse_agent_config uses parse_frontmatter + _extract_body. agent_from_config creates AgentLoop with filtered router. Task 2 has 10 test cases covering parsing, loading, and instantiation. |
| 4 | Search tool calls Tavily API, real results, Semaphore concurrency, env var API key | ✅ | AsyncTavilyClient.search(), Semaphore(5), os.environ.get("TAVILY_API_KEY"). Task 2 has 5 test cases including concurrency verification. |
| 5 | agent_factory pattern allows OrchestratorEngine to create Agent instances on demand | ✅ | `_create_agent()` is the factory method. Incremental `_agent_count` tracking. Creates different Agent types based on complexity assessment. |

## Codebase Alignment Verified

| Plan Reference | Actual Codebase | Match |
|----------------|-----------------|-------|
| Agent ABC: `run() -> AsyncGenerator[AgentEvent, None]` | `agents/base.py` line 23: exact match | ✅ |
| AgentLoop `__init__` params (adapter, model, router, ctx, max_steps, system_prompt) | `agents/agent_loop.py` line 70-92: exact match | ✅ |
| PlanAndSolveAgent `__init__` params (adapter, model, router, ctx, max_steps_per_plan_item, max_replans) | `agents/plan_and_solve.py` line 39-54: exact match | ✅ |
| `parse_frontmatter()` in `memory/frontmatter.py` | Line 47-55: returns `dict[str, str]`, confirmed | ✅ |
| `ToolRegistry.subset(names: set[str])` | `tools/registry.py` line 29-35: exact match | ✅ |
| `ToolRouter.derive(registry)` | `tools/router.py` line 46-50: confirmed | ✅ |
| `create_filtered_router()` pattern | `agents/sub_agent.py` line 15-24: plan reuses this pattern | ✅ |
| Mock adapter pattern from `test_plan_and_solve.py` | Uses `AsyncMock(spec=ILLMAdapter)` with `CompletionResult`: plan references correctly | ✅ |
| Current `search_tools.py` mock handler signature `(args: dict, ctx: ToolUseContext) -> ToolResult` | Line 8: exact match, plan preserves signature | ✅ |
| `engine.py` is empty scaffold | Line 1-16: confirmed, safe to rewrite | ✅ |

## Context Compliance (CONTEXT.md)

| Decision | Locked/Discretion | Plan Coverage | Status |
|----------|-------------------|---------------|--------|
| D-01: Char count threshold (200) | Locked | 07-01 Task 1, point 3: `_assess_complexity()` with `len(task) > threshold` | ✅ Exact |
| D-02: Complex -> PlanAndSolveAgent delegation | Locked | 07-01 Task 1, point 4: creates PlanAndSolveAgent for complex | ✅ Exact |
| D-03: agent_factory creates top-level Agent instances | Locked | 07-01 Task 1, point 4: `_create_agent()` factory method | ✅ Exact |
| D-04: Drift via PlanAndSolve internal replan, max 3 cap | Locked | 07-01 Task 1, point 4-5: `_agent_count > 3` guard, no own drift logic | ✅ Exact |
| D-05: .md frontmatter + body for system_prompt | Locked | 07-02 Task 1, points 1-3: frontmatter metadata + `_extract_body()` for prompt | ✅ Exact |
| D-06: tools field = comma-separated name list | Locked | 07-02 Task 1, point 3: comma-separated -> list[str] | ✅ Exact |
| D-07: system_prompt validation = non-empty check only | Locked | 07-02 Task 1, point 3: raise ValueError if empty | ✅ Exact |
| D-08: Tavily error -> ToolResult(is_error=True) | Locked | 07-03 Task 1, point 4: error handling with ToolResult(is_error=True) | ✅ Exact |
| OrchestratorEngine implements Agent interface? | Discretion | Plan implements `run() -> AsyncGenerator[AgentEvent, None]` with Agent ABC | ✅ Reasonable |
| Semaphore concurrency count | Discretion | Plan chose 5, within recommended 3-5 range | ✅ Reasonable |
| Deferred items | N/A | None exist | ✅ No scope creep |

**No scope reduction detected. All locked decisions implemented fully.**

## Dependency Graph

```
Wave 1: 07-01 (OrchestratorEngine) | 07-03 (Search Tools)
Wave 2: 07-02 (Agent Config)
```

- 07-01 and 07-03: No file overlap, no shared imports -> safe parallel
- 07-02 depends on 07-01 logically (extends agents layer) but has zero code dependency -> soft ordering, safe
- Internal: Task 1 -> Task 2 -> Task 3 sequential within each plan -> valid

**No cycles. No missing references. No forward references. Valid.**

## Scope Assessment

| Plan | Tasks | Files | Complexity | Status |
|------|-------|-------|------------|--------|
| 07-01 | 3 (impl + test + regression) | 3 | Moderate (orchestration logic) | ✅ Within budget |
| 07-02 | 3 (impl + test + regression) | 4 | Moderate (parsing + config) | ✅ Within budget |
| 07-03 | 3 (impl + test + regression) | 3 | Low (single file rewrite + dep) | ✅ Within budget |

All plans within 2-3 task target. All well under file count thresholds.

## Issues Found

### Warnings (should fix)

**1. [task_completeness] Plan 07-01 `_create_agent` for simple tasks does not pass `system_prompt`**
- Plan: 07-01, Task 1
- Detail: The `_create_agent()` method creates `AgentLoop(adapter=..., model=..., router=..., ctx=..., max_steps=...)` without specifying `system_prompt`. AgentLoop defaults to "你是一个有用的助手。可以使用工具来完成任务。" which may be too generic for orchestrated tasks. The user_message is passed through `run()`, so the agent will see the task, but the system prompt may not be contextually appropriate.
- Severity: WARNING (functional, but the default prompt may produce suboptimal results for orchestrated workflows)
- Fix: Consider passing a system_prompt parameter to OrchestratorEngine.__init__ that forwards to created agents, or accept it as acceptable default for v1.

**2. [requirement_coverage] SRCH-03 specifies "SecretStr pattern" but plan uses raw `os.environ.get`**
- Plan: 07-03, Task 1
- Detail: REQUIREMENTS.md says "API key 通过环境变量管理（SecretStr 模式）" and CONTEXT.md lists "SecretStr 保护 API Key" as an established pattern. The plan reads the key directly via `os.environ.get("TAVILY_API_KEY", "")` without wrapping it in SecretStr. The key is passed directly to `AsyncTavilyClient(api_key=...)`.
- Severity: WARNING (the key is not exposed in logs or error messages, and `AsyncTavilyClient` handles it internally, but the established pattern is not followed)
- Fix: Either wrap the key in `SecretStr` for consistency with LLM adapter patterns, or explicitly note this as a simplification since Tavily client manages the key internally.

### Info (suggestions)

**3. [key_links] OrchestratorEngine._create_agent and agent_from_config are parallel factory patterns with no integration**
- Plans 07-01 and 07-02 both create AgentLoop instances but through separate factory mechanisms. `_create_agent()` in OrchestratorEngine directly instantiates AgentLoop/PlanAndSolveAgent, while `agent_from_config()` in config.py creates AgentLoop from parsed .md configs. These two patterns do not compose: OrchestratorEngine cannot use agent_from_config to create its agents.
- Severity: INFO (not a bug — the two factories serve different purposes. OrchestratorEngine is programmatic, agent_from_config is declarative. Future enhancement could bridge them.)
- Note: This is architecturally clean separation. Not flagging as a warning.

**4. [scope_sanity] Test fixture directory `framework/tests/fixtures/agents/` does not exist yet**
- Plan: 07-02, Task 2
- Detail: The plan references creating test fixtures in `framework/tests/fixtures/agents/` but does not list directory creation as a separate step. The test task should create this directory as part of fixture setup.
- Severity: INFO (minor, executor will naturally create the directory when writing fixture files)

## Verdict

**PASS_WITH_NOTES**

The plan is executable and will achieve all 5 success criteria. All 12 requirements (ORCH-01~05, CONF-01~04, SRCH-01~03) are covered with specific, actionable tasks that reference correct codebase artifacts. All 8 locked decisions from CONTEXT.md are implemented exactly. The dependency graph is valid with no cycles. Scope is well within budget (3 tasks per plan, 3-4 files per plan).

Two warnings are noted (system_prompt forwarding in OrchestratorEngine factory, SecretStr pattern not followed for Tavily API key) but neither blocks execution — both are quality improvements that can be addressed during implementation without structural plan changes.
