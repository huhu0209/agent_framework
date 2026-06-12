---
phase: 15-framework
plan: 01
subsystem: infra
tags: [ruff, dead-code, static-analysis, linting]

requires: []
provides:
  - "32 F401/F821 issues resolved — zero ruff warnings"
  - "logger properly defined in agent_loop.py"
  - "httpx import under TYPE_CHECKING guard in llm/base.py"
affects: [framework]

tech-stack:
  added: []
  patterns: ["TYPE_CHECKING guard for optional runtime imports"]

key-files:
  created: []
  modified:
    - framework/agent_framework/agents/agent_loop.py
    - framework/agent_framework/llm/base.py
    - framework/agent_framework/agents/config.py
    - framework/agent_framework/agents/reflection.py
    - framework/agent_framework/agents/sub_agent.py
    - framework/agent_framework/hooks/manager.py
    - framework/agent_framework/llm/providers/anthropic_provider.py
    - framework/agent_framework/llm/providers/deepseek_provider.py
    - framework/agent_framework/llm/providers/openai_provider.py
    - framework/agent_framework/llm/retry.py
    - framework/agent_framework/llm/streaming.py
    - framework/agent_framework/llm/transform/_deepseek.py
    - framework/agent_framework/llm/transform/_openai.py
    - framework/agent_framework/orchestrator/worker_agent.py
    - framework/agent_framework/tasks/runner.py
    - framework/agent_framework/teams/manager.py
    - framework/agent_framework/tools/context/token_counter.py

key-decisions:
  - "Used ruff --fix for bulk F401 removal (trusted static analysis over manual edits)"
  - "Added httpx under TYPE_CHECKING to avoid runtime import cost"

patterns-established:
  - "TYPE_CHECKING guard pattern for optional heavy imports (httpx in llm/base.py)"

requirements-completed: [FW-DEAD-01, FW-DEAD-02, FW-DEAD-03, FW-DEAD-04, FW-DEAD-05, FW-DEAD-06, FW-SEC-01]

duration: 3min
completed: 2026-06-10
---

# Phase 15: Framework 死代码与快速修复 Summary

**清除 32 个 ruff F401/F821 问题 — logger 定义、httpx TYPE_CHECKING guard、29 个未使用 import 自动移除**

## Performance

- **Duration:** 3 min
- **Started:** 2026-06-10
- **Completed:** 2026-06-10
- **Tasks:** 3
- **Files modified:** 17

## Accomplishments
- Fixed 2 F821 errors: added `logger = logging.getLogger(__name__)` in agent_loop.py, added httpx under TYPE_CHECKING guard in llm/base.py
- Removed 29 F401 unused imports via `ruff --fix` across 15 files
- 964 tests pass, zero regressions

## Task Commits

1. **Task 1: Fix F821 undefined names** - `9deeb45` (fix)
2. **Task 2: Remove 29 F401 unused imports** - `0ab10ab` (fix)
3. **Task 3: Full test suite verification** - no code changes (verification passed)

## Files Created/Modified
- `framework/agent_framework/agents/agent_loop.py` - Added logger definition, removed unused `field` import
- `framework/agent_framework/llm/base.py` - Added httpx TYPE_CHECKING guard
- `framework/agent_framework/llm/providers/anthropic_provider.py` - 6 unused imports removed
- `framework/agent_framework/llm/providers/openai_provider.py` - 5 unused imports removed
- `framework/agent_framework/llm/providers/deepseek_provider.py` - 3 unused imports removed
- 12 other files - 1-2 unused imports removed each

## Decisions Made
None - followed plan as specified.

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
None

## Next Phase Readiness
- Zero ruff warnings, ready for Phase 16 (security fixes)
- No breaking changes, all 964 tests pass

---
*Phase: 15-framework*
*Completed: 2026-06-10*
