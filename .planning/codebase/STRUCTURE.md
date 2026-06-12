# Codebase Structure

**Analysis Date:** 2026-05-28

## Directory Layout

```
agent_framework/                         # Project root
├── framework/                           # Standalone pip package (the core framework)
│   ├── pyproject.toml                   # Package config: agent-framework-core v0.1.0
│   └── agent_framework/                 # Python package root
│       ├── __init__.py                  # (1 line) package marker
│       ├── llm/                         # LLM Adapter layer (7,661 total framework lines)
│       │   ├── __init__.py              # Barrel exports for entire LLM module
│       │   ├── base.py                  # ILLMAdapter ABC + error hierarchy
│       │   ├── types.py                 # All message/content/config/result types
│       │   ├── resilient.py             # ResilientLLMAdapter + create_adapter factory
│       │   ├── retry.py                 # RetryConfig + CircuitBreaker
│       │   ├── streaming.py             # SSE parsing + OpenAIStreamParser + StreamCollector
│       │   ├── providers/               # Provider implementations
│       │   │   ├── anthropic_provider.py
│       │   │   ├── openai_provider.py
│       │   │   └── deepseek_provider.py
│       │   └── transform/               # Bidirectional message format converters
│       │       ├── _anthropic.py
│       │       ├── _openai.py
│       │       ├── _deepseek.py
│       │       └── _normalize.py        # Message normalization (merge tool msgs into user)
│       ├── tools/                        # Tool system
│       │   ├── __init__.py              # Barrel exports
│       │   ├── types.py                 # ToolSpec, ToolCall, ToolResult, ToolUseContext
│       │   ├── registry.py              # ToolRegistry (name -> ToolSpec map)
│       │   ├── router.py                # ToolRouter (dispatch + permissions + hooks)
│       │   ├── executor.py              # ToolExecutor (timeout + error wrapping + truncation)
│       │   ├── validator.py             # ToolValidator (JSON Schema type checking)
│       │   ├── degrader.py              # ToolDegrader (fallback mapping)
│       │   ├── builtin/                 # Built-in tool handlers
│       │   │   ├── __init__.py          # create_builtin_registry()
│       │   │   ├── file_tools.py        # read_file, write_file
│       │   │   ├── search_tools.py      # web_search (mock)
│       │   │   └── plan_tools.py        # update_plan_status
│       │   ├── mcp/                     # Model Context Protocol client
│       │   │   ├── client.py            # McpClient (JSON-RPC 2.0 + MCP handshake)
│       │   │   ├── config.py            # McpManager + McpServerConfig
│       │   │   └── transport.py         # McpTransport ABC + StdioTransport
│       │   └── context/                 # Context window management
│       │       ├── compactor.py         # Auto-compaction (LLM summary replaces old turns)
│       │       ├── token_counter.py     # Character-based token estimation
│       │       └── result_truncator.py  # Large result disk dump
│       ├── agents/                      # Agent system
│       │   ├── agent_loop.py            # AgentLoop (core ReAct loop, 406 lines)
│       │   ├── base.py                  # (empty scaffold)
│       │   └── sub_agent.py             # run_subagent + create_filtered_router
│       ├── orchestrator/                # Orchestrator (mostly scaffold)
│       │   ├── engine.py                # (empty scaffold)
│       │   ├── planner.py               # PlanningState + PlanItem + plan parsing
│       │   └── router.py                # (empty scaffold)
│       ├── memory/                      # Dual-layer memory system
│       │   ├── __init__.py              # Barrel exports
│       │   ├── types.py                 # MemoryLayer, EventType, MemoryType, SemanticMemoryDraft
│       │   ├── store.py                 # MemoryStore facade (unified search)
│       │   ├── log_manager.py           # EpisodicLogManager (daily log files)
│       │   ├── retriever.py             # LLMScoringRetriever (LLM-based scoring)
│       │   ├── search.py                # handle_memory_search (tool handler)
│       │   ├── flush.py                 # FlushExtractor (conversation -> events)
│       │   ├── semantic_extractor.py    # SemanticExtractor (events -> memory drafts)
│       │   ├── semantic_writer.py       # SemanticWriter (drafts -> .md files)
│       │   ├── index_manager.py         # MemoryIndexManager (MEMORY.md index)
│       │   └── frontmatter.py           # YAML frontmatter parse/format
│       ├── prompts/                     # Prompt composition
│       │   ├── assembler.py             # PromptAssembler (profile -> system prompt)
│       │   ├── profiles.py              # AgentProfile + PromptBlock models
│       │   └── templates.py             # Plan generation + drift warning templates
│       ├── safety/                      # Safety layer
│       │   ├── __init__.py              # Barrel exports
│       │   ├── boundary.py              # Path sandbox + CommandPolicy
│       │   ├── permissions.py           # PermissionPipeline (DENY->MODE->ALLOW->ASK)
│       │   ├── hitl.py                  # HITLManager (async permission requests)
│       │   └── verification.py          # VerificationRunner (post-tool regex rules)
│       ├── skills/                      # Skills system
│       │   ├── registry.py              # SkillRegistry (multi-dir scanner)
│       │   ├── manifest.py              # SkillManifest + SKILL.md parser
│       │   └── tool.py                  # load_skill ToolSpec
│       ├── tasks/                       # Task system
│       │   ├── types.py                 # Task, TaskStatus, RuntimeTask
│       │   ├── manager.py               # TaskManager (persistent task DAG)
│       │   ├── runner.py                # TaskRunner (background AgentLoop execution)
│       │   └── tools.py                 # 4 task tool specs (create/update/list/get)
│       ├── teams/                       # Team system
│       │   ├── types.py                 # TeammateConfig, TeamMessage, TeamNotification
│       │   ├── bus.py                   # MessageBus (JSONL file inbox)
│       │   ├── manager.py               # TeamManager (spawn/shutdown teammate loops)
│       │   └── tools.py                 # 5 team tool specs (spawn/list/send/read/broadcast)
│       ├── commands/                    # Slash command system
│       │   ├── types.py                 # SlashCommand, ResolvedCommand, CommandSource
│       │   └── router.py               # CommandRouter (/command -> resolved action)
│       └── hooks/                       # Hook system
│           ├── types.py                 # HookConfig, HookEvent, HookContext, HookResult
│           └── manager.py               # HookManager (register, fire, JSON loading)
├── framework/tests/                     # Test suite (9,386 lines, 65 test files)
│   ├── conftest.py                      # Shared fixtures
│   ├── helpers.py                       # Test utilities
│   ├── test_agent_loop.py               # Core loop tests
│   ├── test_agent_loop_resume.py        # Resume behavior tests
│   ├── test_sub_agent.py                # Sub-agent isolation tests
│   ├── test_providers.py                # Provider tests
│   ├── test_resilient.py                # Retry + circuit breaker tests
│   ├── test_streaming.py                # SSE parsing + StreamCollector tests
│   ├── test_transform.py                # Message format conversion tests
│   ├── test_normalize_messages.py       # Message normalization tests
│   ├── test_tool_registry.py            # Registry CRUD tests
│   ├── test_tool_router.py              # Dispatch pipeline tests
│   ├── test_router_derive.py            # Router derivation tests
│   ├── test_tool_executor.py            # Executor timeout/error tests
│   ├── test_tool_validator.py           # Parameter validation tests
│   ├── test_tool_types.py               # Tool type tests
│   ├── test_degrader.py                 # Fallback mapping tests
│   ├── test_builtin_tools.py            # Built-in tool handler tests
│   ├── test_plan_tools.py               # Plan status tool tests
│   ├── test_compactor.py                # Context compaction tests
│   ├── test_token_counter.py            # Token estimation tests
│   ├── test_result_truncator.py         # Large result truncation tests
│   ├── test_context_config.py           # Context window config tests
│   ├── test_registry_subset.py          # Registry subset tests
│   ├── test_mcp_client.py               # MCP JSON-RPC tests
│   ├── test_mcp_manager.py              # MCP lifecycle tests
│   ├── test_mcp_transport.py            # StdioTransport tests
│   ├── test_planner.py                  # Planning state + drift tests
│   ├── test_prompt_assembler.py         # Prompt composition tests
│   ├── test_agent_profile.py            # Profile loading tests
│   ├── test_boundary.py                 # Path sandbox tests
│   ├── test_permissions.py              # Permission pipeline tests
│   ├── test_hitl.py                     # HITL interaction tests
│   ├── test_verification.py             # Verification rule tests
│   ├── test_skills_registry.py          # Skill discovery tests
│   ├── test_skills_manifest.py          # SKILL.md parsing tests
│   ├── test_skills_tool.py              # load_skill handler tests
│   ├── test_task_manager.py             # Task DAG CRUD tests
│   ├── test_task_runner.py              # Background execution tests
│   ├── test_task_tools.py               # Task tool handler tests
│   ├── test_task_types.py               # Task type tests
│   ├── test_teams_bus.py                # MessageBus tests
│   ├── test_teams_manager.py            # TeamManager tests
│   ├── test_teams_tools.py              # Team tool handler tests
│   ├── test_teams_types.py              # Team type tests
│   ├── test_command_router.py           # /command parsing tests
│   ├── test_command_types.py            # Command type tests
│   ├── test_hook_manager.py             # Hook lifecycle tests
│   ├── test_hook_types.py               # Hook type tests
│   ├── test_memory_store.py             # Memory facade tests
│   ├── test_memory_search.py            # Episodic search tests
│   ├── test_memory_retriever.py         # LLM scoring tests
│   ├── test_memory_flush.py             # Flush extraction tests
│   ├── test_memory_types.py             # Memory type tests
│   ├── test_semantic_extractor.py       # Semantic extraction tests
│   ├── test_semantic_writer.py          # Semantic writing tests
│   ├── test_frontmatter.py              # Frontmatter parse/format tests
│   └── test_index_manager.py            # MEMORY.md index tests
├── backend/                             # Application layer (scaffold)
│   ├── pyproject.toml                   # Depends on agent-framework-core via local path
│   ├── main.py                          # (empty scaffold)
│   ├── app/                             # FastAPI app package
│   │   ├── api/v1/                      # API routes (scaffold)
│   │   │   ├── agents.py               # (empty scaffold)
│   │   │   ├── chat.py                 # (empty scaffold)
│   │   │   └── tools.py                # (empty scaffold)
│   │   ├── config/                      # (empty scaffold)
│   │   ├── models/                      # (empty scaffold)
│   │   ├── services/                    # (empty scaffold)
│   │   └── utils/                       # (empty scaffold)
│   └── tests/                           # (empty scaffold)
├── frontend/                            # Frontend (Vite + React + TypeScript + Tailwind)
│   ├── package.json                     # React 19, Vite 8, Tailwind 4
│   ├── src/
│   │   ├── main.tsx                     # App mount
│   │   ├── App.tsx                      # Root component
│   │   ├── lib/api.ts                   # API client
│   │   ├── lib/utils.ts                 # Utilities
│   │   ├── types/index.ts              # TypeScript types
│   │   ├── components/                 # Component directories (.gitkeep only)
│   │   │   ├── agent/
│   │   │   ├── chat/
│   │   │   ├── layout/
│   │   │   └── ui/
│   │   ├── hooks/                       # (.gitkeep only)
│   │   ├── pages/                       # (.gitkeep only)
│   │   └── styles/globals.css
│   └── dist/                            # Build output
├── docs/                                # Documentation
│   ├── plans/                           # Planning documents
│   └── reviews/                         # Review documents
├── .planning/codebase/                  # Codebase analysis output (this file)
└── CLAUDE.md                            # Claude Code instructions
```

