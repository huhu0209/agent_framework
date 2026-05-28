# External Integrations

**Analysis Date:** 2026-05-28

## LLM Providers

### Anthropic (Messages API)

- **Purpose:** Primary LLM provider; Claude models with extended thinking, tool calling, vision, PDF, computer use
- **SDK/Client:** Custom provider via `httpx.AsyncClient` — `framework/agent_framework/llm/providers/anthropic_provider.py`
- **Base URL:** `https://api.anthropic.com`
- **API Version:** `2023-06-01` (set in `anthropic-version` header)
- **Default Model:** `claude-sonnet-4-6-20250514`
- **Auth:** `ANTHROPIC_API_KEY` env var or `api_key` constructor parameter; sent as `x-api-key` header
- **Key Features Used:**
  - Streaming (SSE with `message_start`/`content_block_start`/`content_block_delta`/`message_delta`/`message_stop`)
  - Extended thinking with `budget_tokens`
  - Tool calling via content blocks (`tool_use`/`tool_result`)
  - System prompt as top-level field (not in messages array)
  - `cache_control` for prompt caching
- **Protocol Differences:** System is a top-level field; tool_use/tool_result are content blocks; thinking has signature for round-trip; multi-block parallel streaming by `content_block_index`
- **Transform Layer:** `framework/agent_framework/llm/transform/_anthropic.py` — converts internal `Message` types to/from Anthropic format

### OpenAI (Chat Completions API)

- **Purpose:** LLM provider; GPT models with structured output, vision, reasoning effort
- **SDK/Client:** Custom provider via `httpx.AsyncClient` — `framework/agent_framework/llm/providers/openai_provider.py`
- **Base URL:** `https://api.openseek.com/v1`
- **Default Model:** `gpt-5`
- **Auth:** `OPENAI_API_KEY` env var or `api_key` constructor parameter; sent as `Bearer` token
- **Key Features Used:**
  - Streaming (SSE with `choices[0].delta`)
  - Tool calling via `delta.tool_calls` with incremental JSON arguments
  - `reasoning_effort` parameter (minimal/low/medium/high) for o-series models
  - Vision (image input)
  - Structured output (`json_schema strict`)
- **Protocol Differences:** No `reasoning_content`; system messages in messages array; tool arguments as stringified JSON
- **Transform Layer:** `framework/agent_framework/llm/transform/_openai.py` — shared with DeepSeek for common patterns

### DeepSeek V4 (OpenAI-compatible API)

