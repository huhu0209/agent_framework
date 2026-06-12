---
phase: 17-framework
plan: 02
status: complete
requirements:
  - FW-LOGIC-05
---

## Plan 17-02: SearchClient 类封装消除全局可变状态

### What was built

Refactored search_tools from module-level globals to a SearchClient class instance:

- **SearchClient class**: Encapsulates `_semaphore` (asyncio.Semaphore) and `_client` (AsyncTavilyClient) as instance attributes
- **Module-level globals eliminated**: `_client` and `_semaphore` module-level variables removed
- **Registry integration**: `create_builtin_registry()` now creates a `SearchClient` instance and registers `search_client.search` as handler
- **Backward compatibility**: Module-level `web_search` delegates to default `SearchClient()` instance; `reset_client` delegates to `_default_client.reset`

### Key Files Modified

- `framework/agent_framework/tools/builtin/search_tools.py` — SearchClient class
- `framework/agent_framework/tools/builtin/__init__.py` — updated registration

### Tests

- All 998 tests pass
- 1 new backward-compatibility test added
- Existing search tools tests updated to match new API

### Commits

1. `93c8b7a` feat(17-02): encapsulate search_tools global state into SearchClient class

### Deviations

Tests updated to match new SearchClient API (module-level `_get_client`, `_semaphore`, `_client` symbols removed).

### Self-Check: PASSED
