# Project Research Summary

**Project:** Agent Framework v0.0.2 (multi-type Agent system, orchestration engine, A2A protocol)
**Domain:** Python AI Agent Framework
**Researched:** 2026-05-29
**Confidence:** HIGH

## Executive Summary

This milestone extends an existing Python agent framework (v0.0.1, 687 passing tests) from a single ReAct agent loop into a multi-type agent system with orchestration and inter-agent protocol support. The approach is composition-based: new Agent types (Plan-and-Solve, Reflection) create internal `AgentLoop` instances rather than subclassing it, preserving the existing 406-line AgentLoop unchanged. Only two new external dependencies are needed -- `tavily-python` for real web search and `a2a-sdk` for A2A protocol -- both of which align with the existing async/httpx architecture and add no conflicting transitive dependencies.

The key risk is the Agent ABC extraction (Pitfall 1). Getting the abstract interface wrong would break AgentLoop's 24 test functions and 4 direct consumers simultaneously. Research recommends using `typing.Protocol` for consumption and `ABC` only for genuine code reuse, keeping AgentLoop untouched. The second major risk is over-engineering the OrchestratorEngine: research from Google DeepMind and the MAST study shows multi-agent error amplification up to 17.2x and coordination breakdowns in 36.9% of multi-agent failures. The engine must start as a thin factory, not a sophisticated routing system.

The feature dependency graph is well-understood and linear: Agent ABC is foundational, concrete agents follow, the orchestrator depends on all agent types, and A2A wraps everything. This yields a natural 7-phase build order with only the search tool being fully independent.

## Key Findings

### Recommended Stack

Only two new external libraries are needed. Everything else (Agent ABC, OrchestratorEngine, Agent MD config) is pure Python built on existing Pydantic v2 and asyncio infrastructure.

**Core technologies:**
- `tavily-python` >=0.5.0: Real web search API -- purpose-built for AI agents, `AsyncTavilyClient` with httpx-based async, 1000 free credits/month
- `a2a-sdk[http-server]` >=1.0.3: A2A protocol client/server -- official Google/Linux Foundation SDK, core dep is httpx (already in stack)
- Pure Python ABC + `typing.Protocol`: Agent abstraction -- no external dependency, composition over inheritance

**Explicitly excluded:** LangGraph, CrewAI, AutoGen (competing architectures), `pyyaml` (flat frontmatter sufficient), `sse-starlette`/`websockets` (out of scope).

### Expected Features

**Must have (table stakes):**
- Agent ABC base class + AgentEvent unified output -- shared interface for all agent types
- Plan-and-Solve Agent -- the most common planning agent pattern in the ecosystem
- Reflection Agent -- standard self-critique pattern (Self-Refine variant)
- Agent configuration via Markdown -- extends existing SkillManifest pattern
- Real web search tool -- replaces mock, uses Tavily API

**Should have (competitive):**
- OrchestratorEngine with complexity routing -- genuine orchestration layer
- A2A protocol sync mode -- positions framework for Google A2A ecosystem
- Drift detection wired to replanning -- existing PlanningState/DriftLevel triggers replans

**Defer (v2+):**
- A2A streaming (SSE) and async (webhook) modes
- LLMCompiler / ReWOO DAG scheduling patterns
- Multi-agent A2A federation

### Architecture Approach

Composition-based extension: new Agent types wrap `AgentLoop` instances internally (like existing `SubAgent` pattern), never subclass it. A2A is an adapter layer translating between framework AgentEvent types and A2A JSON-RPC protocol types at the boundary. Agent config reuses the existing `parse_frontmatter_lines` / `SkillManifest` pattern.

