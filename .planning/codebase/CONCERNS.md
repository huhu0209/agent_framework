# Codebase Concerns

**Analysis Date:** 2026-05-28

## Tech Debt

**Backend is entirely scaffold (zero implementation):**
- Issue: Every file in `backend/` is empty (0 lines). All API routes (`agents.py`, `chat.py`, `tools.py`), config, models, services, utils, and `main.py` are placeholder files.
- Files: `backend/app/api/v1/agents.py`, `backend/app/api/v1/chat.py`, `backend/app/api/v1/tools.py`, `backend/app/config/__init__.py`, `backend/app/models/__init__.py`, `backend/app/services/__init__.py`, `backend/app/utils/__init__.py`, `backend/main.py`
- Impact: No application layer exists. The framework cannot be exercised end-to-end through an HTTP API.
- Fix approach: Implement backend incrementally, starting with `main.py` (FastAPI app) and `chat.py` (core chat endpoint).
- **✅ RESOLVED (v0.0.3~v0.0.6):** Backend progressively implemented — EventBus (v0.0.3), code review fixes (v0.0.4~v0.0.5), ConfigLoader integration (v0.0.6). Files now contain real implementation.

**Orchestrator engine and router are empty:**
- Issue: `engine.py` and `router.py` in the orchestrator module are empty (0 lines). Only `planner.py` has implementation.
- Files: `framework/agent_framework/orchestrator/engine.py`, `framework/agent_framework/orchestrator/router.py`
- Impact: No multi-agent orchestration or LLM routing logic exists. Only the planner (plan parsing/drift detection) is implemented.
- Fix approach: Implement `engine.py` for multi-agent coordination and `router.py` for LLM provider routing (model selection, fallback chains).
- **✅ RESOLVED (v0.0.2):** Orchestrator engine implemented in Phase 7. Planner, plan parsing, drift detection all functional. Engine and router are no longer empty.

**Agent tool dispatch is a stub:**
- Issue: `_dispatch_agent` in `ToolRouter` returns a hardcoded "not implemented" error for all `agent__` prefixed tools.
- Files: `framework/agent_framework/tools/router.py:179-183`
- Impact: Agent-to-agent tool calling does not work. The routing prefix `agent__` is reserved but non-functional.
- Fix approach: Implement agent tool dispatch or remove the `agent__` prefix reservation.
- **✅ RESOLVED (v0.0.2):** Sub-Agent dispatch implemented via `run_subagent` tool in `agents/sub_agent.py`. Agent-to-agent tool calling works through `agent__` prefix routing.

**VerificationRunner only implements regex_match:**
- Issue: The `VerificationRule` schema supports 5 check types (`code_compiles`, `tests_pass`, `schema_valid`, `llm_judge`, `regex_match`), but `_run_single` only handles `regex_match` and returns `None` for all others.
- Files: `framework/agent_framework/safety/verification.py:48-53`
- Impact: Post-tool verification only works for regex rules. The remaining 4 check types silently pass.
- Fix approach: Implement remaining check types or remove them from the `Literal` type and document them as future work.

**web_search is a mock implementation:**
- Issue: The `web_search` tool in `search_tools.py` returns hardcoded fake results.
- Files: `framework/agent_framework/tools/builtin/search_tools.py:8-17`
- Impact: Any agent using web search will receive fake data. Not safe for production.
- Fix approach: Integrate a real search API (e.g., SerpAPI, Tavily) or clearly gate behind a feature flag.
- **✅ RESOLVED (v0.0.2):** Replaced with Tavily API integration (`AsyncTavilyClient`). Returns real search results when `TAVILY_API_KEY` is configured.

**CommandPolicy is a placeholder interface:**
- Issue: `CommandPolicy` in `boundary.py` is described as "reserved interface, activate after bash tool implementation" but has no enforcement logic.
- Files: `framework/agent_framework/safety/boundary.py:28-36`
- Impact: No command sandboxing exists. If a bash tool is added without updating this, agents can run arbitrary commands.
- Fix approach: Implement command validation before adding a bash tool.

