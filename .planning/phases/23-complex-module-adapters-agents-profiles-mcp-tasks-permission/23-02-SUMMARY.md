---
phase: 23-complex-module-adapters-agents-profiles-mcp-tasks-permission
plan: 02
subsystem: config
tags: [config-loader, adapter-pattern, factory-method, tdd, mcp, tasks, permissions]

# Dependency graph
requires:
  - phase: 21-discovery-loader-agents-md-chain
    provides: ConfigLoader with discover() and load_settings() methods
  - plan: 23-01
    provides: AgentProfile.from_profile() classmethod
provides:
  - McpManager.from_loader() classmethod — multi-directory server config loading with project override
  - TaskManager default tasks_dir — Path.cwd() / ".agent-framework" / "tasks"
  - PermissionPipeline.from_loader() classmethod — profile + settings permission merge
affects: [phase-24-backend-integration]

# Tech tracking
tech-stack:
  added: []
  patterns: [from_loader @classmethod factory, None-sentinel for lazy default evaluation, model_copy for immutable merge]

key-files:
  created: []
  modified:
    - framework/agent_framework/tools/mcp/config.py
    - framework/agent_framework/tasks/manager.py
    - framework/agent_framework/safety/permissions.py

key-decisions:
  - "McpManager.from_loader iterates discover('mcp') in natural [global, project] order — project overwrites global on name collision with warning"
  - "TaskManager uses None-sentinel for tasks_dir default to evaluate Path.cwd() at call time, not module load time"
  - "PermissionPipeline.from_loader accepts optional _profile kwarg for test injection, delegates to AgentProfile.from_profile in production"
  - "Permission merge is additive (extend, not replace) — settings.permissions.allow/deny entries are appended if not already present"

requirements-completed: [ADP-06, ADP-07, ADP-08, ADP-09]

# Metrics
duration: 3min
completed: "2026-06-12"
---

# Phase 23 Plan 02: Complex Module Adapters — MCP, Tasks, Permissions Summary

**McpManager.from_loader() + TaskManager default path + PermissionPipeline.from_loader() — three module adapters enabling self-initialization from ConfigLoader with merge semantics and TDD**

## Performance

- **Duration:** 3 min
- **Started:** 2026-06-11T23:45:03Z
- **Completed:** 2026-06-12
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- McpManager.from_loader(loader) loads MCP server configs from ConfigLoader.discover("mcp") paths, project overrides global on name collision with warning
- TaskManager() with no args defaults tasks_dir to Path.cwd() / ".agent-framework" / "tasks" using None-sentinel for lazy evaluation
- PermissionPipeline.from_loader(loader, profile_name) loads profile via AgentProfile.from_profile, merges Settings.permissions allow/deny lists into profile without duplicates
- 14 new tests (6 + 2 + 6), all passing; 1121 total tests (up from 1107), zero regression

## Task Commits

Each task was committed atomically:

1. **Task 1: McpManager.from_loader()** - `3a4e7e8` (feat)
2. **Task 2: TaskManager default + PermissionPipeline.from_loader()** - `cf772dd` (feat)

## TDD Gate Compliance

- RED gate: Both tasks had failing tests before implementation (AttributeError on missing classmethod / TypeError on default param)
- GREEN gate: Both tasks had passing tests after implementation
- REFACTOR gate: One auto-fix during GREEN — TaskManager default evaluated Path.cwd() at module-load time, changed to None-sentinel for runtime evaluation

## Files Created/Modified
- `framework/agent_framework/tools/mcp/config.py` — Added from_loader @classmethod with natural-order iteration, servers.json loading, validation with warning on invalid entries, overwrite with warning on collision; added json, Path, ConfigLoader imports
- `framework/agent_framework/tasks/manager.py` — Changed __init__ tasks_dir from `Path` to `Path | None = None` with lazy default evaluation to `Path.cwd() / ".agent-framework" / "tasks"`
- `framework/agent_framework/safety/permissions.py` — Added from_loader @classmethod that loads profile via AgentProfile.from_profile, merges Settings.permissions allow/deny into profile lists; added ConfigLoader and Settings imports

## Decisions Made
- McpManager.from_loader iterates discover("mcp") in natural [global, project] order so last-write-wins gives project priority (same pattern as 23-01 AgentConfig.from_loader)
- TaskManager uses None-sentinel (`tasks_dir: Path | None = None`) rather than default expression because Path.cwd() is evaluated at module load time, not call time — the sentinel forces runtime evaluation
- PermissionPipeline.from_loader uses model_copy(update={...}) for immutable merge of permission lists, preserving all other profile fields
- from_loader accepts keyword-only `_profile` parameter for test injection — production code calls AgentProfile.from_profile(loader, profile_name) which was added in Plan 23-01

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed TaskManager default tasks_dir evaluation timing**
- **Found during:** Task 2 GREEN phase
- **Issue:** Plan specified `def __init__(self, tasks_dir: Path = Path.cwd() / ".agent-framework" / "tasks")` but Path.cwd() is evaluated at module load time, not at __init__ call time — test with monkeypatch.chdir() would fail
- **Fix:** Changed to `tasks_dir: Path | None = None` with `if tasks_dir is None: tasks_dir = Path.cwd() / ...` inside the method body
- **Files modified:** framework/agent_framework/tasks/manager.py
- **Commit:** cf772dd

## Issues Encountered

None beyond the deviation noted above.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness
- All three complex module adapters (MCP, Tasks, Permissions) complete
- Phase 23 fully complete — all 5 from_loader/from_profile factory methods across 5 modules
- config/ module remains a leaf dependency (no reverse imports from framework modules)

---
*Phase: 23-complex-module-adapters-agents-profiles-mcp-tasks-permission*
*Completed: 2026-06-12*

## Self-Check: PASSED

- All 3 modified source files exist on disk
- Both task commits found in git log (3a4e7e8, cf772dd)
- 1121 tests passing (1107 existing + 14 new)
