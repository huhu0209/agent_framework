# Phase 9: Backend 事件系统 - Research

**Researched:** 2026-05-29
**Domain:** asyncio pub-sub + WebSocket 实时推送 + AgentLoop 事件映射
**Confidence:** HIGH

## Summary

Phase 9 要建立从 AgentLoop 内部状态到前端可视化的事件链路。核心由 4 个组件组成：EventBus（asyncio.Queue pub-sub）、VizEvent（Pydantic 模型）、AgentRunner（LoopEvent 到 VizEvent 映射 + AgentLoop 包装）、WsServer（WebSocket 推送）。

所有技术选型已通过 CONTEXT.md 锁定：asyncio.Queue 做 pub-sub、Pydantic v2 做数据模型、websockets 库做 WebSocket 服务。现有代码库已具备成熟的 asyncio 模式（TeamManager.notifications Queue、AgentLoop.run() async generator），以及 Pydantic v2 + pytest-asyncio 测试基础设施。

**Primary recommendation:** 新建 `framework/agent_framework/viz/` 模块，4 个文件各自独立职责。EventBus 用 asyncio.Lock 保护 subscribers set，有界 Queue maxsize=1000 + drop-oldest。AgentRunner 包装 AgentLoop.run() async generator 不改变其行为。WsServer 用 `websockets.asyncio.server.serve()` + `broadcast()` 推送。

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** subscribe() 返回 asyncio.Queue，消费方 await queue.get()，取消时 unsubscribe(queue)
- **D-02:** 单 topic 广播 — 所有事件广播到所有订阅者。topic 过滤留 v0.0.4+（EVNT-F01）
- **D-03:** 有界队列 + 丢弃最旧，maxsize=1000 作为安全网。可视化可靠性优先级低于 agent 执行
- **D-04:** VizEvent 用 Pydantic BaseModel，自带 .model_dump() JSON 序列化
- **D-05:** payload 为松散 dict[str, Any]，按 event type 文档约定结构
- **D-06:** VizEvent type 从前端视角重新定义：idle / thinking / tool_call / done / error / shutdown
- **D-07:** LoopEvent → VizEvent 映射关系：
  - step (stop_reason=tool_use) → thinking
  - tool_result → tool_call
  - step (stop_reason=end_turn) → done
  - error / max_steps → error
  - agent 启动前 → idle
  - agent 停止 → shutdown
  - 映射逻辑在 AgentRunner 内部完成
- **D-08:** AgentRunner 1:1 包装单个 AgentLoop。start_team 时创建多个 AgentRunner
- **D-09:** start_team 通过 asyncio.create_task 异步执行 AgentRunner，不阻塞 WebSocket 处理循环
- **D-10:** 新模块 framework/agent_framework/viz/ — 包含 event_bus.py, viz_event.py, agent_runner.py, ws_server.py
- **D-11:** 双向 JSON 文本帧通信，不用 subprotocol
- **D-12:** 客户端控制命令内联 Agent 配置 — {"type": "start_team", "agent": {"name": "cat", ...}}
- **D-13:** 控制命令响应走独立通道 — {"type": "command_response", "success": bool, "error": "..."}
- **D-14:** WebSocket 服务端放在 framework/agent_framework/viz/ws_server.py，使用 websockets 库

