# Phase 3: 架构与代码质量审查 - Research

**Researched:** 2026-05-28
**Domain:** Architecture review of Python agent framework (~7600 lines, 13 modules)
**Confidence:** HIGH

## Summary

This phase is a read-only audit: systematically review all framework modules for architecture quality, produce ARCH-REVIEW.md structured report with findings and improvement recommendations. The report is organized around 5 known issues from ROADMAP (AgentLoop parameter bloat, ToolRouter mixed responsibilities, TaskManager complex mutation, ToolUseContext type safety, empty file handling) with a full scan to discover new issues. Three empty files get scaffold docstrings.

The codebase is well-structured with consistent patterns (frozen dataclasses for values, Pydantic for cross-boundary data, tool-return-error-not-exception convention). The 5 known issues are real and well-documented in CONCERNS.md. Beyond these, the full scan reveals additional patterns worth recording: `_CRITICAL_TOOLS` never populated, `_dispatch_agent` stub, `VerificationRunner` only handles 1 of 5 check types, `web_search` mock, `PermissionResult` using plain class instead of dataclass, `TeamManager._loop` tight coupling of lifecycle management with AgentLoop construction, and `LLMScoringRetriever` using LLM for file selection without fallback.

**Primary recommendation:** This phase produces one artifact (ARCH-REVIEW.md) plus 3 scaffold docstrings. The review is organized as HIGH/MEDIUM/LOW with direction-level recommendations. No code refactoring occurs. The planner should create a single plan with 2 waves: Wave 1 for the full module scan and report writing, Wave 2 for scaffold docstrings (independent, can run in parallel with report review).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** ARCH-REVIEW.md 按问题驱动组织 -- 以 ROADMAP 列出的 5 个已知问题为骨架，每个问题包含「现状分析 + 改进建议 + 优先级」，全面扫描补充的新发现附在后面
- **D-02:** 架构问题分 3 级：HIGH（影响开发效率，短期内应重构）、MEDIUM（设计不够优，但可用）、LOW（锦上添花）。与 SECURITY-REVIEW.md 的分级风格保持一致
- **D-03:** 方向级 -- 每个问题记录：问题描述 + 改进方向（如"考虑 Builder 模式"）+ 优先级。不写具体接口设计、代码片段或迁移路径
- **D-04:** 3 个空文件全部保留（不删除），添加 module docstring 标记为 scaffold
- **D-05:** Docstring 格式：包含模块用途、当前状态（scaffold）、预期功能、相关模块引用。不添加占位类或函数签名
- **D-06:** 全面扫描 -- 5 个已知问题作为主体骨架，同时审查所有模块发现新问题。新发现也纳入 ARCH-REVIEW.md

### Claude's Discretion
- 全面扫描的具体发现由 reviewer 自行判断
- ARCH-REVIEW.md 的详细排版由 planner 决定
- Scaffold docstring 的具体措辞由 executor 决定

### Deferred Ideas (OUT OF SCOPE)
None
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| R3 | 审查代码架构、设计模式、模块职责划分 | 5 known issues analyzed below; full scan findings documented |
| R3.1 | AgentLoop.__init__ 15 参数问题（God Object 倾向） | Source: `agent_loop.py:71-93`, CONCERNS.md Fragile Areas |
| R3.2 | ToolRouter.dispatch 4 层职责混合 | Source: `router.py:58-156`, CONCERNS.md Fragile Areas |
| R3.3 | _apply_changes 复杂变异逻辑 | Source: `manager.py:185-226`, CONCERNS.md Fragile Areas |
| R3.4 | ToolUseContext.extra 无类型安全 | Source: `tools/types.py:48-57`, ARCHITECTURE.md Anti-Patterns |
| R3.5 | 空文件清理（base.py、engine.py、router.py） | Source: 3 empty files confirmed, D-04/D-05 decisions |
| R3.6 | 产出 ARCH-REVIEW.md | Format: problem-driven, HIGH/MEDIUM/LOW, direction-level recommendations |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| AgentLoop parameter bloat | API / Backend (agents layer) | -- | Constructor design is framework-internal, affects all consumers |
| ToolRouter responsibility separation | API / Backend (tools layer) | -- | Dispatch pipeline is core framework infrastructure |
| TaskManager mutation complexity | API / Backend (tasks layer) | -- | DAG mutation logic is framework-internal, persistence concern |
| ToolUseContext type safety | API / Backend (tools layer) | -- | Cross-module context bag is framework infrastructure |
| Empty file scaffold marking | API / Backend (all layers) | -- | Documentation concern affecting 3 modules |
| Architecture review report | Documentation | -- | Output artifact, not code |

