# Phase 8: A2A 协议 - Research

**Researched:** 2026-05-29
**Domain:** A2A (Agent-to-Agent) 协议实现，HTTP 端点暴露，远程 Agent 工具集成
**Confidence:** HIGH

## Summary

本阶段在框架层新增 A2A 子包，使本地 Agent 可暴露为 HTTP 端点（A2AServer），远程 Agent 可作为工具调用（A2AClient）。实现严格遵循项目约束：同步模式（POST + 轮询），纯 ASGI 接口（零新增依赖），API-key 服务级认证。

A2A 协议规范 v1.0 定义了完整的 Task 生命周期（submitted/working/completed/failed/canceled/input-required/auth-required/rejected/unknown），本阶段简化为同步子集：pending/running/completed/failed/canceled。AgentCard 使用 .md frontmatter 格式，复用 parse_frontmatter()。A2AClient 通过 ToolSpec 注册到 ToolRegistry，与 MCP 工具注册模式一致。

**Primary recommendation:** 使用 Pydantic BaseModel 定义 A2A 数据模型（与 ToolCall/ToolResult/ToolSpec 风格一致），纯 ASGI app 手动解析 scope（无 HTTP 框架依赖），httpx.AsyncClient 实现 A2AClient HTTP 调用。所有模块遵循框架现有的不可变模式、SecretStr API key 管理、ToolResult(is_error=True) 错误处理。

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** 框架层只定义纯 ASGI app 和路由（不引入 starlette/uvicorn 依赖）。应用层（backend）用 FastAPI 或 uvicorn 挂载。框架零新增依赖
- **D-02:** RESTful 路由设计，四个端点：GET /.well-known/agent-card, POST /tasks, GET /tasks/{id}, POST /tasks/{id}/cancel
- **D-03:** A2A 数据模型使用 Pydantic BaseModel（与 ToolCall/ToolResult/ToolSpec 风格一致）
- **D-04:** 远程 Agent 通过 ToolSpec 注册到 ToolRegistry（命名模式 a2a__{agent_name}），与 MCP 工具注册模式一致
- **D-05:** A2AClient 暴露两级 API：send_task() + get_task() 和 send_task_and_wait()
- **D-06:** AgentCard 从配置文件静态加载（非动态从 Agent 实例提取）
- **D-07:** capabilities 字段为字符串列表
- **D-08:** AgentCard 配置使用 .md 文件格式（frontmatter + body），复用 parse_frontmatter()
- **D-09:** 服务级单一 API key 保护整个 A2AServer
- **D-10:** 通过 X-API-Key header 传递 API key
- **D-11:** A2A 操作失败时返回 ToolResult(is_error=True, content=错误描述)
- **D-12:** 独立 framework/agent_framework/a2a/ 子包，包含 models.py, client.py, server.py, __init__.py