### Claude's Discretion
- EventBus 内部并发安全（asyncio.Lock 使用）
- VizEvent payload 各 type 的具体字段定义
- AgentRunner 异常处理和清理逻辑
- WebSocket 心跳超时和重连参数

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| EVNT-01 | EventBus 发布/订阅事件，asyncio.Queue pub-sub | asyncio.Queue bounded + Lock-protected subscribers set (Pattern 1) |
| EVNT-02 | 订阅 EventBus 获取 asyncio.Queue，异步消费 | subscribe() returns Queue, consumer awaits queue.get() |
| EVNT-03 | 取消订阅，EventBus 自动清理 Queue | unsubscribe(queue) removes from set + discards queue ref |
| EVNT-04 | VizEvent 数据模型 type/agent/payload/timestamp，JSON 序列化 | Pydantic v2 BaseModel + model_dump_json() |
| EVNT-05 | AgentRunner 包装 AgentLoop，映射 LoopEvent → VizEvent 并广播 | AgentRunner async generator wrapper pattern (Pattern 3) |
| EVNT-06 | 事件映射覆盖 thinking/tool_call/tool_result/done/error/max_steps | 映射表定义在 D-07，AgentRunner 内部实现 |
| EVNT-07 | AgentRunner yield 原始事件，不改变 AgentLoop 外部行为 | yield-through pattern (Pattern 3) |
| WSRV-01 | WebSocket 服务端订阅 EventBus，实时推送 VizEvent | websockets 16 serve() + broadcast() API |
| WSRV-02 | WebSocket 断开时自动取消 EventBus 订阅 | try/finally cleanup in handler |
| WSRV-03 | 客户端发送 start_team 控制命令 | JSON text frame command protocol |
| WSRV-04 | 客户端发送 stop_team 控制命令 | JSON text frame command protocol |
| WSRV-05 | WebSocket 使用 websockets 库，自带 ping/pong 心跳 | websockets 16 默认 ping_interval=20, ping_timeout=20 |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| EventBus pub-sub | API / Backend | — | 纯 Python asyncio 组件，属于框架层基础设施 |
| VizEvent 数据模型 | API / Backend | — | Pydantic 模型定义，框架层 |
| AgentRunner 映射 | API / Backend | — | 消费 AgentLoop async generator，属于框架层 |
| WebSocket 服务 | API / Backend | — | 独立端口 WebSocket server，使用 websockets 库 |
| AgentLoop 执行 | API / Backend | — | 已有组件，AgentRunner 包装不修改它 |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| asyncio (stdlib) | Python 3.11+ | Queue, Lock, create_task, event loop | 标准库，零依赖，项目已广泛使用 |
| pydantic | 2.12.5 (installed) | VizEvent BaseModel, JSON 序列化 | 项目已依赖 pydantic>=2.0.0 [VERIFIED: framework/pyproject.toml] |
| websockets | 16.0 (installed) | WebSocket 服务端 | 已安装，API 稳定，支持 serve() + broadcast() [VERIFIED: PyPI] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | 8.x (installed) | 测试框架 | 所有单元测试 |
| pytest-asyncio | 1.3.0 (installed) | 异步测试支持 | asyncio_mode = "auto" 已配置 [VERIFIED: pyproject.toml] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| websockets 库 | FastAPI WebSocket | FastAPI WebSocket 需要 ASGI 服务器，增加依赖。websockets 库更轻量、独立，已安装 [CITED: STATE.md] |
| asyncio.Queue pub-sub | blinker / pyee 信号库 | 外部依赖增加，asyncio.Queue 已满足需求且 TeamManager 已验证此模式 |

**Installation:**
```bash
# websockets 需要添加到 framework/pyproject.toml dependencies
cd framework && uv pip install websockets
# 然后更新 pyproject.toml dependencies 添加 "websockets>=14.0"
```

**Version verification:**
```bash
# 已验证
pip index versions websockets  # 16.0 latest, INSTALLED: 16.0
pip index versions pydantic    # 2.13.4 latest, INSTALLED: 2.12.5
pip index versions pytest-asyncio  # 1.4.0 latest, INSTALLED: 1.3.0
```

## Package Legitimacy Audit

> slopcheck 不可用，所有包标记 [ASSUMED]。下表基于 PyPI registry 验证 + 项目已安装状态。

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| websockets | PyPI | ~10 yrs | 极高 (>10M/mo) | github.com/python-websockets/websockets | N/A | [ASSUMED] — 已在本地安装且验证 |
| pydantic | PyPI | ~7 yrs | 极高 (>50M/mo) | github.com/pydantic/pydantic | N/A | [ASSUMED] — 已在 pyproject.toml 声明 |
| pytest-asyncio | PyPI | ~6 yrs | 高 (>5M/mo) | github.com/pytest-dev/pytest-asyncio | N/A | [ASSUMED] — 已在 pyproject.toml 声明 |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

*slopcheck was unavailable at research time. All packages above are tagged `[ASSUMED]` and the planner must gate each install behind a `checkpoint:human-verify` task. However, websockets 16.0 is already installed on the system and importable.*

## Architecture Patterns

### System Architecture Diagram