## Standard Stack

### Core (no new packages -- review-only phase)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.11+ | Runtime for source analysis | Project requirement [VERIFIED: codebase] |
| pytest | 9.0.3 | Verify no regressions from scaffold docstrings | Already in use [VERIFIED: pip show] |
| pathlib | stdlib | File reading for analysis | Standard [VERIFIED: stdlib] |

### No New Dependencies Required

This phase installs zero packages. All work is code reading, analysis, and documentation writing.

**Installation:** None needed.

## Package Legitimacy Audit

> No new packages are installed in this phase. No audit required.

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```text
                 Phase 3: Architecture Review Scope

  ┌──────────────────────────────────────────────────────────────────┐
  │                    Framework Module Map                          │
  │                                                                  │
  │  ┌─────────────┐   ┌──────────────────────────────────────────┐ │
  │  │  agents/    │   │  tools/                                  │ │
  │  │             │   │                                          │ │
  │  │ AgentLoop ──┼──►│ ToolRouter.dispatch()                    │ │
  │  │ 15 params   │   │   1. PermissionPipeline                  │ │
  │  │ ARCH-01     │   │   2. PreToolUse hooks                    │ │
  │  │             │   │   3. Route (builtin/mcp/agent) + degrade │ │
  │  │             │   │   4. PostToolUse hooks                    │ │
  │  │             │   │   ARCH-02                                │ │
  │  │             │   │                                          │ │
  │  │             │   │ ToolUseContext.extra: dict[str, Any]      │ │
  │  │             │   │   ARCH-04                                │ │
  │  └─────────────┘   └──────────────────────────────────────────┘ │
  │                                                                  │
  │  ┌─────────────┐   ┌──────────────┐   ┌──────────────────────┐ │
  │  │  tasks/     │   │ orchestrator/│   │  agents/base.py      │ │
  │  │             │   │              │   │  orchestrator/       │ │
  │  │ TaskManager │   │ engine.py    │   │   engine.py          │ │
  │  │._apply_     │   │ router.py    │   │   router.py          │ │
  │  │ changes()   │   │ (empty)      │   │ (all empty)          │ │
  │  │ ARCH-03     │   │              │   │ ARCH-05              │ │
  │  └─────────────┘   └──────────────┘   └──────────────────────┘ │
  │                                                                  │
  │  ┌─────────┐ ┌─────────┐ ┌──────────┐ ┌───────┐ ┌──────────┐  │
  │  │ llm/    │ │ memory/ │ │ safety/  │ │ teams/│ │ skills/  │  │
  │  │ (well)  │ │ (fair)  │ │ (fair)   │ │(fair) │ │ (good)   │  │
  │  └─────────┘ └─────────┘ └──────────┘ └───────┘ └──────────┘  │
  │                                                                  │
  │  Full scan target: all 13 modules, ~7600 lines                  │
  └──────────────────────────────────────────────────────────────────┘

  Output: docs/reviews/ARCH-REVIEW.md
          3 scaffold docstrings in empty files
```

### Recommended Project Structure (changes only)

```text
framework/agent_framework/
├── agents/base.py               # MODIFIED: add scaffold docstring
├── orchestrator/engine.py       # MODIFIED: add scaffold docstring
└── orchestrator/router.py       # MODIFIED: add scaffold docstring

docs/reviews/
└── ARCH-REVIEW.md              # NEW: architecture review report
```

### Pattern 1: Scaffold Docstring Convention

**What:** Module docstring marking empty files as scaffold with purpose, status, and related modules.
**When to use:** Any empty Python module that is intentionally reserved for future implementation.
**Example:**
```python
# Source: [ASSUMED -- based on CONVENTIONS.md docstring style and D-05 decision]
"""[模块用途描述]。

当前状态: scaffold（预留模块，尚未实现）。
预期功能: [描述该模块应有的核心功能]。
相关模块: [列出相关的已有模块路径]。
"""
```

