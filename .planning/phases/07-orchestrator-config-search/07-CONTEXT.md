# Phase 7: 编排引擎 + 配置化 + 搜索 - Context

**Gathered:** 2026-05-29
**Status:** Ready for planning

<domain>
## Phase Boundary

框架新增三层能力：(1) OrchestratorEngine 根据任务复杂度路由到不同 Agent 类型并纠偏、(2) .md 文件声明式定义 Agent 配置、(3) 搜索工具从 mock 替换为 Tavily 真实 API。

**Plans:**
- 07-01: OrchestratorEngine 编排引擎（ORCH-01~05）
- 07-02: Agent 配置化（CONF-01~04）
- 07-03: 真实搜索工具（SRCH-01~03）

**关键约束：**
- replan 硬上限 2 次（Phase 6 已实现于 PlanAndSolveAgent）
- Agent 链最多 3 个（Orchestrator 级别上限）
- 不引入 pyyaml 依赖，flat frontmatter 足够
- 复杂度评估不做额外 LLM 调用（ORCH-02）

</domain>

<decisions>
## Implementation Decisions

### 复杂度评估规则

- **D-01:** 纯字符数阈值判断任务复杂度，默认 200 字符，通过 `_complexity_threshold` 可配置。一条 if 语句，不做关键词匹配、不做多信号组合、不做额外 LLM 调用。安全网机制：简单任务误判为复杂 → 生成空计划 → PlanAndSolve fallback 到 ReAct；复杂任务误判为简单 → ReAct 也能执行，replan 可在后续纠正

### Orchestrator 架构

- **D-02:** OrchestratorEngine 对复杂任务委托给 PlanAndSolveAgent.run()。OrchestratorEngine 只负责评估 + 路由 + 创建 Agent，不重复实现计划逻辑。简单任务直接创建 AgentLoop 执行
- **D-03:** agent_factory 模式创建顶层 Agent 实例。工厂接收配置（adapter、router、profile 等），按复杂度评估结果创建 PlanAndSolveAgent（复杂）或 AgentLoop（简单）。PlanAndSolveAgent 内部自行创建每步的 AgentLoop
- **D-04:** 偏离检测完全依赖 PlanAndSolveAgent 内部 replan 逻辑（最多 2 次）。"Agent 链最多 3 个"是 OrchestratorEngine 级别的 Agent 实例创建上限，不是 PlanAndSolve 内部步骤的上限

### Agent 配置文件格式

- **D-05:** .md 配置文件结构：frontmatter 放元数据（name, description, model, max_steps, tools），body 放 system_prompt。与 AgentProfile.from_directory() 设计一致（soul.md body = system prompt 内容）。复用 parse_frontmatter() 解析
- **D-06:** tools 字段按名称列表引用，与 ToolRegistry.register() 的 name 字段完全对应。未列出的工具不注册到 Agent 的 ToolRouter
- **D-07:** system_prompt 安全性验证（CONF-04）仅做非空检查。信任配置文件作者（开发者），注入防护交给运行时的 PermissionPipeline 和 Boundary

### 搜索错误处理

- **D-08:** Tavily API 不可用时（网络错误、key 缺失、rate limit）返回 `ToolResult(is_error=True, content="搜索失败：...")`。AgentLoop 已有完善的错误处理机制——LLM 看到错误后会调整策略（换工具、换说法重试、或直接回答）。不降级到空结果，不 fallback 到 mock

### Claude's Discretion

- OrchestratorEngine 是否也实现 Agent 接口（run() → AsyncGenerator[AgentEvent, None]），使其可被嵌套使用
- frontmatter 字段哪些必填、哪些可选（推荐：name + system_prompt 必填，其余可选有默认值）
- Semaphore 并发数（推荐：3-5）
- Tavily AsyncTavilyClient 的具体配置（timeout、max_results 等）
- 配置文件目录路径的默认值和可配置方式

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 6 产出（核心依赖）
- `.planning/phases/06-agent-types/06-CONTEXT.md` — Phase 6 决策：Agent ABC 接口、AgentEvent、PlanAndSolveAgent、ReflectionAgent、偏离检测策略
- `framework/agent_framework/agents/base.py` — Agent ABC + AgentEvent 定义
- `framework/agent_framework/agents/agent_loop.py` — AgentLoop 实现，LoopEvent 定义，`__init__` 参数和 `run()` 签名