**Major components:**
1. **AgentBase (ABC) + AgentEvent** -- `run() -> AsyncGenerator[AgentEvent, None]` interface; discriminated union events
2. **PlanAndSolveAgent** -- two-phase plan-then-execute; reuses existing `PlanningState`/`parse_plan_response()`
3. **ReflectionAgent** -- execute-critique-refine loop; hard-capped 2 iterations; structured verdict
4. **OrchestratorEngine** -- thin wrapper, strategy pattern; max 3 agents per chain
5. **A2AServer / A2AClient** -- adapter layer for JSON-RPC 2.0; client wraps remote agents as ToolSpec
6. **AgentConfig (MD)** -- frontmatter-based agent definitions; AgentRegistry + AgentFactory

### Critical Pitfalls

1. **Agent ABC extraction breaks AgentLoop** -- Use `typing.Protocol` for consumption (zero existing code changes). ABC only for genuine code reuse. AgentEvent must superset LoopEvent.
2. **Plan-and-Solve infinite replan loop** -- Replan counter persisted across resets; hard cap 2. Preserve failed plan context.
3. **Reflection circular refinement** -- Hard cap 2 iterations. Structured `{"pass": bool}` verdict. Never let LLM decide continuation.
4. **OrchestratorEngine over-engineering** -- Start trivial (always ReAct). No LLM routing calls. Cap concurrent agents at 4.
5. **A2A state machine confusion** -- Separate `A2ATaskState` enum (9 states) from internal states. Explicit transition map. Map at boundary only.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Agent ABC + AgentEvent Foundation
**Rationale:** Everything depends on this. Must not break existing 687 tests. Protocol for consumption, ABC for code reuse only.
**Delivers:** AgentBase interface, AgentEvent discriminated union, AgentLoop confirmed compatible
**Addresses:** Agent ABC table-stakes feature
**Avoids:** Pitfall 1 (ABC breaks AgentLoop) -- Protocol means AgentLoop stays untouched

### Phase 2: Real Web Search Tool
**Rationale:** Fully independent of agent type work. High user-facing value, low effort. Can parallel with Phase 3.
**Delivers:** WebSearchTool wrapping AsyncTavilyClient, registered in ToolRouter
**Uses:** tavily-python, existing ToolSpec/ToolRouter infrastructure
**Avoids:** Search rate limiting via asyncio.Semaphore

### Phase 3: Plan-and-Solve Agent
**Rationale:** Core planning agent pattern. Validates Agent ABC design. Reuses existing PlanningState.
**Delivers:** PlanAndSolveAgent(AgentBase) with two-phase plan-then-execute
**Uses:** Agent ABC, existing AgentLoop as executor, existing PlanningState
**Avoids:** Pitfall 2 (infinite replan) -- replan counter hard-capped at 2

### Phase 4: Reflection Agent
**Rationale:** Completes the multi-type agent trio. Can parallel with Phase 3 if ABC is solid.
**Delivers:** ReflectionAgent(AgentBase) with execute-critique-refine loop
**Uses:** Agent ABC, existing AgentLoop
**Avoids:** Pitfall 3 (circular refinement) -- hard cap 2 iterations, structured verdict

### Phase 5: Agent Configuration via Markdown
**Rationale:** Enables declarative agent creation. Reuses established SkillManifest pattern.
**Delivers:** AgentManifest, AgentRegistry, AgentFactory -- agent definitions from .md files
**Uses:** parse_frontmatter_lines, SkillRegistry pattern
**Avoids:** Pitfall 5 (prompt injection) -- validate at load time, version-controlled dirs

### Phase 6: OrchestratorEngine
**Rationale:** Needs all agent types to exist first. Must be thin, not a god class.
**Delivers:** OrchestratorEngine with strategy pattern (sequential, parallel, hierarchical)
**Uses:** Agent ABC interface, all concrete agent types
**Avoids:** Pitfalls 4 (over-engineering) and 7 (reliability decay) -- no LLM routing, max 3 per chain