```
AgentLoop.run()              AgentRunner               EventBus              WsServer
  (async generator)           (wrapper)               (pub-sub)             (websockets)
       |                          |                       |                      |
       |  LoopEvent               |                       |                      |
       |  (step/done/error/       |                       |                      |
       |   tool_result/max_steps) |                       |                      |
       |------------------------->|                       |                      |
       |                          |  map LoopEvent        |                      |
       |                          |  -> VizEvent          |                      |
       |                          |  yield original       |                      |
       |                          |  LoopEvent (passthru) |                      |
       |                          |----------+            |                      |
       |                          |          |            |                      |
       |                          |  publish(VizEvent)    |                      |
       |                          |---------------------->|                      |
       |                          |                       |  broadcast to        |
       |                          |                       |  all queues          |
       |                          |                       |--------+--------+    |
       |                          |                       |        |        |    |
       |                          |                       |  queue1 queue2  |    |
       |                          |                       |        |        |    |
       |                          |                       |        v        |    |
       |                          |                       |  WsHandler 1    |    |
       |                          |                       |  queue.get()    |    |
       |                          |                       |  websocket.send(VizEvent JSON)
       |                          |                       |        |        |    |
       |                          |                       |        |   WsHandler 2    |
       |                          |                       |        |   (control cmd)  |
       |                          |                       |        |        |    |
       v                          v                       v        v        v    v
                                   ^                                            |
                                   |          WebSocket Client                  |
                                   |  <--- JSON text frames --->               |
                                   |     VizEvent stream (server push)         |
                                   |     command_response (server push)         |
                                   |     start_team / stop_team (client cmd)    |
```

### Recommended Project Structure
```
framework/agent_framework/viz/     # 新模块，可视化事件系统
    __init__.py                    # 公开 API: EventBus, VizEvent, AgentRunner, serve_ws
    event_bus.py                   # EventBus 类 — subscribe/unsubscribe/publish
    viz_event.py                   # VizEvent Pydantic 模型
    agent_runner.py                # AgentRunner 包装器 — 映射 + 广播
    ws_server.py                   # WebSocket 服务端 — 推送 + 控制命令处理

framework/tests/
    test_event_bus.py              # EventBus 单元测试
    test_viz_event.py              # VizEvent 模型测试
    test_agent_runner.py           # AgentRunner 映射测试
    test_ws_server.py              # WebSocket 服务端测试
```

### Pattern 1: asyncio.Queue Pub-Sub (EventBus)
**What:** 使用 asyncio.Queue 实现发布-订阅模式，每个订阅者获得独立 Queue 引用
**When to use:** 任何需要一对多事件分发的场景

```python
# Source: [CITED: docs.python.org/3/library/asyncio-queue.html] + 项目 TeamManager 模式
import asyncio
from typing import Any

class EventBus:
    def __init__(self, maxsize: int = 1000) -> None:
        self._subscribers: set[asyncio.Queue[dict[str, Any]]] = set()
        self._lock = asyncio.Lock()
        self._maxsize = maxsize

    async def subscribe(self) -> asyncio.Queue[dict[str, Any]]:
        async with self._lock:
            q: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=self._maxsize)
            self._subscribers.add(q)
            return q

    async def unsubscribe(self, q: asyncio.Queue[dict[str, Any]]) -> None:
        async with self._lock:
            self._subscribers.discard(q)

    async def publish(self, event: dict[str, Any]) -> None:
        async with self._lock:
            subscribers = list(self._subscribers)
        for q in subscribers:
            if q.full():
                q.get_nowait()  # drop oldest
            q.put_nowait(event)
```

**Key decisions:**
- `asyncio.Lock` 保护 `_subscribers` set 的增删，防止迭代时修改 [ASSUMED: 基于 asyncio 单线程模型最佳实践]
- `publish()` 在 Lock 内复制 subscribers list，然后无锁遍历推入。避免持 Lock 做 I/O
- drop-oldest 策略：`q.full()` 时 `get_nowait()` 丢弃最旧，再 `put_nowait()` 推入新事件
- `maxsize=1000` 是安全网，MVP 场景下远不会触达 [CITED: 09-CONTEXT.md D-03]

### Pattern 2: Pydantic v2 VizEvent Model
**What:** 用 Pydantic BaseModel 定义可视化事件，自动 JSON 序列化
**When to use:** 所有需要跨进程/网络传输的事件数据

```python
# Source: [VERIFIED: Pydantic v2 已安装, model_dump_json() 已验证]
from datetime import datetime, timezone
from typing import Any
from pydantic import BaseModel

class VizEvent(BaseModel):
    type: str           # idle | thinking | tool_call | done | error | shutdown
    agent: str          # agent 名称
    payload: dict[str, Any]  # 按 type 文档约定结构
    timestamp: float    # time.time() 精度足够，避免 datetime 序列化复杂度

    def to_json(self) -> str:
        return self.model_dump_json()
```

**Why `timestamp: float` not `datetime`:**
- `time.time()` 返回 float，序列化为 JSON 数字无需额外处理
- 前端 `new Date(timestamp * 1000)` 直接使用
- 避免 `datetime` 序列化的 ISO 格式解析开销 [ASSUMED]

### Pattern 3: AgentRunner Async Generator Wrapper
**What:** 包装 AgentLoop.run() async generator，映射事件并广播，同时透传原始事件
**When to use:** 需要在不修改原始 async generator 的情况下添加副作用

