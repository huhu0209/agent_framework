# Phase 8: A2A 协议 - Context

**Gathered:** 2026-05-29
**Status:** Ready for planning

<domain>
## Phase Boundary

框架新增 A2A（Agent-to-Agent）通信协议能力：(1) AgentCard 描述 Agent 能力，(2) A2AServer 将本地 Agent 暴露为 HTTP 端点（AgentCard 发现 + 任务创建 + 状态查询 + 取消），(3) A2AClient 向远程 Agent 提交任务并获取结果，(4) API-key 认证保护所有通信。仅同步模式（POST + 轮询）。

**Plans:**
- 08-01: A2A 数据模型 + AgentCard（A2A-01, A2A-02）
- 08-02: A2AServer + A2AClient 实现（A2A-03, A2A-04, A2A-05）
- 08-03: API-key 认证（A2A-06）

**关键约束：**
- 同步模式（POST + 轮询），不做 SSE 流式和 Webhook 异步
- 纯 ASGI 接口，框架层不引入 HTTP server 依赖
- API-key 为服务级单一 key，不做 per-agent 粒度

</domain>

<decisions>
## Implementation Decisions

### HTTP Server 实现

- **D-01:** 框架层只定义纯 ASGI app 和路由（不引入 starlette/uvicorn 依赖）。应用层（backend）用 FastAPI 或 uvicorn 挂载。框架零新增依赖
- **D-02:** RESTful 路由设计，四个端点：
  - `GET /.well-known/agent-card` → AgentCard 发现
  - `POST /tasks` → 创建任务
  - `GET /tasks/{id}` → 查询任务状态
  - `POST /tasks/{id}/cancel` → 取消任务

### 数据模型风格

- **D-03:** A2A 数据模型（AgentCard, A2ATask, A2AMessage, A2ATaskStatus）使用 Pydantic BaseModel。与 ToolCall/ToolResult/ToolSpec 风格一致，天生适合 JSON 序列化/反序列化

### Client 工具集成

- **D-04:** 远程 Agent 通过 ToolSpec 注册到 ToolRegistry（命名模式 `a2a__{agent_name}`）。Agent 通过工具调用触发 A2AClient，无需知道是远程调用。与 MCP 工具注册模式一致（`mcp__{server}__{tool}`）
- **D-05:** A2AClient 暴露两级 API：
  - `send_task(message) -> task_id` + `get_task(task_id) -> A2ATask`：应用层手动控制
  - `send_task_and_wait(message, poll_interval=2.0, timeout=300.0) -> A2ATask`：ToolSpec handler 用，内部轮询等待直到完成/失败/超时

### AgentCard 设计

- **D-06:** AgentCard 从配置文件静态加载（非动态从 Agent 实例提取）。简单可预测
- **D-07:** capabilities 字段为字符串列表（如 `['text-generation', 'web-search']`）。简单轻量，调用方自行解读含义
- **D-08:** AgentCard 配置使用 .md 文件格式（frontmatter + body），与 Phase 7 的 Agent 配置格式一致。复用 parse_frontmatter() 解析

### API-key 认证

- **D-09:** 服务级单一 API key 保护整个 A2AServer。简单直接，与 LLM Provider 的 api_key 模式一致
- **D-10:** 通过 `X-API-Key` header 传递。与 Anthropic API 的 x-api-key 模式一致

### 错误处理

- **D-11:** A2A 操作失败时返回 `ToolResult(is_error=True, content=错误描述)`。复用现有工具错误处理模式，AgentLoop 的 ReAct 循环自然处理

### 模块组织

- **D-12:** 独立 `framework/agent_framework/a2a/` 子包，与 llm/、tools/、agents/ 等平级。包含：
  - `models.py` — AgentCard + A2ATask + A2AMessage + A2ATaskStatus（Pydantic BaseModel）
  - `client.py` — A2AClient（两级 API）
  - `server.py` — A2AServer（纯 ASGI app + 路由）
  - `__init__.py` — 导出

### Claude's Discretion

