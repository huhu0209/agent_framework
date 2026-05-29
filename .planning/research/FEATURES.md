# Feature Landscape

**Domain:** Agent Framework -- v0.0.2 multi-type Agent system, orchestration engine, and A2A protocol
**Researched:** 2026-05-29

## Table Stakes

Features users expect in a framework claiming "multi-type agents" and "orchestration." Missing any = the framework feels incomplete or dishonest about its claims.

| Feature | Why Expected | Complexity | Dependencies | Notes |
|---------|--------------|------------|--------------|-------|
| Agent ABC base class | Without a shared base, each agent type is ad-hoc. Users expect a consistent `run()` interface. | Low | None (foundational) | Must define `AgentEvent` unified output so callers handle all agent types identically. Current `LoopEvent` dataclass is agent-loop-specific, not agent-agnostic. |
| AgentEvent unified output | Every agent type must yield a common event stream. Without this, consumers need type-specific handling. | Low | Agent ABC | Discriminated union: `StepEvent`, `PlanEvent`, `ReflectionEvent`, `DoneEvent`, `ErrorEvent`. Pydantic v2 discriminated union with `type` field. |
| Plan-and-Solve Agent | The most common "planning agent" pattern in the ecosystem (LangChain, LangGraph, Microsoft Azure patterns all implement it). | Medium | Agent ABC, existing AgentLoop as executor | Two-phase: planner LLM call generates ordered steps, then executor (can reuse current AgentLoop) runs each step. Re-plan on drift detected via existing `PlanningState`. |
| Reflection Agent | Standard self-critique pattern in every agent framework (LangGraph Reflexion, AWS evaluator-reflect-refine, academic papers). | Medium | Agent ABC, existing AgentLoop | Generator-critic loop: execute task, LLM critiques output, refine, repeat up to N iterations or quality threshold. |
| Agent configuration via Markdown | Already established in the codebase via `SkillManifest` frontmatter parsing. Extending to agent definition is natural. | Low-Medium | Existing `parse_frontmatter_lines`, `SkillRegistry` pattern | Reuse frontmatter parser. New `AgentManifest` with fields: `agent_type`, `model`, `tools`, `system_prompt_file`, `max_steps`, etc. |
| Real web search tool | Any agent framework with "tool use" must have a working search tool, not a mock. | Low | Existing ToolRouter, ToolSpec | Tavily recommended: 1000 free credits/month, single `pip install tavily-python`, purpose-built for AI agents. One `WebSearchTool` class wrapping Tavily API. |

## Differentiators

Features that set this framework apart from a basic LangChain/LangGraph usage. Not expected, but valuable.

| Feature | Value Proposition | Complexity | Dependencies | Notes |
|---------|-------------------|------------|--------------|-------|
| OrchestratorEngine with complexity routing | Most frameworks hardcode one agent type. An engine that assesses query complexity and routes to ReAct (simple) or Plan-and-Solve (complex) is a genuine orchestration layer. | High | Agent ABC, Plan-and-Solve Agent, Reflection Agent, existing `PlanningState` | Assess -> Route -> Plan -> Execute -> Adjust loop. The "assess" step is an LLM call that classifies complexity. "Adjust" means replan or switch agent type mid-execution. |
| A2A protocol support (sync mode) | Very few Python frameworks have A2A implemented. This positions the framework for interoperability with Google's growing A2A ecosystem. | High | Agent ABC, ToolRouter, httpx (already a dependency) | JSON-RPC 2.0 over HTTP. Implement AgentCard discovery (`/.well-known/agent.json`), `tasks/send`, `tasks/get`, `tasks/cancel`. Skip streaming (SSE) and push notifications per PROJECT.md scope. |
| Drift detection and replanning | The existing `PlanningState` already has `DriftLevel` enum. Wiring it into the orchestrator to trigger replans (not just warnings) is a differentiator. | Medium | Existing `PlanningState`, `DriftLevel`, `parse_plan_response` | Current code detects drift but only warns. Wire it to actually trigger replan or agent-type switch. |