```python
# Source: [VERIFIED: agent_loop.py:243-408 run() async generator 接口]
import asyncio
from typing import AsyncGenerator
from agent_framework.agents.agent_loop import LoopEvent
from agent_framework.viz.event_bus import EventBus
from agent_framework.viz.viz_event import VizEvent

class AgentRunner:
    def __init__(self, agent_name: str, bus: EventBus) -> None:
        self._agent_name = agent_name
        self._bus = bus

    async def wrap(
        self, loop_gen: AsyncGenerator[LoopEvent, None]
    ) -> AsyncGenerator[LoopEvent, None]:
        """包装 AgentLoop.run() 生成器 — 映射事件 + 广播 + 透传原始事件。"""
        # idle 事件 — agent 启动前
        await self._bus.publish(VizEvent(
            type="idle", agent=self._agent_name,
            payload={}, timestamp=time.time(),
        ).model_dump())

        async for event in loop_gen:
            viz = self._map_event(event)
            if viz is not None:
                await self._bus.publish(viz.model_dump())
            yield event  # 透传原始 LoopEvent，不改变外部行为

        # shutdown 事件 — agent 运行结束
        await self._bus.publish(VizEvent(
            type="shutdown", agent=self._agent_name,
            payload={}, timestamp=time.time(),
        ).model_dump())

    def _map_event(self, event: LoopEvent) -> VizEvent | None:
        """LoopEvent → VizEvent 映射。[CITED: 09-CONTEXT.md D-07]"""
        now = time.time()
        if event.type == "step":
            stop_reason = event.data.get("stop_reason", "")
            if stop_reason == "tool_use":
                return VizEvent(type="thinking", agent=self._agent_name,
                                payload={"step": event.step}, timestamp=now)
            elif stop_reason in ("end_turn", "stop_sequence"):
                return VizEvent(type="done", agent=self._agent_name,
                                payload={"step": event.step}, timestamp=now)
        elif event.type == "tool_result":
            return VizEvent(type="tool_call", agent=self._agent_name,
                            payload={"step": event.step, **event.data}, timestamp=now)
        elif event.type in ("error", "max_steps"):
            return VizEvent(type="error", agent=self._agent_name,
                            payload={"step": event.step, **event.data}, timestamp=now)
        elif event.type == "done":
            return VizEvent(type="done", agent=self._agent_name,
                            payload={"step": event.step, **event.data}, timestamp=now)
        return None
```

**Key design decisions:**
- `wrap()` 是 async generator — 调用方 `async for event in runner.wrap(loop.run(prompt))` 仍获得原始 LoopEvent
- 映射逻辑完全在 `_map_event()` 内部，单一职责
- idle 在循环前发布，shutdown 在循环后（生成器正常结束）发布
- 映射关系严格遵循 D-07 [CITED: 09-CONTEXT.md]

### Pattern 4: WebSocket Server with EventBus Integration
**What:** websockets 16 serve() + EventBus 订阅，双向 JSON 通信
**When to use:** 实时事件推送到浏览器客户端

```python
# Source: [VERIFIED: websockets 16.0 serve() + broadcast() API 已验证]
import asyncio
import json
from websockets.asyncio.server import serve, ServerConnection

async def handler(websocket: ServerConnection, bus: EventBus) -> None:
    """每个 WebSocket 连接的处理器。"""
    queue = await bus.subscribe()
    try:
        # 双任务：事件推送 + 命令接收
        recv_task = asyncio.create_task(_handle_commands(websocket, bus))
        push_task = asyncio.create_task(_push_events(websocket, queue))
        done, pending = await asyncio.wait(
            [recv_task, push_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
    finally:
        await bus.unsubscribe(queue)

async def _push_events(websocket: ServerConnection, queue: asyncio.Queue) -> None:
    """从 EventBus 消费事件并推送到 WebSocket。"""
    while True:
        event = await queue.get()
        await websocket.send(json.dumps(event))

async def _handle_commands(websocket: ServerConnection, bus: EventBus) -> None:
    """接收客户端控制命令。"""
    async for message in websocket:
        cmd = json.loads(message)
        # 处理 start_team / stop_team 等
        ...
```

**Key points:**
- `serve()` 是 async context manager：`async with serve(handler, host, port)` [VERIFIED: websockets 16.0 docs]
- `ServerConnection` 支持 `async for message in websocket` 迭代接收 [VERIFIED]
- `ping_interval=20, ping_timeout=20` 默认启用心跳 [VERIFIED: websockets docs]
- 连接断开时 `async for` 退出 → finally 中 unsubscribe [ASSUMED: ConnectionClosed 异常行为]
- 双任务模式（push + recv）避免单循环阻塞 [ASSUMED: asyncio.wait 最佳实践]