## Directory Purposes

**`framework/agent_framework/`:**
- Purpose: The entire reusable agent framework as a pip package
- Contains: 13 sub-modules implementing the orchestrator pattern
- Total: ~7,661 lines of Python across 62 source files
- Key constraint: Zero dependencies on application layer

**`framework/agent_framework/llm/`:**
- Purpose: LLM provider abstraction
- Contains: 3 providers, bidirectional transforms, streaming, retry, circuit breaker
- File count: 12 source files, ~2,078 lines
- Key files: `base.py` (interface), `resilient.py` (factory), `types.py` (all shared types)

**`framework/agent_framework/tools/`:**
- Purpose: Tool registration, routing, execution
- Contains: Registry, router, executor, validator, degrader, builtin tools, MCP client, context management
- File count: 16 source files across 4 subdirectories, ~1,151 lines
- Key files: `router.py` (dispatch pipeline), `types.py` (ToolSpec)

**`framework/agent_framework/agents/`:**
- Purpose: Agent loop and sub-agent spawning
- Contains: Core ReAct loop, filtered router creation
- File count: 3 source files, ~498 lines
- Key file: `agent_loop.py` (406 lines -- the heart of the system)

**`framework/agent_framework/memory/`:**
- Purpose: Dual-layer persistent memory
- Contains: Store facade, log manager, retriever, search, flush, extractor, writer, index, frontmatter
- File count: 10 source files, ~839 lines
- Key files: `store.py` (facade), `semantic_writer.py` (persistence)