### Claude's Discretion
- ASGI app 的具体实现方式（手动解析 scope/send vs 更结构化的 helper）
- A2ATask 状态机的完整状态列表（至少需要：pending, running, completed, failed, cancelled）
- A2AMessage 的具体字段设计
- 轮询间隔和超时的默认值微调
- AgentCard .md 文件的 frontmatter 字段细节（name, description, url, version, capabilities 哪些必填）
- 认证失败的 HTTP 状态码和错误响应格式

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| A2A-01 | AgentCard 数据模型（name, description, url, version, capabilities） | Pydantic BaseModel，.md frontmatter 格式，复用 parse_frontmatter() |
| A2A-02 | A2ATask/A2AMessage/A2ATaskStatus 数据模型 | Pydantic BaseModel，简化状态机（pending/running/completed/failed/canceled），in-memory TaskStore |
| A2A-03 | A2AClient 实现远程 Agent 任务提交 + 状态轮询 + 取消 | httpx.AsyncClient，两级 API（send_task/get_task + send_task_and_wait），ToolSpec 注册 |
| A2A-04 | A2AServer 暴露本地 Agent 为 HTTP 端点 | 纯 ASGI app，手动路由解析，Agent.run() -> AsyncGenerator[AgentEvent] 调用，in-memory task 管理 |
| A2A-05 | 同步模式（POST + 轮询），不做流式和异步 | send_task_and_wait() 轮询实现，asyncio.sleep + time.monotonic 超时 |
| A2A-06 | API-key 认证机制 | X-API-Key header，SecretStr 管理，每个请求前验证，401/403 错误响应 |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| A2A 数据模型定义 | Framework | — | 数据模型是框架层契约，被 Server/Client/A2A 生态共享 |
| A2AServer (HTTP 端点) | Framework (ASGI app) | Backend (挂载) | 框架定义纯 ASGI 接口，应用层负责 HTTP server 启动和挂载 |
| A2AClient (HTTP 调用) | Framework | — | 复用框架的 httpx 依赖，注册为 ToolSpec 供 Agent 调用 |
| API-key 认证 | Framework (验证逻辑) | Backend (key 管理) | 框架提供验证中间件，应用层配置具体 key 值 |
| AgentCard 配置 | Framework (解析) | Backend (.md 文件) | 框架解析 frontmatter，应用层提供 .md 配置文件 |
| Task 状态管理 | Framework (in-memory) | — | 同步模式下框架内 in-memory 存储足够 |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pydantic | 2.12.5 | A2A 数据模型（AgentCard, A2ATask, A2AMessage） | [VERIFIED: pip registry] 项目已有依赖，ToolCall/ToolResult/ToolSpec 使用同一模式 |
| httpx | 0.28.1 | A2AClient HTTP 调用 | [VERIFIED: pip registry] 项目已有依赖，AnthropicProvider 使用同一模式 |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | 8.x | 测试框架 | 所有 A2A 模块测试 |
| pytest-asyncio | 1.3.0 | 异步测试支持 | A2AServer/A2AClient 异步逻辑测试 |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| 手动 ASGI 解析 | Starlette/Starlette-mini | 项目约束明确禁止引入 HTTP 框架依赖。手动解析 scope 对 4 个端点足够 |
| in-memory TaskStore | dict + asyncio.Lock | asyncio.Lock 保护并发安全，TaskStore 封装 dict 操作 |

**Installation:** 零新增安装 — 所有依赖已在 pyproject.toml 中。

**Version verification:**
```
pydantic: 2.12.5 (pip show, 2026-05-29)
httpx: 0.28.1 (pip show, 2026-05-29)
pytest: 8.x (pip show)
pytest-asyncio: 1.3.0 (pip show)
```

## Package Legitimacy Audit

本阶段零新增依赖，所有使用的包均为项目已有依赖。

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| pydantic | PyPI | ~5 yrs | ~200M/mo | github.com/pydantic/pydantic | N/A (existing) | Approved |
| httpx | PyPI | ~5 yrs | ~60M/mo | github.com/encode/httpx | N/A (existing) | Approved |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    Framework Layer                       │
│                                                         │
│  ┌─────────────┐   ┌──────────────┐   ┌──────────────┐ │
│  │ Agent ABC   │   │ Tool System  │   │  a2a/ NEW    │ │
│  │ run() ->    │◄──│ ToolRegistry │◄──│              │ │
│  │ AgentEvent  │   │ ToolSpec     │   │ models.py    │ │
│  └─────────────┘   └──────────────┘   │ client.py    │ │
│       ▲                               │ server.py    │ │
│       │                               └──────┬───────┘ │
│       │                                      │         │
│  ┌────┴──────┐                               │         │
│  │ parse_    │◄──────────────────────────────┘         │
│  │ frontmatter│  (AgentCard .md 解析)                  │
│  └───────────┘                                         │
└─────────────────────────────────────────────────────────┘
                         │
                    ASGI interface
                         │