### Anti-Patterns to Avoid
- **Anti-pattern: 在 AgentLoop.run() 内部添加事件发布逻辑。** AgentLoop 是核心执行循环，不应耦合可视化关注点。AgentRunner 通过包装层注入副作用，不修改源代码。
- **Anti-pattern: EventBus.publish() 内持 Lock 做 Queue.put_nowait()。** 持锁期间如果 Queue 操作异常，会阻塞所有 subscribe/unsubscribe。应在 Lock 内只复制 subscribers，释放锁后再遍历推入。
- **Anti-pattern: WebSocket handler 内直接 await AgentLoop.run()。** 会阻塞 WebSocket 接收命令的能力。必须用 `asyncio.create_task()` 异步执行 AgentRunner。
- **Anti-pattern: 用 websockets.broadcast() 替代 EventBus。** broadcast() 操作 ServerConnection set，不经过 EventBus 的有界队列保护。丢失 EventBus 的 drop-oldest 安全网。
- **Anti-pattern: VizEvent 用 dataclass 而非 Pydantic。** CONTEXT.md 已锁定 D-04 使用 Pydantic BaseModel。

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| WebSocket 协议实现 | 自定义 WebSocket server | websockets 库 serve() | 协议复杂（RFC 6455），需处理帧分片、掩码、心跳、扩展 |
| JSON 序列化/反序列化 | 手写 JSON encoder/decoder | Pydantic model_dump_json() + json.loads() | Pydantic v2 已提供高效序列化 |
| 心跳检测 | 手写 ping/pong 定时器 | websockets 默认 ping_interval/ping_timeout | 库内置，配置即用 |
| 有界队列 | 手写环形缓冲区 | asyncio.Queue(maxsize=N) + get_nowait/put_nowait | stdlib 已提供，项目已使用此模式 |

**Key insight:** 这个 phase 的核心复杂度在"事件映射"和"异步流程编排"，不在基础设施。所有基础设施组件（Queue、WebSocket、Pydantic）都有成熟库支持。

## Common Pitfalls

### Pitfall 1: EventBus subscribers set 在迭代时被修改
**What goes wrong:** publish() 遍历 _subscribers 时，另一个协程 unsubscribe() 修改 set → RuntimeError
**Why it happens:** asyncio 虽然单线程，但 yield 点（await）会发生协程切换
**How to avoid:** publish() 在 Lock 内 `list(self._subscribers)` 复制，遍历复制的 list
**Warning signs:** 测试中出现 `RuntimeError: Set changed size during iteration`

### Pitfall 2: WebSocket 连接断开后 Queue 泄漏
**What goes wrong:** 客户端断开但 unsubscribe 未被调用，Queue 持续积累事件
**Why it happens:** handler 异常退出但 finally 未执行（极少见），或 subscribe/unsubscribe 路径有 bug
**How to avoid:** handler 严格使用 try/finally 模式。测试验证断开后 subscribe count 归零
**Warning signs:** 长时间运行后内存持续增长

### Pitfall 3: AgentRunner 包装改变 AgentLoop 行为
**What goes wrong:** AgentRunner 不 yield 某些 LoopEvent，或改变事件顺序
**Why it happens:** 映射逻辑遗漏事件类型，或异常处理吞掉了事件
**How to avoid:** AgentRunner.wrap() 必须 `yield event` 对每一个 `async for event` 迭代。测试覆盖所有 LoopEvent type 的透传验证
**Warning signs:** EVNT-07 测试失败 — 期望收到 N 个 LoopEvent，实际收到更少

### Pitfall 4: asyncio.Queue.full() 和 get_nowait() 竞态
**What goes wrong:** 检查 full() 为 True，但 get_nowait() 抛 QueueEmpty（另一个协程抢先 get）
**Why it happens:** 在 asyncio 单线程中理论上不会发生（Queue 操作无 await 点），但 defensive coding 是好习惯
**How to avoid:** drop-oldest 用 try/except 包裹 get_nowait()
```python
if q.full():
    try:
        q.get_nowait()
    except asyncio.QueueEmpty:
        pass
q.put_nowait(event)
```
**Warning signs:** 不太可能在当前单线程场景触发，但防御性编程避免未来问题

### Pitfall 5: websockets 16 import 路径错误
**What goes wrong:** 使用旧版 `from websockets.server import serve` 导入失败
**Why it happens:** websockets 14+ 重构了 API，所有 asyncio server API 移到 `websockets.asyncio.server`
**How to avoid:** 使用 `from websockets.asyncio.server import serve, broadcast, ServerConnection`
**Warning signs:** ImportError 或 ModuleNotFoundError

