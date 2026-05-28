---
phase: 02-security
reviewed: 2026-05-28T12:00:00Z
depth: standard
files_reviewed: 9
files_reviewed_list:
  - framework/agent_framework/tools/builtin/file_tools.py
  - framework/agent_framework/tools/mcp/config.py
  - framework/tests/test_builtin_tools.py
  - framework/tests/test_mcp_manager.py
  - framework/agent_framework/llm/providers/openai_provider.py
  - framework/agent_framework/llm/providers/anthropic_provider.py
  - framework/agent_framework/llm/providers/deepseek_provider.py
  - framework/tests/test_providers.py
  - docs/reviews/SECURITY-REVIEW.md
findings:
  critical: 1
  warning: 4
  info: 3
  total: 8
status: issues_found
---

# Phase 2: Code Review Report

**Reviewed:** 2026-05-28
**Depth:** standard
**Files Reviewed:** 9
**Status:** issues_found

## Summary

Reviewed 9 files across the security-hardened framework: file tools with path sandbox, MCP config with env blacklist, three LLM providers with SecretStr API keys, their tests, and the security audit report itself.

The security fixes applied in Phase 02 (SEC-01 path traversal, SEC-02 env injection, SEC-03 SecretStr) are properly implemented and tested. However, one new security regression was found: the `read_file` error message for non-existent files leaks the user-supplied path, partially defeating the "no path leakage" goal established by SEC-01. Additionally, several robustness issues were found in the providers and MCP manager.

## Critical Issues

### CR-01: read_file leaks user-supplied path in error message for non-existent files

**File:** `framework/agent_framework/tools/builtin/file_tools.py:25`
**Issue:** When `read_file` encounters a non-existent file that passes the sandbox check, it returns the raw user-supplied `path` in the error message: `f"文件不存在: {path}"`. This leaks the path the LLM agent requested, which is the exact information the `_PATH_REJECTED` constant was designed to hide. An attacker controlling LLM output can use this to probe the filesystem structure within the sandbox (e.g., distinguish which paths exist vs. which don't), even though they cannot escape the sandbox. The test at `test_builtin_tools.py:106-114` verifies that traversal paths don't leak, but no test verifies that non-traversal non-existent paths don't leak.

For `write_file`, there is no non-existence check at all (it creates the file), so the issue is limited to `read_file`.

**Fix:**
```python
# file_tools.py line 24-25 — replace:
#     if not full_path.exists():
#         return ToolResult(content=f"文件不存在: {path}", is_error=True)
# with:
    if not full_path.exists():
        return ToolResult(content="文件不存在", is_error=True)
```

Also add a test case verifying that a legitimate-looking but non-existent path does not appear in the error message.

## Warnings

### WR-01: OpenAI _build_request_body accesses config.provider_extras without null check

**File:** `framework/agent_framework/llm/providers/openai_provider.py:71`
**Issue:** When `config.thinking` is enabled, the code does `config.provider_extras.get("reasoning_effort", "high")`. If `config.provider_extras` is `None`, this raises `AttributeError`. The later block at line 75 correctly guards with `if config.provider_extras:`, but the thinking block at line 71 does not. This means a `CompletionConfig` with `thinking=ThinkingConfig(type="enabled")` and `provider_extras=None` (the default) will crash.

**Fix:**
```python
# line 71 — replace:
#     effort = config.provider_extras.get("reasoning_effort", "high")
# with:
    effort = (config.provider_extras or {}).get("reasoning_effort", "high")
```

### WR-02: MCP env blacklist is substring-matched and can be bypassed with crafted key names

**File:** `framework/agent_framework/tools/mcp/config.py:48`
**Issue:** The blacklist check uses `any(pattern in lowered for pattern in _BLOCKED_ENV_PATTERNS)` which is a substring match. While this is intentionally broad, it also means legitimate environment variables that happen to contain a substring like "secret" or "token" in an unrelated context will be rejected. More importantly, the blacklist can be bypassed by naming conventions that avoid these exact substrings -- for example, `AUTH0_JWT` (no "token"), `AWS_SESSION_CREDENTIAL` (contains "credential" so caught, but `AWS_SESSION_CERT` would not be). This is a partial mitigation at best.

This is not a bug per se (the design is intentional), but the security audit report SEC-02 should more clearly state the limitation: the blacklist is a heuristic, not a complete solution. A whitelist approach would be stronger.

**Fix:** Document the limitation. Consider adding a `allowed_env_prefixes` whitelist to `McpServerConfig` as a complement to the blacklist.

### WR-03: McpManager._register_tools registers tools without a dispatch handler

**File:** `framework/agent_framework/tools/mcp/config.py:109-124`
**Issue:** The `ToolSpec` objects registered by `_register_tools` have `handler=None` (the default). The test at `test_mcp_manager.py:93` verifies `spec.handler is None`. This means the registry contains specs that cannot be dispatched through the normal `spec.handler(args, ctx)` path. The MCP tool dispatch must go through `McpManager.call_tool` instead. If any consumer of `ToolRegistry` assumes `spec.handler` is callable, it will crash with a `TypeError`. This is a design coupling issue -- the registry is being used to store metadata without the handler contract.

**Fix:** Either document that MCP tools must be dispatched via `McpManager.call_tool` and never via `spec.handler`, or provide a wrapper handler in the spec that delegates to the manager.

### WR-04: Anthropic stream parser silently swallows malformed JSON in tool arguments

**File:** `framework/agent_framework/llm/providers/anthropic_provider.py:234-237`
**Issue:** When parsing tool call arguments at stream end, if `json.loads` fails, the code falls back to `{"_raw": block["input_json"]}`. This means downstream consumers receive a dict with a `_raw` key instead of the expected tool argument structure. There is no logging of this failure, making it invisible in production. The consumer (likely the agent loop) would then pass `_raw` as a tool argument name to the actual tool, causing a confusing downstream error rather than a clear failure at the source.

**Fix:** Add a logger warning when JSON parsing fails, and consider raising an error or returning a structured error indicator instead of a magic `_raw` key:
```python
try:
    args = json.loads(block["input_json"]) if block["input_json"] else {}
except json.JSONDecodeError:
    logger.warning(
        "Malformed tool arguments in stream: idx=%s, raw=%.200s",
        idx, block["input_json"],
    )
    args = {"_raw_parse_error": block["input_json"]}
```

## Info

### IN-01: SECURITY-REVIEW.md claims SEC-05 is "wired" but ToolRouter HITL gap remains architectural

**File:** `docs/reviews/SECURITY-REVIEW.md:66-72`
**Issue:** The security report accurately describes the ASK-not-wired-to-HITL gap. This is not a new finding but noting that the "Documented only" status means this remains an open gap where tools requiring user approval are silently rejected. The report is clear about this limitation.

### IN-02: DeepSeek _build_request_body duplicates provider_extras logic with OpenAI

**File:** `framework/agent_framework/llm/providers/deepseek_provider.py:99-116`
**Issue:** The `provider_extras` merging logic (iterate over extras, skip `reasoning_effort`, merge rest) is duplicated between DeepSeek and OpenAI providers. A shared helper in `transform.py` would reduce drift risk.

### IN-03: Test helper _make_provider uses object.__new__ bypass which masks __init__ bugs

**File:** `framework/tests/test_providers.py:191-198`
**Issue:** The `_make_provider` helper patches `__init__` to do nothing and uses `object.__new__` to create instances. This means if a provider's `__init__` is changed to set additional required attributes, the tests won't catch the mismatch until runtime in a different test. This is acceptable for mock-based testing but worth noting as a maintenance risk.

---

_Reviewed: 2026-05-28_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