- ASGI app 的具体实现方式（手动解析 scope/send vs 更结构化的 helper）
- A2ATask 状态机的完整状态列表（至少需要：pending, running, completed, failed, cancelled）
- A2AMessage 的具体字段设计
- 轮询间隔和超时的默认值微调
- AgentCard .md 文件的 frontmatter 字段细节（name, description, url, version, capabilities 哪些必填）
- 认证失败的 HTTP 状态码和错误响应格式

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 6 产出（核心依赖）
- `.planning/phases/06-agent-types/06-CONTEXT.md` — Phase 6 决策：Agent ABC 接口、AgentEvent
- `framework/agent_framework/agents/base.py` — Agent ABC + AgentEvent 定义

### Phase 7 产出（配置模式参考）
- `.planning/phases/07-orchestrator-config-search/07-CONTEXT.md` — Phase 7 决策：Agent 配置化（.md 文件格式）、parse_frontmatter() 复用、SecretStr 模式
- `framework/agent_framework/memory/frontmatter.py` — parse_frontmatter(), format_frontmatter(), parse_frontmatter_lines()。AgentCard 配置解析复用

### 工具系统（Client 集成）
- `framework/agent_framework/tools/types.py` — ToolCall, ToolResult, ToolSpec, ToolUseContext 定义
- `framework/agent_framework/tools/registry.py` — ToolRegistry，register() 和 subset() 方法
- `framework/agent_framework/tools/mcp/config.py` — MCP 工具注册模式（`mcp__{server}__{tool}`），A2A 工具注册参考

### ASGI / HTTP 模式参考
- `framework/agent_framework/llm/providers/anthropic_provider.py` — httpx.AsyncClient 使用模式、SecretStr API key 管理、x-api-key header 模式
- `framework/agent_framework/llm/streaming.py` — SSE 解析模式（A2A 同步模式不直接使用，但作为 HTTP 通信参考）

### 项目级
- `.planning/REQUIREMENTS.md` — A2A-01~06 需求定义
- `.planning/codebase/ARCHITECTURE.md` — 系统架构，数据流图
- `.planning/codebase/CONCERNS.md` — 已知问题

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **Agent ABC 接口:** `run() -> AsyncGenerator[AgentEvent, None]`，A2AServer 接收 Agent 实例并调用 run()
- **ToolSpec + ToolRegistry:** 完整的工具注册和调度机制，A2AClient 注册为 ToolSpec 时直接复用
- **parse_frontmatter():** flat frontmatter 解析，AgentCard 配置文件复用
- **SecretStr 模式:** API key 安全管理，与 LLM Provider 一致
- **httpx.AsyncClient:** 异步 HTTP 客户端，A2AClient 直接使用

### Established Patterns
- **Pydantic BaseModel for wire types:** ToolCall/ToolResult/ToolSpec 使用 Pydantic，A2A 模型遵循此模式
- **ToolResult(is_error=True):** 工具不抛异常返回错误结果。A2A 错误复用此模式
- **Tool naming convention:** `prefix__name` 格式（mcp__, agent__），A2A 使用 `a2a__`
- **ASGI scope/send interface:** 纯 ASGI app 无额外依赖，应用层负责挂载

### Integration Points
- `framework/agent_framework/a2a/` — 新子包，包含 models.py, client.py, server.py
- `framework/agent_framework/tools/registry.py` — A2AClient 注册 ToolSpec 到 Registry
- `framework/agent_framework/agents/__init__.py` — 可能需导出新类型
- `framework/agent_framework/__init__.py` — 可能需导出 a2a 模块

</code_context>

<specifics>
## Specific Ideas

- A2AClient.send_task_and_wait() 实现形态：
  ```python
  async def send_task_and_wait(self, message, *, poll_interval=2.0, timeout=300.0):
      task_id = await self.send_task(message)
      deadline = time.monotonic() + timeout
      while time.monotonic() < deadline:
          task = await self.get_task(task_id)
          if task.status.is_terminal:
              return task
          await asyncio.sleep(poll_interval)
      return A2ATask(task_id=task_id, status=A2ATaskStatus.FAILED, error="超时")
  ```
- AgentCard .md 文件示例形态：
  ```
  ---
  name: research-agent
  description: 远程研究分析 Agent
  url: https://remote.example.com
  version: "1.0"
  capabilities: text-generation, web-search, code-execution
  ---
  ```
- A2AServer 纯 ASGI app 形态：定义路由映射，手动解析 scope，调用对应 handler，通过 send() 返回 JSON 响应。无框架依赖

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 08-a2a-protocol*
*Context gathered: 2026-05-29*