**`_CRITICAL_TOOLS` global is always empty:**
- Issue: The global `_CRITICAL_TOOLS` set in `permissions.py` is initialized empty and never populated. The DENY step of the permission pipeline always passes through.
- Files: `framework/agent_framework/safety/permissions.py:40`
- Impact: No tools are globally blocked, even if they should be (e.g., `rm -rf`, `execute_code`). The pipeline's first defense layer is inactive.
- Fix approach: Either populate `_CRITICAL_TOOLS` from configuration or make it a parameter on `PermissionPipeline`.

**`agents/base.py` is empty:**
- Issue: The file exists with 0 lines. No base agent abstraction is defined.
- Files: `framework/agent_framework/agents/base.py`
- Impact: All agent implementations are concrete classes with no shared interface beyond what `AgentLoop` provides.
- Fix approach: Either remove the empty file or define a base agent protocol.
- **✅ RESOLVED (v0.0.2~v0.0.5):** File now contains `AgentEvent` dataclass and `Agent` ABC with abstract `async def run()` (24 lines).

## Known Bugs

**Missing `Path` import in `agent_loop.py`:**
- Symptoms: `skill_dirs: list[Path] | None = None` on line 87 references `Path` without importing it. This will raise `NameError` at class instantiation time if `skill_dirs` is passed.
- Files: `framework/agent_framework/agents/agent_loop.py:87`
- Trigger: Instantiating `AgentLoop` with a non-None `skill_dirs` argument.
- Workaround: Import `Path` from `pathlib` at the top of the file.
- **✅ RESOLVED (v0.0.5):** `from pathlib import Path` added at line 12.

**Type annotation bug in `TaskManager._apply_changes`:**
- Symptoms: `pending_writes: list[tuple[Task]] = []` on line 199 is an invalid type annotation. `tuple[Task]` is a single-element tuple, but the code only appends `Task` objects directly (not tuples). The variable is used as `for dep_task in pending_writes` expecting `Task` items.
- Files: `framework/agent_framework/tasks/manager.py:199`
- Trigger: Code runs at runtime (Python ignores the annotation mismatch), but type checkers will flag this and it signals confused intent.
- Workaround: Change type to `list[Task]` or adjust usage to match `list[tuple[Task]]`.
- **✅ RESOLVED (v0.0.5):** Refactored to use `field_updates: dict` with `TaskChanges` TypedDict and `_VALID_CHANGE_KEYS` validation. No annotation bug remains.

**`HITLManager.create_pending` uses deprecated `get_event_loop`:**
- Symptoms: `asyncio.get_event_loop()` on line 47 is deprecated in Python 3.10+. In contexts without a running loop, this can return the wrong loop or raise.
- Files: `framework/agent_framework/safety/hitl.py:47`
- Trigger: Calling `create_pending` outside of an async context or in a nested event loop scenario.
- Workaround: Use `asyncio.get_running_loop()` instead, which is the recommended replacement.
- **✅ RESOLVED (v0.0.5):** Now uses `asyncio.get_running_loop()`.

**`normalize_messages` mutates `last.content` in-place:**
- Symptoms: Line 45 in `_normalize.py` does `last.content = [*last.content, *msg.content]`, mutating a Pydantic model field in-place. This violates immutability principles and can cause subtle bugs if the same message object is shared.
- Files: `framework/agent_framework/llm/transform/_normalize.py:45`
- Trigger: When consecutive `UserMessage` or `AssistantMessage` objects are normalized (merged).
- Workaround: Replace the merged message with a new object instead of mutating `last.content`.
- **✅ RESOLVED (v0.0.5):** Now creates a new `result` list with `model_copy()` / `model_copy(update={...})`. Original messages list never mutated.

**`_apply_changes` mutates dataclass in-place via `_clear_dependency`:**
- Symptoms: `_clear_dependency` on line 228 is called inside `_apply_changes` and writes dependent tasks to disk, but the write happens inside the `_lock` context. If `_clear_dependency` fails partway through, some dependency cleanups are written while others are lost, leaving inconsistent state.
- Files: `framework/agent_framework/tasks/manager.py:228-236`
- Trigger: Completing a task that is a blocker for many other tasks, with a file I/O error midway.
- Workaround: Batch all dependency clears and write atomically, or implement a rollback mechanism.
- **✅ RESOLVED (v0.0.5):** Refactored to use `field_updates: dict` with `_VALID_CHANGE_KEYS` validation and `dataclasses.replace()` for immutable updates.

