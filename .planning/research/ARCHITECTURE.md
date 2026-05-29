# Architecture Patterns: v0.0.2 Agent Extension & Orchestration

**Domain:** Python Agent Framework -- multi-type Agent system, orchestration engine, A2A protocol
**Researched:** 2026-05-29
**Confidence:** HIGH (based on direct codebase analysis + A2A SDK documentation)

## Recommended Architecture

The v0.0.2 features integrate with the existing framework through a composition-based extension pattern. New Agent types wrap `AgentLoop` rather than inheriting from it. The `OrchestratorEngine` sits above individual Agent instances. A2A protocol wraps the Agent interface for remote access.

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                        NEW in v0.0.2                                    │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                    OrchestratorEngine                           │    │
│  │  Coordinates multiple Agents via strategies                     │    │
│  │  (sequential, parallel, hierarchical)                          │    │
│  └────────┬──────────────┬──────────────┬─────────────────────────┘    │
│           │              │              │                               │
│  ┌────────▼──────┐ ┌─────▼──────┐ ┌────▼───────────┐                 │
│  │ ReActAgent    │ │ PlanAndSolve│ │ ReflectionAgent│  (Agent ABC)    │
│  │ (wraps Loop)  │ │ (wraps Loop│ │ (wraps Loop    │                 │
│  │               │ │  x2 phases)│ │  xN cycles)    │                 │
│  └───────┬───────┘ └──────┬──────┘ └───────┬────────┘                 │
│          │                │                 │                           │
│  ┌───────▼────────────────▼─────────────────▼──────────────────┐      │
│  │                   AgentLoop (existing, unchanged core)       │      │
│  │  ReAct cycle: LLM call -> tool dispatch -> observe -> repeat │      │
│  └──────────────────────────┬──────────────────────────────────┘      │
│                             │                                          │
│  ┌──────────────────────────▼──────────────────────────────────┐      │
│  │           ToolRouter / ToolRegistry / ToolSpec               │      │
│  └─────────────────────────────────────────────────────────────┘      │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────┐     │
│  │                   A2A Protocol Layer                         │     │
│  │  ┌─────────────────────┐  ┌──────────────────────────────┐  │     │
│  │  │ A2AServer           │  │ A2AClient                    │  │     │
│  │  │ Agent -> JSON-RPC   │  │ JSON-RPC -> Remote Agent     │  │     │
│  │  │ AgentCard + Tasks   │  │ tasks/send, tasks/get        │  │     │
│  │  └─────────────────────┘  └──────────────────────────────┘  │     │
│  └──────────────────────────────────────────────────────────────┘     │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────┐     │
│  │                   AgentConfig (MD files)                      │     │
│  │  Reuses SkillManifest frontmatter pattern                    │     │
│  │  Defines: type, model, tools, system_prompt, profile         │     │
│  └──────────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────────┘
```

## Component Boundaries

### NEW Components

| Component | File Location | Responsibility | Communicates With |
|-----------|--------------|----------------|-------------------|
| AgentABC | `agents/base.py` | Abstract base defining Agent interface: `run()`, `name`, `config` | All Agent subclasses |
| AgentEvent | `agents/base.py` | Unified event model replacing raw `LoopEvent` | OrchestratorEngine, A2A Server, callers |
| ReActAgent | `agents/react_agent.py` (NEW) | Concrete Agent wrapping existing `AgentLoop` | AgentABC, AgentLoop |
| PlanAndSolveAgent | `agents/plan_solve.py` (NEW) | Two-phase Agent: plan first via LLM, then execute steps | AgentABC, AgentLoop (x2 instances) |
| ReflectionAgent | `agents/reflection.py` (NEW) | Execute-reflect-improve loop Agent | AgentABC, AgentLoop (x1 instance, multiple runs) |
| OrchestratorEngine | `orchestrator/engine.py` | Multi-agent coordination with pluggable strategies | AgentABC instances, AgentConfig |
| AgentConfig | `orchestrator/config.py` (NEW) | Parse `.md` files into Agent definitions | SkillManifest pattern (reuse `memory/frontmatter.py`) |
| A2AServer | `orchestrator/a2a_server.py` (NEW) | Expose Agent as A2A JSON-RPC endpoint | AgentABC, httpx/Starlette |
| A2AClient | `orchestrator/a2a_client.py` (NEW) | Call remote A2A agents, present as ToolSpec | httpx, ToolRegistry |
| AgentCardBuilder | `orchestrator/a2a_types.py` (NEW) | Build A2A AgentCard from AgentConfig + capabilities | A2AServer, AgentConfig |

### MODIFIED Components

| Component | File Location | Change Type | What Changes |
|-----------|--------------|-------------|-------------|
| `agents/__init__.py` | `agents/__init__.py` | Extension | Export new Agent types + AgentABC |
| `orchestrator/__init__.py` | `orchestrator/__init__.py` | Extension | Export OrchestratorEngine, AgentConfig, A2A |
| `tools/router.py` | `tools/router.py` | Small change | Implement `_dispatch_agent()` for A2A-wrapped agents |
| `tools/builtin/search_tools.py` | `tools/builtin/search_tools.py` | Replacement | Replace mock web_search with real API |
| `agents/agent_loop.py` | `agents/agent_loop.py` | Minimal | May need minor refactor to support AgentABC wrapper (constructor stays stable) |

### UNCHANGED Components (confirmed safe)

| Component | Why Unchanged |
|-----------|--------------|
| `llm/` (entire module) | Agent types use the same `ILLMAdapter` interface |
| `tools/types.py` | `ToolSpec`, `ToolCall`, `ToolResult`, `ToolUseContext` remain the same |
| `tools/registry.py` | Same registration mechanism for new tools |
| `memory/` (entire module) | Memory system is consumed by AgentLoop, not Agent types |
| `safety/` (entire module) | Permission pipeline stays the same |
| `prompts/` (entire module) | `AgentProfile` and `PromptAssembler` reused as-is |
| `skills/` (entire module) | Skill system reused for AgentConfig parsing pattern |
| `tasks/` (entire module) | Tasks operate below Agent abstraction |
| `teams/` (entire module) | Teams operate below Agent abstraction |
| `hooks/` (entire module) | Hooks stay the same |
| `commands/` (entire module) | Commands stay the same |
| `orchestrator/planner.py` | `PlanningState` is leveraged by PlanAndSolve, not modified |

## Data Flow

### Agent ABC Interface

```text
Caller (Engine / App / Test)
  │
  ▼