### Pitfall 6: WebSocket 控制命令阻塞事件推送
**What goes wrong:** handler 中 await recv() 等待命令时，无法同时 push 事件
**Why it happens:** 单任务处理双向通信 — recv 阻塞时无法 send
**How to avoid:** 双任务模式 — recv_task 和 push_task 并行运行，asyncio.wait() 管理生命周期
**Warning signs:** 前端连接后只收到初始事件，之后停止接收

## Code Examples

### EventBus 完整实现（含类型标注）

```python
# event_bus.py
from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)

class EventBus:
    """asyncio.Queue pub-sub 事件总线。

    所有事件广播到所有订阅者。有界队列 + 丢弃最旧策略。
    """

    def __init__(self, maxsize: int = 1000) -> None:
        self._subscribers: set[asyncio.Queue[dict[str, Any]]] = set()
        self._lock = asyncio.Lock()
        self._maxsize = maxsize

    async def subscribe(self) -> asyncio.Queue[dict[str, Any]]:
        async with self._lock:
            q: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=self._maxsize)
            self._subscribers.add(q)
            return q

    async def unsubscribe(self, q: asyncio.Queue[dict[str, Any]]) -> None:
        async with self._lock:
            self._subscribers.discard(q)

    async def publish(self, event: dict[str, Any]) -> None:
        async with self._lock:
            snapshot = list(self._subscribers)
        for q in snapshot:
            if q.full():
                try:
                    q.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            q.put_nowait(event)

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)
```

### VizEvent 模型

```python
# viz_event.py
from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel

VizEventType = Literal[
    "idle", "thinking", "tool_call", "done", "error", "shutdown"
]

class VizEvent(BaseModel):
    """前端可视化事件模型。[CITED: 09-CONTEXT.md D-04, D-05, D-06]"""
    type: VizEventType
    agent: str
    payload: dict[str, Any]
    timestamp: float
```

### AgentRunner 包装器

```python
# agent_runner.py — 核心映射逻辑
import time
from typing import AsyncGenerator

from agent_framework.agents.agent_loop import LoopEvent
from agent_framework.viz.event_bus import EventBus
from agent_framework.viz.viz_event import VizEvent


class AgentRunner:
    """1:1 包装 AgentLoop，将 LoopEvent 映射为 VizEvent 并广播。[CITED: D-08]"""

    def __init__(self, agent_name: str, bus: EventBus) -> None:
        self._agent_name = agent_name
        self._bus = bus

    async def wrap(
        self, loop_gen: AsyncGenerator[LoopEvent, None]
    ) -> AsyncGenerator[LoopEvent, None]:
        """包装 AgentLoop.run() — 映射 + 广播 + 透传。[CITED: D-07, EVNT-07]"""
        await self._publish("idle", {})

        try:
            async for event in loop_gen:
                viz = self._map(event)
                if viz is not None:
                    await self._bus.publish(viz.model_dump())
                yield event  # 始终透传原始事件
        except Exception as exc:
            await self._publish("error", {"error": str(exc)})
            raise
        finally:
            await self._publish("shutdown", {})

    def _map(self, event: LoopEvent) -> VizEvent | None:
        now = time.time()
        name = self._agent_name
        step = event.step

        if event.type == "step":
            sr = event.data.get("stop_reason", "")
            if sr == "tool_use":
                return VizEvent(type="thinking", agent=name,
                                payload={"step": step}, timestamp=now)
            if sr in ("end_turn", "stop_sequence"):
                return VizEvent(type="done", agent=name,
                                payload={"step": step, **event.data}, timestamp=now)

        elif event.type == "tool_result":
            return VizEvent(type="tool_call", agent=name,
                            payload={"step": step, **event.data}, timestamp=now)

        elif event.type == "done":
            return VizEvent(type="done", agent=name,
                            payload={"step": step, **event.data}, timestamp=now)

        elif event.type in ("error", "max_steps"):
            return VizEvent(type="error", agent=name,
                            payload={"step": step, **event.data}, timestamp=now)

        return None

    async def _publish(self, viz_type: str, payload: dict) -> None:
        await self._bus.publish(VizEvent(
            type=viz_type, agent=self._agent_name,
            payload=payload, timestamp=time.time(),
        ).model_dump())
```

### WebSocket Server 控制命令处理