## Security Considerations

**No path sandboxing on file tools:**
- Risk: `read_file` and `write_file` in `file_tools.py` resolve paths relative to `working_dir` but do not call `safe_path()` from the boundary module. An LLM could craft `../../etc/passwd` paths.
- Files: `framework/agent_framework/tools/builtin/file_tools.py:11-12,25-26`
- Current mitigation: None. The `safe_path` function exists in `framework/agent_framework/safety/boundary.py` but is not used.
- Recommendations: Call `safe_path(path, ctx.working_dir)` before any file I/O in both tools.
- **✅ RESOLVED (v0.0.5):** Both `read_file` and `write_file` now call `safe_path(path, Path(ctx.working_dir))` and return `_PATH_REJECTED` on escape.

**MCP server env injection:**
- Risk: `StdioTransport` merges user-supplied `env` dict with `os.environ` (`{**os.environ, **(self._env or {})}`). Malicious MCP config could inject sensitive env vars or override existing ones.
- Files: `framework/agent_framework/tools/mcp/transport.py:57`, `framework/agent_framework/tools/mcp/config.py:27`
- Current mitigation: None. The `env` dict from config is trusted without validation.
- Recommendations: Validate `McpServerConfig.env` keys against an allowlist or block sensitive keys (e.g., `API_KEY`, `TOKEN`, `PASSWORD`).
- **✅ RESOLVED (v0.0.5):** Two mitigations: (1) `StdioTransport.connect()` filters inherited env to `_ALLOWED_ENV_KEYS` allowlist; (2) `McpServerConfig` has `@field_validator("env")` blocking sensitive key patterns (api_key, token, secret, password).

**API keys stored in provider instances:**
- Risk: `_api_key` is stored as a plain string on provider instances. If an object is serialized or logged, the key could leak.
- Files: `framework/agent_framework/llm/providers/openai_provider.py:111`, `framework/agent_framework/llm/providers/anthropic_provider.py:259`, `framework/agent_framework/llm/providers/deepseek_provider.py:149`
- Current mitigation: None. The key is stored in `self._api_key` and set in httpx headers at construction time.
- Recommendations: Clear `_api_key` after client construction or use a secret reference pattern.
- **✅ RESOLVED (v0.0.5):** All three providers now store `_api_key` as `SecretStr`. Only `get_secret_value()` is used when constructing HTTP headers.

**Hook commands execute arbitrary shell:**
- Risk: `_execute_command` in `HookManager` runs `bash -c <user-configured-command>`. If hook config is loaded from an untrusted source, this is arbitrary code execution.
- Files: `framework/agent_framework/hooks/manager.py:120-122`
- Current mitigation: `trusted` flag gates execution; untrusted workspaces return empty results.
- Recommendations: Document the trust model clearly. Consider path-restricting hook commands.

**Permission ASK decision returns error instead of blocking:**
- Risk: In `ToolRouter.dispatch`, when `PermissionPipeline` returns `ASK`, the tool is rejected with an error message rather than actually prompting the user via HITL. The HITL system exists but is not wired into the dispatch flow.
- Files: `framework/agent_framework/tools/router.py:72-76`
- Current mitigation: The error message mentions "needs user confirmation" but no confirmation flow exists.
- Recommendations: Wire `HITLManager` into `ToolRouter` to handle ASK decisions with actual user prompts.

**MessageBus uses predictable file paths:**
- Risk: Team inbox files are stored as `<team_dir>/inbox/<name>.jsonl`. Any process with filesystem access can read, modify, or inject messages.
- Files: `framework/agent_framework/teams/bus.py:24-30`
- Current mitigation: Relies on filesystem permissions.
- Recommendations: Document that team directories must have restricted permissions. Consider message signing for tamper detection.

## Performance Concerns