**`framework/agent_framework/safety/`:**
- Purpose: Execution boundaries and permission system
- Contains: Path sandbox, permission pipeline, HITL, verification
- File count: 5 source files, ~315 lines
- Key file: `permissions.py` (4-step cascade)

**`framework/agent_framework/tasks/`:**
- Purpose: Persistent task DAG with background execution
- Contains: Manager (CRUD + DAG), runner (async background), 4 tools, types
- File count: 4 source files, ~553 lines
- Key files: `manager.py` (242 lines, full DAG), `runner.py` (118 lines)

**`framework/agent_framework/teams/`:**
- Purpose: Multi-agent team coordination
- Contains: Message bus (JSONL), team manager, 5 tools, types
- File count: 4 source files, ~323 lines
- Key files: `manager.py` (115 lines), `bus.py` (53 lines)

**`framework/tests/`:**
- Purpose: Complete test suite for framework
- Contains: 65 test files, 1 conftest, 1 helper, ~9,386 lines
- Coverage: Every module has dedicated test files following `test_{module}.py` naming

**`backend/`:**
- Purpose: Application layer consuming the framework
- Contains: FastAPI scaffolding (all files empty/0 lines)
- Status: Scaffold only -- no implementation yet

**`frontend/`:**
- Purpose: Web UI for the agent system
- Contains: React 19 + Vite 8 + Tailwind 4 scaffolding
- Status: Scaffold only -- component directories are empty (.gitkeep)

