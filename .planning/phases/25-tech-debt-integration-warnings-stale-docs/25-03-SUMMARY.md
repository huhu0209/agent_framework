---
phase: 25-tech-debt-integration-warnings-stale-docs
plan: 03
status: complete
executor: orchestrator-inline
started: "2026-06-12T06:33:00Z"
finished: "2026-06-12T06:37:00Z"
---

# Plan 25-03 Summary: README.md Update

## Objective
Update README.md to reflect current v0.0.6 state — fix class names, add missing modules, update roadmap.

## What Was Done

### Task 1: Fix class names and add missing modules ✅
- **D-04a**: `CommandRouter` → `CommandDispatcher` in module overview table
- **D-04b**: Added `config/` entry in project structure tree (after `commands/`)
- **D-04b**: Added `rules/` entry in project structure tree (after `prompts/`)
- **D-04d**: Added `ConfigLoader`, `Settings` row and `RuleLoader` row to module overview table
- **D-04e**: Test count already correct in Roadmap (1146 for v0.0.6, historical counts preserved)

### Task 2: Update Roadmap ✅
- Replaced phase-by-phase table (stopped at Phase 13 "Plugin — 计划中") with milestone-level view
- All 6 milestones shown with correct dates and test counts
- No reference to "Plugin" remains

## Verification
- Zero `CommandRouter` occurrences
- `config/` appears 2x (structure + table), `rules/` appears 2x
- `ConfigLoader` appears 2x, `RuleLoader` appears 2x
- Roadmap covers v0.0.1 through v0.0.6
- Test count 1146 present

## Files Modified
- `README.md` — project structure, module overview table, roadmap section