**Synchronous file I/O in async context:**
- Problem: Memory subsystem (`log_manager.py`, `index_manager.py`, `semantic_writer.py`, `store.py`) and team bus (`bus.py`) use synchronous `Path.read_text()` / `open()` calls. These block the event loop.
- Files: `framework/agent_framework/memory/log_manager.py:44-45`, `framework/agent_framework/teams/bus.py:26-30`, `framework/agent_framework/tools/context/result_truncator.py:34`
- Cause: All I/O is synchronous despite the framework being fully async.
- Improvement path: Wrap in `asyncio.to_thread()` or use `aiofiles`. The code already documents this in `log_manager.py` line 3-4.
- **✅ PARTIALLY RESOLVED (v0.0.5~v0.0.6):** `log_manager.py` now uses `aiofiles.open()` for all reads/writes. `teams/bus.py` (`send()` and `read_inbox()`) still uses synchronous I/O.

**MessageBus inbox read clears file:**
- Problem: `read_inbox` reads the entire JSONL file and immediately writes empty string back (`path.write_text("")`). This is non-atomic: if the process crashes between read and write, messages are lost.
- Files: `framework/agent_framework/teams/bus.py:38-39`
- Cause: No atomic read-and-clear mechanism.
- Improvement path: Use rename-based atomic swap (write to temp, rename), or use `os.replace` pattern as done in `MemoryIndexManager._atomic_write`.

**Context compaction makes an extra LLM call per compression:**
- Problem: Every time compaction triggers, a full LLM call is made to summarize old messages. This adds latency and cost.
- Files: `framework/agent_framework/tools/context/compactor.py:126-156`
- Cause: Design choice, but no caching of summaries or incremental summarization.
- Improvement path: Cache previous summaries and only summarize the delta since last compaction.

**`_read_until_header_end` reads one byte at a time:**
- Problem: The MCP transport header parser reads 1 byte at a time from stdout, which is extremely slow for large messages.
- Files: `framework/agent_framework/tools/mcp/transport.py:123-129`
- Cause: Line-by-line parsing without buffered reading.
- Improvement path: Use `readline()` or buffered reading with a larger chunk size.

**TaskManager scans all JSON files on every query:**
- Problem: `count_active()`, `_find_in_progress()`, `_load_all()`, and `_clear_dependency()` all scan the entire tasks directory with `glob("task_*.json")` and read each file. No in-memory index.
- Files: `framework/agent_framework/tasks/manager.py:139-146,158-161,164-168,228-236`
- Cause: No caching; each operation re-reads from disk.
- Improvement path: Maintain an in-memory index of task statuses, updated on write.

## Fragile Areas

**`AgentLoop.__init__` has 15 parameters:**
- Files: `framework/agent_framework/agents/agent_loop.py:70-92`
- Why fragile: Adding new integrations (memory, skills, hooks, tasks, teams, sub-agents) keeps growing the constructor. Each integration has its own optional parameter and conditional initialization block.
- Safe modification: Refactor to a config dataclass or builder pattern that collects integration options.
- Test coverage: Good (test files exist for agent loop), but the growing parameter list makes it harder to test all combinations.

**`ToolRouter.dispatch` has 4 layers of responsibility:**
- Files: `framework/agent_framework/tools/router.py:58-156`
- Why fragile: Single method handles permission checks, pre-hooks, execution with fallback, and post-hooks. Adding any new concern requires modifying this already complex method.
- Safe modification: Extract each layer into a pipeline/middleware pattern.
- Test coverage: Good (`test_tool_router.py` exists).

**`_apply_changes` in TaskManager has complex mutation logic:**
- Files: `framework/agent_framework/tasks/manager.py:185-226`
- Why fragile: The method mutates task state, manages bidirectional dependencies, and writes to disk all within a single lock scope. The `pending_writes` variable adds dependent task writes inside the same operation.
- Safe modification: Separate dependency management into its own method with clear input/output contracts.
- Test coverage: Moderate (`test_task_manager.py` exists).

## Scaling Limits

**JSONL inbox files grow without bound:**
- Current capacity: No limit on inbox file size.
- Limit: A busy team with many messages will produce large JSONL files that `read_inbox` must read entirely into memory.
- Scaling path: Implement file rotation or line-count limits on inbox files.

**TaskManager uses per-task JSON files:**
- Current capacity: Designed for up to `MAX_ACTIVE_TASKS = 12`.
- Limit: Each operation scans all task files. At hundreds of tasks, disk I/O dominates.
- Scaling path: Move to SQLite or maintain an in-memory index synchronized to disk.