## Anti-Features

Features to explicitly NOT build. Documented here to prevent scope creep.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| A2A streaming (SSE) mode | PROJECT.md explicitly scopes this out. SSE adds significant complexity (connection management, backpressure, event ordering). | Sync mode only: `tasks/send` returns completed task or `tasks/get` for polling. |
| A2A async mode (webhook callbacks) | PROJECT.md explicitly scopes this out. Requires webhook endpoint management, retry logic, and security considerations. | Sync polling only. |
| LLMCompiler / ReWOO patterns | These are advanced plan-and-execute variants with DAG scheduling and variable binding. Premature optimization for a v0.0.2. | Basic Plan-and-Solve (sequential step execution) is sufficient. Can add DAG later. |
| Multi-agent A2A federation | Building a "registry of registries" or federation layer for discovering agents across organizations. Way beyond scope. | Support single-server A2A. Agent discovery via well-known URI only. |
| Custom agent DSL or visual builder | Some platforms offer drag-and-drop agent construction. This is a framework, not a platform. | Markdown-based agent configuration. Simple, versionable, git-friendly. |
| Agent memory sharing across A2A boundary | A2A is explicitly "opaque execution" -- agents don't share internal state. Trying to sync memory violates the protocol's design principle. | Each agent maintains its own memory. Communication only through A2A Messages and Artifacts. |

## Feature Dependencies

```
Agent ABC + AgentEvent (foundational, no deps)
    |
    +---> Plan-and-Solve Agent (depends on Agent ABC, reuses AgentLoop as executor)
    |
    +---> Reflection Agent (depends on Agent ABC, reuses AgentLoop as generator)
    |
    +---> Agent Config via MD (depends on Agent ABC, reuses frontmatter parser from skills)
    |
    +---> OrchestratorEngine (depends on ALL above: ABC, Plan-and-Solve, Reflection)
    |
    +---> Real Search Tool (independent, depends on ToolRouter only)
    |
    +---> A2A Protocol (depends on Agent ABC for wrapping agents as A2A servers)
```

Dependency ordering for roadmap:

1. Agent ABC + AgentEvent (everything else needs this)
2. Real search tool (independent, can build in parallel with #1)
3. Plan-and-Solve Agent (needs #1)
4. Reflection Agent (needs #1, can parallel with #3)
5. Agent config via MD (needs #1, can parallel with #3/#4)
6. OrchestratorEngine (needs #1, #3, #4)
7. A2A protocol (needs #1, can start after #1 but benefits from #5 for agent card generation)

## Feature Detail: Plan-and-Solve Agent

**How it works (established pattern from Wang et al. "Plan-and-Solve Prompting", LangChain, Microsoft Azure):**

1. **Goal Analysis**: Receive high-level objective from user
2. **Planning Phase**: LLM call generates ordered list of sub-tasks (the "plan")
3. **Execution Phase**: For each step in the plan, invoke tools or an inner agent loop
4. **Observation**: Collect results from each step execution
5. **Replanning**: After execution (or on drift), LLM evaluates whether plan succeeded or needs revision
6. **Completion**: Final response synthesized from all step results

**Key design decisions for this framework:**
- Planner should be a separate LLM call (can use cheaper/smaller model)
- Executor can reuse the existing `AgentLoop` for each step
- Replanning uses existing `PlanningState` drift detection
- Plan representation: ordered list of `PlanItem` (already exists in codebase)

**Complexity drivers:**
- Prompt engineering for the planner (getting good plans from LLM)
- Replanning logic (when to replan vs. when to continue)
- Context management (passing step results to subsequent steps without overflowing context window)

**Confidence: HIGH** -- Well-documented pattern with multiple reference implementations.

Sources:
- [LangChain: Plan-and-Execute Agents](https://www.langchain.com/blog/planning-agents) (detailed 3-variant analysis)
- [Microsoft Azure: AI Agent Orchestration Patterns](https://learn.microsoft.com/en-us/azure/architecture/ai-ml/guide/ai-agent-design-patterns)
- [Google Cloud: Choose a Design Pattern for Agentic AI](https://docs.cloud.google.com/architecture/choose-design-pattern-agentic-ai-system)

## Feature Detail: Reflection Agent

**How it works (established pattern from Shinn et al. "Reflexion", Madaan et al. "Self-Refine"):**

1. **Generation**: Execute task using standard agent loop (the "generator")
2. **Critique**: LLM call evaluates the output against criteria (the "critic")
3. **Refinement**: If critique identifies issues, regenerate with feedback incorporated
4. **Iteration**: Repeat steps 2-3 until quality threshold met or max iterations reached
5. **Output**: Return final refined result

**Two common variants:**
- **Self-Refine**: Single LLM acts as both generator and critic (simpler, fewer API calls)
- **Reflexion**: Critic reflections stored in memory for cross-episode learning (more powerful but more complex)

**Recommendation for this framework:**
- Implement Self-Refine first (single LLM, simpler)
- Store reflection history in existing episodic memory for future potential Reflexion upgrade
- Use configurable `max_reflections` and `quality_threshold` parameters

**Complexity drivers:**
- Defining good critique criteria (task-specific, hard to generalize)
- Avoiding infinite refinement loops (diminishing returns after 2-3 iterations)
- Token cost (each reflection round doubles token usage)

**Confidence: HIGH** -- Well-studied pattern with academic grounding and production implementations.

Sources:
- [LangChain: Reflection Agents](https://www.langchain.com/blog/reflection-agents)
- [AWS Prescriptive Guidance: Evaluator Reflect-Refine Loop](https://docs.aws.amazon.com/prescriptive-guidance/latest/agentic-ai-patterns/evaluator-reflect-refine-loop-patterns.html)
- [arXiv: Self-Reflection in LLM Agents](https://arxiv.org/html/2405.06682v3)

## Feature Detail: OrchestratorEngine

**How it works (pattern synthesized from multiple orchestration frameworks):**

1. **Assess**: Analyze incoming task complexity (LLM call or heuristic classifier)
2. **Route**: Select appropriate agent type based on complexity assessment
   - Simple (factual lookup, single tool call) -> ReAct Agent (existing AgentLoop)
   - Complex (multi-step, requires planning) -> Plan-and-Solve Agent
   - Quality-sensitive (needs accuracy) -> Reflection Agent
3. **Plan**: For complex tasks, generate execution plan
4. **Execute**: Run selected agent
5. **Adjust**: Monitor execution, replan or switch agent type if results are unsatisfactory

**Key design decisions:**
- Complexity assessment can start as a simple heuristic (message length, number of questions, keyword detection) and evolve to LLM-based classification
- The "adjust" step should use existing drift detection from `PlanningState`
- Route selection should be pluggable (strategy pattern) so users can customize routing logic

**Complexity drivers:**
- Complexity assessment accuracy (bad routing = bad outcomes)
- "Adjust" logic (when to replan vs. when to switch agent type vs. when to give up)
- State management across agent-type switches

**Confidence: MEDIUM** -- Pattern is well-described conceptually but few production reference implementations. Most "orchestration" in practice is hardcoded, not dynamic routing.

Sources:
- [Dataiku: Agent Orchestration Explained](https://www.dataiku.com/stories/blog/agent-orchestration-explained)
- [Chainlink: AI Agent Orchestration](https://chain.link/article/ai-agent-orchestration) (routing and execution layer)
- [Microsoft Azure: AI Agent Orchestration Patterns](https://learn.microsoft.com/en-us/azure/architecture/ai-ml/guide/ai-agent-design-patterns)

## Feature Detail: A2A Protocol (Sync Mode)

**How it works (from Google's official A2A specification v0.1.0):**

1. **Agent Discovery**: Client fetches `AgentCard` from `/.well-known/agent.json`
   - AgentCard describes: name, description, URL, capabilities, authentication, skills
   - Each skill has: id, name, description, tags, examples, input/output modes
2. **Task Submission**: Client sends `tasks/send` (JSON-RPC 2.0 over HTTP POST)
   - Request contains: task ID (client-generated UUID), message (role + parts)
   - Parts can be: TextPart, FilePart, DataPart (discriminated union on `type` field)
3. **Task Lifecycle**: submitted -> working -> completed/failed/canceled
   - `input-required` state for multi-turn (agent asks user for more info)
4. **Status Polling**: Client calls `tasks/get` to check task state
5. **Artifacts**: Results returned as `Artifact` objects containing `Part[]`

**What to implement for this framework (sync mode only):**
- `A2AServer`: Wraps any Agent subclass as an A2A-compliant HTTP endpoint
- `A2AClient`: Sends tasks to remote A2A servers
- `AgentCard`: Auto-generated from agent configuration (ties into Agent config via MD)
- JSON-RPC 2.0 handler (can use FastAPI since backend already uses it)
- Transport: HTTP POST, Content-Type: application/json

**What NOT to implement (per PROJECT.md scope):**
- `tasks/sendSubscribe` (SSE streaming)
- `tasks/pushNotification/set` and `tasks/pushNotification/get` (webhook callbacks)
- `tasks/resubscribe` (SSE reconnection)

**Complexity drivers:**
- JSON-RPC 2.0 error handling (11 A2A-specific error codes)
- Task state machine correctness (terminal vs. non-terminal states)
- AgentCard generation from agent configuration
- Part type discrimination (TextPart, FilePart, DataPart) mapping to/from framework's internal types

**Confidence: HIGH** -- Detailed official specification with multiple Python SDK implementations available. The spec is concrete and implementable.

Sources:
- [A2A Protocol Official Specification](https://google.github.io/A2A/specification/) (full protocol reference)
- [A2A GitHub Repository](https://github.com/a2aproject/A2A)
- [python-a2a library](https://github.com/themanojdesai/python-a2a) (reference implementation)
- [A2A Python SDK](https://a2a-protocol.org/latest/sdk/python/api/) (official SDK)

## Feature Detail: Real Web Search Tool

**Recommendation: Tavily**

| Criterion | Tavily | Exa |
|-----------|--------|-----|
| Free tier | 1,000 credits/month | Limited |
| Python SDK | `tavily-python` (mature) | `exa-python` (available) |
| Integration simplicity | 3 lines of code | Similar |
| Purpose | Built for AI agents | Built for semantic search |
| Agent framework adoption | LangChain, CrewAI, LangGraph built-in | Less common |
| Post-acquisition stability | Acquired by Nebius (2026) -- ongoing service | Independent |

**Choose Tavily because:** Purpose-built for AI agents, widest framework adoption, generous free tier for development, simplest integration. The Nebius acquisition provides infrastructure backing.

**Implementation approach:**
- Create `WebSearchTool` extending `ToolSpec`
- Wrap `tavily-python` client
- Return structured results (title, url, snippet) as JSON
- API key via environment variable (existing `SecretStr` pattern)
- Register with `ToolRegistry` like any other tool

**Confidence: HIGH** -- Well-documented API, simple integration, widely adopted.

Sources:
- [Tavily Official Site](https://tavily.com/)
- [Tavily Python SDK on GitHub](https://github.com/tavily-ai/tavily-python)
- [Tavily Agent Skills Documentation](https://docs.tavily.com/documentation/agent-skills)

## Feature Detail: Agent Configuration via Markdown

**How it works (following existing Skill pattern):**

1. **File format**: `AGENTS/agent-name.md` with YAML frontmatter
2. **Frontmatter fields**:
   - `name`: Agent display name
   - `type`: `react` | `plan-and-solve` | `reflection` (maps to Agent subclass)
   - `model`: LLM model identifier (optional, uses default)
   - `tools`: List of tool names this agent can use
   - `system_prompt`: Path to system prompt file, or inline body
   - `max_steps`: Maximum agent loop iterations
   - `max_reflections`: For reflection agents, max critique-refine cycles
3. **Discovery**: `AgentRegistry` scans configured directories (same pattern as `SkillRegistry`)
4. **Instantiation**: `AgentFactory.create(name)` reads config, instantiates correct Agent subclass with configured parameters

**Reuse from existing codebase:**
- `parse_frontmatter_lines` from `memory/frontmatter.py` for YAML parsing
- `SkillRegistry` pattern for multi-directory scanning with mtime refresh
- `SkillManifest` pattern for `AgentManifest` dataclass

**Complexity: Low-Medium** -- Mostly reusing established patterns. The only new logic is the factory instantiation based on `type` field.

**Confidence: HIGH** -- Pattern is well-established within this codebase. Direct analog to existing Skill system.

## MVP Recommendation

**Prioritize (must-have for v0.0.2):**
1. Agent ABC + AgentEvent (foundational -- everything blocks on this)
2. Real search tool (independent, high user-facing value, low effort)
3. Plan-and-Solve Agent (core differentiator for "multi-type agent" claim)
4. Agent configuration via MD (enables declarative agent creation)

**Second wave (v0.0.2 completeness):**
5. Reflection Agent (completes the "multi-type" trio)
6. OrchestratorEngine (ties everything together)

**Third wave (ecosystem play):**
7. A2A protocol sync mode (interoperability story)

**Defer:**
- A2A streaming/async modes: per PROJECT.md out of scope
- LLMCompiler/ReWOO: premature optimization
- Multi-agent federation: beyond scope

## Sources

- [LangChain: Plan-and-Execute Agents](https://www.langchain.com/blog/planning-agents) -- Plan-and-Solve pattern with 3 variants (HIGH confidence)
- [LangChain: Reflection Agents](https://www.langchain.com/blog/reflection-agents) -- Self-Refine and Reflexion patterns (HIGH confidence)
- [A2A Protocol Official Specification v0.1.0](https://google.github.io/A2A/specification/) -- Complete A2A protocol reference (HIGH confidence)
- [A2A GitHub Repository](https://github.com/a2aproject/A2A) -- Official A2A spec and samples (HIGH confidence)
- [python-a2a library](https://github.com/themanojdesai/python-a2a) -- Reference Python A2A implementation (HIGH confidence)
- [A2A Python SDK](https://a2a-protocol.org/latest/sdk/python/api/) -- Official SDK documentation (HIGH confidence)
- [Microsoft Azure: AI Agent Design Patterns](https://learn.microsoft.com/en-us/azure/architecture/ai-ml/guide/ai-agent-design-patterns) -- Orchestration patterns (MEDIUM confidence)
- [AWS: Evaluator Reflect-Refine Loop](https://docs.aws.amazon.com/prescriptive-guidance/latest/agentic-ai-patterns/evaluator-reflect-refine-loop-patterns.html) -- Reflection patterns (HIGH confidence)
- [Tavily Official Documentation](https://docs.tavily.com/) -- Search API for agents (HIGH confidence)
- [Tavily Python SDK](https://github.com/tavily-ai/tavily-python) -- Python integration (HIGH confidence)
- [Dataiku: Agent Orchestration](https://www.dataiku.com/stories/blog/agent-orchestration-explained) -- Orchestration overview (MEDIUM confidence)
- [Google Cloud: Agentic AI Design Patterns](https://docs.cloud.google.com/architecture/choose-design-pattern-agentic-ai-system) -- Pattern selection guide (MEDIUM confidence)
