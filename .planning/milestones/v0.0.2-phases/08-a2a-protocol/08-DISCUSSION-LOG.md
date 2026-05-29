# Phase 8: A2A 协议 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-29
**Phase:** 08-a2a-protocol
**Areas discussed:** HTTP Server 实现, 数据模型风格, Client 工具集成, AgentCard 设计, API-key 认证细节, 错误处理策略, 模块组织结构

---

## HTTP Server 实现

| Option | Description | Selected |
|--------|-------------|----------|
| starlette | 引入轻量 ASGI 框架，框架层自包含 | |
| 纯 ASGI 接口 | 框架层只定义 ASGI app，零新增依赖 | ✓ |
| 应用层实现 | A2A 端点放 backend/ 层 | |

**User's choice:** 纯 ASGI 接口
**Notes:** 框架层零新增依赖，应用层用 FastAPI/uvicorn 挂载

### 路由设计

| Option | Description | Selected |
|--------|-------------|----------|
| RESTful 路由 | GET /.well-known/agent-card, POST /tasks, GET /tasks/{id}, POST /tasks/{id}/cancel | ✓ |
| Google A2A 规范 | 遵循 Google A2A spec 路径格式 | |

**User's choice:** RESTful 路由

---

## 数据模型风格

| Option | Description | Selected |
|--------|-------------|----------|
| Pydantic BaseModel | 内置 JSON 序列化，与 ToolCall/ToolResult 一致 | ✓ |
| dataclass | 与 AgentEvent/PlanItem 一致，需手动序列化 | |

**User's choice:** Pydantic BaseModel
**Notes:** A2A 模型天生是 HTTP wire format，Pydantic 更适合

---

## Client 工具集成

| Option | Description | Selected |
|--------|-------------|----------|
| ToolSpec 注册 | 远程 Agent 注册为 ToolSpec（a2a__{name}），Agent 无需知道是远程调用 | ✓ |
| 独立 Client API | A2AClient 作为独立 API，应用层直接调用 | |
| 两者兼备 | 底层 Client API + 上层 ToolSpec 封装 | |

**User's choice:** ToolSpec 注册

### 同步等待策略

| Option | Description | Selected |
|--------|-------------|----------|
| 轮询等待 | send_task_and_wait() 内部轮询直到完成 | |
| 即发即忘 | send_task() 立即返回 task_id | |
| 两者兼备 | 低级 + 高级 API | ✓ |

**User's choice:** 两者兼备（用户提供详细实现方案）
**Notes:** A2AClient 暴露两级 API：send_task() + get_task()（应用层手动控制）和 send_task_and_wait()（ToolSpec handler 用，内部轮询）

---

## AgentCard 设计

| Option | Description | Selected |
|--------|-------------|----------|
| 静态配置 | 从配置文件加载，简单可预测 | ✓ |
| 动态发现 | 从 Agent 实例动态生成 | |

**User's choice:** 静态配置

### capabilities 字段

| Option | Description | Selected |
|--------|-------------|----------|
| 字符串列表 | 简单轻量，调用方自行解读 | ✓ |
| 结构化对象 | 每个 capability 含 name + description + schema | |

**User's choice:** 字符串列表

### 配置文件格式

| Option | Description | Selected |
|--------|-------------|----------|
| .md 文件 | 与 Phase 7 Agent 配置一致，复用 parse_frontmatter() | ✓ |
| JSON 文件 | 更适合机器读写 | |

**User's choice:** .md 文件

---

## API-key 认证细节

| Option | Description | Selected |
|--------|-------------|----------|
| 服务级单一 key | 一个 key 保护整个 A2AServer | ✓ |
| Per-agent key | 每个 Agent 独立 key | |

**User's choice:** 服务级单一 key

### Key 传递方式

| Option | Description | Selected |
|--------|-------------|----------|
| Header 传递 | X-API-Key header，与 Anthropic API 一致 | ✓ |
| Query param | URL 参数，不安全 | |

**User's choice:** Header 传递

---

## 错误处理策略

| Option | Description | Selected |
|--------|-------------|----------|
| 复用 ToolResult 模式 | ToolResult(is_error=True)，与现有工具错误处理一致 | ✓ |
| 专用错误类型 | A2AError, A2ATimeoutError 等 | |

**User's choice:** 复用 ToolResult 模式

---

## 模块组织结构

| Option | Description | Selected |
|--------|-------------|----------|
| 独立 a2a/ 子包 | framework/agent_framework/a2a/，与 llm/tools/agents 平级 | ✓ |
| 嵌套在 tools/ 下 | tools/a2a/，与 MCP 平级 | |

**User's choice:** 独立 a2a/ 子包
**Notes:** A2A 不仅是工具（Server 端不是工具），放在 tools/ 下语义不准确

---

## Claude's Discretion

- ASGI app 的具体实现方式
- A2ATask 状态机的完整状态列表
- A2AMessage 的具体字段设计
- 轮询间隔和超时的默认值微调
- AgentCard .md 文件的 frontmatter 字段细节
- 认证失败的 HTTP 状态码和错误响应格式

## Deferred Ideas

None — discussion stayed within phase scope
