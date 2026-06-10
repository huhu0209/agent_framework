---
phase: 17-framework
plan: 04
status: complete
requirements:
  - FW-LOGIC-03
  - FW-LOGIC-09
---

## Plan 17-04: AgentLoop.run 复杂度拆分 + _apply_changes 复杂度拆分

### What was built

Pure method extraction to reduce complexity — zero behavioral changes.

1. **AgentLoop.run complexity reduction** (FW-LOGIC-03): Extracted 5 private methods from `run()`:
   - `_init_messages` — init/resume message setup
   - `_fire_session_start_hook` — SessionStart hook firing
   - `_drain_notifications` — task_runner + team_manager notification drain
   - `_inject_plan_context` — plan context injection/removal
   - `_handle_tool_calls` — tool call dispatch (async generator)

   C901: 30 -> 12 (target was < 20)

2. **TaskManager._apply_changes complexity reduction** (FW-LOGIC-09): Extracted `_update_dependencies` method. Fixed `pending_writes` type annotation bug (`list[tuple[Task]]` -> `list[Task]`).

   C901: 11 -> 5 (target was <= 10)

### Key Files Modified

- `framework/agent_framework/agents/agent_loop.py` — 5 methods extracted
- `framework/agent_framework/tasks/manager.py` — 1 method extracted

### Tests

- 988 tests pass with zero behavioral changes

### Commits

1. `3810890` refactor(17-04): extract methods from AgentLoop.run to reduce C901 30->12
2. `ca28644` refactor(17-04): extract _update_dependencies from _apply_changes to reduce C901 11->5

### Self-Check: PASSED
