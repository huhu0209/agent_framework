# Architecture Review Report

**Audit Date:** 2026-05-28
**Scope:** `framework/agent_framework/` (full framework layer, 13 modules, ~7600 lines)
**Auditor:** Automated architecture review (Phase 03)
**Format:** Severity-based, matching SECURITY-REVIEW.md conventions

---

## HIGH

Findings that impact development efficiency and should be refactored in the near term.

### ARCH-01: AgentLoop Constructor Parameter Bloat

**Description:** `AgentLoop.__init__` accepts 15 parameters (4 positional, 11 keyword-only). The parameters span 6 distinct categories: core execution (adapter, model, router, ctx), loop control (max_steps, system_prompt), planning (profile, drift_warn, drift_abort), context compaction (compact_adapter, compact_keep_turns, compact_trigger_pct), memory (memory_flush_enabled, semantic_extractor), and subsystem integrations (skill_dirs, hook_manager, task_runner, enable_subagent, team_manager). The integration category will grow with every new subsystem added to the framework.

**File Location:** `framework/agent_framework/agents/agent_loop.py:71-93`

**Current Impact:** Adding any new subsystem (e.g., rate limiting, audit logging) requires modifying the AgentLoop constructor signature, which is the most widely-used entry point in the framework. This creates a God Object tendency where a single class accumulates configuration for every subsystem it might interact with. Each new parameter increases the cognitive load for callers and makes test setup verbose.

**Improvement Direction:** Extract integration parameters into a dedicated config dataclass (e.g., `AgentLoopConfig`) with optional fields for each subsystem. Alternatively, consider a Builder pattern for incremental construction. The core 4 parameters (adapter, model, router, ctx) should remain explicit as they define the loop's identity. This keeps the constructor stable as new subsystems are added.

**Priority:** HIGH

---

### ARCH-02: ToolRouter.dispatch Mixed Responsibilities

**Description:** The `dispatch` method handles 4 distinct concerns in a single 99-line method: (1) permission checking via PermissionPipeline (lines 64-76), (2) PreToolUse hook execution with possible blocking or input modification (lines 78-98), (3) tool routing and execution with error recovery and degradation fallback (lines 100-135), and (4) PostToolUse hook execution with supplementary injection (lines 137-155). Each concern has different failure modes and error handling strategies, but they are interleaved rather than isolated.

**File Location:** `framework/agent_framework/tools/router.py:58-156`

**Current Impact:** The dispatch method is the most complex single method in the framework. Testing any one concern (e.g., "does the degradation fallback work?") requires setting up all other concerns. The try/except block at line 101 wraps only concern 3 but its error handling also interacts with concern 2 (the modified `active_call` variable). Adding a new cross-cutting concern (e.g., rate limiting, audit logging) would further increase the method's complexity.

**Improvement Direction:** Extract each concern into a pipeline step following a middleware pattern. Each step receives `ToolCall + ToolUseContext` and returns either a `ToolResult` (short-circuit) or modified `ToolCall` (pass to next step). This makes the dispatch composable, testable in isolation, and extensible for new cross-cutting concerns.

**Priority:** HIGH

---

## MEDIUM

Findings that are suboptimal but functional. Not blocking, but should be addressed during regular development.

### ARCH-03: TaskManager._apply_changes Complex Mutation Logic

**Description:** The `_apply_changes` method handles 3 different concerns in 42 lines: (1) field updates via `dataclasses.replace` (lines 186-195), (2) bidirectional dependency management that reads other tasks from disk and creates pending cross-reference writes (lines 197-221), and (3) batch disk writes without transaction guarantees (lines 223-224). The dependency management logic is the most complex part -- it reads other tasks from disk (`self.get(dep_id)`) and creates pending writes, all within the caller's lock scope.

**File Location:** `framework/agent_framework/tasks/manager.py:185-226`

**Current Impact:** The method mixes in-memory computation with synchronous disk I/O inside a mutation method. If the process crashes between writing the dependent tasks (lines 223-224), the dependency graph becomes inconsistent. Testing dependency logic requires mocking the disk layer, which increases test complexity.

**Improvement Direction:** Separate dependency management into a dedicated method (e.g., `_update_dependencies(task, changes) -> list[Task]`) that returns the list of tasks needing write, keeping the write decision in the caller. This makes the mutation logic testable without disk I/O and allows for batched or transactional writes in the future.

**Priority:** MEDIUM

---

### ARCH-04: ToolUseContext.extra Lacks Type Safety

**Description:** `ToolUseContext.extra` is `dict[str, Any]`. Four keys are used across the codebase as magic strings with no central registry: `skill_registry` (set in `agent_loop.py`, read in `skills/tool.py`), `planning_state` (set and read in `agent_loop.py`), `teammate_name` (set in `teams/manager.py`), and `message_bus` (set in `teams/manager.py`). Keys are discovered only by reading calling code, and there is no type checking on the values retrieved from this dict.