## Key File Locations

**Entry Points:**
- `framework/agent_framework/__init__.py`: Package marker (1 line)
- `backend/main.py`: FastAPI server entry (empty scaffold)
- `frontend/src/main.tsx`: React app mount

**Configuration:**
- `framework/pyproject.toml`: Framework package config (pydantic + httpx deps, pytest)
- `backend/pyproject.toml`: App config (depends on framework via local path, FastAPI + uvicorn)
- `frontend/package.json`: Frontend deps (React 19, Vite 8, Tailwind 4)

**Core Logic:**
- `framework/agent_framework/agents/agent_loop.py`: ReAct agent loop (406 lines)
- `framework/agent_framework/llm/base.py`: LLM adapter interface (195 lines)
- `framework/agent_framework/llm/resilient.py`: Resilient wrapper + factory (187 lines)
- `framework/agent_framework/tools/router.py`: Tool dispatch pipeline (183 lines)
- `framework/agent_framework/orchestrator/planner.py`: Session planning (135 lines)
- `framework/agent_framework/tasks/manager.py`: Task DAG (242 lines)
- `framework/agent_framework/teams/manager.py`: Team manager (115 lines)

**Type Definitions:**
- `framework/agent_framework/llm/types.py`: All LLM types (257 lines)
- `framework/agent_framework/tools/types.py`: Tool system types (60 lines)
- `framework/agent_framework/memory/types.py`: Memory types (42 lines)
- `framework/agent_framework/tasks/types.py`: Task types (46 lines)
- `framework/agent_framework/teams/types.py`: Team types (37 lines)

**Testing:**
- `framework/tests/conftest.py`: Shared fixtures
- `framework/tests/helpers.py`: Test utilities

## Naming Conventions

**Files:**
- Modules: `snake_case.py` (e.g., `agent_loop.py`, `tool_router.py`)
- Private helpers: `_prefix.py` (e.g., `_anthropic.py`, `_normalize.py`)
- Test files: `test_{module_name}.py` (e.g., `test_agent_loop.py`)
- Type files: `types.py` (one per module)

