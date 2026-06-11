---
phase: 23-complex-module-adapters-agents-profiles-mcp-tasks-permission
reviewed: 2026-06-12T08:00:00Z
depth: standard
files_reviewed: 5
files_reviewed_list:
  - framework/agent_framework/agents/config.py
  - framework/agent_framework/prompts/profiles.py
  - framework/agent_framework/safety/permissions.py
  - framework/agent_framework/tasks/manager.py
  - framework/agent_framework/tools/mcp/config.py
findings:
  critical: 0
  warning: 2
  info: 3
  total: 5
status: issues_found
---

# Phase 23: Code Review Report

**Reviewed:** 2026-06-12T08:00:00Z
**Depth:** standard
**Files Reviewed:** 5
**Status:** issues_found

## Summary

Reviewed 5 source files that add `from_loader()` and `from_profile()` factory methods to existing classes (AgentConfig, AgentProfile, PermissionPipeline, McpManager, TaskManager). The implementation is purely additive with no existing constructors modified.

Overall quality is solid: merge semantics are correct (project overrides global), immutable patterns are followed (dataclasses.replace, model_copy), error handling is comprehensive, and import direction is correct (config/ is a leaf with no reverse imports). 102 tests all pass.

Issues found: 0 Critical, 2 Warning, 3 Info.

## Critical Issues

No critical issues found.

## Warnings

### WR-01: McpManager.start() overly broad exception swallows tool registration conflicts

**File:** `framework/agent_framework/tools/mcp/config.py:111-119`
**Issue:** The `start()` method wraps the entire per-server block (transport creation, connection, AND tool registration) in a single `except Exception`. If `registry.register()` raises a `ValueError` due to a tool name conflict (e.g., two MCP servers with the same name somehow register the same prefixed tool), the error message says "启动失败" (startup failed), which misleads the operator into thinking it is a connection issue rather than a name conflict. Additionally, if `client.connect()` succeeds but `_register_tools()` fails, the connected client is never stored in `self._clients` and never gets cleaned up during `shutdown()`, creating a leaked connection.

**Fix:** Separate the connection and registration try/except blocks, or store the client before registering tools, and use a more specific error message for registration failures:

```python
async def start(self, registry: ToolRegistry) -> None:
    for cfg in self._configs:
        try:
            transport = self._create_transport(cfg)
            client = McpClient(cfg.name, transport)
            await client.connect()
        except Exception as e:
            logger.warning("MCP server '%s' 连接失败，跳过: %s", cfg.name, e)
            continue

        try:
            self._register_tools(client, cfg, registry)
            self._clients[cfg.name] = client
        except Exception as e:
            logger.warning("MCP server '%s' 工具注册失败，跳过: %s", cfg.name, e)
            try:
                await client.close()
            except Exception:
                pass
```

### WR-02: McpManager.start() uses f-string in logger.warning instead of %-style formatting

**File:** `framework/agent_framework/tools/mcp/config.py:119`
**Issue:** Line 119 uses `logger.warning(f"MCP server '{cfg.name}' 启动失败，跳过: {e}")` while all other logging calls in the same file use `%`-style lazy formatting (e.g., line 89, 98, 102, 148). F-string formatting evaluates immediately even if the log level is filtered out, wasting CPU cycles. More importantly, this inconsistency makes the codebase harder to maintain.

**Fix:**
```python
# Line 119: Change from:
logger.warning(f"MCP server '{cfg.name}' 启动失败，跳过: {e}")
# To:
logger.warning("MCP server '%s' 启动失败，跳过: %s", cfg.name, e)
```

## Info

### IN-01: PermissionPipeline.from_loader converts None tool lists to empty lists, changing check() branch semantics

**File:** `framework/agent_framework/safety/permissions.py:73-86`
**Issue:** When `profile.allowed_tools` is `None` (meaning "no whitelist filter, pass through"), `from_loader` converts it to `[]` via `list(profile.allowed_tools or [])`. After this transformation, the `is not None` guard in `check()` (line 113) always evaluates to `True`, meaning the ALLOW whitelist check always runs. In the current logic this does not produce incorrect behavior because `tool_name in []` is always `False`, so it still falls through to ASK -- the same outcome as when `allowed_tools is None`. However, this is a fragile equivalence that could break if the check logic is refactored to distinguish between "no whitelist" and "empty whitelist."

**Fix:** If the distinction matters, preserve `None` semantics:
```python
allowed = list(profile.allowed_tools) if profile.allowed_tools is not None else None
# Then merge settings allow list...
```
If the distinction does not matter (current behavior), add a comment documenting this intentional normalization.

### IN-02: TaskManager._read does not validate task ID format from disk

**File:** `framework/agent_framework/tasks/manager.py:127-139`
**Issue:** `_read()` loads any JSON from a file matching `task_*.json` without validating that the `id` field in the JSON matches the filename convention (numeric). The `_path()` method enforces numeric IDs, and `_load_max_id()` has its own parsing. But if a corrupted or manually edited file contains a non-numeric `id`, `_read()` will happily return a `Task` with that ID, which will then cause unexpected behavior in `_validate_transition()` or `list_all()` (the `int(t.id)` sort key on line 101 would crash).

**Fix:** Add a guard in `_read()`:
```python
def _read(self, path: Path) -> Task:
    data = json.loads(path.read_text())
    task_id = data.get("id", "")
    if not task_id.isdigit():
        raise ValueError(f"Corrupted task file {path}: non-numeric id '{task_id}'")
    # ... rest of parsing
```

### IN-03: AgentProfile.from_profile does not map permission-related fields

**File:** `framework/agent_framework/prompts/profiles.py:57-79`
**Issue:** `from_profile()` maps `soul`, `agents` -> `agents_rules`, `identity`, and `tool_guidance`, but does not populate `allowed_tools`, `disallowed_tools`, or `permission_mode`. These fields remain at their Pydantic defaults (`None`, `None`, `"ask"`). This is not a bug (the fields may not be intended to come from profile files), but it means the profile is incomplete relative to the `AgentProfile` schema. `PermissionPipeline.from_loader` compensates by merging settings-level permissions, but the profile-level tool lists are always empty when loaded via `from_profile`.

**Fix:** If profile files should support tool permissions, add mapping for these fields. If not, document that `from_profile` is intentionally limited to prompt content fields only.

---

_Reviewed: 2026-06-12T08:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