The existing codebase convention is Chinese one-line docstrings at module top (e.g., `"""工具路由 -- 按来源分叉到正确的执行路径。"""`). Scaffold docstrings extend this with structured sections. No placeholder classes or function signatures per D-05.

### Pattern 2: ARCH-REVIEW.md Organization

**What:** Problem-driven report structure following SECURITY-REVIEW.md conventions.
**When to use:** Architecture review report.
**Example structure:**
```markdown
# Architecture Review Report

## HIGH

### ARCH-01: [Problem Name]
**Description:** ...
**File Location:** ...
**Current Impact:** ...
**Improvement Direction:** ...
**Priority:** HIGH

## MEDIUM
...

## LOW
...

## Summary
| Metric | Count |
|--------|-------|
| Total issues | N |
| HIGH | N |
| MEDIUM | N |
| LOW | N |
```

### Anti-Patterns to Avoid

- **Writing code refactoring:** This phase is review-only. Even if a fix seems trivial, record it in ARCH-REVIEW.md instead of fixing it.
- **Adding placeholder classes/functions to scaffold files:** D-05 explicitly forbids this. Only add module docstrings.
- **Proposing specific interface designs:** D-03 limits recommendations to direction-level ("consider Builder pattern", not actual interface code).
- **Duplicating CONCERNS.md content verbatim:** ARCH-REVIEW.md should synthesize and add architectural perspective, not copy-paste.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Architecture review report | Custom template engine | Simple markdown in ARCH-REVIEW.md | Phase produces one document; complexity not justified |
| Scaffold docstring generator | Script to inject docstrings | Manual docstring writing | Only 3 files; automation overhead exceeds manual effort |

## Common Pitfalls

### Pitfall 1: Confusing architecture issues with security/performance issues

**What goes wrong:** Recording security problems (already fixed in Phase 2) or performance issues (Phase 4 scope) in ARCH-REVIEW.md.
**Why it happens:** Issues overlap across dimensions (e.g., `_apply_changes` mutation is both architecture and correctness).
**How to avoid:** Focus on architectural dimension -- responsibility assignment, coupling, cohesion, extensibility, type safety. Security and performance are covered by other phases. Reference them if relevant ("this architectural issue also has security implications, see SECURITY-REVIEW.md SEC-05") but don't re-analyze.
**Warning signs:** ARCH-REVIEW.md contains "buffer overflow", "memory leak", "SQL injection" type findings.

### Pitfall 2: Recreating CONCERNS.md instead of adding architectural perspective

**What goes wrong:** ARCH-REVIEW.md becomes a copy of CONCERNS.md with the same findings and language.
**Why it happens:** CONCERNS.md already has excellent analysis of the 5 known issues.
**How to avoid:** CONCERNS.md is an input. ARCH-REVIEW.md should synthesize: add architectural assessment, classify severity using HIGH/MEDIUM/LOW, add improvement directions. The CONCERNS.md analysis can be referenced but the report adds value through prioritization and architectural reasoning.
**Warning signs:** ARCH-REVIEW.md text is substantially identical to CONCERNS.md sections.

### Pitfall 3: Scaffold docstrings too specific or too vague

**What goes wrong:** Either writing a full design spec in the docstring (too specific, locks in design) or writing just "TODO: implement" (too vague, loses context about intended purpose).
**Why it happens:** Balance between providing guidance and not over-constraining future work.
**How to avoid:** Follow D-05: module purpose + current status (scaffold) + expected functionality + related module references. Keep purpose description at 1-2 sentences, expected functionality at 2-3 bullet points.
**Warning signs:** Docstring exceeds 10 lines or contains implementation details.

### Pitfall 4: Full scan misses cross-module coupling issues

**What goes wrong:** Reviewing each module in isolation and missing issues that only appear at module boundaries (e.g., `ToolUseContext.extra` keys used across modules).
**Why it happens:** Module-by-module review is natural but coupling issues span boundaries.
**How to avoid:** After individual module review, trace the `ToolUseContext.extra` key usage across all modules. Check for circular dependencies and import-time side effects. Look at how `AgentLoop` integrates with all optional subsystems.
**Warning signs:** Report has per-module findings but no cross-cutting concerns.

## Code Examples

### Example 1: Scaffold docstring for agents/base.py

