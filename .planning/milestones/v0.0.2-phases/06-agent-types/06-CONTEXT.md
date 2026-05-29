# Phase 6: Agent 类型扩展 - Context

**Gathered:** 2026-05-29
**Status:** Ready for planning

<domain>
## Phase Boundary

在现有 AgentLoop 基础上建立 Agent ABC 抽象基类和 AgentEvent 统一事件模型，新增 PlanAndSolve Agent（先规划后执行）和 Reflection Agent（执行→反省→改进循环）两种 Agent 类型。现有 687 测试必须全部通过。

**Plans:**
- 06-01: Agent ABC + AgentEvent 基础设施（AGENT-01~05）
- 06-02: Plan-and-Solve Agent（PLAN-01~05）
- 06-03: Reflection Agent（REFL-01~04）

</domain>

<decisions>
## Implementation Decisions

### AgentEvent 与 LoopEvent 设计

- **D-01:** AgentEvent 为基类（dataclass），字段：`type: str`, `step: int`, `data: dict[str, Any]`。LoopEvent 继承 AgentEvent 并增加 `plan: PlanSnapshot | None = None`。AgentLoop.run() 仍返回 LoopEvent（Python 协变返回类型保证兼容）
- **D-02:** AgentEvent.data 精简模式，各类型只带必要字段：
  - `step`: `{text: str, tool_calls: list[dict]}` — LLM 文本输出 + 工具调用列表
  - `tool_result`: `{tool_name: str, is_error: bool, result_text: str}` — 单个工具结果
  - `done`: `{text: str}` — 最终文本输出
  - `max_steps`: `{}` — 无额外数据
  - `error`: `{error_message: str}` — 错误信息
- **D-03:** 仅 sub_agent.py、tasks/runner.py、teams/manager.py 的类型标注从 `AgentLoop` 更新为 `Agent`。59 个测试文件零改动

### PlanAndSolve Agent

- **D-04:** 每个步骤的 AgentLoop 实例接收：原始任务 + 步骤描述 + 前序步骤的摘要输出（不是完整历史）。保持轻量同时让后续步骤了解前序进展
- **D-05:** 偏离检测使用混合策略：先规则检查（快速失败：error 结果、空输出），规则无法判断时 fallback 到 LLM 评估。replan 硬上限 2 次
- **D-06:** 复用现有 `orchestrator/planner.py` 的 `PlanningState` + `parse_plan_response()`。PlanAndSolve 内部维护 PlanningState 实例，每步执行后更新状态
- **D-07:** 空计划时 fallback 到直接 ReAct 执行（PLAN-05 已定义）

### Reflection Agent

- **D-08:** 评估基于三维度：正确性（是否回答了任务）、完整性（是否有遗漏）、清晰度（是否清晰明了）。每个维度 1-5 分
- **D-09:** ReflectionVerdict 为 dataclass：`satisfied: bool`, `scores: dict[str, int]`, `critique: str`。提供 `from_llm_response(text: str)` classmethod 进行 JSON 解析 + 容错 fallback（解析失败时 `satisfied=False`, `scores={}`, `critique=f"评估失败，原始输出：{text[:200]}"`）
- **D-10:** 执行和改进阶段复用 AgentLoop 实例（保留工具调用能力）。仅反射/评估阶段用独立 LLM completion 调用（不增加 tool calling 复杂度）
- **D-11:** 改进轮次硬上限 2 次（REFL-03 已定义），不满意时将 critique 注入下一轮用户消息（REFL-04 已定义）

### Agent ABC 提取策略

- **D-12:** Agent 为 ABC（abc.ABC + @abstractmethod），仅定义 `run() -> AsyncGenerator[AgentEvent, None]`。不约束 `__init__` 签名，不定义 name/description 等属性（Phase 8 A2A 时再考虑）
- **D-13:** 06-01 文件改动范围：`agents/base.py`（新建 Agent ABC + AgentEvent）、`agents/agent_loop.py`（LoopEvent 继承 AgentEvent、AgentLoop 继承 Agent）、`agents/sub_agent.py` / `tasks/runner.py` / `teams/manager.py`（类型标注改为 Agent）、`agents/__init__.py`（导出更新）

