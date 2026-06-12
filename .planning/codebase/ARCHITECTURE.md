<!-- refreshed: 2026-05-28 -->
# Architecture

**Analysis Date:** 2026-05-28

## System Overview

```text
┌─────────────────────────────────────────────────────────────────────┐
│                         Application Layer                           │
│  `backend/app/`  (FastAPI, depends on framework via pip install -e) │
├─────────────────────────────────────────────────────────────────────┤
│                         Frontend (React)                            │
│  `frontend/src/`  (Vite + React + TypeScript + Tailwind)            │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ HTTP API
┌──────────────────────────────▼──────────────────────────────────────┐
│                     Agent Framework Core                            │
│  `framework/agent_framework/`                                       │
│                                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐            │
│  │ agents/  │  │ commands/ │  │  hooks/  │  │  tasks/  │            │
│  │AgentLoop │  │ CommandR. │  │ HookMgr  │  │TaskRunner│            │
│  └────┬─────┘  └──────────┘  └──────────┘  └────┬─────┘            │
│       │                                         │                  │
│  ┌────▼─────────────────────────────────────────▼─────┐            │
│  │                    tools/                           │            │
│  │  ToolRouter → ToolExecutor → ToolSpec handlers      │            │
│  │  ToolRegistry, McpManager, ToolValidator, Degrader  │            │
│  └───────────┬─────────────────────────────────────────┘            │
│              │                                                      │
│  ┌───────────▼───────────┐  ┌──────────────────────────┐           │
│  │        llm/           │  │     orchestrator/        │           │
│  │ ILLMAdapter (ABC)     │  │ Planner (session plans)  │           │
│  │ Providers x3          │  │ Engine (scaffold)        │           │
│  │ Transform, Streaming  │  │ Router (scaffold)        │           │
│  │ Resilient, Retry      │  └──────────────────────────┘           │
│  │ CircuitBreaker        │                                         │
│  └───────────────────────┘                                         │
│                                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│  │ memory/  │  │ prompts/ │  │ safety/  │  │ skills/  │           │
│  │Episodic  │  │Assembler │  │Boundary  │  │Registry  │           │
│  │Semantic  │  │Profiles  │  │Perms     │  │Manifest  │           │
│  │Flush     │  │Templates │  │HITL      │  │Tool      │           │
│  └──────────┘  └──────────┘  │Verify    │  └──────────┘           │
│                               └──────────┘                         │
│  ┌──────────┐                                                      │
│  │  teams/  │                                                      │
│  │MsgBus    │                                                      │
│  │TeamMgr   │                                                      │
│  └──────────┘                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | Key File(s) |
|-----------|----------------|-------------|
| AgentLoop | ReAct loop: LLM call -> tool dispatch -> repeat until done | `framework/agent_framework/agents/agent_loop.py` |
| ILLMAdapter | Abstract LLM provider interface (complete + stream) | `framework/agent_framework/llm/base.py` |
| ResilientLLMAdapter | Retry + circuit breaker wrapper around any provider | `framework/agent_framework/llm/resilient.py` |
| ToolRouter | Dispatch tool calls: builtin / mcp / agent, with perms + hooks | `framework/agent_framework/tools/router.py` |
| ToolRegistry | Name -> ToolSpec dispatch map | `framework/agent_framework/tools/registry.py` |
| ToolExecutor | Timeout, error wrapping, truncation, validation | `framework/agent_framework/tools/executor.py` |
| PlanningState | Session plan tracking with drift detection | `framework/agent_framework/orchestrator/planner.py` |
| MemoryStore | Dual-layer memory facade (episodic + semantic) | `framework/agent_framework/memory/store.py` |
| PromptAssembler | AgentProfile -> ordered system prompt | `framework/agent_framework/prompts/assembler.py` |
| PermissionPipeline | DENY -> MODE -> ALLOW -> ASK cascade | `framework/agent_framework/safety/permissions.py` |
| HookManager | Shell hook lifecycle: register, match, fire | `framework/agent_framework/hooks/manager.py` |
| SkillRegistry | Multi-directory skill discovery with mtime refresh | `framework/agent_framework/skills/registry.py` |
| TaskManager | Persistent task DAG with JSON files | `framework/agent_framework/tasks/manager.py` |
| TaskRunner | Background AgentLoop execution with notification drain | `framework/agent_framework/tasks/runner.py` |
| TeamManager | Persistent teammate loops with inbox-based messaging | `framework/agent_framework/teams/manager.py` |
| MessageBus | JSONL file inbox for inter-agent communication | `framework/agent_framework/teams/bus.py` |
| CommandRouter | `/command` parsing -> builtin or skill resolution | `framework/agent_framework/commands/router.py` |
| McpManager | MCP server lifecycle + tool registration + call routing | `framework/agent_framework/tools/mcp/config.py` |

## Pattern Overview

**Overall:** Orchestrator pattern with a ReAct agent loop at the core. The framework is a standalone pip package; the application layer consumes it.

**Key Characteristics:**
- **Provider abstraction:** `ILLMAdapter` ABC with 3 providers (Anthropic, OpenAI, DeepSeek), each with a bidirectional transform layer
- **Tool system pipeline:** `ToolRouter.dispatch()` chains permission check -> pre-hooks -> route (builtin/mcp/agent) -> execute -> degrade on failure -> post-hooks
- **Session planning:** Plans parsed from `<plan>` tags in LLM output, tracked with drift detection (WARN/ABORT)
- **Dual-layer memory:** Episodic (daily log files, keyword search) + Semantic (LLM-scored retrieval, frontmatter-indexed markdown files)
- **Context management:** Automatic compaction when token estimate exceeds threshold, with LLM-generated summary replacing old turns
- **Everything-is-a-tool:** SubAgents, tasks, team operations, skills -- all exposed as `ToolSpec` objects registered in `ToolRegistry`

## Layers

### LLM Adapter Layer

- Purpose: Abstract away provider-specific HTTP APIs
- Location: `framework/agent_framework/llm/`
- Contains: Provider implementations, transform codecs, streaming parsers, retry/circuit-breaker
- Depends on: `httpx`, `pydantic`
- Used by: `agents/`, `memory/` (for LLM-based extraction/scoring/retrieval), `tools/context/` (compaction)

### Tool System Layer

- Purpose: Register, validate, route, and execute tool calls
- Location: `framework/agent_framework/tools/`
- Contains: Registry, router, executor, validator, degrader, builtin tools, MCP client, context management
- Depends on: `llm/` (types only), `safety/` (permissions)
- Used by: `agents/agent_loop.py` (primary consumer)

### Agent Loop Layer

- Purpose: Drive the ReAct cycle (think -> act -> observe -> repeat)
- Location: `framework/agent_framework/agents/`
- Contains: `AgentLoop` (core), `sub_agent.py` (one-off child loops)
- Depends on: `llm/`, `tools/`, `orchestrator/planner.py`, `prompts/`, `skills/`, `hooks/`, `tasks/`, `teams/`
- Used by: Application layer, `tasks/runner.py`, `teams/manager.py`

### Memory Layer

- Purpose: Dual-layer persistent memory (episodic + semantic)
- Location: `framework/agent_framework/memory/`
- Contains: Store facade, log manager, semantic writer/extractor, retriever, flush, frontmatter, index
- Depends on: `llm/` (for LLM-based scoring/extraction)
- Used by: Application layer, `tools/builtin/` (memory_search tool)

### Safety Layer

- Purpose: Execution boundary, permission pipeline, HITL, verification
- Location: `framework/agent_framework/safety/`
- Contains: Path sandbox, permission cascade, HITL manager, verification runner
- Depends on: `prompts/profiles.py` (AgentProfile for permission config)
- Used by: `tools/router.py` (permission pipeline)

### Prompt Layer

- Purpose: Compose system prompts from modular blocks
- Location: `framework/agent_framework/prompts/`
- Contains: Assembler, profile model, templates (plan/drift)
- Depends on: `skills/` (optional, for skill catalog injection)
- Used by: `agents/agent_loop.py`

### Skills Layer

- Purpose: Discover and load SKILL.md documents from directories
- Location: `framework/agent_framework/skills/`
- Contains: Registry (multi-dir scanner), manifest parser, load_skill tool
- Depends on: `memory/frontmatter.py`, `tools/types.py`
- Used by: `agents/agent_loop.py`, `commands/router.py`

### Tasks Layer

- Purpose: Persistent task DAG with background execution
- Location: `framework/agent_framework/tasks/`
- Contains: Manager (CRUD + DAG), Runner (asyncio background), 4 tool specs, types
- Depends on: `agents/agent_loop.py` (runner creates loops), `tools/types.py`
- Used by: `agents/agent_loop.py` (notification drain)

### Teams Layer

- Purpose: Persistent teammate agents with inbox-based messaging
- Location: `framework/agent_framework/teams/`
- Contains: MessageBus (JSONL inbox), TeamManager (spawn/shutdown), 5 tool specs, types
- Depends on: `agents/agent_loop.py`, `agents/sub_agent.py`
- Used by: `agents/agent_loop.py` (notification drain)

### Commands Layer

- Purpose: Parse `/command` user input into resolved actions
- Location: `framework/agent_framework/commands/`
- Contains: Router, types
- Depends on: `skills/registry.py`
- Used by: Application layer (pre-processing user input)

### Hooks Layer

- Purpose: Shell-based lifecycle hooks (PreToolUse, PostToolUse, SessionStart)
- Location: `framework/agent_framework/hooks/`
- Contains: Manager, types
- Depends on: `asyncio` (subprocess execution)
- Used by: `tools/router.py`, `agents/agent_loop.py`

## Data Flow

### Primary Request Path (ReAct Loop)

1. User input arrives at `AgentLoop.run()` (`agents/agent_loop.py:243`)
2. System prompt assembled from profile/skills (`agents/agent_loop.py:131-140`)
3. Session plan context injected into message history (`agents/agent_loop.py:233-241`)
4. Background notifications drained (tasks + teams) (`agents/agent_loop.py:289-314`)
5. Context compaction check via `_maybe_compact()` (`agents/agent_loop.py:196-231`)
6. LLM called via `adapter.complete()` (`agents/agent_loop.py:326`)
7. If `stop_reason == TOOL_USE`: extract tool calls, dispatch via `ToolRouter.dispatch()` (`agents/agent_loop.py:361-399`)
8. `ToolRouter.dispatch()` chains: permissions -> pre-hooks -> route/execute -> degrade -> post-hooks (`tools/router.py:58-156`)
9. Tool result appended to messages, loop continues from step 3
10. If `stop_reason == END_TURN`: yield `done` event, return (`agents/agent_loop.py:343-348`)

### Tool Dispatch Pipeline

1. `ToolRouter.dispatch(call, ctx)` receives a `ToolCall` (`tools/router.py:58`)
2. Permission pipeline checks (DENY -> MODE -> ALLOW -> ASK) (`tools/router.py:65-76`)
3. PreToolUse hooks fire, may block or modify input (`tools/router.py:79-98`)
4. Route by name prefix: `mcp__` -> MCP, `agent__` -> agent, else -> builtin (`tools/router.py:100-107`)
5. Builtin: `ToolExecutor.execute()` -> validate -> call handler -> truncate (`tools/executor.py:18-53`)
6. On failure: check `ToolDegrader` for fallback (`tools/router.py:110-117`)
7. PostToolUse hooks fire, may inject supplementary info (`tools/router.py:138-155`)

### Memory Flush Pipeline

1. Conversation text extracted from message history (`memory/flush.py:49-80`)
2. LLM extracts key events (decisions, errors, preferences) via structured prompt
3. Events written to daily log file via `EpisodicLogManager.write_raw()` (`memory/log_manager.py:54-61`)
4. Optionally cascades to `SemanticExtractor` -> `SemanticWriter` for long-term memory

### Team Communication Flow

1. Agent calls `send_message` tool -> `MessageBus.send()` writes JSONL line (`teams/bus.py:19-31`)
2. Teammate loop reads inbox via `MessageBus.read_inbox()` (destructive read) (`teams/bus.py:33-48`)
3. Teammate's `AgentLoop` processes inbox content as a resumed conversation (`teams/manager.py:102-109`)
4. On shutdown or idle timeout, notification pushed to `TeamManager.notifications` queue (`teams/manager.py:113-115`)
5. Lead agent drains notifications each ReAct step (`agents/agent_loop.py:306-314`)

### Sub-Agent Spawning Flow

1. Agent calls `run_subagent` tool (`agents/sub_agent.py:59-92`)
2. `create_filtered_router()` strips recursive tools (run_subagent, task_create, spawn_teammate) (`agents/sub_agent.py:14-23`)
3. New `AgentLoop` created with filtered router, runs to completion
4. Final text extracted from `done` events and returned as `ToolResult`

**State Management:**
- All mutable state lives in `AgentLoop._messages` (message history) and `ToolUseContext.extra` (shared runtime bag)
- `PlanningState` stored in `ctx.extra["planning_state"]`
- Task DAG persisted as individual JSON files in `tasks_dir/`
- Team messages persisted as JSONL files in `team_dir/inbox/`
- Memory persisted as markdown files in `memory_dir/`

## Key Abstractions

**ILLMAdapter (ABC):**
- Purpose: Single-provider LLM interface with complete + stream
- Examples: `llm/providers/anthropic_provider.py`, `llm/providers/openai_provider.py`, `llm/providers/deepseek_provider.py`
- Pattern: Strategy -- providers are interchangeable; `ResilientLLMAdapter` decorates with retry + circuit breaker
- Factory: `create_adapter()` in `llm/resilient.py:153` creates provider by name string

**ToolSpec:**
- Purpose: Self-contained tool definition: LLM schema + handler function
- Examples: `tools/builtin/file_tools.py`, `tasks/tools.py`, `teams/tools.py`, `skills/tool.py`
- Pattern: Command -- each tool encapsulates its own validation and execution
- Registration: `ToolRegistry.register(spec)` makes it available to `ToolRouter`

**AgentLoop:**
- Purpose: ReAct agent that drives LLM multi-turn tool calling
- Examples: `agents/agent_loop.py`
- Pattern: Generator -- `run()` is an async generator yielding `LoopEvent` objects
- Extension: Composable via optional dependencies (hooks, tasks, teams, skills, planning)

**AgentProfile:**
- Purpose: Declarative agent persona (soul, rules, identity, tools, permissions)
- Examples: `prompts/profiles.py`
- Pattern: Configuration object -- loaded from directory of markdown files

## Entry Points

**Framework entry:**
- Location: `framework/agent_framework/__init__.py`
- Triggers: `pip install -e .` from `framework/`, then `from agent_framework.xxx import ...`
- Responsibilities: Exposes all public APIs via `__init__.py` barrel exports

**Application entry:**
- Location: `backend/main.py` (scaffold, 0 lines)
- Triggers: `uvicorn backend.main:app`
- Responsibilities: FastAPI server wiring (not yet implemented)

**Frontend entry:**
- Location: `frontend/src/main.tsx`
- Triggers: `npm run dev`
- Responsibilities: React app mount

**Test entry:**
- Location: `framework/tests/conftest.py`
- Triggers: `cd framework && pytest tests/ -v`
- Responsibilities: Shared fixtures and test configuration

## Architectural Constraints

- **Threading:** Single-threaded asyncio event loop. All I/O is async. `asyncio.Lock` used in `TaskManager` for serialized file writes. No thread pool or worker threads.
- **Global state:** `safety/permissions.py` has module-level `_CRITICAL_TOOLS` set (empty by default). `ToolRegistry._tools` is instance-scoped, not global.
- **Circular imports:** `tools/router.py` uses lazy imports for `hooks/types.py` to break circular dependency. `agents/agent_loop.py` uses `TYPE_CHECKING` guards for `hooks/manager.py`, `tasks/runner.py`, `teams/manager.py`.
- **Framework/App boundary:** Framework is pip-installable with zero knowledge of the application. Backend depends on framework via `pyproject.toml` local path source.
- **File-based persistence:** Tasks (JSON), team messages (JSONL), memory (Markdown) all use synchronous file I/O, safe under single-threaded asyncio.

## Anti-Patterns

### Scaffold Files (Empty Stubs)

**What happens:** `orchestrator/engine.py` and `orchestrator/router.py` exist but contain 0 lines. `backend/` files are all 0-line stubs.
**Why it matters:** New code placed in scaffold files must match the intended interface. The `engine.py` is reserved for a top-level orchestrator that coordinates multiple agents.
**Do this instead:** Check if a module has actual implementation before depending on it. The real orchestration currently lives in `AgentLoop` itself.

### web_search Is a Mock

**What happens:** `tools/builtin/search_tools.py` returns hardcoded placeholder text, not real search results.
**Why it matters:** Any feature relying on web search will get fake data.
**Do this instead:** Replace with a real search API integration when needed. Register the new handler via the same `ToolSpec` mechanism in `tools/builtin/__init__.py`.

### ToolUseContext.extra Is an Unstructured Bag

**What happens:** `ToolUseContext.extra` is `dict[str, Any]` carrying planning state, skill registry, memory dir, teammate name, message bus, etc.
**Why it matters:** No type safety; keys are magic strings scattered across modules.
**Do this instead:** When adding new context, document the key name. Long-term, consider a typed context model.

## Error Handling

**Strategy:** Layered error handling with typed exceptions.

**Patterns:**
- **LLM errors:** `LLMAdapterError` hierarchy (`RateLimitError`, `ServiceUnavailableError`, `InvalidRequestError`, `CircuitOpenError`) in `llm/base.py`
- **Tool errors:** `ToolResult(is_error=True)` -- tools never throw, they return error results
- **Task errors:** `TaskLimitError`, `TaskNotFoundError`, `TaskConflictError`, `TaskStatusError` in `tasks/manager.py`
- **Safety errors:** `PathEscapesWorkspace` in `safety/boundary.py`
- **MCP errors:** `McpToolError` in `tools/mcp/client.py`
- **Circuit breaker:** `resilient.py` catches `LLMAdapterError` and records success/failure for breaker state

## Cross-Cutting Concerns

**Logging:** Python `logging` module throughout. All modules use `logger = logging.getLogger(__name__)`. No structured logging or centralized log aggregation.

**Validation:** Two levels:
1. Tool parameter validation via `ToolValidator` (JSON Schema type checking) in `tools/validator.py`
2. Semantic memory validation via `SemanticWriter.validate()` (feedback/project must contain Why + How) in `memory/semantic_writer.py`

**Authentication:** Not implemented at framework level. Provider auth via `api_key` parameter in `create_adapter()`. Environment variable patterns expected at application layer.

---

*Architecture analysis: 2026-05-28*