```python
# ws_server.py — 命令协议示例
import json
from typing import Any

async def _handle_command(
    cmd: dict[str, Any], websocket: ServerConnection, bus: EventBus
) -> None:
    """处理客户端控制命令。[CITED: D-11, D-12, D-13]"""
    cmd_type = cmd.get("type")

    if cmd_type == "start_team":
        agent_cfg = cmd.get("agent", {})
        name = agent_cfg.get("name", "agent")
        # 创建 AgentRunner + AgentLoop + asyncio.create_task(...)
        response = {"type": "command_response", "success": True}
        await websocket.send(json.dumps(response))

    elif cmd_type == "stop_team":
        name = cmd.get("name", "")
        # 停止指定 agent runner
        response = {"type": "command_response", "success": True}
        await websocket.send(json.dumps(response))

    else:
        response = {
            "type": "command_response",
            "success": False,
            "error": f"Unknown command: {cmd_type}",
        }
        await websocket.send(json.dumps(response))
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `from websockets.server import serve` | `from websockets.asyncio.server import serve` | websockets 14.0 (2024) | import 路径变更，API 相似 |
| `websockets.broadcast(ws_set, msg)` | `websockets.asyncio.server.broadcast(connections, msg)` | websockets 14.0 | broadcast 函数移到 asyncio.server 模块 |
| `Server` 作为 context manager 返回 | `serve()` 返回 `Server`，支持 `serve_forever()` | websockets 14.0 | 更灵活的服务生命周期管理 |
| `ServerConnection` 替代旧 `WebSocketServerProtocol` | 新 `ServerConnection` 类 | websockets 14.0 | 类型标注更清晰，API 更一致 |

**Deprecated/outdated:**
- `websockets.legacy.server`: 已移除，使用 `websockets.asyncio.server`
- `websockets.server` (旧路径): 已废弃，使用 `websockets.asyncio.server`

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | websockets 16.0 broadcast() 函数可独立使用，不需要 Server 实例引用 | Architecture Patterns | 需要改用 per-queue 推送模式 |
| A2 | asyncio 单线程下 Queue.full() + get_nowait() 无竞态 | Common Pitfalls | 理论上无风险，但防御性编码已覆盖 |
| A3 | timestamp 用 float (time.time()) 而非 datetime | Pattern 2 | 前端需要调整时间解析逻辑 |
| A4 | AgentRunner.wrap() 正常结束时发布 shutdown，异常时在 except 中发布 error + finally 中发布 shutdown | Pattern 3 | 可能发布重复的 shutdown 事件，需在实现中处理幂等 |
| A5 | websockets 需要添加到 framework/pyproject.toml dependencies（当前不在依赖列表中） | Standard Stack | 安装会失败，需要 planner 添加安装步骤 |
| A6 | WebSocket 服务端端口选择（默认值如 8765）留给实现时决定 | Architecture | 与前端 WebSocket 连接配置需要协调 |

## Open Questions

1. **websockets 依赖添加位置**
   - What we know: websockets 16.0 已安装但不在 framework/pyproject.toml
   - What's unclear: 是否需要也添加到 backend/pyproject.toml（如果 backend 有独立依赖）
   - Recommendation: planner 添加到 framework/pyproject.toml 的 dependencies 列表

2. **WebSocket 服务端口配置**
   - What we know: serve() 接受 host 和 port 参数
   - What's unclear: 默认端口选择、是否需要与 FastAPI 端口分开
   - Recommendation: 使用 8765 作为默认 WebSocket 端口，配置化

3. **start_team 控制命令的 AgentLoop 依赖注入**
   - What we know: AgentLoop.__init__() 需要 adapter, model, router, ctx
   - What's unclear: 这些依赖从哪里传入 WsServer — 是否需要全局 registry 或构造时注入
   - Recommendation: WsServer 构造时接受 adapter/router/ctx 等依赖，存储为实例属性

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11+ | asyncio, type hints | Yes | 3.14 | -- |
| websockets | WsServer | Yes | 16.0 | -- |
| pydantic | VizEvent model | Yes | 2.12.5 | -- |
| pytest | Tests | Yes | 8.x | -- |
| pytest-asyncio | Async tests | Yes | 1.3.0 | -- |

**Missing dependencies with no fallback:**
- websockets 需要添加到 framework/pyproject.toml（已安装但未声明）

**Missing dependencies with fallback:**
- None

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 1.3.0 |
| Config file | framework/pyproject.toml [tool.pytest.ini_options] |
| Quick run command | `cd framework && pytest tests/test_event_bus.py tests/test_viz_event.py tests/test_agent_runner.py -v` |
| Full suite command | `cd framework && pytest tests/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EVNT-01 | EventBus publish/subscribe | unit | `pytest tests/test_event_bus.py::test_publish_broadcasts_to_subscribers -v` | Wave 0 |
| EVNT-02 | subscribe returns Queue for async consumption | unit | `pytest tests/test_event_bus.py::test_subscribe_returns_queue -v` | Wave 0 |
| EVNT-03 | unsubscribe cleans up Queue | unit | `pytest tests/test_event_bus.py::test_unsubscribe_removes_queue -v` | Wave 0 |
| EVNT-04 | VizEvent model serialization | unit | `pytest tests/test_viz_event.py::test_viz_event_json_serialization -v` | Wave 0 |
| EVNT-05 | AgentRunner maps + broadcasts | unit | `pytest tests/test_agent_runner.py::test_maps_loop_event_to_viz_event -v` | Wave 0 |
| EVNT-06 | Event mapping coverage | unit | `pytest tests/test_agent_runner.py::test_mapping_all_types -v` | Wave 0 |
| EVNT-07 | AgentRunner yields original events | unit | `pytest tests/test_agent_runner.py::test_yields_original_events -v` | Wave 0 |
| WSRV-01 | WsServer subscribes and pushes | integration | `pytest tests/test_ws_server.py::test_pushes_events_to_client -v` | Wave 0 |
| WSRV-02 | Disconnect unsubscribes | integration | `pytest tests/test_ws_server.py::test_disconnect_unsubscribes -v` | Wave 0 |
| WSRV-03 | start_team command | integration | `pytest tests/test_ws_server.py::test_start_team_command -v` | Wave 0 |
| WSRV-04 | stop_team command | integration | `pytest tests/test_ws_server.py::test_stop_team_command -v` | Wave 0 |
| WSRV-05 | ping/pong heartbeat | integration | `pytest tests/test_ws_server.py::test_heartbeat -v` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd framework && pytest tests/test_event_bus.py tests/test_viz_event.py tests/test_agent_runner.py -v`
- **Per wave merge:** `cd framework && pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `framework/tests/test_event_bus.py` — covers EVNT-01, EVNT-02, EVNT-03
- [ ] `framework/tests/test_viz_event.py` — covers EVNT-04
- [ ] `framework/tests/test_agent_runner.py` — covers EVNT-05, EVNT-06, EVNT-07
- [ ] `framework/tests/test_ws_server.py` — covers WSRV-01 through WSRV-05
- [ ] Framework dependency: add `websockets>=14.0` to framework/pyproject.toml

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | MVP 阶段无认证需求 |
| V3 Session Management | no | WebSocket 连接无状态 |
| V4 Access Control | no | 单用户本地开发场景 |
| V5 Input Validation | yes | WebSocket 控制命令 JSON 解析需要 try/except |
| V6 Cryptography | no | 本地开发 ws:// 无需 TLS |

