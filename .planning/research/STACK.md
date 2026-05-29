# Technology Stack -- v0.0.2 New Capabilities

**Project:** Agent Framework v0.0.2 (Agent expansion + orchestration + A2A)
**Researched:** 2026-05-29
**Scope:** ONLY stack additions/changes for NEW features. Existing validated stack (Python 3.11+, Pydantic v2, httpx, asyncio, pytest, FastAPI scaffold) is NOT re-evaluated.

## Summary

Only two new external dependencies are needed: `tavily-python` for real web search and `a2a-sdk` for A2A protocol. Everything else (Agent ABC, OrchestratorEngine, Agent MD config) builds on the existing stack with pure Python code using Pydantic v2 and asyncio.

## Recommended Stack Additions

### External Libraries (NEW)

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| `tavily-python` | >=0.5.0 | Real web search API client | Purpose-built for AI agents. Provides `AsyncTavilyClient` with httpx-based async (aligns with project's async-first architecture). 1000 free credits/month for development. Widest agent framework adoption (LangChain, CrewAI built-in integrations). Single API key via env var fits existing `SecretStr` pattern. |
| `a2a-sdk` | >=1.0.3 | A2A protocol client and server | Official Google/Linux Foundation Python SDK for Agent-to-Agent protocol. Provides `A2AClient`, `A2AServer`, data models (`AgentCard`, `Task`, `Message`, `Part`, `Artifact`). `a2a-sdk[http-server]` extra adds FastAPI server integration (project already has FastAPI scaffold). Core dependency is `httpx>=0.27.0` which is already in the stack -- no new transitive deps. |

### Internal Modules (No New Dependencies)

| Module | Purpose | Built With | Rationale |
|--------|---------|------------|-----------|
| `AgentABC` + `AgentEvent` | Abstract base class for all agent types, unified event model | `abc.ABC`, Pydantic v2 discriminated union, `asyncio` | No external library needed. Pure Python ABC with `@abstractmethod run()` returning `AsyncGenerator[AgentEvent, None]`. AgentEvent uses Pydantic v2 discriminated union on `type` field. |
| `PlanAndSolveAgent` | Generate plan then execute step by step | Existing `AgentLoop` as executor, existing `PlanningState`/`PlanItem` from `orchestrator/planner.py` | Two-phase agent: planner LLM call generates ordered steps, then reuses `AgentLoop` for each step. No new deps -- orchestrator/planner.py already has the plan data model. |
| `ReflectionAgent` | Execute, self-critique, refine loop | Existing `AgentLoop` as generator, Pydantic v2 for critique schema | Self-Refine pattern: one LLM generates, another critiques, loop until quality threshold or max iterations. No new deps. |
| `OrchestratorEngine` | Complexity routing, plan/execute/adjust cycle | All agent types above, existing `PlanningState`, Pydantic v2 | Assess complexity -> route to agent type -> monitor -> adjust. Strategy pattern for routing. No new deps. |
| `AgentManifest` + `AgentRegistry` + `AgentFactory` | Agent configuration via Markdown files | Existing `parse_frontmatter_lines` from `memory/frontmatter.py`, `SkillRegistry` pattern from `skills/` | Direct analog to existing Skill system. Reuse frontmatter parser (flat key:value is sufficient for agent config). No new deps. |

## Alternatives Considered

### Web Search

| Recommended | Alternative | Why Not |
|-------------|-------------|---------|
| `tavily-python` | `exa-py` (Exa) | Exa is semantic-search focused, not agent-purposed. More complex API. Less common in agent frameworks. No clear free tier advantage. Tavily is simpler and more widely adopted in the agent ecosystem. |
| `tavily-python` | SerpAPI (`google-search-results`) | Wrapper around Google SERP. Requires billing setup. Not purpose-built for agents. Tavily returns structured results designed for LLM consumption. |
| `tavily-python` | Brave Search API | Good quality results but requires separate API key management and response parsing. No Python SDK with built-in async support comparable to Tavily's `AsyncTavilyClient`. |

### A2A Protocol

| Recommended | Alternative | Why Not |
|-------------|-------------|---------|
| `a2a-sdk` (official) | `python-a2a` (community) | `python-a2a` is a third-party implementation. `a2a-sdk` is the official SDK from the A2A project (Google/Linux Foundation). Official SDK gets spec updates first and has better long-term maintenance guarantees. |
| `a2a-sdk` | Manual JSON-RPC implementation | Could implement JSON-RPC 2.0 handler from scratch with httpx + FastAPI. But `a2a-sdk[http-server]` provides ready-made data models, server, and client. Reinventing would be ~500 lines for marginal dependency savings. The SDK's core dep (httpx) is already in stack. |

### Agent Abstraction

| Recommended | Alternative | Why Not |
|-------------|-------------|---------|
| Pure Python ABC | LangGraph | LangGraph is an opinionated framework with its own graph abstraction. Adding it would create a competing architecture. The project has its own agent loop, tool system, and orchestrator -- LangGraph would duplicate or conflict with all of these. |
| Pure Python ABC | CrewAI | Same concern as LangGraph -- CrewAI brings its own agent abstraction that would conflict with the existing architecture. |
| Pure Python ABC | AutoGen | Microsoft's AutoGen has its own agent base class and message passing. Would require adapting the existing tool system and LLM adapter to fit AutoGen's abstractions. |

## Integration Points

### tavily-python Integration

```
framework/agent_framework/tools/search_tools.py  (NEW file)
  - WebSearchTool(ToolSpec) wrapping AsyncTavilyClient
  - API key from env: TAVILY_API_KEY (stored via SecretStr in tool config)
  - Returns JSON: [{"title": ..., "url": ..., "content": ..., "score": ...}]
  - Registered with ToolRouter like any other tool

Existing code touch points:
  - framework/agent_framework/tools/router.py -- no changes needed (ToolSpec registration)
  - framework/pyproject.toml -- add tavily-python dependency
```

### a2a-sdk Integration

```
framework/agent_framework/a2a/                    (NEW package)
  - __init__.py
  - server.py    -- A2AServer: wraps AgentABC as A2A HTTP endpoint
  - client.py    -- A2AClient: sends tasks to remote A2A agents
  - card.py      -- AgentCard generation from AgentManifest
  - transport.py -- JSON-RPC 2.0 request/response handling

Dependencies on existing code:
  - AgentABC.run() -> A2A server calls run() and maps AgentEvent -> A2A Artifact
  - AgentManifest  -> AgentCard generation (frontmatter fields -> A2A spec fields)
  - httpx (already in stack) -> a2a-sdk core transport
  - FastAPI (scaffold exists) -> a2a-sdk[http-server] server mounting

Existing code touch points:
  - framework/pyproject.toml -- add a2a-sdk[http-server] dependency
  - No changes to existing agent code -- A2A wraps AgentABC from outside
```

### Internal Module Integration (No New Deps)

```
framework/agent_framework/agents/
  - base.py              (NEW) -- AgentABC, AgentEvent discriminated union
  - agent_loop.py        (MODIFY) -- AgentLoop(AgentABC), LoopEvent adapts to AgentEvent
  - sub_agent.py         (MODIFY) -- Update type hints to use AgentABC
  - plan_and_solve.py    (NEW) -- PlanAndSolveAgent(AgentABC)
  - reflection.py        (NEW) -- ReflectionAgent(AgentABC)

framework/agent_framework/orchestrator/
  - engine.py            (REPLACE scaffold) -- OrchestratorEngine
  - planner.py           (EXISTING, no changes) -- PlanningState, PlanItem reused

framework/agent_framework/agents/config/
  - manifest.py          (NEW) -- AgentManifest dataclass
  - registry.py          (NEW) -- AgentRegistry (follows SkillRegistry pattern)
  - factory.py           (NEW) -- AgentFactory.create(name) -> AgentABC

framework/agent_framework/tools/
  - search_tools.py      (NEW) -- WebSearchTool wrapping tavily-python
```

## Installation

```bash
# From framework/ directory

# Production dependencies (add to pyproject.toml [dependencies])
uv pip install "tavily-python>=0.5.0" "a2a-sdk[http-server]>=1.0.3"

# No new dev/test dependencies needed
# pytest, pytest-asyncio already in stack
```

### pyproject.toml Changes

```toml
[project]
dependencies = [
    "pydantic>=2.0.0",
    "httpx>=0.27.0",
    "tavily-python>=0.5.0",
    "a2a-sdk[http-server]>=1.0.3",
]
```

## What NOT to Add

| Library | Why NOT | Reasoning |
|---------|---------|-----------|
| `pyyaml` | Not needed for Agent MD config | Existing `parse_frontmatter_lines` handles flat key:value pairs. Agent config fields (name, type, model, tools, max_steps) are all flat. If nested config is needed later, reconsider then. |
| `langchain` / `langgraph` | Competing architecture | These bring their own agent loop, tool abstraction, and state management. The project already has all of these. Adding them creates dual architectures. |
| `crewai` | Competing architecture | Same concern as LangChain. CrewAI has its own agent/process abstraction that would conflict. |
| `autogen-agentchat` | Competing architecture | Microsoft's AutoGen brings its own runtime. Would require adapters for existing tool system and LLM layer. |
| `grpcio` | Not needed for A2A sync mode | A2A spec supports gRPC binding but PROJECT.md scopes to sync HTTP only. JSON-RPC over HTTP uses plain httpx. |
| `sse-starlette` | Not needed (A2A streaming out of scope) | PROJECT.md explicitly excludes A2A SSE streaming. Add only if streaming is prioritized in a future milestone. |
| `websockets` | Not needed | A2A sync mode uses HTTP POST, not WebSocket. No other feature requires WebSocket. |

## Dependency Risk Assessment

| Dependency | Risk | Mitigation |
|------------|------|------------|
| `tavily-python` | LOW -- Stable API, acquired by Nebius (infrastructure backing). Risk: service could change pricing. | Abstract behind `WebSearchTool` interface. If Tavily becomes unsuitable, swap to Exa or Brave with one adapter change. |
| `a2a-sdk` | MEDIUM -- v1.0.3 is early. A2A spec is evolving (Google/Linux Foundation). API may change between minor versions. | Pin minimum version. Wrap SDK types behind framework interfaces so SDK changes don't leak into agent code. The `AgentCard`/`Task`/`Message` data models are unlikely to change dramatically (spec-stable). |

## Sources

- Tavily Python SDK: https://github.com/tavily-ai/tavily-python (verified SDK structure, AsyncTavilyClient)
- A2A SDK on PyPI: https://pypi.org/project/a2a-sdk/ (v1.0.3, httpx dependency confirmed)
- A2A Protocol Specification: https://google.github.io/A2A/specification/ (data model, operations, bindings)
- A2A GitHub: https://github.com/a2aproject/A2A (official samples and spec)
- Existing codebase: `framework/agent_framework/memory/frontmatter.py` (frontmatter parser, flat key:value)
- Existing codebase: `framework/agent_framework/skills/manifest.py` (MD config pattern to reuse)
- Existing codebase: `framework/agent_framework/orchestrator/planner.py` (PlanningState/PlanItem model)
- Existing codebase: `framework/pyproject.toml` (current dependencies)
