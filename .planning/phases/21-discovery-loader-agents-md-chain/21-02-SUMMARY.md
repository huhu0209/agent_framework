---
phase: 21-discovery-loader-agents-md-chain
plan: 02
subsystem: config
tags: [config, loader, agents-md, instruction-chain, profile-loading, tdd, git-root]

# Dependency graph
requires:
  - phase: "21-01"
    provides: "ConfigLoader class with load_settings() and discover()"
provides:
  - "ConfigLoader.load_agents_md() with full instruction chain concatenation"
  - "ConfigLoader.load_profile() with dual-path merge"
  - "_read_text_file() helper for silent file reads"
  - "_find_git_root() for .git boundary detection"
  - "PROFILE_FILES constant for profile subfile names"
affects:
  - "Phase 24 PromptAssembler will consume load_agents_md() output"
  - "Phase 23 adapter will consume load_profile() dict output"

# Tech tracking
tech-stack:
  added: []
  patterns: [instruction-chain, dual-path-merge, git-root-boundary]

key-files:
  created: []
  modified:
    - framework/agent_framework/config/loader.py
    - framework/tests/test_loader.py

key-decisions:
  - "load_agents_md() returns str with '# Source:' headers, empty list returns '' (D-08)"
  - "Parent chain traversed from .git root down to project_dir, low-to-high priority (D-06)"
  - "_find_git_root limits traversal to .git boundary, no infinite upward walk (T-21-05)"
  - "load_profile() returns dict[str, str], not AgentProfile object (leaf dependency)"
  - "Project non-empty fields override global fields in profile merge (D-10)"

patterns-established:
  - "Instruction chain: global -> project -> local -> parent dirs -> user.md"
  - "Dual-path profile merge: load global first, overlay project non-empty fields"
  - "Silent file read: _read_text_file returns empty string for missing files"

requirements-completed: [INS-01, INS-02, INS-04, INS-05]

# Metrics
duration: 4min
completed: 2026-06-11
---

# Phase 21 Plan 02: AGENTS.md Chain + Profile Loading Summary

**load_agents_md() 5-layer instruction chain (global/project/local/parent-chain/user.md) and load_profile() dual-path merge with non-empty override**

## Performance

- **Duration:** 4 min
- **Started:** 2026-06-11T11:33:18Z
- **Completed:** 2026-06-11T11:37:28Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- load_agents_md() concatenates 5 instruction layers with "# Source:" headers and double-newline separation
- Parent directory chain traverses from .git root down to project_dir with correct priority ordering
- load_profile() merges global and project profiles, project non-empty fields override global
- 17 new tests (9 for load_agents_md, 8 for load_profile), 54 total tests pass with zero regression

## Task Commits

Each task was committed atomically (TDD RED-GREEN):

1. **Task 1 RED: load_agents_md tests** - `4071e6e` (test)
2. **Task 1 GREEN: load_agents_md implementation** - `812f929` (feat)
3. **Task 2 RED: load_profile tests** - `5effffe` (test)
4. **Task 2 GREEN: load_profile implementation** - `9f409d5` (feat)

## Files Created/Modified
- `framework/agent_framework/config/loader.py` - Added _read_text_file, _find_git_root, _parent_agents_chain, load_agents_md, PROFILE_FILES, load_profile
- `framework/tests/test_loader.py` - Added TestLoadAgentsMd (9 tests) and TestLoadProfile (8 tests)

## Decisions Made
- _read_text_file() reimplemented in config/ (3 lines) instead of importing from prompts/profiles.py to maintain leaf dependency
- PROFILE_FILES placed at module level before class definition for clarity
- Parent chain labels use try/except for relative_to() to handle edge cases where paths are not relative

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Missing parents=True in test_parent_chain_direction**
- **Found during:** Task 1 GREEN phase
- **Issue:** Test created `.git` directory without `parents=True`, parent `repo/` did not exist
- **Fix:** Added `parents=True` to `.mkdir()` call in test
- **Files modified:** framework/tests/test_loader.py
- **Verification:** All 9 TestLoadAgentsMd tests pass
- **Committed in:** 812f929 (Task 1 GREEN commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Test-only fix, no impact on production code.

## Issues Encountered
None - implementation followed plan specification closely.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- ConfigLoader now has full capabilities: load_settings(), discover(), load_agents_md(), load_profile()
- Phase 22 SkillRegistry/HookManager can use discover() for path discovery
- Phase 23 adapter can consume load_profile() dict output to create AgentProfile objects
- Phase 24 PromptAssembler can inject load_agents_md() output into system prompt

## TDD Gate Compliance

- RED: `4071e6e` - test(21-02): failing tests for load_agents_md instruction chain
- GREEN: `812f929` - feat(21-02): implement load_agents_md with instruction chain loading
- RED: `5effffe` - test(21-02): failing tests for load_profile dual-path merge
- GREEN: `9f409d5` - feat(21-02): implement load_profile with dual-path merge

## Test Coverage

| Test Class | Tests | Coverage |
|------------|-------|----------|
| TestConfigLoaderConstruction | 3 | Default and custom path construction |
| TestLoadSettings | 5 | No-config defaults, global override, 4-level chain, env var, JSON error |
| TestDiscover | 6 | Both/one/none exist, unknown type, all 8 types, file-not-dir skip |
| TestLeafDependency | 1 | No non-config framework imports |
| TestBarrelExport | 2 | ConfigLoader in __all__, importable from barrel |
| TestLoadAgentsMd | 9 | Full chain, partial, empty, parent direction, no-git, git-at-project, separation, header format, empty skip |
| TestLoadProfile | 8 | Global-only, project override, non-empty override, empty-no-override, no-profile, partial, 4 subfiles, return type |

---
*Phase: 21-discovery-loader-agents-md-chain*
*Completed: 2026-06-11*

## Self-Check: PASSED

- FOUND: framework/agent_framework/config/loader.py
- FOUND: framework/tests/test_loader.py
- FOUND: .planning/phases/21-discovery-loader-agents-md-chain/21-02-SUMMARY.md
- FOUND: 4071e6e (Task 1 RED)
- FOUND: 812f929 (Task 1 GREEN)
- FOUND: 5effffe (Task 2 RED)
- FOUND: 9f409d5 (Task 2 GREEN)
