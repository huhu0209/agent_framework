# Phase 17: Framework 逻辑与架构修复 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-10
**Phase:** 17-Framework 逻辑与架构修复
**Areas discussed:** ASK/HITL 交互机制, 复杂度降低策略, 配置机制与存根处理, extra 结构化与验证增强

---

## ASK/HITL 交互机制

### Q1: ASK 权限决策如何处理？

| Option | Description | Selected |
|--------|-------------|----------|
| 真正连接 HITLManager | 将 HITLManager 注入 ToolRouter，ASK 决策时调用 create_pending() 挂起协程等待外部 resolve() | ✓ |
| 标记式处理 | ASK 返回 ToolResult 标记 needs_confirmation=True，由上层 AgentLoop 决定处理 | |
| 仅改善错误消息 | 将 ASK 视为 DENY，改善错误消息 | |

**User's choice:** 真正连接 HITLManager
**Notes:** HITLManager 已存在于 safety/hitl.py 但从未被连接到 dispatch 流程

### Q2: HITLManager 的 resolve 来源怎么设计？

| Option | Description | Selected |
|--------|-------------|----------|
| 回调注入模式 | HITLManager 持有外部可设置的 resolve 回调，灵活解耦 | |
| 事件驱动 | yield HitlRequestEvent，上层 AgentLoop 处理 | |
| 你决定 | Claude 自行选择最合适方案 | ✓ |

**User's choice:** Claude 自行决定
**Notes:** 建议采用回调注入模式（与 Phase 16 解耦风格一致）

---

## 复杂度降低策略

### Q3: 复杂度如何降低？

| Option | Description | Selected |
|--------|-------------|----------|
| 纯方法提取 | 拆分为更小私有方法，不改架构 | ✓ |
| 管道/中间件重构 | 改为管道模式，每阶段独立中间件 | |

**User's choice:** 纯方法提取
**Notes:** 最安全、可预测、测试改动小

### Q4: 复杂度目标是严格达成还是尽力而为？

| Option | Description | Selected |
|--------|-------------|----------|
| 目标达成 (<20/<10) | AgentLoop < 20、dispatch < 10，硬性要求 | ✓ |
| 尽力降低即可 | 明显降低就行，不强求具体数值 | |

**User's choice:** 目标达成 (<20/<10)

---

## 配置机制与存根处理

### Q5: _CRITICAL_TOOLS 注册机制如何设计？

| Option | Description | Selected |
|--------|-------------|----------|
| 构造参数注入 | PermissionPipeline.__init__ 接受 critical_tools 参数 | ✓ |
| 模块级注册函数 | 添加 register_critical_tool() 模块级函数 | |
| 你决定 | Claude 自行选择 | |

**User's choice:** 构造参数注入
**Notes:** 与 Phase 16 白名单注入模式一致，消除全局状态

### Q6: _dispatch_agent 存根如何处理？

| Option | Description | Selected |
|--------|-------------|----------|
| 移除存根和 agent__ 路由 | agent__ 前缀从未使用，SubAgent 已通过内置工具路径工作 | ✓ |
| 连接 SubAgent 实现 | 将 _dispatch_agent 连接到 SubAgent 系统 | |

**User's choice:** 移除存根和 agent__ 路由
**Notes:** 移除同时降低 dispatch 复杂度

---

## extra 结构化与验证增强

### Q7: ToolUseContext.extra 结构化程度？

| Option | Description | Selected |
|--------|-------------|----------|
| TypedDict 标注 | 定义 ToolContextExtra TypedDict，向后兼容 | ✓ |
| Pydantic Model 替换 | 定义 Pydantic BaseModel 替换 dict | |
| 保持 dict + 文档化 | 不改变类型，只文档化 | |

**User's choice:** TypedDict 标注
**Notes:** 已知键：skill_registry、memory_dir、memory_store、planning_session、worker_manager

### Q8: ToolValidator 验证增强范围？

| Option | Description | Selected |
|--------|-------------|----------|
| enum + unknown 参数 | 只添加 FW-LOGIC-06 明确要求的两项 | ✓ |
| 扩展 JSON Schema 验证 | 还添加 min/max、pattern 等常用约束 | |

**User's choice:** enum + unknown 参数

### Q9: search_tools 全局状态如何消除？

| Option | Description | Selected |
|--------|-------------|----------|
| 类实例封装 | 封装到 SearchClient 类，注册实例方法 | ✓ |
| 闭包/contextvars 替换 | 保留函数式 API 但用闭包替代 global | |

**User's choice:** 类实例封装

### Q10: MCP ToolSpec 无 handler 如何处理？

| Option | Description | Selected |
|--------|-------------|----------|
| 文档化 schema-only 设计 | 添加注释说明 MCP ToolSpec 是 schema-only，零代码改动 | ✓ |
| 添加实际 handler | 为 MCP ToolSpec 注册真正 handler，统一路由 | |

**User's choice:** 文档化 schema-only 设计

---

## Claude's Discretion

- HITL resolve 的具体实现方式（回调注入 vs 事件驱动）
- HITLManager 注入 ToolRouter 的具体方式
- AgentLoop.run / ToolRouter.dispatch 方法提取的具体拆分方式
- TypedDict 的具体字段定义和命名
- SearchClient 类的具体 API 设计
- 每个 plan 内部的修复顺序

## Deferred Ideas

None — discussion stayed within phase scope
