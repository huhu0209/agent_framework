---
phase: 17-framework
plan: 01
status: complete
requirements:
  - FW-LOGIC-02
  - FW-LOGIC-06
  - FW-LOGIC-07
  - FW-LOGIC-10
---

## Plan 17-01: _CRITICAL_TOOLS 构造注入 + ToolValidator enum/unknown + TypedDict extra + MCP 文档

### What was built

Four independent fixes in the framework tools and safety modules:

1. **PermissionPipeline critical_tools injection** (FW-LOGIC-02): Removed module-level `_CRITICAL_TOOLS` global; `PermissionPipeline.__init__` now accepts `critical_tools: frozenset[str] = frozenset()`. Backward compatible with empty default.

2. **ToolValidator enum + unknown validation** (FW-LOGIC-06): Added enum constraint checking and unknown parameter detection to `ToolValidator.validate()`. Returns clear error messages for violations.

3. **ToolContextExtra TypedDict** (FW-LOGIC-07): Defined `ToolContextExtra` TypedDict with known keys (skill_registry, memory_dir, memory_store, planning_session, worker_manager). ToolUseContext.extra remains `dict[str, Any]` for Pydantic compatibility.

4. **MCP ToolSpec schema-only documentation** (FW-LOGIC-10): Added comments explaining MCP ToolSpec objects are schema-only definitions with handler=None intentional.

### Key Files Modified

- `framework/agent_framework/safety/permissions.py` — constructor injection
- `framework/agent_framework/tools/validator.py` — enum + unknown validation
- `framework/agent_framework/tools/types.py` — ToolContextExtra TypedDict
- `framework/agent_framework/tools/mcp/config.py` — documentation comments

### Tests

- 3 new tests for critical_tools injection
- 5 new tests for enum/unknown validation
- All 998 tests pass (998 = 990 pre-existing + 8 new)

### Commits

1. `d705cb0` test(17-01): add failing tests for critical_tools constructor injection (RED)
2. `62209d5` feat(17-01): inject critical_tools into PermissionPipeline constructor (GREEN)
3. `09f9462` test(17-01): add failing tests for enum and unknown parameter validation (RED)
4. `c55391b` feat(17-01): add enum and unknown parameter validation to ToolValidator (GREEN)
5. `2415b87` feat(17-01): add ToolContextExtra TypedDict for extra field type hints
6. `4b2019b` docs(17-01): document MCP ToolSpec schema-only design

### Self-Check: PASSED
