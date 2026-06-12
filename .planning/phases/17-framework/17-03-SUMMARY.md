---
phase: 17-framework
plan: 03
status: complete
requirements:
  - FW-LOGIC-01
  - FW-LOGIC-04
  - FW-LOGIC-08
---

## Plan 17-03: HITLManager 注入 ToolRouter + dispatch 复杂度拆分 + 移除 _dispatch_agent

### What was built

Core router improvements: HITL integration, dispatch decomposition, and dead code removal.

1. **Remove _dispatch_agent stub** (FW-LOGIC-08): Deleted the entire `_dispatch_agent` method and `agent__` prefix routing branch from dispatch(). Agent-prefixed tool calls now fall through to `_dispatch_builtin` (returns "unknown tool").

2. **Decompose dispatch + wire HITL** (FW-LOGIC-01, FW-LOGIC-04):
   - Added `hitl_manager: HITLManager | None = None` parameter to ToolRouter.__init__
   - Decomposed dispatch into 4 private methods:
     - `_check_permission` — handles DENY and ASK (HITL or fallback error)
     - `_run_pre_hooks` — pre-hook processing
     - `_execute_tool` — mcp/builtin execution + degrader fallback
     - `_run_post_hooks` — post-hook processing
   - ASK decision with HITLManager: calls `create_pending()` and awaits Future resolve
   - ASK without HITLManager: returns error (backward compatible)
   - `derive()` propagates hitl_manager to sub-routers

### Key Files Modified

- `framework/agent_framework/tools/router.py` — HITL integration, dispatch decomposition
- `framework/tests/test_tool_router.py` — 4 new HITL tests, updated existing tests

### Complexity

- ToolRouter.dispatch C901: 18 -> < 10 (verified by ruff)

### Tests

- 1002 tests pass (4 new HITL integration tests)

### Commits

1. `5efbc01` fix(17-03): remove _dispatch_agent stub and agent__ prefix routing
2. `f59b01f` test(17-03): add failing tests for HITL integration and dispatch decomposition (RED)
3. `0498cac` feat(17-03): wire HITLManager into ToolRouter and decompose dispatch (GREEN)

### Self-Check: PASSED