- **Purpose:** LLM provider; DeepSeek V4 Pro with reasoning/thinking mode
- **SDK/Client:** Custom provider via `httpx.AsyncClient` — `framework/agent_framework/llm/providers/deepseek_provider.py`
- **Base URL:** `https://api.deepseek.com`
- **Default Model:** `deepseek-v4-pro`
- **Auth:** `DEEPSEEK_API_KEY` env var or `api_key` constructor parameter; sent as `Bearer` token
- **Key Features Used:**
  - Streaming (reuses `OpenAIStreamParser` from streaming.py)
  - `reasoning_content` field (non-standard, must be echoed in tool call scenarios)
  - Thinking mode via `extra_body={"thinking": {"type": "enabled"}}`
  - `reasoning_effort` accepts only `"high"` / `"max"` (not OpenAI's scale)
  - 1M context window
- **Limitations:** No vision support — `ImageBlock` in messages raises `InvalidRequestError`
- **Protocol Quirks:** `temperature`/`top_p` silently ignored in thinking mode (warning logged)
- **Transform Layer:** `framework/agent_framework/llm/transform/_deepseek.py` — handles `reasoning_content` mapping

### Provider Abstraction Layer

- **Interface:** `ILLMAdapter` ABC in `framework/agent_framework/llm/base.py`
- **Unified Types:** `framework/agent_framework/llm/types.py` — `CompletionConfig`, `CompletionResult`, `StreamEvent`, `Message`, `ContentBlock`, `ToolDefinition`
- **Resilience Wrapper:** `framework/agent_framework/llm/resilient.py` — `ResilientLLMAdapter` wraps any provider with retry + circuit breaker
- **Factory:** `create_adapter()` in `resilient.py` — dynamically imports provider class by name string (`"anthropic"` / `"openai"` / `"deepseek"`)
- **Streaming:** `framework/agent_framework/llm/streaming.py` — SSE parsing (`parse_sse_lines`), `OpenAIStreamParser`, `AnthropicStreamParser`, `StreamCollector`
- **Retry & Circuit Breaker:** `framework/agent_framework/llm/retry.py` — exponential backoff with jitter, 429 rate-limit handling, circuit breaker (CLOSED/OPEN/HALF_OPEN states)
- **Transform:** `framework/agent_framework/llm/transform/` — message format converters for each provider, plus `normalize_messages()` for internal consistency

## MCP (Model Context Protocol) Integration

- **Purpose:** Connect to external MCP servers for tool discovery and execution
- **Protocol:** JSON-RPC 2.0 over stdio transport
- **Protocol Version:** `2025-03-26`

### Components:

- **McpClient** (`framework/agent_framework/tools/mcp/client.py`):
  - Manages JSON-RPC id counter, `initialize` handshake, `tools/list` discovery, `tools/call` execution
  - Stores discovered tools as `list[dict]`

- **McpTransport** (`framework/agent_framework/tools/mcp/transport.py`):
  - Abstract base class with `connect()`, `close()`, `send()`, `send_notification()`
  - **StdioTransport** implementation: spawns subprocess, communicates via stdin/stdout with `Content-Length` framing
  - Manages async reader loop for responses and notification queue

- **McpManager** (`framework/agent_framework/tools/mcp/config.py`):
  - Holds all `McpClient` instances, manages lifecycle (`start()`, `shutdown()`)
  - Registers discovered tools into `ToolRegistry` with prefixed names: `mcp__{server_name}__{tool_name}`
  - Routes tool calls to correct MCP server via `call_tool()`
  - Gracefully handles individual server startup failures (logs warning, skips)

- **McpServerConfig** (`framework/agent_framework/tools/mcp/config.py`):
  - Pydantic model: `name`, `transport` (currently only `"stdio"`), `command`, `args`, `env`, `timeout_ms`, `url`, `headers`
  - Supports passing custom env vars to MCP server subprocesses

## Data Storage

### Databases:
- No traditional database — all storage is file-based

### File Storage:
- **Memory Store** (`framework/agent_framework/memory/`):
  - Episodic layer: daily markdown log files in `{memory_dir}/` (via `EpisodicLogManager`)
  - Semantic layer: structured markdown with frontmatter (via `SemanticWriter`)
  - Search: keyword-based for episodic, LLM-scoring for semantic (`LLMScoringRetriever`)
  - Index management: `IndexManager` tracks file metadata
- **Team Communication** (`framework/agent_framework/teams/bus.py`):
  - `MessageBus` uses JSONL file inbox per agent in `{team_dir}/inbox/{name}.jsonl`
  - Messages appended as JSON lines, read and cleared atomically

### Caching:
- LLM prompt caching via Anthropic `cache_control` (provider-side, not application-level)
- No application-level cache implementation

## Authentication & Identity

**LLM Provider Auth:**
- API key per provider, sourced from environment variables or constructor parameters
- Keys stored in `httpx.AsyncClient` headers — not persisted to disk
- No OAuth or token refresh flows

**Application Auth:**
- Not yet implemented — `backend/app/` is scaffolding with FastAPI endpoints

## Monitoring & Observability

**Error Tracking:**
- Python `logging` module throughout — all modules use `logging.getLogger(__name__)`
- Circuit breaker stats available via `CircuitBreaker.get_stats()` for monitoring
- No external error tracking service (no Sentry, etc.)

**Health Checks:**
- Each LLM provider implements `health_check()` — sends lightweight request to verify connectivity
- Used by circuit breaker for fallback routing decisions

## CI/CD & Deployment

**Hosting:**
- Not yet configured

**CI Pipeline:**
- None detected (no `.github/workflows/`, no `Makefile`, no `Dockerfile`)

## Environment Configuration

**Required env vars (at least one provider):**
- `ANTHROPIC_API_KEY` — Anthropic provider
- `OPENAI_API_KEY` — OpenAI provider
- `DEEPSEEK_API_KEY` — DeepSeek provider

**MCP server env vars:**
- Passed per-server via `McpServerConfig.env` dict — no fixed var names

**Secrets location:**
- Environment variables only (no `.env` file detected in repository)
- No secret management service integration

## Webhooks & Callbacks

**Incoming:**
- None

**Outgoing:**
- None

## Internal Integration Points

### Tool System

- **ToolRegistry** (`framework/agent_framework/tools/registry.py`) — central registry for all tools (builtin, MCP, agent)
- **ToolRouter** (`framework/agent_framework/tools/router.py`) — routes tool calls by source: builtin executor, MCP manager, or sub-agent
- **ToolExecutor** (`framework/agent_framework/tools/executor.py`) — executes builtin tool handlers
- **PermissionPipeline** (`framework/agent_framework/safety/permissions.py`) — safety gate before tool execution
- **ToolDegrader** (`framework/agent_framework/tools/degrader.py`) — graceful degradation on tool failures

### Agent System

- **AgentLoop** (`framework/agent_framework/agents/agent_loop.py`) — ReAct loop: LLM call -> tool execution -> LLM call cycle
- **SubAgent** (`framework/agent_framework/agents/sub_agent.py`) — isolated child agent with filtered tool access, prevents recursive tool calls
- **TeamManager** (`framework/agent_framework/teams/manager.py`) — manages persistent teammate agent loops
- **MessageBus** (`framework/agent_framework/teams/bus.py`) — inter-agent JSONL file-based messaging

### Task System

- **TaskManager** (`framework/agent_framework/tasks/manager.py`) — task CRUD and lifecycle
- **TaskRunner** (`framework/agent_framework/tasks/runner.py`) — executes tasks with agent loops
- **Task tools** (`framework/agent_framework/tasks/tools.py`) — `task_create`, `task_status`, `task_update`, `task_list` as agent-callable tools

### Safety System

- **Permissions** (`framework/agent_framework/safety/permissions.py`) — permission pipeline for tool access control
- **Boundary** (`framework/agent_framework/safety/boundary.py`) — agent execution boundaries
- **HITL** (`framework/agent_framework/safety/hitl.py`) — human-in-the-loop approval
- **Verification** (`framework/agent_framework/safety/verification.py`) — output verification

### Context Management

- **Compactor** (`framework/agent_framework/tools/context/compactor.py`) — compresses context when approaching token limits
- **Token Counter** (`framework/agent_framework/tools/context/token_counter.py`) — estimates token count from character count (4 chars = 1 token, 1.33x multiplier for non-English)

---

*Integration audit: 2026-05-28*
