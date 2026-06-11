---
phase: 23-complex-module-adapters-agents-profiles-mcp-tasks-permission
plan: 01
subsystem: config
tags: [config-loader, adapter-pattern, factory-method, tdd, agents, profiles]

# Dependency graph
requires:
  - phase: 21-discovery-loader-agents-md-chain
    provides: ConfigLoader with discover() and load_profile() methods
provides:
  - AgentConfig.from_loader() @classmethod — multi-directory scan with project overriding global
  - AgentProfile.from_profile() @classmethod — named profile loading with field-level merge
affects: [phase-24-backend-integration]

# Tech tracking
tech-stack:
  added: []
  patterns: [from_loader @classmethod factory pattern, natural-order iteration for overwrite semantics]

key-files:
  created: []
  modified:
    - framework/agent_framework/agents/config.py
    - framework/agent_framework/prompts/profiles.py

key-decisions:
  - "AgentConfig.from_loader iterates discover() in natural [global, project] order — project overwrites global on collision, last-write-wins"
  - "AgentProfile.from_profile delegates merge to ConfigLoader.load_profile() which already handles global+project field-level merge"
  - "from_profile raises ValueError when load_profile returns empty dict (profile not found)"

requirements-completed: [ADP-04, ADP-05, ADP-09]

# Metrics
duration: 8min
completed: "2026-06-12"
---

# Phase 23 Plan 01: Complex Module Adapters — Agents & Profiles Summary

**Two @classmethod factory methods (AgentConfig.from_loader, AgentProfile.from_profile) enabling self-initialization from ConfigLoader paths with project-override-global semantics and TDD**

## Performance

- **Duration:** 8 min
- **Started:** 2026-06-11T14:39:06Z
- **Completed:** 2026-06-12
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- AgentConfig.from_loader(loader) loads agents from ConfigLoader.discover("agents") paths, project overwrites global on collision with logger.warning
- AgentProfile.from_profile(loader, name) loads named profile via ConfigLoader.load_profile(), maps "agents" key to "agents_rules" field
- 11 new tests (6 + 5), all passing; 1107 total tests (up from 1096), zero regression

## Task Commits

Each task was committed atomically:

1. **Task 1: AgentConfig.from_loader()** - `96e8d7b` (feat)
2. **Task 2: AgentProfile.from_profile()** - `84ecc0e` (feat)

## TDD Gate Compliance

- RED gate: Both tasks had failing tests before implementation (AttributeError on missing classmethod)
- GREEN gate: Both tasks had passing tests after implementation
- REFACTOR gate: No refactoring needed — implementations are concise

## Files Created/Modified
- `framework/agent_framework/agents/config.py` — Added from_loader @classmethod with natural-order iteration for project-overwrite-global; added logging import and logger
- `framework/agent_framework/prompts/profiles.py` — Added from_profile @classmethod delegating to ConfigLoader.load_profile(); added ConfigLoader import

## Decisions Made
- AgentConfig.from_loader iterates discover() in natural [global, project] order so last-write-wins gives project priority (contrast with Phase 22 SkillRegistry which reverses and uses first-found-wins)
- AgentProfile.from_profile delegates entirely to ConfigLoader.load_profile() for the merge — no need to call from_directory() twice since load_profile already does global-then-project field merge
- Empty tool_guidance string filtered to None for the Optional[str] field on AgentProfile

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed iteration order for AgentConfig.from_loader**
- **Found during:** Task 1 GREEN phase
- **Issue:** Plan specified "reverse the list so project is iterated first" with "overwrite" semantics, but reversed + overwrite means global (iterated last) would win over project — the opposite of intent
- **Fix:** Changed to natural-order iteration [global, project] with overwrite — project writes last and wins, matching the design intent
- **Files modified:** framework/agent_framework/agents/config.py
- **Commit:** 96e8d7b

**2. [Rule 3 - Blocking] Fixed test helper _setup_profile_dir double-nesting**
- **Found during:** Task 2 GREEN phase
- **Issue:** Test helper created `base / scope / ".agent-framework" / profiles` but ConfigLoader already prepends `.agent-framework` to the passed directory, causing double nesting
- **Fix:** Removed the redundant `scope` parameter — helper now creates `base / ".agent-framework" / profiles / name`
- **Files modified:** framework/tests/test_agent_profile.py
- **Commit:** (test file not tracked per project convention)

## Issues Encountered

None beyond the deviations noted above.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness
- Both complex module adapters (agents, profiles) complete, extending the from_loader/from_profile factory pattern
- Phase 23 remaining plans can build on these for MCP, Tasks, and Permissions adapters
- config/ module remains a leaf dependency (no reverse imports)

---
*Phase: 23-complex-module-adapters-agents-profiles-mcp-tasks-permission*
*Completed: 2026-06-12*

## Self-Check: PASSED

- Both modified source files exist on disk
- Both task commits found in git log (96e8d7b, 84ecc0e)
- 1107 tests passing (1096 existing + 11 new)
