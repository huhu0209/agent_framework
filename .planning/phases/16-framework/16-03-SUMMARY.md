---
phase: 16-framework
plan: 03
subsystem: prompts/skills
tags: [xml-boundary, prompt-injection-defense, tdd]
dependency_graph:
  requires: []
  provides: [FW-SEC-04, FW-SEC-05]
  affects: [framework/agent_framework/prompts/assembler.py]
tech_stack:
  added: []
  patterns: [XML boundary markers for system prompt blocks, trust-level tagging]
key_files:
  created: []
  modified:
    - framework/agent_framework/prompts/assembler.py
    - framework/tests/test_prompt_assembler.py
decisions:
  - Block-to-tag mapping as module-level dict for clarity and extensibility
  - user-provided tag (not "user") to explicitly signal untrusted source
  - No content scanning for skills (per D-08) — XML boundary tags only
metrics:
  duration: 5m 21s
  completed: "2026-06-10"
  tasks: 2
  files_modified: 2
  tests_added: 9
  tests_passing: 973
---

# Phase 16 Plan 03: Prompt XML Boundary Markers Summary

XML boundary tags added to PromptAssembler.render() — each PromptBlock wrapped in its own XML tag, user-provided content explicitly marked as untrusted source.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | assembler.py XML tag wrapping + user-provided marking | 34c869e, 5b21af4 | assembler.py, test_prompt_assembler.py |
| 2 | Verify SkillRegistry XML wrapping (no changes needed) | N/A (verification-only) | registry.py |

## What Changed

### framework/agent_framework/prompts/assembler.py
- Added `_BLOCK_TAGS` module-level mapping: SOUL->soul, AGENTS_RULES->instructions, IDENTITY->identity, USER->user-provided, SKILLS->skills, TOOL_GUIDANCE->tool-guidance
- Modified `render()` to wrap each non-empty block content in its XML tag
- `assemble()` unchanged — returns raw PromptBlock list as before

### framework/tests/test_prompt_assembler.py
- Added 9 new tests in `TestRenderXmlTags` class covering all 6 block types, empty profile, assemble() no-XML invariant, and full profile integration

### framework/agent_framework/skills/registry.py
- No changes — `_format_skill_body()` already wraps in `<skill name="...">...</skill>` XML tags

## Decisions Made

1. **Module-level dict for tag mapping** — Clean, declarative, easy to extend with new block types
2. **`user-provided` tag name** — Explicitly signals untrusted origin to LLM, distinct from a generic "user" tag
3. **No content scanning for skills** — Per D-08, skills are developer-controlled; XML boundary markers provide sufficient defense without over-engineering

## Deviations from Plan

None — plan executed exactly as written.

## Verification Results

- `pytest tests/ -v`: 973 passed in 8.13s
- `grep "user-provided" assembler.py`: Found in _BLOCK_TAGS mapping
- `grep "<skill" registry.py`: Found at line 190 in `_format_skill_body`

## TDD Gate Compliance

- RED commit: `34c869e` — 7 failing tests for XML tag wrapping
- GREEN commit: `5b21af4` — all 20 prompt assembler tests pass
- REFACTOR: Not needed — implementation is clean and minimal