**File Location:** `framework/agent_framework/tools/types.py:48-57`

**Current Impact:** Adding a new context value requires finding all places that construct `ToolUseContext` and all places that read the key. A typo in a key name silently returns `None` or `KeyError` at runtime. IDE auto-completion cannot suggest available keys. Cross-module coupling through `extra` keys is invisible at the type level.

**Improvement Direction:** Define a typed context model using `TypedDict` or a Pydantic model with optional typed fields for each known key. Alternatively, use a typed accessor protocol. The goal is to make key names discoverable, type-checked, and centralized so that adding or removing a context key is visible at compile time.

**Priority:** MEDIUM

---

### ARCH-06: _CRITICAL_TOOLS Global Never Populated

**Description:** `_CRITICAL_TOOLS: set[str] = set()` is initialized as an empty global in `permissions.py` and never populated anywhere in the codebase. The first step of the permission pipeline's `check` method tests against this set (line 58), but since it is always empty, no tool is ever denied by this mechanism. This means the first defense layer of the four-step permission cascade is entirely inactive.

**File Location:** `framework/agent_framework/safety/permissions.py:25-40`

**Current Impact:** No tools are globally blocked regardless of risk level. If a bash tool, file deletion tool, or other destructive tool is added, there is no mechanism to globally deny it from the permission pipeline without adding it to every agent profile's `disallowed_tools` list. The empty global also creates misleading code -- readers see a critical-tools check but it does nothing.

**Improvement Direction:** Either populate `_CRITICAL_TOOLS` from configuration or make it a parameter on `PermissionPipeline.__init__`. Consider removing the global state entirely and making critical tools part of the `AgentProfile.disallowed_tools` configuration, which is already functional and per-profile.

**Priority:** MEDIUM

---

## LOW

Findings that are nice-to-have improvements. No urgency, but worth recording for future consideration.

### ARCH-05: Empty Files Need Scaffold Marking

**Description:** Three files exist as empty placeholders with no content: `agents/base.py`, `orchestrator/engine.py`, and `orchestrator/router.py`. These files signal intended future modules but provide no indication of their purpose, expected functionality, or relationship to existing modules.

**File Location:**
- `framework/agent_framework/agents/base.py` (0 lines)
- `framework/agent_framework/orchestrator/engine.py` (0 lines)
- `framework/agent_framework/orchestrator/router.py` (0 lines)

**Current Impact:** Developers encountering these empty files have no context about what should go there. The files are importable but contain nothing, which can cause confusion when reading module structure.

**Improvement Direction:** Add module docstrings marking each file as scaffold, describing its intended purpose, expected functionality, and related modules. See Phase 03 Plan 02 for implementation.

**Priority:** LOW

---

### ARCH-07: _dispatch_agent Is a Permanent Stub

**Description:** `_dispatch_agent` returns a hardcoded "not implemented" error for all `agent__` prefixed tools. The routing prefix is reserved in the dispatch method (line 104: `elif name.startswith("agent__")`) but is non-functional. This creates dead code in the dispatch path and misleading API surface -- agent tools appear routable but always fail with an unhelpful error message.

**File Location:** `framework/agent_framework/tools/router.py:104,179-183`

**Current Impact:** Code that attempts to use agent tools receives a generic error. The `agent__` prefix reservation constrains tool naming without providing value. The stub adds a branch to the already-complex dispatch method (see ARCH-02).

**Improvement Direction:** Either implement agent dispatch or remove the `agent__` prefix reservation and document it as a future extension point. If kept as a stub, the error message should be more specific about the feature's status.

**Priority:** LOW

---

### ARCH-08: VerificationRunner Only Handles 1 of 5 Check Types

**Description:** `VerificationRule` schema supports 5 check types (`code_compiles`, `tests_pass`, `schema_valid`, `llm_judge`, `regex_match`), but `_run_single` only handles `regex_match` and returns `None` for all others. This means 4 check types silently pass through `run_post_tool` without verification, giving false confidence that rules are being enforced.

**File Location:** `framework/agent_framework/safety/verification.py:48-53`

**Current Impact:** Post-tool verification only works for regex rules. Rules configured with `code_compiles`, `tests_pass`, `schema_valid`, or `llm_judge` check types have no effect -- they are accepted as valid configuration but never executed.

**Improvement Direction:** Implement remaining check types or remove them from the `Literal` type definition and document them as future work. At minimum, log a warning when an unhandled check type is encountered instead of silently returning `None`.

**Priority:** LOW

---

### ARCH-09: PermissionResult Uses Plain Class Instead of Dataclass