Agent.run(input: str, context: AgentContext) -> AsyncGenerator[AgentEvent, None]
  │
  ├── ReActAgent: delegates to AgentLoop.run()
  ├── PlanAndSolveAgent: plan phase -> execute phase (2 sequential AgentLoop runs)
  └── ReflectionAgent: execute -> reflect -> improve (N AgentLoop runs)
  │
  ▼
AgentEvent (unified)
  ├── type: "step" | "tool_result" | "done" | "error" | "plan_update" | "reflection"
  ├── data: dict (content, tool calls, results)
  └── metadata: agent_name, step_number, phase (plan/execute/reflect)
```

### Plan-and-Solve Agent Flow

```text
User input
  │
  ▼
PlanAndSolveAgent.run()
  │
  ├── Phase 1: Planning
  │   └── AgentLoop with system prompt:
  │       "Analyze the task, output <plan>...</plan>"
  │   └── LLM returns plan text with <plan> tags
  │   └── Parse plan via existing parse_plan_response()
  │   └── Yield AgentEvent(type="plan_update", data={plan items})
  │
  ├── Phase 2: Execution
  │   └── AgentLoop with plan injected (caller_injected plan_source)
  │   └── Existing PlanningState + drift detection handles execution
  │   └── Yield AgentEvent per step
  │
  └── Yield AgentEvent(type="done")
```

Key insight: Plan-and-Solve reuses `PlanningState` and `parse_plan_response()` from `orchestrator/planner.py`. The first LLM call generates the plan, then the second AgentLoop run executes it with `plan=items` parameter -- the existing `AgentLoop.run(plan=...)` parameter already supports this.

### Reflection Agent Flow

```text
User input
  │
  ▼
ReflectionAgent.run()
  │
  ├── Iteration 1: Execute
  │   └── AgentLoop runs to completion
  │   └── Collect final output
  │
  ├── Reflection Phase
  │   └── New AgentLoop with reflection prompt:
  │       "Review this output for quality, completeness, errors..."
  │   └── LLM evaluates and suggests improvements
  │   └── Parse reflection result (structured feedback)
  │   └── Yield AgentEvent(type="reflection", data={feedback})
  │
  ├── Decision: continue or done?
  │   └── If feedback indicates issues AND max_iterations not reached:
  │       └── Iteration 2: Improved execution with feedback injected
  │   └── Else: finalize
  │
  └── Yield AgentEvent(type="done", data={final output})
