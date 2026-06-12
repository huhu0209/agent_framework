---
phase: 24-backend-integration-e2e-wiring-path-scoped-rules
plan: 02
subsystem: prompts
tags: [assembler, config-loader, rule-loader, block-order, integration]
dependency_graph:
  requires: [config/loader, rules/loader, prompts/profiles]
  provides: [prompts/assembler-updated]
  affects: [agents/agent_loop]
tech_stack:
  added: []
  patterns: [ConfigLoader injection, RuleLoader delegation, ordered block construction]
key_files:
  created:
    - framework/tests/test_prompt_assembler.py
  modified:
    - framework/agent_framework/prompts/assembler.py
decisions:
  - assemble() takes ConfigLoader as first parameter per D-09
  - Block order: USER_PROVIDED -> RULES -> SOUL -> AGENTS_RULES -> IDENTITY -> SKILLS -> TOOL_GUIDANCE per D-10
  - USER_PROVIDED from loader.load_agents_md(), RULES from RuleLoader.load_rules() per D-11
  - Old USER block (from profile.user_context) removed; content now from AGENTS.md chain
metrics:
  duration: 285s
  completed: "2026-06-12"
  tasks: 2
  tests_added: 26
  files_created: 1
  files_modified: 1
---

# Phase 24 Plan 02: PromptAssembler Integration Summary

PromptAssembler rewritten with assemble(loader, profile, context_path) signature, new D-10 block order, and ConfigLoader/RuleLoader integration; 26 tests verify all blocks and XML rendering.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Modify PromptAssembler with new signature and block order | bbbca5d | assembler.py |
| 2 | Add PromptAssembler tests for new signatures | 2004934 | test_prompt_assembler.py |

## Commits

| Hash | Message |
|------|---------|
| bbbca5d | feat(24-02): modify PromptAssembler with new signature and block order |
| 2004934 | test(24-02): add PromptAssembler tests for new signatures |

## What Was Built

### PromptAssembler modifications (assembler.py)
- `assemble(self, loader: ConfigLoader, profile: AgentProfile, context_path: str | None = None) -> list[PromptBlock]` per D-09
- `render(self, loader: ConfigLoader, profile: AgentProfile, context_path: str | None = None) -> str` updated signature
- Block construction order per D-10: USER_PROVIDED -> RULES -> SOUL -> AGENTS_RULES -> IDENTITY -> SKILLS -> TOOL_GUIDANCE
- USER_PROVIDED block from `loader.load_agents_md()` per D-11
- RULES block from `RuleLoader.load_rules(loader, context_path)` per D-11
- Old USER block (from `profile.user_context`) removed
- `_BLOCK_TAGS` updated: added `USER_PROVIDED` and `RULES`, removed old `USER`
- Added `ConfigLoader` and `RuleLoader` imports at top level (not TYPE_CHECKING)
- `__init__` unchanged per A4

### Tests (test_prompt_assembler.py, 26 tests)
- TestPromptAssembler (9 tests): empty profile, soul, agents_rules, identity, user_context not separate block, cache breakpoints, render to string, render empty, block order
- TestPromptAssemblerWithSkills (4 tests): skills block present, absent without registry, not cache breakpoint, position before TOOL_GUIDANCE
- TestRenderXmlTags (7 tests): soul, instructions, identity, tool-guidance, user-provided, rules, full profile tags
- TestUserProvidedFromLoader (2 tests): USER_PROVIDED from AGENTS.md content, empty when no AGENTS.md
- TestRulesBlockFromLoader (2 tests): RULES from rule files, empty when no rules
- TestContextPathForwarding (2 tests): context_path matching loads scoped rules, non-matching skips scoped rules

## Verification

- 26 new tests pass
- 95 total framework tests pass (zero regressions)
- agent_loop.py still references old `render(self.profile)` signature — caller update deferred to Plan 03

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Test file was gitignored**
- **Found during:** Task 2 commit
- **Issue:** `.gitignore` contains `framework/tests/` pattern. Existing test files were tracked with `git add -f`. New test file needed the same treatment.
- **Fix:** Used `git add -f` to force-add the file.
- **Files modified:** none (git operation only)
- **Commit:** 2004934

**2. [Rule 3 - Blocking] pytest vs python -m pytest path resolution**
- **Found during:** Task 2 verification
- **Issue:** Direct `pytest` command fails with ModuleNotFoundError for `agent_framework.config`, but `python -m pytest` works because editable install path hooks are loaded correctly.
- **Fix:** Used `python -m pytest` for all test commands.
- **Files modified:** none (command adjustment only)

## Known Stubs

None.

## Threat Flags

None — no new security-relevant surface. ConfigLoader and RuleLoader inputs are strings from controlled file reads (T-24-03 accept, T-24-04 accept, T-24-SC mitigate: zero new packages).

## Self-Check: PASSED

- assembler.py modified and committed (bbbca5d)
- test_prompt_assembler.py created and committed (2004934)
- All 95 framework tests pass
