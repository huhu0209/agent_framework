---
phase: 24-backend-integration-e2e-wiring-path-scoped-rules
plan: 01
subsystem: rules
tags: [rule-loader, fnmatch, path-filtering, leaf-dependency, tdd]
dependency_graph:
  requires: [config/loader, memory/frontmatter]
  provides: [rules/loader, rules/__init__]
  affects: []
tech_stack:
  added: [fnmatch (stdlib)]
  patterns: [frontmatter parsing, path-scoped filtering, barrel export]
key_files:
  created:
    - framework/agent_framework/rules/__init__.py
    - framework/agent_framework/rules/loader.py
    - framework/tests/test_rules.py
    - framework/tests/test_config_leaf.py
  modified: []
decisions:
  - fnmatch (stdlib) for path pattern matching — no new dependencies
  - rules with paths but no context_path are skipped (D-12)
  - unclosed frontmatter treated as no-frontmatter, load entire content
metrics:
  duration: 205s
  completed: "2026-06-12"
  tasks: 2
  tests_added: 10
  files_created: 4
---

# Phase 24 Plan 01: RuleLoader Module + Leaf Dependency Test Summary

RuleLoader loads rules/*.md from ConfigLoader.discover("rules") paths with frontmatter-based fnmatch path filtering; config/ leaf dependency test covers all files via AST analysis.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create RuleLoader module with tests | 0180b38, ee57f93 | rules/__init__.py, rules/loader.py, test_rules.py |
| 2 | Create config leaf dependency test | 645faca | test_config_leaf.py |

## Commits

| Hash | Message |
|------|---------|
| 0180b38 | test(24-01): add failing tests for RuleLoader |
| ee57f93 | feat(24-01): implement RuleLoader with fnmatch path filtering |
| 645faca | test(24-01): add comprehensive config leaf dependency tests |

## What Was Built

### RuleLoader module (rules/loader.py)
- `RuleLoader.load_rules(loader, context_path=None) -> str` static method
- `_parse_rule_document(text) -> (meta, body)` helper following skills/parser.py pattern
- `_parse_paths(value) -> list[str] | None` helper for comma-separated patterns
- Loads rules from `ConfigLoader.discover("rules")` in global-then-project order
- Rules without `paths` frontmatter always loaded (D-07)
- Rules with `paths` frontmatter filtered via `fnmatch(context_path, pattern)` (D-05/D-06)
- Rules with `paths` but no `context_path` are skipped (D-12)
- Unclosed frontmatter treated as no-frontmatter

### Barrel export (rules/__init__.py)
- `__all__ = ["RuleLoader"]` with one-line Chinese docstring

### Tests (test_rules.py, 8 tests)
- No rules directories returns empty string
- Rules without frontmatter loaded and joined by double newline
- Paths frontmatter matching context_path loads the rule
- Paths frontmatter non-matching context_path skips the rule
- No context_path loads only unscoped rules
- Discover order: global then project
- Malformed/unclosed frontmatter treated as no-frontmatter
- Comma-separated paths patterns parsed correctly

### Config leaf dependency test (test_config_leaf.py, 2 tests)
- AST scan of all config/*.py verifies no imports outside agent_framework.config
- Barrel __init__.py verified to only re-export from config submodules

## TDD Compliance

- RED commit: 0180b38 (failing tests)
- GREEN commit: ee57f93 (implementation, all tests pass)
- No REFACTOR needed

## Verification

- 10 new tests pass (8 RuleLoader + 2 leaf dependency)
- 59 existing framework tests pass (69 total, zero regressions)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed fnmatch pattern in comma-separated test**
- **Found during:** Task 1 GREEN phase
- **Issue:** Test used `src/**/*.py` pattern but fnmatch does not support `**` (glob-style recursive match). The pattern `tests/**/*.py` does not match `tests/test_foo.py` with fnmatch.
- **Fix:** Changed test pattern to `src/**.py, tests/**.py` which works correctly with fnmatch.
- **Files modified:** framework/tests/test_rules.py
- **Commit:** ee57f93

## Known Stubs

None.

## Threat Flags

None — no new security-relevant surface beyond what the threat model covers. RuleLoader reads files from ConfigLoader.discover() paths only (T-24-01 accept), parses as text only (T-24-02 accept), zero new packages (T-24-SC mitigate).

## Self-Check: PASSED

All 5 created files found. All 4 commit hashes verified.