### Known Threat Patterns for asyncio + WebSocket Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Malformed JSON in control commands | Tampering | try/except json.JSONDecodeError, respond with command_response error |
| Unbounded queue memory growth | Denial of Service | Bounded Queue maxsize=1000 + drop-oldest |
| Slow WebSocket client blocking EventBus | Denial of Service | websockets ping_interval/ping_timeout 断开慢客户端 |
| WebSocket connection leak | Denial of Service | try/finally unsubscribe + websockets keepalive |

## Sources

### Primary (HIGH confidence)
- websockets 16.0 official docs — serve(), broadcast(), ServerConnection API: https://websockets.readthedocs.io/en/stable/reference/asyncio/server.html [VERIFIED: installed and import-tested]
- websockets broadcast guide: https://websockets.readthedocs.io/en/stable/topics/broadcast.html [VERIFIED: docs fetched and patterns confirmed]
- Python asyncio.Queue docs: https://docs.python.org/3/library/asyncio-queue.html [CITED]
- Project source: framework/agent_framework/agents/agent_loop.py — LoopEvent, run() async generator [VERIFIED: file read]
- Project source: framework/agent_framework/teams/manager.py — asyncio.Queue pub-sub pattern reference [VERIFIED: file read]

### Secondary (MEDIUM confidence)
- Project pyproject.toml — dependency declarations [VERIFIED: file read]
- Project tests/test_teams_manager.py — test patterns and conventions [VERIFIED: file read]

### Tertiary (LOW confidence)
- None — all findings verified from primary sources

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages verified installed and importable
- Architecture: HIGH — patterns based on official docs and existing project conventions
- Pitfalls: HIGH — based on asyncio/websockets known behaviors and project-specific integration points

**Research date:** 2026-05-29
**Valid until:** 2026-06-29 (stable domain — asyncio/websockets APIs change slowly)