```python
# Source: [ASSUMED -- pattern from CONVENTIONS.md + D-05 decision]
"""Agent 基类协议定义。

当前状态: scaffold（预留模块，尚未实现）。
预期功能:
  - 定义 Agent 基础协议/接口（Protocol 或 ABC）
  - 提供 AgentLoop 以外的 Agent 变体共享契约
  - 为 SubAgent、TeamAgent 等提供统一类型约束
相关模块:
  - agent_framework.agents.agent_loop (核心 ReAct 循环)
  - agent_framework.agents.sub_agent (子 Agent 创建)
  - agent_framework.teams.manager (队友 Agent 管理)
"""
```

### Example 2: Scaffold docstring for orchestrator/engine.py

```python
# Source: [ASSUMED -- pattern from CONVENTIONS.md + D-05 decision]
"""编排引擎 — 多 Agent 协调调度。

当前状态: scaffold（预留模块，尚未实现）。
预期功能:
  - 多 Agent 编排策略（顺序、并行、层级）
  - Agent 间的任务分配和结果聚合
  - 全局上下文管理和共享状态协调
相关模块:
  - agent_framework.orchestrator.planner (Session Planning)
  - agent_framework.orchestrator.router (LLM 路由)
  - agent_framework.agents.agent_loop (Agent 执行)
  - agent_framework.teams.manager (团队管理)
"""
```

### Example 3: Scaffold docstring for orchestrator/router.py

