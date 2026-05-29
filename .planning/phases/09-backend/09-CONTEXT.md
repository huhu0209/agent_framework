# Phase 9: Backend 事件系统 - Context

**Gathered:** 2026-05-29
**Status:** Ready for planning

<domain>
## Phase Boundary

EventBus pub-sub + VizEvent 数据模型 + AgentRunner 包装层 + WebSocket 实时推送。
将 AgentLoop 内部状态（thinking/tool_call/idle 等）通过事件链路暴露给前端。
MVP 阶段单个 AgentLoop 验证端到端链路，架构预留多 Agent 扩展。

</domain>

<decisions>
## Implementation Decisions

### EventBus 订阅模型
- **D-01:** subscribe() 返回 asyncio.Queue，消费方 await queue.get()，取消时 unsubscribe(queue)
- **D-02:** 单 topic 广播 — 所有事件广播到所有订阅者。topic 过滤留 v0.0.4+（EVNT-F01）
- **D-03:** 有界队列 + 丢弃最旧，maxsize=1000 作为安全网。可视化可靠性优先级低于 agent 执行，AgentLoop 不能被展示层节流

### VizEvent 数据模型
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

### AgentRunner 与 Team 关系
- **D-08:** AgentRunner 1:1 包装单个 AgentLoop。start_team 时创建多个 AgentRunner
- **D-09:** start_team 通过 asyncio.create_task 异步执行 AgentRunner，不阻塞 WebSocket 处理循环
- **D-10:** 新模块 framework/agent_framework/viz/ — 包含 event_bus.py, viz_event.py, agent_runner.py, ws_server.py

### WebSocket 消息协议
- **D-11:** 双向 JSON 文本帧通信，不用 subprotocol
- **D-12:** 客户端控制命令内联 Agent 配置 — {"type": "start_team", "agent": {"name": "cat", "role": "helper", "system_prompt": "..."}}
- **D-13:** 控制命令响应走独立通道 — {"type": "command_response", "success": bool, "error": "..."}，与 VizEvent 事件流分离
- **D-14:** WebSocket 服务端放在 framework/agent_framework/viz/ws_server.py，使用 websockets 库

### Claude's Discretion
- EventBus 内部并发安全（asyncio.Lock 使用）
- VizEvent payload 各 type 的具体字段定义
- AgentRunner 异常处理和清理逻辑
- WebSocket 心跳超时和重连参数

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 事件模型基础
- `framework/agent_framework/agents/base.py` — AgentEvent 基类（type/step/data）和 Agent ABC
- `framework/agent_framework/agents/agent_loop.py` — LoopEvent(AgentEvent) 定义，run() async generator 的事件类型（step/done/error/max_steps/tool_result）
- `framework/agent_framework/teams/types.py` — TeammateConfig, TeammateStatus, TeamNotification 类型

### Team 管理
- `framework/agent_framework/teams/manager.py` — TeamManager（spawn/shutdown/list_all/notifications 接口）
- `framework/agent_framework/teams/bus.py` — MessageBus JSONL 通信模式

### 需求追踪
- `.planning/REQUIREMENTS.md` — EVNT-01~07（EventBus）和 WSRV-01~05（WebSocket）需求定义
- `.planning/ROADMAP.md` — Phase 9 目标、成功标准、计划分解

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `AgentEvent` dataclass（agents/base.py）— 可参考其 type/step/data 结构设计 VizEvent，但 VizEvent 用 Pydantic
- `asyncio.Queue` 已被 TeamManager.notifications 使用（teams/manager.py）— 同样的 pub-sub 模式可参考
- `TeammateConfig` frozen dataclass（teams/types.py）— start_team 控制命令的 agent 配置可复用此结构
- `AgentLoop.run()` async generator（agents/agent_loop.py:243-408）— AgentRunner 的核心输入源

### Established Patterns
- 框架层代码放在 framework/agent_framework/ 下，应用层通过 pip install -e 引用
- 所有数据模型用 Pydantic v2（LLM types, MCP config, teams types 等）
- 异步操作用 asyncio 单线程事件循环，asyncio.Lock 保护共享状态
- 错误处理用 typed exceptions（LLMAdapterError 层次结构），工具错误用 ToolResult(is_error=True)

### Integration Points
- `AgentLoop.run()` yield LoopEvent — AgentRunner 消费此接口
- `TeamManager.spawn(config)` / `shutdown(name)` — start/stop_team 命令的底层调用
- `AgentLoop.__init__()` 需要 adapter, model, router, ctx — AgentRunner 创建 AgentLoop 需要这些依赖
- WebSocket 服务需要独立端口（与 FastAPI 并行运行，或由 backend 启动）

</code_context>

<specifics>
## Specific Ideas

- EventBus 有界队列实现模式：`if q.full(): q.get_nowait()` 丢弃最旧，`q.put_nowait(event)` 推入新事件。1000 上限正常运行时永远触不到
- WebSocket 消息分两类流：(1) VizEvent 事件流 — 服务端持续推送；(2) command_response — 控制命令的确认/错误响应
- MVP 场景单 Agent 短任务全程几十个事件，Queue 远不会满。安全网防的是消费端异常（如 WebSocket send buffer 满了）

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 9-Backend 事件系统*
*Context gathered: 2026-05-29*