**Description:** `PermissionResult` is a plain class with manual `__init__`, while every other type in the codebase follows a consistent convention: `dataclass(frozen=True)` for value objects and Pydantic `BaseModel` for cross-boundary data. `PermissionResult` is a value object (action, reason, risk_level) but does not follow the frozen dataclass convention.

**File Location:** `framework/agent_framework/safety/permissions.py:25-36`

**Current Impact:** Minor inconsistency with project conventions. No functional impact, but reduces codebase uniformity and signals that this module may have been written before conventions were established.

**Improvement Direction:** Convert to `@dataclass(frozen=True)` since it is an immutable value object. This aligns with the project convention for value types and enables structural equality comparison.

**Priority:** LOW

---

### ARCH-10: web_search Is a Documented Mock

**Description:** The `web_search` tool returns hardcoded fake search results for any query. It is documented as mock in its source comment, but its tool description does not indicate this status. Any agent using web search receives fabricated data that looks plausible, which can lead to incorrect decisions.

**File Location:** `framework/agent_framework/tools/builtin/search_tools.py:8-17`

**Current Impact:** Production safety concern if agents rely on search results for decision-making. The mock output looks realistic enough that LLM agents may trust the results without questioning their validity.

**Improvement Direction:** Gate behind a feature flag, or clearly document the mock status in the tool's description string so that LLM agents are aware the data is fabricated. Consider adding a `mock` annotation in the tool metadata.

**Priority:** LOW

---

### ARCH-11: TeamManager._loop Tightly Couples Lifecycle with AgentLoop Construction

**Description:** The `_loop` method handles 4 interleaved concerns in 50 lines: (1) AgentLoop construction with context setup including `extra` key injection (lines 68-81), (2) inbox reading and shutdown detection (lines 84-89), (3) prompt construction from inbox messages (lines 102-105), and (4) idle timeout management (lines 93-96, 100). Additionally, `TeamManager.__init__` accepts an untyped `team_dir` parameter (line 29) while usage suggests `Path`.

**File Location:** `framework/agent_framework/teams/manager.py:66-115`

**Current Impact:** Testing loop behavior (e.g., "does shutdown detection work?") requires constructing a full AgentLoop. The untyped `team_dir` parameter reduces IDE support. The 4 concerns have different change rates (AgentLoop construction is stable, timeout logic may change frequently) but cannot evolve independently.

**Improvement Direction:** Extract AgentLoop construction into a factory method. Add type annotation to `team_dir`. Consider separating inbox processing from lifecycle management into distinct methods.

**Priority:** LOW

---

### ARCH-12: LLMScoringRetriever Has No Fallback for LLM Failure

**Description:** The `retrieve` method calls the LLM for file selection and silently returns an empty list on JSON parse failure (line 94). If the LLM returns malformed JSON, all semantic memory retrieval silently fails with zero results and no indication to the caller. There is no fallback to simpler selection strategies.

**File Location:** `framework/agent_framework/memory/retriever.py:55-110`

**Current Impact:** Memory retrieval degrades silently without any warning to the user or calling code. Agents that depend on memory for context may produce lower-quality responses without any diagnostic signal.

**Improvement Direction:** Log a warning when LLM scoring fails. Consider a keyword-based fallback for semantic file selection when the LLM is unavailable. Alternatively, return all candidates (up to `max_results`) as a degraded result instead of an empty list.

**Priority:** LOW

---

## Summary

| Metric | Count |
|--------|-------|
| Total issues found | 12 |
| HIGH | 2 (ARCH-01, ARCH-02) |
| MEDIUM | 3 (ARCH-03, ARCH-04, ARCH-06) |
| LOW | 7 (ARCH-05, ARCH-07, ARCH-08, ARCH-09, ARCH-10, ARCH-11, ARCH-12) |

**Assessment:** The framework is well-structured with consistent patterns (frozen dataclasses for values, Pydantic for cross-boundary data, tool-return-error-not-exception convention). The two HIGH findings (AgentLoop parameter bloat and ToolRouter dispatch complexity) represent the most impactful architectural debt -- both are central infrastructure that all consumers interact with, and both will become harder to refactor as more subsystems are added. The MEDIUM findings (mutation logic, type safety, inactive permission guard) are functional but create friction for maintenance and extension. The seven LOW findings are quality-of-life improvements that can be addressed opportunistically during feature work.

**Cross-cutting concern:** The `ToolUseContext.extra` type-safety issue (ARCH-04) connects to ARCH-01 (subsystem integrations inject keys into `extra`) and ARCH-11 (TeamManager injects `teammate_name` and `message_bus` keys). As new subsystems are added, the number of magic-string keys in `extra` will grow. Addressing ARCH-04 would simultaneously simplify the integration story for ARCH-01.

---

*Report generated: 2026-05-28*
*Phase: 03-arch-review*
