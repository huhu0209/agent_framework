# Security Audit Report

**Audit Date:** 2026-05-28
**Scope:** `framework/agent_framework/` (full framework layer)
**Auditor:** Automated security review (Phase 02)

---

## CRITICAL

### SEC-01: File Path Sandbox

**Description:** The `read_file` and `write_file` tools in `file_tools.py` resolved paths relative to `working_dir` without calling `safe_path()` from the boundary module. An LLM agent could craft paths like `../../etc/passwd` to read or write arbitrary files outside the workspace.

**File Location:** `framework/agent_framework/tools/builtin/file_tools.py` (lines 11-12, 25-26)

**Impact:** Arbitrary file read/write. An attacker controlling LLM output could exfiltrate secrets from the host system or write malicious files.

**Fix Status:** **FIXED** in Phase 02 (Plan 01). The `safe_path()` function from `framework/agent_framework/safety/boundary.py` is now called before any file I/O in both `read_file` and `write_file`. Generic error messages prevent path leakage.

---

## HIGH

### SEC-02: MCP Environment Variable Injection

**Description:** `StdioTransport` merges user-supplied `env` dict with `os.environ` (`{**os.environ, **(self._env or {})}`). A malicious MCP server configuration could inject sensitive environment variable overrides (e.g., `API_KEY`, `AWS_SECRET_ACCESS_KEY`) to steal credentials or alter process behavior.

**File Location:** `framework/agent_framework/tools/mcp/transport.py:57`, `framework/agent_framework/tools/mcp/config.py:27`

**Impact:** Sensitive environment variable theft. An attacker controlling MCP config could override critical env vars like API keys, tokens, or database credentials.

**Fix Status:** **FIXED** in Phase 02 (Plan 01). A `field_validator` on `McpServerConfig.env` now blocks keys matching sensitive patterns (`api_key`, `token`, `secret`, `password`, `credential`, `private_key`, `access_key`) with case-insensitive matching.

---

## MEDIUM

### SEC-03: API Key Plaintext Storage

**Description:** The `_api_key` attribute was stored as a plain Python `str` on all 3 provider instances (OpenAI, Anthropic, DeepSeek). If a provider object is serialized, logged, printed via `repr()`, or inspected in a debugger, the API key would be exposed in plaintext.

**File Locations:**
- `framework/agent_framework/llm/providers/openai_provider.py:111`
- `framework/agent_framework/llm/providers/anthropic_provider.py:259`
- `framework/agent_framework/llm/providers/deepseek_provider.py:149`

**Impact:** API key leak through repr/logging/serialization. Keys stored as plain strings are vulnerable to accidental exposure in error reports, log aggregation, or debugger sessions.

**Fix Status:** **FIXED** in Phase 02 (Plan 02). All 3 providers now store `_api_key` as `pydantic.SecretStr`. The `str()` and `repr()` of the key return `"**********"`, while HTTP headers use `get_secret_value()` for authentication.

### SEC-04: Hook Command Execution

**Description:** The `HookManager._execute_command` method runs `bash -c <user-configured-command>` with arbitrary shell commands. If hook configuration is loaded from an untrusted source (e.g., a cloned repository with malicious `.hooks.json`), this enables arbitrary code execution.

**File Location:** `framework/agent_framework/hooks/manager.py:120-122`

**Impact:** Arbitrary shell command execution. An attacker who controls hook configuration can execute any command on the host system with the same privileges as the agent process.

**Current Mitigation:** The `trusted` flag on workspace context gates execution. Untrusted workspaces return an empty `HookResult` without executing commands.

**Fix Status:** **Documented only.** The `trusted` flag provides defense in depth -- untrusted workspaces do not execute hooks. Recommend documenting the trust model in user-facing documentation. Path-restricting hook commands could be considered as a future hardening measure.

### SEC-05: Permission ASK Not Wired to HITL

**Description:** In `ToolRouter.dispatch`, when `PermissionPipeline` returns `ASK` (user confirmation required), the tool is rejected with an error message rather than actually prompting the user via the HITL (Human-in-the-Loop) system. The `HITLManager` exists and is functional but is not wired into the dispatch flow.

**File Location:** `framework/agent_framework/tools/router.py:72-76`

**Impact:** Tools requiring user approval are silently rejected instead of prompting for confirmation. This breaks the permission model -- the ASK decision exists but cannot actually reach the user.

**Fix Status:** **Documented only.** Improvement path: wire `ToolRouter` to `HITLManager` for ASK decisions, replacing the error return with an actual user confirmation flow. This requires architectural changes to `ToolRouter` that are out of scope for the security phase.

---

## LOW

### SEC-06: MessageBus Predictable File Paths

**Description:** Team inbox files are stored as `<team_dir>/inbox/<name>.jsonl` with no integrity protection. The files are plain JSONL that any process with filesystem access can read, modify, or inject messages into. Additionally, `read_inbox` performs a non-atomic read-and-clear (read the file, then write empty string), which can lose messages if the process crashes between the two operations.

**File Location:** `framework/agent_framework/teams/bus.py:24-30`

**Impact:** Any process with filesystem access to the team directory can read team messages (potential information disclosure), modify messages in transit (tampering), or inject fake messages (spoofing). Message loss possible due to non-atomic read-and-clear.

**Fix Status:** **Documented only.** Recommend restricting team directory permissions (e.g., `chmod 700`) and considering message signing for tamper detection. The non-atomic read-and-clear could be improved with rename-based atomic swap.

---

## Summary

| Metric | Count |
|--------|-------|
| Total issues found | 6 |
| Fixed in this phase | 3 (SEC-01, SEC-02, SEC-03) |
| Documented only | 3 (SEC-04, SEC-05, SEC-06) |

**Assessment:** The framework is now hardened against the top-severity attack vectors. The two CRITICAL/HIGH issues (path traversal and env injection) are fully resolved with automated tests. The MEDIUM SecretStr fix prevents the most common API key leak vectors. The remaining 3 documented-only issues (hook execution, HITL wiring, file-based messaging) represent architectural limitations that require design work beyond the security phase and have existing mitigations or clear improvement paths documented above.

---

*Report generated: 2026-05-28*
*Phase: 02-security*
