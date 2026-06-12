---
phase: "07"
plan: "02"
subsystem: agents
tags: [config, frontmatter, agent-config, tool-filtering]
dependency_graph:
  requires: [memory/frontmatter.py, agents/agent_loop.py, tools/router.py, tools/registry.py]
  provides: [agents/config.py, agents/__init__.py]
  affects: [agents/]
tech_stack:
  added: [dataclass, parse_frontmatter reuse]
  patterns: [declarative-agent-config, md-frontmatter-config]
key_files:
  created:
    - framework/agent_framework/agents/config.py
    - framework/tests/test_agent_config.py
    - framework/tests/fixtures/agents/research-agent.md
    - framework/tests/fixtures/agents/minimal-agent.md
  modified:
    - framework/agent_framework/agents/__init__.py
decisions:
  - Reused parse_frontmatter() from memory/frontmatter.py for metadata extraction
  - Body after second --- separator becomes system_prompt
  - tools field is comma-separated list, None means all tools
  - agent_from_config uses router.derive() + registry.subset() for tool filtering
metrics:
  duration: 146s
  completed: "2026-05-29"
  tasks: 3
  files: 5
---

# Phase 07 Plan 02: Agent 配置化 Summary

Declarative Agent configuration via .md files with frontmatter metadata and body system_prompt, supporting tool filtering on AgentLoop creation.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Implement Agent config system | 1798c32 | config.py, __init__.py |
| 2 | Write agent config tests | 7b8f46b | test_agent_config.py, fixtures/agents/*.md |
| 3 | Verify zero regression | (no changes) | - |

## Key Changes

### config.py — AgentConfig dataclass + helpers

- `AgentConfig` dataclass: name, system_prompt, description, model, max_steps, tools
- `parse_agent_config()`: parses frontmatter for metadata, extracts body as system_prompt, validates non-empty
- `load_agent_configs()`: scans directory for .md files, returns dict keyed by name, detects duplicates
- `agent_from_config()`: creates AgentLoop with optional tool filtering via `router.derive(registry.subset(...))`
- `_extract_body()`: splits on `---`, returns text after second separator

### agents/__init__.py — new exports

Added: `AgentConfig`, `parse_agent_config`, `load_agent_configs`, `agent_from_config`

### Test coverage

13 test cases across 3 test classes:
- `TestParseAgentConfig`: full parse, minimal parse, missing name, empty prompt
- `TestLoadAgentConfigs`: directory loading, duplicates, empty directory
- `TestAgentFromConfig`: tool filtering, all tools, type checks, field propagation

## Deviations from Plan

None - plan executed exactly as written.

## Self-Check

- config.py exists and imports successfully
- test_agent_config.py: 13/13 passed
- Full suite: 737 passed, 0 failed