```

### OrchestratorEngine Flow

```text
User input
  │
  ▼
OrchestratorEngine.run(task: str, strategy: str)
  │
  ├── Load Agent definitions from AgentConfig
  │
  ├── Strategy: Sequential
  │   └── For each Agent in order:
  │       └── Agent.run(previous_output)
  │       └── Collect AgentEvent stream
  │       └── Pass output to next Agent
  │
  ├── Strategy: Parallel
  │   └── asyncio.gather(*[Agent.run(task) for Agent in agents])
  │   └── Aggregate results
  │
  ├── Strategy: Hierarchical
  │   └── Lead Agent.run(task) with sub-agents as tools
  │   └── Sub-agents called on demand via ToolSpec registration
  │
  └── Yield OrchestrationEvent(final result)
```

### A2A Protocol Flow (Synchronous Mode)

```text
Remote Client                          Our Framework
     │                                      │
     │  GET /.well-known/agent-card.json    │
     │◄─────────────────────────────────────│  A2AServer returns AgentCard
     │                                      │
     │  POST /a2a/jsonrpc/                  │
     │  {method: "tasks/send",              │
     │   params: {message: ...}}            │
     │─────────────────────────────────────►│  A2AServer
     │                                      │  └── Deserialize A2A Message
     │                                      │  └── Extract user text
     │                                      │  └── Agent.run(text)
     │                                      │  └── Collect final output
     │                                      │  └── Build Task object
     │  {result: {task: {status: "completed",│
     │   artifacts: [...]}}  }             │
     │◄─────────────────────────────────────│
     │                                      │
     │  POST /a2a/jsonrpc/                  │
     │  {method: "tasks/get",               │
     │   params: {taskId: "..."}}           │
     │─────────────────────────────────────►│  Return stored task state
     │◄─────────────────────────────────────│
```

### A2A Client Flow (Calling Remote Agents)

```text
Our Agent                          Remote A2A Agent
    │                                    │
    │  Tool call: "call_remote_agent"    │
    │  {agent_url: "...", message: "..."}│
    │───────────────────────────────────►│  A2AClient
    │                                    │  └── Fetch AgentCard
    │                                    │  └── tasks/send
    │                                    │  └── Poll tasks/get
    │  ToolResult: "remote response"     │
    │◄───────────────────────────────────│
```

The A2AClient wraps the remote agent call as a `ToolSpec`, registered in `ToolRegistry` like any other tool. This follows the existing "everything-is-a-tool" pattern.

## Patterns to Follow

### Pattern 1: Composition over Inheritance for Agent Types

**What:** Each Agent type creates `AgentLoop` instances internally (like `SubAgent` does in `agents/sub_agent.py`). Agent types do NOT subclass `AgentLoop`.

**When:** Always. This is the established pattern in the codebase.

**Why:** AgentLoop has 20+ optional constructor parameters representing cross-cutting concerns (hooks, tasks, teams, skills, compaction). Subclassing would force every Agent type to understand and forward all these parameters. Composition lets each Agent type configure its own AgentLoop instances with only the features it needs.

**Example:**
```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, AsyncGenerator

@dataclass
class AgentEvent:
    """Unified event from any Agent type."""
    type: str  # "step" | "tool_result" | "done" | "error" | "plan_update" | "reflection"
    step: int
    data: dict[str, Any]
    agent_name: str