### Claude's Discretion

- PlanAndSolve 的 LLM 评估偏离的具体 prompt 设计
- Reflection 三维度评估的具体 prompt 设计
- 前序步骤摘要的生成方式（LLM 摘要 vs. 截取最后 N 字符）

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Core Architecture
- `.planning/codebase/ARCHITECTURE.md` — 系统架构，AgentLoop 数据流、Tool Dispatch Pipeline、Sub-Agent Spawning Flow
- `.planning/codebase/CONCERNS.md` — 已知问题清单（agents/base.py 为空、AgentLoop 15 参数、LoopEvent 使用范围）
- `.planning/codebase/CONVENTIONS.md` — 编码规范

### Source Code (Integration Points)
- `framework/agent_framework/agents/agent_loop.py` — 现有 AgentLoop 实现，LoopEvent 定义
- `framework/agent_framework/agents/base.py` — 空文件，Agent ABC 放置位置
- `framework/agent_framework/agents/sub_agent.py` — 子 Agent 创建，类型标注需更新
- `framework/agent_framework/tasks/runner.py` — 任务执行器，类型标注需更新
- `framework/agent_framework/teams/manager.py` — 团队管理器，类型标注需更新
- `framework/agent_framework/orchestrator/planner.py` — PlanningState、parse_plan_response()、drift detection（PlanAndSolve 复用）

### Requirements
- `.planning/REQUIREMENTS.md` — v0.0.2 需求定义，AGENT-01~05, PLAN-01~05, REFL-01~04

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **PlanningState + parse_plan_response():** 已有计划解析和偏离检测逻辑，PlanAndSolve 直接复用
- **AgentLoop:** 成熟的 ReAct 循环实现，PlanAndSolve 和 Reflection 的执行/改进阶段直接创建 AgentLoop 实例
- **LoopEvent:** 已有 5 种事件类型（step/tool_result/done/max_steps/error），AgentEvent 继承此模式
- **create_filtered_router() (sub_agent.py):** 过滤工具的模式，可用于 PlanAndSolve 每步创建独立 AgentLoop

### Established Patterns
- **dataclass 优先:** 所有数据模型使用 dataclass（不是 Pydantic BaseModel），与 LoopEvent、PlanItem、PlanSnapshot 一致
- **AsyncGenerator 模式:** AgentLoop.run() 返回 AsyncGenerator，所有 Agent 类型统一此模式
- **不抛异常返回错误:** 工具调用返回 ToolResult(is_error=True)，AgentEvent.error 类型而非异常

### Integration Points
- `agents/__init__.py` — 需导出 Agent、AgentEvent
- `agents/base.py` — Agent ABC + AgentEvent 定义位置
- `agents/agent_loop.py` — LoopEvent 改为继承 AgentEvent，AgentLoop 继承 Agent
- `agents/sub_agent.py` — 类型标注 AgentLoop → Agent
- `tasks/runner.py` — 类型标注 AgentLoop → Agent
- `teams/manager.py` — 类型标注 AgentLoop → Agent

</code_context>

<specifics>
## Specific Ideas

- AgentEvent 继承方向：AgentEvent 是基类，LoopEvent 继承它。Python 协变返回类型允许 AgentLoop.run() 声明返回 LoopEvent（AgentEvent 的子类）同时满足 Agent ABC 的 run() 签名
- ReflectionVerdict.from_llm_response() 容错解析：JSON 解析失败时默认 satisfied=False，不 crash
- PlanAndSolve 混合偏离检测：规则检查零额外成本，LLM 评估仅在规则无法判断时触发
- 不使用 tool calling 做 Reflection 评估：避免将简单评估变为 tool_use 往返

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 06-agent-types*
*Context gathered: 2026-05-29*