┌─────────────────────────────────────────────────────────┐
│                    Application Layer                    │
│                                                         │
│  ┌──────────────┐                                       │
│  │ FastAPI /    │  挂载 A2AServer ASGI app              │
│  │ Uvicorn      │  提供 Agent 实例 + AgentCard .md      │
│  └──────────────┘                                       │
└─────────────────────────────────────────────────────────┘

数据流：远程调用场景
──────────────────────────────────────────────────────────

  远程 Agent Server              本地 A2AClient
  ┌──────────────┐              ┌──────────────┐
  │ A2AServer    │◄──HTTP───────│ A2AClient    │
  │ (ASGI app)   │  POST /tasks │              │
  │              │  GET /tasks/  │ send_task()  │
  │ Agent.run()  │  {id}        │ get_task()   │
  │              │              │ send_task_   │
  │ AgentCard    │              │ and_wait()   │
  └──────────────┘              └──────┬───────┘
                                       │ 注册为 ToolSpec
                                       ▼
                                ┌──────────────┐
                                │ ToolRegistry │
                                │ a2a__{name}  │
                                └──────────────┘
                                       │ Agent 调用
                                       ▼
                                ┌──────────────┐
                                │ AgentLoop    │
                                │ ReAct 循环   │
                                └──────────────┘
```

### Recommended Project Structure
```
framework/agent_framework/a2a/
├── __init__.py      # 模块导出
├── models.py        # AgentCard + A2ATask + A2AMessage + A2ATaskStatus
├── client.py        # A2AClient（两级 API + ToolSpec 注册）
└── server.py        # A2AServer（纯 ASGI app + 路由 + 认证中间件）

framework/tests/
├── test_a2a_models.py    # 数据模型测试
├── test_a2a_client.py    # Client 测试（mock httpx）
└── test_a2a_server.py    # Server 测试（ASGI 测试工具）
```

### Pattern 1: Pydantic BaseModel 数据模型
**What:** 所有 A2A wire types 使用 Pydantic BaseModel，与 ToolCall/ToolResult/ToolSpec 风格一致
**When to use:** models.py 中所有对外数据结构
**Example:**
```python
# 来源: 框架现有模式 (tools/types.py)
from pydantic import BaseModel, ConfigDict, Field
from typing import Any
from enum import Enum