```python
# Source: [ASSUMED -- pattern from CONVENTIONS.md + D-05 decision]
"""LLM 路由 — Provider 选择和降级策略。

当前状态: scaffold（预留模块，尚未实现）。
预期功能:
  - 基于 model 名称/能力需求的 Provider 路由
  - 多 Provider 降级链配置（主 -> 备 -> 兜底）
  - 成本/延迟/能力维度的智能选择
相关模块:
  - agent_framework.orchestrator.engine (编排引擎)
  - agent_framework.llm.resilient (ResilientLLMAdapter + create_adapter 工厂)
  - agent_framework.llm.providers (Provider 实现)
"""
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Large constructor with many params | Builder pattern / Config dataclass | Established pattern | Reduces coupling, improves testability |
| Mixed-responsibility dispatch | Pipeline/Middleware pattern | Established pattern | Each concern isolated, extensible |
| dict[str, Any] for context | Typed context models (Pydantic/TypedDict) | Python typing maturity | IDE support, compile-time checks |
| Empty files with no documentation | Scaffold docstrings | Community convention | Signals intent without over-constraining |

**Deprecated/outdated:**
- None specific to this review phase.

## Known Architecture Issues (Pre-Analysis)

The following 5 issues are the ROADMAP skeleton. Analysis is based on direct source code reading.

### ARCH-01: AgentLoop Parameter Bloat (HIGH)

**Location:** `framework/agent_framework/agents/agent_loop.py:71-93`

The `__init__` method has 15 parameters. Analysis of parameter categories:

| Category | Parameters | Count |
|----------|-----------|-------|
| Core (required) | adapter, model, router, ctx | 4 |
| Loop control | max_steps, system_prompt | 2 |
| Planning | profile, drift_warn, drift_abort | 3 |
| Compaction | compact_adapter, compact_keep_turns, compact_trigger_pct | 3 |
| Memory | memory_flush_enabled, semantic_extractor | 2 |
| Subsystem integrations | skill_dirs, hook_manager, task_runner, enable_subagent, team_manager | 5 |

Total: 15 parameters (4 positional, 11 keyword-only). The integrations category grows with every new subsystem.

**Improvement direction:** Extract integration parameters into a config dataclass (e.g., `AgentLoopConfig` with optional fields for each subsystem). Or use Builder pattern for incremental construction. The core 4 parameters (adapter, model, router, ctx) should remain explicit.

### ARCH-02: ToolRouter.dispatch Mixed Responsibilities (HIGH)

**Location:** `framework/agent_framework/tools/router.py:58-156`

The `dispatch` method handles 4 distinct concerns in a single 99-line method:

1. **Permission check** (lines 64-76): DENY/ASK decision
2. **Pre-hook execution** (lines 78-98): PreToolUse hooks, may block or modify input
3. **Route + Execute + Degrade** (lines 100-135): builtin/MCP/agent routing with fallback
4. **Post-hook execution** (lines 137-155): PostToolUse hooks, may inject supplementary info

Each concern has different failure modes and error handling. The try/except at line 101 wraps only concern 3 but its error handling also interacts with concern 2 (modifying `active_call`).

**Improvement direction:** Extract each concern into a pipeline step (middleware pattern). Each step receives `ToolCall + ToolUseContext` and returns either a `ToolResult` (short-circuit) or modified `ToolCall` (pass to next step). This makes the dispatch composable and testable in isolation.

### ARCH-03: TaskManager._apply_changes Complex Mutation (MEDIUM)

**Location:** `framework/agent_framework/tasks/manager.py:185-226`

The method handles 3 different concerns in 42 lines:

1. **Field updates** (lines 186-195): Simple field replacement via `dataclasses.replace`
2. **Bidirectional dependency management** (lines 197-224): Adds cross-references and schedules pending writes to related tasks
3. **Batch disk writes** (lines 223-224): Writes all pending changes without transaction guarantees

The dependency management logic (concern 2) is the most complex part -- it reads other tasks from disk (`self.get(dep_id)`) and creates pending writes for them, all within the caller's lock scope.

**Improvement direction:** Separate dependency management into a dedicated method (e.g., `_update_dependencies(task, changes) -> list[Task]`) that returns the list of tasks needing write, keeping the write decision in the caller. This makes the mutation logic testable without disk I/O.

### ARCH-04: ToolUseContext.extra Type Safety (MEDIUM)

**Location:** `framework/agent_framework/tools/types.py:48-57`

`ToolUseContext.extra` is `dict[str, Any]`. Key usage across codebase:

| Key | Set In | Read In | Type |
|-----|--------|---------|------|
| `skill_registry` | `agent_loop.py:120` | `skills/tool.py` | `SkillRegistry` |
| `planning_state` | `agent_loop.py:167,284` | `agent_loop.py` | `PlanningState` |
| `teammate_name` | `teams/manager.py:72` | (not found) | `str` |
| `message_bus` | `teams/manager.py:72` | (not found) | `MessageBus` |

Keys are magic strings scattered across modules. No central registry of valid keys or their types.

**Improvement direction:** Define a typed context model using `TypedDict` or Pydantic model with optional typed fields. Or use a `Context` protocol with typed accessor methods. The goal is to make key names discoverable and type-checked.

### ARCH-05: Empty Files Need Scaffold Marking (LOW)

**Location:** 3 files confirmed empty (0 lines):
- `framework/agent_framework/agents/base.py`
- `framework/agent_framework/orchestrator/engine.py`
- `framework/agent_framework/orchestrator/router.py`

These files exist as placeholders for future implementation. Currently they provide no indication of their intended purpose.

**Improvement direction:** Add module docstrings per D-04/D-05 decisions. See Code Examples section for suggested content.

## Full Scan: Additional Findings

Beyond the 5 known issues, the following architectural concerns were discovered during full module scan.

### ARCH-06: _CRITICAL_TOOLS Global Never Populated (MEDIUM)

**Location:** `framework/agent_framework/safety/permissions.py:40`

`_CRITICAL_TOOLS: set[str] = set()` is initialized empty and never populated anywhere in the codebase. The DENY step of the permission pipeline (`PermissionPipeline.check` line 58) checks this set but always passes through. This means the first defense layer of the permission system is inactive.

**Impact:** No tools are globally blocked regardless of risk. If a bash tool or destructive tool is added, there is no mechanism to globally deny it from the permission pipeline.

**Improvement direction:** Either populate `_CRITICAL_TOOLS` from configuration or make it a parameter on `PermissionPipeline.__init__`. Consider removing the global state and making critical tools part of the `AgentProfile.disallowed_tools` configuration.

### ARCH-07: _dispatch_agent Is a Permanent Stub (LOW)

**Location:** `framework/agent_framework/tools/router.py:179-183`

`_dispatch_agent` returns a hardcoded "not implemented" error for all `agent__` prefixed tools. The routing prefix is reserved but non-functional. This creates dead code in the dispatch path (the `elif name.startswith("agent__")` branch) and misleading API surface (agent tools appear routable but always fail).

**Impact:** Code that attempts to use agent tools gets unhelpful error messages. The `agent__` prefix reservation constrains tool naming without providing value.

**Improvement direction:** Either implement agent dispatch or remove the `agent__` prefix reservation and document it as a future extension point. If kept as a stub, the error message should be more specific about when this feature is planned.

### ARCH-08: VerificationRunner Only Handles 1 of 5 Check Types (LOW)

**Location:** `framework/agent_framework/safety/verification.py:48-53`

`VerificationRule` schema supports 5 check types (`code_compiles`, `tests_pass`, `schema_valid`, `llm_judge`, `regex_match`), but `_run_single` only handles `regex_match` and returns `None` for all others. This means 4 check types silently pass verification without actually checking anything.

**Impact:** Post-tool verification only works for regex rules. Other verification rules give false confidence.

**Improvement direction:** Implement remaining check types or remove them from the `Literal` type and document them as future work. At minimum, log a warning when an unhandled check type is encountered instead of silently passing.

### ARCH-09: PermissionResult Uses Plain Class Instead of Dataclass (LOW)

**Location:** `framework/agent_framework/safety/permissions.py:25-36`

`PermissionResult` is a plain class with manual `__init__`. Every other type in the codebase uses either `dataclass(frozen=True)` (for value objects) or Pydantic `BaseModel` (for cross-boundary data). This is inconsistent with project conventions documented in CONVENTIONS.md.

**Impact:** Minor inconsistency. No functional impact but reduces codebase uniformity.

**Improvement direction:** Convert to `@dataclass(frozen=True)` since it is a value object (action, reason, risk_level). This aligns with the project convention for immutable value types.

### ARCH-10: web_search Is a Documented Mock (LOW)

**Location:** `framework/agent_framework/tools/builtin/search_tools.py:8-17`

Already documented in CONCERNS.md as a known tech debt. The mock returns hardcoded fake results. This is not a new finding but should be included in ARCH-REVIEW.md for completeness since it affects architectural trustworthiness -- any agent using web search will receive fake data.

**Impact:** Production safety concern if agents rely on search results for decision-making.

**Improvement direction:** Gate behind a feature flag or clearly document the mock status in the tool's description string so LLMs are aware the data is fake.

### ARCH-11: TeamManager._loop Tightly Couples Lifecycle with AgentLoop Construction (LOW)

**Location:** `framework/agent_framework/teams/manager.py:66-115`

The `_loop` method handles 4 concerns: (1) AgentLoop construction with context setup, (2) inbox reading and shutdown detection, (3) prompt construction from inbox messages, (4) idle timeout management. All interleaved in a 50-line method.

Additionally, `TeamManager.__init__` accepts untyped `team_dir` parameter (line 29: `team_dir` without type annotation), while the docstring and usage suggest `Path`.

**Impact:** Testing the loop behavior in isolation is difficult. The untyped parameter reduces IDE support.

**Improvement direction:** Extract AgentLoop construction into a factory method. Add type annotation to `team_dir`. Consider separating inbox processing from lifecycle management.

### ARCH-12: LLMScoringRetriever Has No Fallback for LLM Failure (LOW)

**Location:** `framework/agent_framework/memory/retriever.py:55-110`

The `retrieve` method calls LLM for file selection and silently returns `[]` on JSON parse failure (line 94). If the LLM returns malformed JSON, all semantic memory retrieval silently fails with zero results. There is no fallback to keyword-based selection.

**Impact:** Memory retrieval degrades silently without indication. Users may not realize semantic memory is not working.

**Improvement direction:** Log a warning when LLM scoring fails. Consider a keyword-based fallback for semantic file selection when LLM is unavailable. Alternatively, return all candidates (up to `max_results`) as a degraded result instead of empty list.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Scaffold docstring format follows existing Chinese one-line docstring convention | Code Examples | Docstrings may look inconsistent with existing style |
| A2 | `_CRITICAL_TOOLS` is never populated anywhere in the codebase (not in config, tests, or application layer) | ARCH-06 | If it IS populated somewhere, the finding is incorrect |
| A3 | `agent__` prefix is not used by any external code or tests | ARCH-07 | If external code depends on this prefix, removing it would break integration |
| A4 | `VerificationRunner._run_single` returns `None` for unhandled types (not verified by running the code) | ARCH-08 | The behavior might be different at runtime |
| A5 | The `teammate_name` and `message_bus` keys in `ctx.extra` are not read outside of `teams/manager.py` | ARCH-04 | If other modules read these keys, the type safety issue is more widespread |

## Open Questions (RESOLVED)

1. **Should ARCH-REVIEW.md include findings already documented in CONCERNS.md?** — RESOLVED: Per D-01, ARCH-REVIEW.md is self-contained with enough context to be readable standalone, but can reference CONCERNS.md for detailed analysis. New findings are fully documented in ARCH-REVIEW.md.

2. **What is the threshold for recording a finding vs. noting it as acceptable design?** — RESOLVED: Record anything that would cause a developer to pause and think during maintenance. Priority level (HIGH/MEDIUM/LOW) communicates whether action is recommended.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11+ | Source analysis | Yes | 3.11.14 | -- |
| pytest | Verify no regressions from scaffold docstrings | Yes | 9.0.3 | -- |

Step 2.6: Most dependencies SKIPPED (review-only phase with no external tool dependencies).

**Missing dependencies with no fallback:** None

**Missing dependencies with fallback:** None

## Validation Architecture

> Note: `workflow.nyquist_validation` is not set in config.json (absent = enabled).

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 + pytest-asyncio |
| Config file | None (conftest.py only) |
| Quick run command | `cd framework && pytest tests/ -v --timeout=60` |
| Full suite command | `cd framework && pytest tests/ -v --timeout=60` |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| R3 | ARCH-REVIEW.md exists with required structure | manual | `test -f docs/reviews/ARCH-REVIEW.md && grep -c "HIGH" docs/reviews/ARCH-REVIEW.md` | Wave 0 (new file) |
| R3.5 | base.py has scaffold docstring | unit | `cd framework && python -c "import agent_framework.agents.base; print(agent_framework.agents.base.__doc__)"` | Wave 0 (modify existing) |
| R3.5 | engine.py has scaffold docstring | unit | `cd framework && python -c "import agent_framework.orchestrator.engine; print(agent_framework.orchestrator.engine.__doc__)"` | Wave 0 (modify existing) |
| R3.5 | router.py has scaffold docstring | unit | `cd framework && python -c "import agent_framework.orchestrator.router; print(agent_framework.orchestrator.router.__doc__)"` | Wave 0 (modify existing) |
| Regression | All existing tests still pass | unit | `cd framework && pytest tests/ -v --timeout=60` | Existing |

### Sampling Rate
- **Per task commit:** `cd framework && pytest tests/ -v --timeout=60` (verify scaffold docstrings don't break imports)
- **Per wave merge:** `cd framework && pytest tests/ -v --timeout=60`
- **Phase gate:** Full suite green + ARCH-REVIEW.md exists with all 5 known issues addressed

### Wave 0 Gaps
- [ ] `docs/reviews/ARCH-REVIEW.md` -- covers R3.6
- [ ] Scaffold docstrings in 3 files -- covers R3.5
- [ ] No framework install or config needed -- already in place

## Sources

### Primary (HIGH confidence)
- All source files in `framework/agent_framework/` read and analyzed in this session
- `.planning/codebase/CONCERNS.md` -- 5 known issues with detailed analysis
- `.planning/codebase/ARCHITECTURE.md` -- module dependencies, data flow, pattern overview
- `.planning/codebase/CONVENTIONS.md` -- coding style, naming, immutability patterns
- `.planning/codebase/STRUCTURE.md` -- file organization, module sizes, naming conventions
- `docs/reviews/SECURITY-REVIEW.md` -- format reference for ARCH-REVIEW.md
- `.planning/phases/01-bug/01-VERIFICATION.md` -- Phase 1 completion state
- `.planning/phases/02-security/02-VERIFICATION.md` -- Phase 2 completion state

### Secondary (MEDIUM confidence)
- `.planning/phases/02-security/02-RESEARCH.md` -- structure reference for this document

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Known issues (5 ROADMAP items): HIGH - all source files read, CONCERNS.md cross-referenced
- Full scan findings: HIGH - all 13 modules reviewed, specific code locations cited
- Scaffold docstring patterns: MEDIUM - based on existing conventions but scaffold format is new
- Report format: HIGH - SECURITY-REVIEW.md provides proven template

**Research date:** 2026-05-28
**Valid until:** 2026-06-28 (stable -- no code changes in this phase)