class AgentBase(ABC):
    """Agent ABC -- all Agent types implement this interface."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    async def run(
        self,
        message: str,
        *,
        context: dict[str, Any] | None = None,
    ) -> AsyncGenerator[AgentEvent, None]:
        """Execute agent logic, yielding events."""
        ...
        # Make this a generator to satisfy ABC
        if False:
            yield
```

### Pattern 2: AgentLoop Construction via Factory Helpers

**What:** Extract the repeated AgentLoop construction pattern into shared factory functions.

**When:** When multiple Agent types need to create AgentLoop instances with similar configuration.

**Example:**
```python
def create_loop(
    adapter: ILLMAdapter,
    model: str,
    router: ToolRouter,
    ctx: ToolUseContext,
    *,
    system_prompt: str,
    max_steps: int = 10,
    **kwargs,
) -> AgentLoop:
    """Shared factory for creating AgentLoop instances within Agent types."""
    return AgentLoop(
        adapter=adapter,
        model=model,
        router=router,
        ctx=ctx,
        max_steps=max_steps,
        system_prompt=system_prompt,
        **kwargs,
    )
```

### Pattern 3: Everything-is-a-Tool for Agent Exposure

**What:** Remote agents (via A2A Client) are exposed as `ToolSpec` objects, registered in `ToolRegistry` like builtin tools.

**When:** Whenever an Agent (local or remote) needs to be callable by another Agent.

**Why:** This is the existing pattern for SubAgent (`create_run_subagent_spec()`), tasks (4 task ToolSpecs), and teams (5 team ToolSpecs). The ToolRouter pipeline (permissions -> hooks -> execute -> degrade) applies uniformly.

**Example:**
```python
def create_a2a_client_spec(
    agent_url: str,
    agent_name: str,
    description: str,
) -> ToolSpec:
    """Wrap an A2A remote agent as a callable ToolSpec."""
    async def handler(args: dict, ctx: ToolUseContext) -> ToolResult:
        client = await create_a2a_client(agent_url)
        result = await client.send_task(args["message"])
        return ToolResult(content=result)

    return ToolSpec(
        name=f"agent__{agent_name}",
        description=description,
        parameters=ToolParameterSchema(
            properties={"message": {"type": "string", "description": "Message to send"}},
            required=["message"],
        ),
        handler=handler,
        timeout_ms=300_000,
    )
```

Note the `agent__` prefix convention -- this matches the existing `mcp__` prefix pattern and routes through `ToolRouter._dispatch_agent()`.

### Pattern 4: MD Frontmatter for Agent Config

**What:** Agent configuration files use YAML frontmatter in `.md` files, reusing the `parse_frontmatter_lines()` pattern from `skills/manifest.py`.

**When:** For declarative Agent definitions loaded at runtime.

**Why:** The codebase already has this pattern for `SKILL.md` files. Reusing it keeps the config approach consistent and shares existing parsing infrastructure.

**Example AGENT.md:**
```markdown
---
name: research_agent
type: plan_and_solve
model: claude-sonnet-4-5
max_steps: 20
allowed_tools:
  - web_search
  - read_file
  - memory_search
system_prompt: "You are a research agent. Plan your approach, then execute."
---

## Additional context loaded into system prompt

This agent specializes in deep research tasks...
```

**Parser pattern (reuses existing code):**
```python
from agent_framework.memory.frontmatter import parse_frontmatter_lines
from agent_framework.skills.manifest import _parse_skill_document

def parse_agent_config(path: Path) -> AgentConfig:
    text = path.read_text(encoding="utf-8")
    meta, body = _parse_skill_document(text)
    return AgentConfig(
        name=meta.get("name", path.stem),
        type=meta.get("type", "react"),
        model=meta.get("model"),
        max_steps=int(meta.get("max_steps", 10)),
        allowed_tools=_parse_list(meta.get("allowed_tools")),
        system_prompt=body or meta.get("system_prompt", ""),
    )
```

### Pattern 5: A2A Protocol Integration via Adapter

**What:** A2A is implemented as an adapter layer that translates between the framework's Agent interface and the A2A JSON-RPC protocol. Do NOT embed A2A types (Pydantic models from `a2a.types`) deep into the framework.

**When:** For A2A server and client implementations.

**Why:** Keeps the framework core independent of the A2A SDK. The A2A SDK's `AgentCard`, `Task`, `Message` types are protocol-level concerns, not framework-level concerns. Translation happens at the adapter boundary.

**Example adapter pattern:**
```python
# orchestrator/a2a_server.py -- adapter translates between our Agent and A2A types
class A2AServer:
    def __init__(self, agent: AgentBase, card: AgentCard) -> None:
        self._agent = agent
        self._card = card

    async def handle_tasks_send(self, a2a_message: A2AMessage) -> A2ATask:
        # Translate A2A message -> framework input
        user_text = self._extract_text(a2a_message)

        # Run agent
        final = ""
        async for event in self._agent.run(user_text):
            if event.type == "done":
                final = self._extract_final_text(event)

        # Translate framework output -> A2A Task
        return self._build_completed_task(user_text, final)
```

## Anti-Patterns to Avoid

### Anti-Pattern 1: Inheriting from AgentLoop

**What:** Creating `class PlanAndSolveAgent(AgentLoop)` with overridden methods.

**Why bad:** AgentLoop is a concrete class with complex internal state (`_messages`, `_last_usage`, `_compact_failures`), 20+ constructor parameters, and tight coupling to tool dispatch. Subclassing creates a fragile coupling where any change to AgentLoop internals breaks subclass behavior.

**Instead:** Follow the SubAgent pattern -- create a NEW `AgentLoop` instance internally. Each Agent type owns its own loop lifecycle.

### Anti-Pattern 2: Leaking A2A SDK Types into Framework Core

**What:** Using `from a2a.types import Task, Message` in `agents/base.py` or `agents/agent_loop.py`.

**Why bad:** Couples the framework core to a specific protocol SDK. The A2A SDK may change between versions (it already migrated from v0.3 ClientFactory to v1.0 `create_client()`). Framework types should remain SDK-independent.

**Instead:** Define framework-internal event types (`AgentEvent`). Translate to/from A2A types only in the `orchestrator/a2a_*.py` adapter layer.

### Anti-Pattern 3: God OrchestratorEngine

**What:** A single OrchestratorEngine class that handles all strategies, agent loading, routing, error recovery, and monitoring.

**Why bad:** Violates single responsibility. Each strategy (sequential, parallel, hierarchical) has distinct control flow and error handling needs. Mixing them makes testing and extension harder.

**Instead:** Strategy pattern -- OrchestratorEngine delegates to `OrchestrationStrategy` implementations. Each strategy is an independent, testable unit.

### Anti-Pattern 4: Modifying AgentLoop Constructor for New Agent Types

**What:** Adding `agent_type: str = "react"` or `reflection_config: ... | None = None` to AgentLoop's constructor.

**Why bad:** AgentLoop already has 20+ parameters. Adding type-specific parameters makes the constructor unmaintainable and couples the loop to specific Agent type concerns.

**Instead:** AgentLoop stays generic. Type-specific behavior lives in the Agent type classes that create and configure their own AgentLoop instances.

### Anti-Pattern 5: Using ToolUseContext.extra for Agent State

**What:** Storing Agent-type-specific state in `ctx.extra["reflection_history"]` or `ctx.extra["plan_phase"]`.

**Why bad:** `ToolUseContext.extra` is already an unstructured bag with magic string keys (planning_state, skill_registry, memory_dir). Adding more keys makes it worse.

**Instead:** Agent types manage their own state internally. Only pass truly shared state through `ctx.extra`, and document every key.

## Build Order (Dependency-Driven)

```text
Phase 1: Foundation
  └── Agent ABC + AgentEvent (agents/base.py)
      ├── No dependencies on other new components
      ├── Existing AgentLoop continues to work unchanged
      └── Tests: Test ABC contract, event types

Phase 2: Concrete Agents
  ├── ReActAgent (thin wrapper around existing AgentLoop)
  ├── PlanAndSolveAgent (2-phase, uses existing PlanningState)
  └── ReflectionAgent (execute-reflect loop)
      ├── Depends on: Phase 1 (Agent ABC)
      ├── Reuses: orchestrator/planner.py (PlanningState, parse_plan_response)
      ├── Reuses: agents/sub_agent.py pattern (composition, filtered routers)
      └── Tests: Each agent type in isolation with mock LLM

Phase 3: Orchestration
  └── OrchestratorEngine + Strategies
      ├── Depends on: Phase 1 (Agent ABC interface)
      ├── Depends on: Phase 2 (concrete agents to coordinate)
      ├── Populates: orchestrator/engine.py (currently empty scaffold)
      └── Tests: Strategy coordination, error propagation, agent chaining

Phase 4: Configuration
  └── AgentConfig (MD file parsing)
      ├── Depends on: Phase 1 (Agent ABC types to configure)
      ├── Reuses: skills/manifest.py (_parse_skill_document, parse_frontmatter_lines)
      ├── Reuses: memory/frontmatter.py (parse_frontmatter_lines)
      └── Tests: Config parsing, validation, missing fields

Phase 5: Real Search
  └── Replace web_search mock
      ├── No dependencies on other new components
      ├── Modifies: tools/builtin/search_tools.py
      └── Tests: Integration with real API (mock at HTTP level)

Phase 6: A2A Protocol
  ├── A2ATypes + AgentCardBuilder
  ├── A2AServer (expose Agent as JSON-RPC endpoint)
  └── A2AClient (call remote agents as ToolSpec)
      ├── Depends on: Phase 1 (Agent ABC interface)
      ├── Depends on: Phase 4 (AgentConfig for AgentCard data)
      ├── Populates: orchestrator/router.py (currently empty scaffold -- A2A routing)
      ├── Modifies: tools/router.py._dispatch_agent() (currently returns error)
      ├── New dependency: a2a-python SDK (`pip install a2a`)
      └── Tests: JSON-RPC request/response, AgentCard, task lifecycle
```

**Rationale for this order:**
1. Agent ABC first because everything depends on it, and it requires zero changes to existing code
2. Concrete agents next because they validate the ABC design and provide testable Agent instances
3. OrchestratorEngine needs concrete agents to coordinate
4. AgentConfig can be built independently but is more useful after agents exist
5. Real search is fully independent -- can be done in parallel with any phase
6. A2A is last because it wraps everything else and has the heaviest external dependency

## Scalability Considerations

| Concern | At 1 Agent | At 5 Agents (Orchestrated) | At 20 Agents (Distributed) |
|---------|-----------|---------------------------|---------------------------|
| Memory | Single AgentLoop._messages list | 5 loop instances, sequential GC | Need message streaming between agents |
| LLM Calls | Sequential, 1 adapter | Parallel calls need rate limit awareness | Need LLMRouter (scaffold) for cost/load routing |
| Tool Conflicts | Single registry, no collision | Namespaced tools (agent__ prefix) | A2A Client ToolSpecs must be uniquely named |
| Error Propagation | LoopEvent type="error" | OrchestratorEngine must catch and decide retry/fallback | A2A Task states (failed, rejected) map to AgentEvent |
| A2A Network | N/A | Single server, localhost | Need connection pooling, retry, timeout on A2AClient |
| Config Loading | Single AGENT.md | Multiple files, validated at startup | Hot reload / watcher for config changes |

## File Structure After v0.0.2

```text
framework/agent_framework/
├── agents/
│   ├── __init__.py              # Updated: export new types
│   ├── base.py                  # NEW: AgentBase ABC + AgentEvent
│   ├── agent_loop.py            # UNCHANGED
│   ├── react_agent.py           # NEW: ReActAgent (wraps AgentLoop)
│   ├── plan_solve.py            # NEW: PlanAndSolveAgent
│   ├── reflection.py            # NEW: ReflectionAgent
│   └── sub_agent.py             # UNCHANGED
├── orchestrator/
│   ├── __init__.py              # Updated: export new types
│   ├── engine.py                # FILLED: OrchestratorEngine + strategies
│   ├── config.py                # NEW: AgentConfig MD parsing
│   ├── planner.py               # UNCHANGED
│   ├── router.py                # FILLED: A2A routing / LLM routing
│   ├── a2a_server.py            # NEW: A2A JSON-RPC server
│   ├── a2a_client.py            # NEW: A2A client + ToolSpec wrapper
│   └── a2a_types.py             # NEW: AgentCard builder, protocol types
├── tools/
│   ├── router.py                # MODIFIED: implement _dispatch_agent()
│   ├── builtin/
│   │   └── search_tools.py      # REPLACED: real search API
│   └── ...                      # REST UNCHANGED
└── ...                          # REST UNCHANGED
```

New files: 7
Modified files: 4 (router.py, search_tools.py, 2x __init__.py)
Unchanged files: ~60

## Sources

- Direct codebase analysis: `agents/agent_loop.py`, `agents/sub_agent.py`, `agents/base.py`, `tools/router.py`, `orchestrator/planner.py`, `orchestrator/engine.py`, `skills/manifest.py`, `memory/frontmatter.py`
- Codebase documentation: `.planning/codebase/ARCHITECTURE.md`, `.planning/codebase/STRUCTURE.md`, `.planning/codebase/CONVENTIONS.md`
- A2A Python SDK documentation via Context7: `a2aproject/a2a-python` v1.0 API -- `create_client()`, `AgentExecutor`, `TaskUpdater`, `AgentCard` structure
- A2A Protocol specification: GitHub README at `github.com/a2aproject/A2A`
- Confidence: HIGH for all integration patterns (composition, frontmatter reuse, ToolSpec wrapping) because they are verified against existing code