class A2ATaskStatus(str, Enum):
    """A2A 任务状态（同步子集）。"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"

    @property
    def is_terminal(self) -> bool:
        return self in (self.COMPLETED, self.FAILED, self.CANCELED)

class A2ATask(BaseModel):
    """A2A 任务对象。"""
    id: str
    status: A2ATaskStatus = A2ATaskStatus.PENDING
    result: str | None = None
    error: str | None = None
    created_at: str  # ISO 8601
    updated_at: str  # ISO 8601
```

### Pattern 2: 纯 ASGI App 手动路由
**What:** 不依赖任何 HTTP 框架，直接解析 ASGI scope 的 method + path
**When to use:** server.py 中 A2AServer 实现
**Example:**
```python
# 来源: ASGI 规范 + 项目约束 D-01
from typing import Any, Callable, Awaitable

Scope = dict[str, Any]
Receive = Callable[[], Awaitable[dict[str, Any]]]
Send = Callable[[dict[str, Any]], Awaitable[None]]

class A2AServer:
    def __init__(self, agent, agent_card: dict, api_key: str | None = None):
        self._agent = agent
        self._agent_card = agent_card
        self._api_key = api_key
        self._tasks: dict[str, A2ATask] = {}

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            return
        method = scope["method"]
        path = scope["path"]

        # 路由分发
        if method == "GET" and path == "/.well-known/agent-card":
            await self._handle_agent_card(scope, receive, send)
        elif method == "POST" and path == "/tasks":
            await self._handle_create_task(scope, receive, send)
        elif method == "GET" and path.startswith("/tasks/"):
            task_id = path.split("/tasks/")[1]
            await self._handle_get_task(task_id, scope, receive, send)
        elif method == "POST" and path.startswith("/tasks/") and path.endswith("/cancel"):
            task_id = path.split("/tasks/")[1].rstrip("/cancel")
            await self._handle_cancel_task(task_id, scope, receive, send)
        else:
            await self._send_json(send, 404, {"error": "not found"})
```

### Pattern 3: ToolSpec 注册远程 Agent
**What:** A2AClient 注册为 ToolSpec，Agent 通过 ReAct 循环自然调用远程 Agent
**When to use:** client.py 中注册方法
**Example:**
```python
# 来源: 框架现有模式 (tools/mcp/config.py:109-124)
def register_as_tool(self, registry: ToolRegistry) -> None:
    """将远程 Agent 注册为本地工具。"""
    spec = ToolSpec(
        name=f"a2a__{self._agent_name}",
        description=self._agent_card.description,
        parameters=ToolParameterSchema(
            type="object",
            properties={"message": {"type": "string", "description": "任务描述"}},
            required=["message"],
        ),
        handler=self._handle_tool_call,
    )
    registry.register(spec)

async def _handle_tool_call(self, args: dict, ctx: ToolUseContext) -> ToolResult:
    try:
        task = await self.send_task_and_wait(args["message"])
        if task.status == A2ATaskStatus.COMPLETED:
            return ToolResult(content=task.result or "")
        return ToolResult(content=task.error or "unknown error", is_error=True)
    except Exception as e:
        return ToolResult(content=str(e), is_error=True)
```

### Pattern 4: SecretStr API Key 管理
**What:** API key 使用 pydantic.SecretStr 包装，不暴露在日志/序列化中
**When to use:** server.py 认证验证，client.py 发送 API key
**Example:**
```python
# 来源: 框架现有模式 (llm/providers/anthropic_provider.py:267)
from pydantic import SecretStr

class A2AServer:
    def __init__(self, ..., api_key: str | None = None):
        self._api_key = SecretStr(api_key) if api_key else None

    def _verify_auth(self, headers: list[tuple[bytes, bytes]]) -> bool:
        if self._api_key is None:
            return True  # 无认证模式
        for key, value in headers:
            if key == b"x-api-key":
                return value.decode() == self._api_key.get_secret_value()
        return False
```

### Anti-Patterns to Avoid
- **在框架层引入 starlette/fastapi/uvicorn 依赖:** 项目约束 D-01 明确禁止。纯 ASGI 足够处理 4 个简单端点
- **在 AgentCard 中使用 Pydantic 嵌套模型过度建模:** AgentCard 从 flat frontmatter 解析，保持简单 str 字段，不搞嵌套 capabilities 对象
- **A2AClient 直接抛异常:** 必须返回 ToolResult(is_error=True)，与 MCP 错误处理模式一致（D-11）
- **忽略 Agent.run() 的 AsyncGenerator 特性:** Agent.run() 产生多个 AgentEvent，需收集最终文本结果作为 task result
- **在 ASGI handler 中直接 await 长时间运行的 Agent 任务:** 需用 asyncio.create_task() 后台运行，handler 立即返回 task_id

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON 序列化/反序列化 | 手动 dict <-> JSON 转换 | Pydantic BaseModel.model_dump() / model_validate_json() | 类型安全、验证、一致性 |
| Frontmatter 解析 | 自写 YAML 解析器 | parse_frontmatter() (memory/frontmatter.py) | 项目已有，flat key:value 格式匹配 |
| HTTP 客户端 | 自写 HTTP 请求 | httpx.AsyncClient | 项目已有依赖，支持异步、超时、重试 |
| API key 安全 | 字符串直接传递 | pydantic.SecretStr | 项目已有模式（AnthropicProvider 使用同一模式） |
| 任务 ID 生成 | 自写 ID 算法 | uuid.uuid4() | 标准库，简单可靠 |
| ISO 时间戳 | 手动格式化 | datetime.datetime.now(timezone.utc).isoformat() | 标准库，时区正确 |

**Key insight:** 框架已有 httpx + pydantic + SecretStr + parse_frontmatter() 基础设施，A2A 实现几乎不需要新的底层工具。核心工作是组合现有模式。

## Common Pitfalls

### Pitfall 1: ASGI body 读取不完整
**What goes wrong:** ASGI receive() 可能分多次返回 body chunks，只读第一次会丢失数据
**Why it happens:** ASGI 规范不保证单次 receive 包含完整 body
**How to avoid:** 循环调用 receive() 直到收到 http.disconnect 或 type 不是 http.request
**Warning signs:** POST /tasks 请求体解析为空 JSON 或截断

### Pitfall 2: Agent.run() AsyncGenerator 未正确消费
**What goes wrong:** Agent.run() 返回 AsyncGenerator，如果只获取第一个事件就退出，后续事件丢失
**Why it happens:** 对 async generator 生命周期理解不足
**How to avoid:** 使用 async for event in agent.run(message) 完整消费，收集最后一个 step/done 事件的数据
**Warning signs:** Task result 为空或只有部分结果

### Pitfall 3: 并发 TaskStore 访问无保护
**What goes wrong:** 多个并发请求同时读写 task dict，导致数据竞争
**Why it happens:** asyncio 单线程模型中，await 点之间的代码是原子的，但跨 await 的操作需要保护
**How to avoid:** 使用 asyncio.Lock 保护 task dict 的读写操作
**Warning signs:** 偶发的 task status 不一致

### Pitfall 4: AgentCard .md 文件 capabilities 解析错误
**What goes wrong:** parse_frontmatter() 返回 dict[str, str]，capabilities 逗号分隔字符串需要手动 split
**Why it happens:** frontmatter 是 flat string，不像 JSON 有原生列表类型
**How to avoid:** 明确 split(",") + strip() + filter 空，与 AgentConfig.tools 解析模式一致
**Warning signs:** capabilities 列表包含空字符串

### Pitfall 5: send_task_and_wait() 无限等待
**What goes wrong:** 如果远程 Agent 卡住不返回终态，轮询永不停止
**Why it happens:** 忘记设置超时或超时逻辑有 bug
**How to avoid:** 使用 time.monotonic() + deadline 严格超时，默认 timeout=300s
**Warning signs:** AgentLoop 等待远程 Agent 时挂起

### Pitfall 6: 路径解析错误（tasks/{id} 边界情况）
**What goes wrong:** /tasks/ 后面可能是空字符串，/tasks//cancel 等异常路径
**Why it happens:** 手动 split path 没有充分验证
**How to avoid:** 使用 path.startswith() + strip + 长度检查，或用简单的正则
**Warning signs:** 404 应该返回时返回 500，或 task_id 为空

## Code Examples

### AgentCard 数据模型 + .md 解析

```python
# models.py — AgentCard 从 .md frontmatter 加载
from pydantic import BaseModel
from agent_framework.memory.frontmatter import parse_frontmatter

class AgentCard(BaseModel):
    """Agent 能力描述卡片。"""
    name: str
    description: str = ""
    url: str
    version: str = "1.0"
    capabilities: list[str] = []

def load_agent_card(text: str, filename: str = "<unknown>") -> AgentCard:
    """从 .md frontmatter 解析 AgentCard。"""
    meta = parse_frontmatter(text)

    name = meta.get("name")
    if not name:
        raise ValueError(f"AgentCard 缺少 name 字段: {filename}")

    url = meta.get("url")
    if not url:
        raise ValueError(f"AgentCard 缺少 url 字段: {filename}")

    capabilities_raw = meta.get("capabilities", "")
    capabilities = [c.strip() for c in capabilities_raw.split(",") if c.strip()]

    return AgentCard(
        name=name,
        description=meta.get("description", ""),
        url=url,
        version=meta.get("version", "1.0"),
        capabilities=capabilities,
    )
```

### AgentCard .md 文件示例
```markdown
---
name: research-agent
description: 远程研究分析 Agent
url: https://remote.example.com
version: "1.0"
capabilities: text-generation, web-search, code-execution
---
```

### ASGI body 完整读取

```python
# server.py — 正确读取 ASGI request body
async def _read_body(self, receive: Receive) -> bytes:
    """完整读取 ASGI request body。"""
    body = b""
    while True:
        message = await receive()
        body += message.get("body", b"")
        if not message.get("more_body", False):
            break
    return body

async def _send_json(self, send: Send, status: int, data: dict) -> None:
    """发送 JSON 响应。"""
    body = json.dumps(data).encode("utf-8")
    await send({
        "type": "http.response.start",
        "status": status,
        "headers": [
            [b"content-type", b"application/json"],
            [b"content-length", str(len(body)).encode()],
        ],
    })
    await send({
        "type": "http.response.body",
        "body": body,
    })
```

### A2AClient send_task_and_wait 轮询

```python
# client.py — 同步轮询等待
import asyncio
import time
import httpx
from pydantic import SecretStr

class A2AClient:
    def __init__(self, agent_card: AgentCard, api_key: str | None = None):
        self._agent_card = agent_card
        self._api_key = SecretStr(api_key) if api_key else None
        self._client = httpx.AsyncClient(
            base_url=agent_card.url,
            headers=self._build_headers(),
            timeout=httpx.Timeout(connect=5.0, read=30.0, write=10.0, pool=120.0),
        )

    async def send_task(self, message: str) -> str:
        """发送任务，返回 task_id。"""
        response = await self._client.post("/tasks", json={"message": message})
        response.raise_for_status()
        data = response.json()
        return data["id"]

    async def get_task(self, task_id: str) -> A2ATask:
        """查询任务状态。"""
        response = await self._client.get(f"/tasks/{task_id}")
        response.raise_for_status()
        return A2ATask.model_validate(response.json())

    async def send_task_and_wait(
        self, message: str, *, poll_interval: float = 2.0, timeout: float = 300.0,
    ) -> A2ATask:
        """发送任务并轮询等待完成。"""
        task_id = await self.send_task(message)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            task = await self.get_task(task_id)
            if task.status.is_terminal:
                return task
            await asyncio.sleep(poll_interval)
        return A2ATask(
            id=task_id,
            status=A2ATaskStatus.FAILED,
            error=f"超时 ({timeout}s)",
            created_at=task.created_at,
            updated_at=task.updated_at,
        )

    def _build_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["X-API-Key"] = self._api_key.get_secret_value()
        return headers
```

### A2AServer 后台执行 Agent 任务

```python
# server.py — 后台运行 Agent 并更新 task status
import asyncio
import uuid
from datetime import datetime, timezone

class A2AServer:
    def __init__(self, agent, agent_card_data: dict, api_key: str | None = None):
        self._agent = agent
        self._agent_card_data = agent_card_data
        self._api_key = SecretStr(api_key) if api_key else None
        self._tasks: dict[str, A2ATask] = {}
        self._lock = asyncio.Lock()

    async def _execute_task(self, task_id: str, message: str) -> None:
        """后台执行 Agent 任务。"""
        try:
            result_parts = []
            async for event in self._agent.run(message):
                if event.type == "done" and "text" in event.data:
                    result_parts.append(event.data["text"])

            async with self._lock:
                task = self._tasks[task_id]
                self._tasks[task_id] = A2ATask(
                    id=task.id,
                    status=A2ATaskStatus.COMPLETED,
                    result="\n".join(result_parts) if result_parts else "",
                    created_at=task.created_at,
                    updated_at=datetime.now(timezone.utc).isoformat(),
                )
        except Exception as e:
            async with self._lock:
                task = self._tasks[task_id]
                self._tasks[task_id] = A2Task(
                    id=task.id,
                    status=A2ATaskStatus.FAILED,
                    error=str(e),
                    created_at=task.created_at,
                    updated_at=datetime.now(timezone.utc).isoformat(),
                )

    async def _handle_create_task(self, scope, receive, send):
        body = await self._read_body(receive)
        data = json.loads(body)
        message = data.get("message", "")

        task_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        task = A2ATask(
            id=task_id,
            status=A2ATaskStatus.PENDING,
            created_at=now,
            updated_at=now,
        )
        async with self._lock:
            self._tasks[task_id] = task

        # 后台执行
        asyncio.create_task(self._execute_task(task_id, message))

        await self._send_json(send, 201, task.model_dump())
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| A2A v0.3 JSON-RPC only | A2A v1.0 多 binding（JSON-RPC + gRPC + REST） | 2025 | 本项目使用 REST 子集，符合最新规范方向 |
| A2A kind discriminator | JSON member name discriminator | v1.0 (2025) | Part 类型不再需要 "kind" 字段，字段名即为类型标识 |
| 全状态 TaskState (9 states) | 简化子集 (5 states) | 本项目决定 | 同步模式不需要 input-required/auth-required/rejected/unknown |

**Deprecated/outdated:**
- A2A v0.3 MessageSendParams: 已更名为 SendMessageRequest
- A2A v0.3 kind 字段: v1.0 已移除，用 JSON member name 替代

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Agent.run() 的 done 事件中 data["text"] 包含最终结果 | Pattern Examples | Agent 事件格式理解偏差，需确认 AgentEvent 契约 |
| A2 | A2A 规范 v1.0 的 REST binding 路径 /tasks 是创建任务的标准路径 | State of the Art | 实际规范用 /message:send，但项目决定 D-02 锁定了 /tasks |
| A3 | parse_frontmatter() 可以直接复用于 AgentCard .md 解析 | Pattern 1 | frontmatter 中 capabilities 字段的逗号分隔格式需手动 split |
| A4 | asyncio.create_task() 在 ASGI handler 中可安全使用 | Pattern 4 | ASGI server 的 event loop 生命周期可能影响后台任务 |

## Open Questions

1. **Agent.run() 事件中的最终文本提取方式**
   - What we know: AgentEvent 有 type/step/data 字段，type 包含 step/tool_result/done/max_steps/error
   - What's unclear: done 事件的 data 字段确切结构是什么？文本在 data["text"] 还是其他 key？
   - Recommendation: 08-01 实现时先读 agents/base.py 和 AgentLoop 的 done 事件构建逻辑确认

2. **A2AServer 是否需要优雅关闭后台任务**
   - What we know: asyncio.create_task() 创建的后台任务在 server 关闭时可能被取消
   - What's unclear: 是否需要提供 shutdown() 方法等待正在运行的任务完成
   - Recommendation: Claude's Discretion 范围，建议先不实现，后续按需添加

3. **A2AMessage 的具体字段设计**
   - What we know: A2A 规范定义 Message 有 role + parts，但本项目同步模式可简化
   - What's unclear: 是否需要完整的 parts 结构，还是简化为 role + text 足够
   - Recommendation: Claude's Discretion 范围，建议简化为 role: str + text: str

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11 | 所有模块 | ✓ | 3.11.14 | — |
| pydantic | 数据模型 | ✓ | 2.12.5 | — |
| httpx | A2AClient | ✓ | 0.28.1 | — |
| pytest | 测试 | ✓ | 8.x | — |
| pytest-asyncio | 异步测试 | ✓ | 1.3.0 | — |

**Missing dependencies with no fallback:** none
**Missing dependencies with fallback:** none

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 1.3.0 |
| Config file | framework/pyproject.toml ([tool.pytest.ini_options]) |
| Quick run command | `cd framework && pytest tests/test_a2a_models.py -v -x` |
| Full suite command | `cd framework && pytest tests/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| A2A-01 | AgentCard 数据模型创建 + 验证 + .md 解析 | unit | `pytest tests/test_a2a_models.py -v -x` | Wave 0 |
| A2A-02 | A2ATask 状态机 + A2AMessage 创建 | unit | `pytest tests/test_a2a_models.py -v -x` | Wave 0 |
| A2A-03 | A2AClient send_task/get_task/cancel + ToolSpec 注册 | unit + integration | `pytest tests/test_a2a_client.py -v -x` | Wave 0 |
| A2A-04 | A2AServer ASGI 路由 + Agent 调用 + 认证 | unit + integration | `pytest tests/test_a2a_server.py -v -x` | Wave 0 |
| A2A-05 | send_task_and_wait 轮询 + 超时 | unit | `pytest tests/test_a2a_client.py::test_send_task_and_wait -v` | Wave 0 |
| A2A-06 | API-key 认证（有效/无效/缺失 key） | unit | `pytest tests/test_a2a_server.py -k auth -v` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd framework && pytest tests/test_a2a_*.py -v -x`
- **Per wave merge:** `cd framework && pytest tests/ -v`
- **Phase gate:** `cd framework && pytest tests/ -v` 全部通过

### Wave 0 Gaps
- [ ] `framework/tests/test_a2a_models.py` — covers A2A-01, A2A-02
- [ ] `framework/tests/test_a2a_client.py` — covers A2A-03, A2A-05
- [ ] `framework/tests/test_a2a_server.py` — covers A2A-04, A2A-06

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | API-key via X-API-Key header，SecretStr 管理 |
| V3 Session Management | no | 无 session 概念，每次请求独立认证 |
| V4 Access Control | yes | 服务级单一 key，全部端点或无访问 |
| V5 Input Validation | yes | Pydantic BaseModel 验证 + JSON 解析异常处理 |
| V6 Cryptography | no | 框架层不处理 TLS，应用层负责 HTTPS |

### Known Threat Patterns for A2A Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| API key 泄露 | Information Disclosure | SecretStr 包装，不记录日志，不序列化 |
| 路径遍历攻击 | Tampering | 路由严格匹配，task_id UUID 格式验证 |
| JSON 注入 | Tampering | Pydantic 验证 + json.loads() 异常处理 |
| 未认证访问 | Spoofing | 每个请求前验证 X-API-Key header |
| 超时 DoS | Denial of Service | send_task_and_wait 严格超时，后台任务超时取消 |
| SSRF (Client 侧) | Tampering | AgentCard.url 由配置文件提供，非用户输入 |

## Sources

### Primary (HIGH confidence)
- A2A Protocol Specification v1.0 — [github.com/a2aproject/A2A/docs/specification.md](https://github.com/a2aproject/A2A/blob/main/docs/specification.md) — 完整协议规范（数据模型、操作、绑定）
- A2A Task Lifecycle — [agent2agent.info/docs/concepts/task/](https://agent2agent.info/docs/concepts/task/) — Task 状态机定义
- 框架源码: tools/types.py, tools/mcp/config.py, agents/base.py, memory/frontmatter.py, llm/providers/anthropic_provider.py — 所有代码模式来自实际代码库验证

### Secondary (MEDIUM confidence)
- Google A2A 公告 — [developers.googleblog.com](https://developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability/) — 协议设计理念和目标

### Tertiary (LOW confidence)
- 无

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — 所有依赖已在项目中，版本已验证
- Architecture: HIGH — ASGI 纯接口模式明确，MCP 模块提供成熟参考
- Pitfalls: HIGH — ASGI body 读取和 AsyncGenerator 消费是已知常见陷阱
- A2A 规范: HIGH — 完整阅读了 v1.0 规范

**Research date:** 2026-05-29
**Valid until:** 2026-06-29（稳定期，A2A v1.0 规范近期不会大变）