### Orchestrator 相关
- `framework/agent_framework/orchestrator/planner.py` — PlanningState, PlanItem, PlanSnapshot, parse_plan_response(), strip_plan_tags()。PlanAndSolve 和 OrchestratorEngine 共享
- `framework/agent_framework/orchestrator/engine.py` — 空 scaffold，OrchestratorEngine 放置位置
- `framework/agent_framework/orchestrator/router.py` — docstring-only scaffold，预留路由逻辑

### 配置化相关
- `framework/agent_framework/memory/frontmatter.py` — parse_frontmatter(), format_frontmatter(), parse_frontmatter_lines()。Agent 配置解析复用
- `framework/agent_framework/prompts/profiles.py` — AgentProfile 定义（allowed_tools, disallowed_tools, permission_mode），from_directory() 模式参考
- `framework/agent_framework/agents/sub_agent.py` — create_filtered_router() 工具过滤模式，agent_from_config() 复用
- `framework/agent_framework/tools/registry.py` — ToolRegistry，subset() 方法用于按配置过滤工具

### 搜索相关
- `framework/agent_framework/tools/builtin/search_tools.py` — 当前 mock web_search handler，签名 (dict, ToolUseContext) -> ToolResult
- `framework/agent_framework/tools/builtin/__init__.py` — create_builtin_registry() 注册 web_search

### 项目级
- `.planning/REQUIREMENTS.md` — ORCH-01~05, CONF-01~04, SRCH-01~03 需求定义
- `.planning/codebase/ARCHITECTURE.md` — 系统架构，数据流图
- `.planning/codebase/CONCERNS.md` — 已知问题（engine.py 和 router.py 为空 scaffold）

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **PlanningState + parse_plan_response():** 完整的计划解析和偏离检测逻辑，OrchestratorEngine 通过 PlanAndSolveAgent 间接使用
- **Agent ABC 接口:** `run() -> AsyncGenerator[AgentEvent, None]`，三种 Agent 类型统一此接口
- **create_filtered_router() (sub_agent.py):** 按 allowed_tools 过滤 ToolRouter 的模式，agent_from_config() 复用此模式
- **parse_frontmatter() (memory/frontmatter.py):** flat frontmatter 解析，Agent 配置文件复用
- **ToolRegistry.subset():** 按名称集合创建子 Registry，配合配置化工具过滤
- **AgentProfile:** 已有 allowed_tools/disallowed_tools 字段，agent_from_config() 可直接映射

### Established Patterns
- **dataclass 优先:** 所有数据模型使用 dataclass（不是 Pydantic BaseModel），与 AgentEvent、PlanItem、PlanSnapshot 一致
- **AsyncGenerator 模式:** 所有 Agent 的 run() 返回 AsyncGenerator
- **ToolResult(is_error=True):** 工具不抛异常，返回错误结果。搜索工具复用此模式
- **SecretStr 保护 API Key:** 与 LLM Provider 的 api_key 管理一致

### Integration Points
- `orchestrator/engine.py` — 空 scaffold，OrchestratorEngine 定义位置
- `orchestrator/router.py` — docstring-only scaffold，复杂度评估+路由逻辑可放此处或合并到 engine
- `tools/builtin/search_tools.py` — mock handler 替换为 Tavily 调用
- `tools/builtin/__init__.py` — web_search 注册点不变，handler 替换即可
- `agents/__init__.py` — 可能需导出新类型

</code_context>

<specifics>
## Specific Ideas

- 复杂度评估的代码形态：`if len(task) > self._complexity_threshold: return "complex" else: return "simple"`。一条 if 语句，默认阈值 200 字符
- Agent 配置文件示例形态：
  ```
  ---
  name: research-agent
  description: 研究分析助手
  model: claude-sonnet-4-6-20250514
  max_steps: 15
  tools: read_file, web_search, memory_search
  ---
  你是一个专业的分析师...
  ```
- OrchestratorEngine 与 PlanAndSolveAgent 的关系：OrchestratorEngine 是调度器，PlanAndSolveAgent 是执行器。职责分离清晰
- 搜索工具错误传播：`ToolResult(is_error=True, content=f"搜索失败：{error}")`，LLM 自然处理错误

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 07-orchestrator-config-search*
*Context gathered: 2026-05-29*