**SkillRegistry scans directories on every access:**
- Current capacity: `mtime` check on every `describe_available()` and `load_full_text()` call.
- Limit: Frequent filesystem `stat()` calls on directories with many skills.
- Scaling path: Add a debounce interval or watch-based refresh.

## Dependencies at Risk

**Dynamic import in `create_adapter`:**
- Risk: `resilient.py` uses `importlib.import_module` to dynamically load provider classes. If module paths change, the `_PROVIDER_MAP` dict becomes stale silently.
- Impact: Runtime `ImportError` or `AttributeError` when creating adapters.
- Migration plan: Use entry points or static imports with a registry pattern.

**`httpx` as sole HTTP client:**
- Risk: All providers depend on `httpx`. If `httpx` has a breaking change or vulnerability, all providers are affected.
- Impact: Complete loss of LLM connectivity.
- Migration plan: The `ILLMAdapter` abstraction already insulates business logic; only provider implementations would need changes.

## Missing Critical Features

**No streaming to AgentLoop:**
- Problem: `AgentLoop.run` uses `adapter.complete()` (non-streaming). No streaming mode exists for real-time token output.
- Files: `framework/agent_framework/agents/agent_loop.py:326`
- Blocks: Real-time UI streaming display, lower time-to-first-token.

**No conversation persistence:**
- Problem: `AgentLoop._messages` is an in-memory list. When the process exits, the entire conversation is lost.
- Files: `framework/agent_framework/agents/agent_loop.py:106`
- Blocks: Session resume across process restarts, conversation history review.

**No structured logging:**
- Problem: All logging uses `logger.warning/info/debug` with string interpolation. No structured (JSON) logging for production monitoring.
- Files: Throughout the codebase (e.g., `framework/agent_framework/llm/retry.py`, `framework/agent_framework/tools/router.py`)
- Blocks: Production monitoring, alerting, log aggregation.

**No rate limiting on LLM calls:**
- Problem: While the circuit breaker prevents calls to failing providers, there is no client-side rate limiter to proactively avoid hitting provider rate limits.
- Files: `framework/agent_framework/llm/resilient.py`
- Blocks: Sustained high-throughput use without triggering 429 errors.

## Test Coverage Gaps

**No integration tests for multi-provider scenarios:**
- What's not tested: Switching between providers, fallback from one provider to another, provider-specific parameter handling end-to-end.
- Files: `framework/tests/test_providers.py`, `framework/tests/test_resilient.py`
- Risk: Provider-specific edge cases (e.g., Anthropic thinking block handling) may fail in production.
- Priority: Medium

**No tests for backend (empty scaffold):**
- What's not tested: Everything in `backend/`.
- Files: `backend/tests/__init__.py` (empty)
- Risk: Cannot verify any application-layer behavior.
- Priority: Low (no code to test yet)
- **✅ RESOLVED (v0.0.3~v0.0.6):** Backend progressively implemented — EventBus, WebSocket, ConfigLoader integration. Backend has tests for implemented features.

**TeamManager loop behavior is undertested:**
- What's not tested: The actual async loop in `TeamManager._loop` (idle timeout, shutdown request handling, inbox reading with real `AgentLoop`).
- Files: `framework/tests/test_teams_manager.py`
- Risk: Teammate lifecycle bugs (hangs, premature shutdown, message loss) may go undetected.
- Priority: High

**MCP transport is tested but not against real MCP servers:**
- What's not tested: Integration with actual MCP server binaries.
- Files: `framework/tests/test_mcp_transport.py`
- Risk: Protocol edge cases (partial writes, binary data, encoding issues) may fail with real servers.
- Priority: Medium

**Safety boundary not integrated with tool execution in tests:**
- What's not tested: The `safe_path` function is tested in isolation (`test_boundary.py`) but never verified to be called from `file_tools.py`.
- Files: `framework/tests/test_boundary.py`, `framework/tests/test_builtin_tools.py`
- Risk: Path sandboxing is tested but not enforced -- the gap documented in Security Considerations.
- Priority: High
- **✅ RESOLVED (v0.0.5):** `file_tools.py` now calls `safe_path()` directly. Path sandboxing is enforced at the tool level, not just in isolation tests.

---

*Concerns audit: 2026-05-28*
*Last verified: 2026-06-12 — 10 items resolved, 17 remain open*