### Phase 7: A2A Protocol (Sync Mode)
**Rationale:** Wraps everything else. Heaviest dependency. Benefits from AgentConfig for AgentCard.
**Delivers:** A2AServer, A2AClient, AgentCardBuilder, JSON-RPC 2.0 handler
**Uses:** a2a-sdk[http-server], Agent ABC, AgentConfig, existing httpx
**Avoids:** Pitfall 6 (state machine) -- separate A2ATaskState, camelCase serialization, API-key auth

### Phase Ordering Rationale

- Agent ABC first because every component depends on it and it requires zero changes to existing code (Protocol pattern)
- Real search is independent, can parallel with Phases 3-4
- Plan-and-Solve and Reflection can parallel after Phase 1 but are separate phases for testability
- AgentConfig after agent types so the factory has real types to instantiate
- OrchestratorEngine after all agent types because it coordinates them
- A2A last because it wraps the entire agent interface and has the heaviest dependency

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 6 (OrchestratorEngine):** MEDIUM confidence on dynamic routing. Few production reference implementations exist. Most orchestration is hardcoded in practice. Consider `/gsd:plan-phase --research-phase 6` to validate strategy pattern against concrete use cases.
- **Phase 7 (A2A Protocol):** `a2a-sdk` v1.0.3 is early and the A2A spec is evolving. Consider `/gsd:plan-phase --research-phase 7` to verify current SDK API surface before implementation.

Phases with standard patterns (skip research-phase):
- **Phase 1 (Agent ABC):** Well-established `typing.Protocol` pattern. LoopEvent fully understood from codebase.
- **Phase 2 (Search Tool):** Simple ToolSpec wrapping an async client. Well-documented API.
- **Phase 3 (Plan-and-Solve):** Documented pattern with multiple reference implementations.
- **Phase 4 (Reflection):** Well-studied academic pattern. Straightforward implementation.
- **Phase 5 (Agent Config):** Direct analog to existing SkillManifest. Reuses proven parser.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Only 2 new deps, both verified. a2a-sdk core dep (httpx) already in stack. |
| Features | HIGH | Established patterns with academic grounding and production implementations. |
| Architecture | HIGH | Composition pattern verified against codebase via SubAgent. 687 tests = regression safety. |
| Pitfalls | HIGH | Sourced from DeepMind research, MAST study (1,642 traces), A2A spec, direct codebase analysis. |

**Overall confidence:** HIGH

### Gaps to Address

- **OrchestratorEngine routing heuristics:** Research recommends simple heuristics over LLM routing but does not specify exact criteria. Define concrete routing rules during Phase 6 planning (task length, keyword detection, tool requirements).
- **A2A authentication scheme:** Research recommends API-key auth from day one but the A2A spec's `securitySchemes` mechanism needs validation against `a2a-sdk` API. Verify during Phase 7 planning.
- **AgentEvent / LoopEvent compatibility layer:** Research says "wrap, don't replace" but the exact mechanism (adapter function vs inheritance) needs design during Phase 1 planning.

## Sources

### Primary (HIGH confidence)
- A2A Protocol Official Specification v0.1.0 -- complete protocol reference
- A2A Python SDK on PyPI (v1.0.3) -- verified dependency structure
- Tavily Python SDK (GitHub) -- AsyncTavilyClient API verified
- Existing codebase: agent_loop.py, sub_agent.py, planner.py, skills/manifest.py, memory/frontmatter.py

### Secondary (MEDIUM confidence)
- LangChain: Plan-and-Execute Agents -- 3-variant plan-and-solve analysis
- Microsoft Azure: AI Agent Design Patterns -- orchestration taxonomy
- AWS Prescriptive Guidance: Evaluator Reflect-Refine Loop
- Google DeepMind (2025): Multi-agent error amplification up to 17.2x
- MAST Study: 1,642 traces, 36.9% coordination breakdowns

### Tertiary (LOW confidence)
- Dataiku: Agent Orchestration -- conceptual overview only
- Google Cloud: Agentic AI Design Patterns -- generic selection guide

---
*Research completed: 2026-05-29*
*Ready for roadmap: yes*
