---
phase: 22-simple-module-adapters-skills-hooks-commands
plan: 01
subsystem: config
tags: [config-loader, adapter-pattern, factory-method, tdd]

# Dependency graph
requires:
  - phase: 21-discovery-loader-agents-md-chain
    provides: ConfigLoader with discover() method returning [global, project] paths
provides:
  - SkillRegistry.from_loader() @classmethod — project-overrides-global semantics
  - HookManager.from_loader() @classmethod — global-first-then-project hook loading
  - CommandDispatcher.from_loader() @classmethod — auto-populates SkillRegistry from loader
affects: [phase-23-complex-module-adapters, phase-24-backend-integration]

# Tech tracking
tech-stack:
  added: []
  patterns: [from_loader @classmethod factory pattern, reversed discover() for priority override]

key-files:
  created: []
  modified:
    - framework/agent_framework/skills/registry.py
    - framework/agent_framework/hooks/manager.py
    - framework/agent_framework/commands/dispatcher.py

key-decisions:
  - "SkillRegistry.from_loader reverses discover() [global,project] -> [project,global] so __init__ first-found-wins gives project priority"
  - "HookManager.from_loader iterates discover() in natural [global,project] order, loading global hooks.json first then appending project"
  - "CommandDispatcher.from_loader delegates entirely to SkillRegistry.from_loader — no command directory scanning"

patterns-established:
  - "from_loader @classmethod pattern: accept ConfigLoader, call discover(), adapt result for constructor"
  - "Reversed-discover pattern for first-found-wins semantics (project overrides global)"
  - "Natural-order iteration for append semantics (global loaded first, project appended)"

requirements-completed: [ADP-01, ADP-02, ADP-03, ADP-09]

# Metrics
duration: 4min
completed: "2026-06-11"
---

# Phase 22 Plan 01: Simple Module Adapters Summary

**Three from_loader() @classmethod factory methods on SkillRegistry, HookManager, and CommandDispatcher, each 3-8 lines, enabling self-initialization from ConfigLoader.discover() paths with TDD**

## Performance

- **Duration:** 4 min
- **Started:** 2026-06-11T13:13:39Z
- **Completed:** 2026-06-11T13:17:51Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments
- SkillRegistry.from_loader(loader) creates registry from discover("skills") with project-override-global via reversed scan order
- HookManager.from_loader(loader, trusted=False) loads hooks from all discovered hooks.json files, global first then project appended
- CommandDispatcher.from_loader(loader) delegates to SkillRegistry.from_loader for auto-populated skill registry
- 17 new tests (5 + 7 + 5), all passing; 1096 total tests (up from 1079), zero regression

## Task Commits

Each task was committed atomically:

1. **Task 1: SkillRegistry.from_loader()** - `7ee58f3` (feat)
2. **Task 2: HookManager.from_loader()** - `e357d05` (feat)
3. **Task 3: CommandDispatcher.from_loader()** - `70615b5` (feat)

## TDD Gate Compliance

- RED gate: All 3 tasks had failing tests before implementation (AttributeError on missing from_loader)
- GREEN gate: All 3 tasks had passing tests after implementation
- REFACTOR gate: No refactoring needed — implementations are 3-8 lines each

## Files Created/Modified
- `framework/agent_framework/skills/registry.py` - Added from_loader @classmethod with reversed discover() for project-priority
- `framework/agent_framework/hooks/manager.py` - Added from_loader @classmethod with natural-order iteration and trusted parameter
- `framework/agent_framework/commands/dispatcher.py` - Added from_loader @classmethod delegating to SkillRegistry.from_loader

## Decisions Made
- SkillRegistry reverses discover() order because its __init__ uses first-found-wins semantics, so [project, global] gives project priority
- HookManager iterates discover() in natural order because load_from_json appends to internal list, so global hooks are registered first
- CommandDispatcher does not scan command directories — it only wraps SkillRegistry.from_loader per D-07

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- All three simple module adapters complete, establishing the from_loader() pattern
- Phase 23 can replicate this pattern for complex modules (Agents, Profiles, MCP, Tasks, Permissions)
- config/ module remains a leaf dependency (no reverse imports verified)

---
*Phase: 22-simple-module-adapters-skills-hooks-commands*
*Completed: 2026-06-11*

## Self-Check: PASSED

- All 3 modified files exist on disk
- All 3 task commits found in git log (7ee58f3, e357d05, 70615b5)
- 1096 tests passing (1079 existing + 17 new)
