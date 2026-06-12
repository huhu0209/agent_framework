# Phase 9: Backend 事件系统 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-29
**Phase:** 09-Backend 事件系统
**Areas discussed:** EventBus 订阅模型, VizEvent payload 结构, AgentRunner 与 Team 关系, WebSocket 消息协议

---

## EventBus 订阅模型

### Q1: EventBus.subscribe() 返回什么？

| Option | Description | Selected |
|--------|-------------|----------|
| Queue 模式 (Recommended) | subscribe() 返回 asyncio.Queue，消费方 await queue.get()，取消时 unsubscribe(queue) | ✓ |
| Callback 模式 | subscribe(callback) 注册 async callback，EventBus 内部遍历调用 | |
| Subscription 对象 | subscribe() 返回 Subscription 对象，支持 async with 自动清理 | |

**User's choice:** Queue 模式
**Notes:** 与 TeamManager.notifications 模式一致，简单直观

### Q2: MVP 是否只做单 topic 广播？

| Option | Description | Selected |
|--------|-------------|----------|
| 单 topic 广播 (Recommended) | 所有事件广播到所有订阅者，topic 过滤留 v0.0.4+ | ✓ |
| 多 topic 预留 | subscribe(topic) 支持按 agent_name 订阅 | |

**User's choice:** 单 topic 广播

### Q3: asyncio.Queue 是否设置容量上限？

| Option | Description | Selected |
|--------|-------------|----------|
| 有界队列（丢弃） | Queue 满时丢弃最旧事件 | ✓ |
| 无界队列 | 不设置上限，理论上可无限增长 | |
| 有界队列（阻塞） | Queue 满时 await put() 阻塞 | |

**User's choice:** 有界队列 + 丢弃最旧，maxsize=1000 作为安全网
**Notes:** 用户给出了详细理由——无界队列在消费端变慢时默默堆积难发现；阻塞会拖慢 AgentLoop（业务核心不能被展示层节流）；有界+丢弃最旧丢的是可视化历史不影响 agent 正确性。正常运行时 1000 上限永远触不到，真触到说明消费端已挂。

---

## VizEvent payload 结构

### Q1: VizEvent 用 Pydantic model 还是 dataclass？

| Option | Description | Selected |
|--------|-------------|----------|
| Pydantic model (Recommended) | 自带 .model_dump() JSON 序列化，与框架其他模型一致 | ✓ |
| dataclass | 需要手动 to_dict()，与 AgentEvent/LoopEvent 风格一致 | |

**User's choice:** Pydantic model

### Q2: payload 是统一 dict 还是强类型 union？

| Option | Description | Selected |
|--------|-------------|----------|
| 松散 dict (Recommended) | payload: dict[str, Any]，按 type 文档约定 | ✓ |
| 强类型 union | Pydantic discriminated union，每种 type 有专属 payload 类型 | |

**User's choice:** 松散 dict

### Q3: VizEvent 的 event type 如何定义？

| Option | Description | Selected |
|--------|-------------|----------|
| 复用 LoopEvent 映射 | thinking / tool_call / tool_result / done / error / max_steps | |
| 前端视角重新定义 (Recommended) | idle / thinking / tool_call / done / error / shutdown | ✓ |

**User's choice:** 前端视角重新定义 — idle/thinking/tool_call/done/error/shutdown
**Notes:** 前端 Canvas 只需 idle/thinking/tool_call 三种状态帧，加上 done/error/shutdown 作为生命周期事件

---

## AgentRunner 与 Team 关系

### Q1: AgentRunner 包装什么？

| Option | Description | Selected |
|--------|-------------|----------|
| 1:1 AgentLoop (Recommended) | 每个 AgentLoop 一个 AgentRunner，start_team 时创建多个 | ✓ |
| 包装 TeamManager | AgentRunner 内部管理多个 AgentLoop 的事件 | |

**User's choice:** 1:1 AgentLoop

### Q2: start_team 如何运行 AgentRunner？

| Option | Description | Selected |
|--------|-------------|----------|
| asyncio.create_task (Recommended) | 异步执行，不阻塞 WebSocket 处理循环 | ✓ |
| await 同步执行 | 简单但阻塞 WebSocket | |

**User's choice:** asyncio.create_task

### Q3: EventBus/VizEvent/AgentRunner 放在哪？

| Option | Description | Selected |
|--------|-------------|----------|
| framework/viz/ (Recommended) | 新模块，框架层、可复用 | ✓ |
| framework/agents/ | 跟 AgentLoop 同级 | |
| backend/app/ | 仅应用层 | |

**User's choice:** framework/agent_framework/viz/

---

## WebSocket 消息协议

### Q1: WebSocket 消息格式？

| Option | Description | Selected |
|--------|-------------|----------|
| JSON 文本帧 (Recommended) | 双向 JSON 文本帧，不用 subprotocol | ✓ |
| JSON-RPC 2.0 | 正式但增加复杂度 | |

**User's choice:** JSON 文本帧

### Q2: 控制命令如何携带 Agent 配置？

| Option | Description | Selected |
|--------|-------------|----------|
| 内联配置 (Recommended) | WebSocket 内完成创建+启动，{"type": "start_team", "agent": {...}} | ✓ |
| REST 创建 + WS 控制 | 先 HTTP API 创建配置，WebSocket 只发控制命令 | |

**User's choice:** 内联配置

### Q3: 控制命令执行失败如何反馈？

| Option | Description | Selected |
|--------|-------------|----------|
| 推送 error 事件 | 错误融入 VizEvent 流，前端用同一 reducer | |
| 独立响应通道 | {"type": "command_response", "success": bool, "error": "..."} | ✓ |

**User's choice:** 独立响应通道
**Notes:** 命令确认/错误与事件流分离，前端 reducer 分别处理

### Q4: WebSocket 服务端放在哪？

| Option | Description | Selected |
|--------|-------------|----------|
| framework/viz/ (Recommended) | 框架层提供 WebSocket 服务 | ✓ |
| backend/app/ | 应用层处理 WebSocket | |

**User's choice:** framework/agent_framework/viz/ws_server.py

---

## Claude's Discretion

- EventBus 内部并发安全（asyncio.Lock）
- VizEvent payload 各 type 的具体字段定义
- AgentRunner 异常处理和清理逻辑
- WebSocket 心跳超时和重连参数

## Deferred Ideas

None — discussion stayed within phase scope