**Directories:**
- Module directories: `snake_case/` matching the Python package name
- Sub-packages: Organized by concern (e.g., `providers/`, `builtin/`, `context/`)

## Where to Add New Code

**New LLM Provider:**
1. Create `framework/agent_framework/llm/providers/{name}_provider.py` implementing `ILLMAdapter`
2. Create `framework/agent_framework/llm/transform/_{name}.py` for message conversion
3. Register in `_PROVIDER_MAP` in `framework/agent_framework/llm/resilient.py:137`
4. Add tests in `framework/tests/test_providers.py` and `framework/tests/test_transform.py`

**New Built-in Tool:**
1. Create handler in `framework/agent_framework/tools/builtin/{name}_tools.py`
2. Register in `create_builtin_registry()` in `framework/agent_framework/tools/builtin/__init__.py`
3. Add tests in `framework/tests/test_builtin_tools.py`

**New System Module (e.g., new capability):**
1. Create directory `framework/agent_framework/{module_name}/`
2. Add `__init__.py` with barrel exports
3. Add `types.py` for data models
4. Integrate into `AgentLoop` via optional constructor parameter
5. Add test files `framework/tests/test_{module}_*.py`

**New Tool Exposed to Agent (system-level tools like tasks/teams):**
1. Create `framework/agent_framework/{module}/tools.py` returning `list[ToolSpec]`
2. Call from application layer: `registry.register(spec)` for each tool
3. Add `framework/tests/test_{module}_tools.py`

**New API Endpoint (application layer):**
1. Add route file in `backend/app/api/v1/{name}.py`
2. Register router in `backend/app/api/v1/__init__.py`
3. Add service logic in `backend/app/services/`

**New Frontend Component:**
1. Add component in `frontend/src/components/{category}/{Name}.tsx`
2. Add types in `frontend/src/types/index.ts`
3. Add hooks in `frontend/src/hooks/use{Name}.ts`

**New Skill (runtime discoverable):**
1. Create directory with `SKILL.md` (frontmatter + body)
2. Place in skill directories passed to `SkillRegistry`
3. Framework auto-discovers via directory scan

## Special Directories

**`framework/.agent_results/`:**
- Purpose: Large tool result disk dumps (when result exceeds 20K chars)
- Generated: Yes (by `tools/context/result_truncator.py`)
- Committed: No (should be in `.gitignore`)

**`{tasks_dir}/`:**
- Purpose: Persistent task JSON files (`task_{id}.json`)
- Generated: Yes (by `tasks/manager.py`)
- Committed: No (runtime data)

**`{team_dir}/inbox/`:**
- Purpose: Inter-agent JSONL message files
- Generated: Yes (by `teams/bus.py`)
- Committed: No (runtime data)

**`{memory_dir}/`:**
- Purpose: Persistent memory files (daily logs + semantic .md files + MEMORY.md index)
- Generated: Yes (by `memory/` module)
- Committed: No (runtime data, except possibly seed memories)

**`docs/plans/`:**
- Purpose: Planning documents for project phases
- Generated: No
- Committed: Yes

## Module Size Summary

| Module | Files | Lines | Key File |
|--------|-------|-------|----------|
| llm/ | 12 | 2,078 | `providers/anthropic_provider.py` (372) |
| tools/ | 16 | 1,151 | `context/compactor.py` (204) |
| agents/ | 3 | 498 | `agent_loop.py` (406) |
| memory/ | 10 | 839 | `semantic_writer.py` (133) |
| tasks/ | 4 | 553 | `manager.py` (242) |
| teams/ | 4 | 323 | `tools.py` (118) |
| safety/ | 5 | 315 | `permissions.py` (110) |
| skills/ | 3 | 294 | `registry.py` (166) |
| hooks/ | 2 | 194 | `manager.py` (145) |
| orchestrator/ | 3 | 135 | `planner.py` (135) |
| prompts/ | 3 | 165 | `assembler.py` (84) |
| commands/ | 2 | 141 | `router.py` (106) |
| **Total framework** | **67** | **~7,661** | |
| **Total tests** | **67** | **~9,386** | |

---

*Structure analysis: 2026-05-28*
