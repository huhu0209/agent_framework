# Phase 17: Framework 逻辑与架构修复 - Context

**Gathered:** 2026-06-10
**Status:** Ready for planning

<domain>
## Phase Boundary

修复 v0.0.4 审查中发现的 10 个 framework 逻辑/架构问题（FW-LOGIC-01~10）：ASK 权限决策不触发 HITL、_CRITICAL_TOOLS 始终为空、AgentLoop/ToolRouter 复杂度过高、search_tools 模块级全局可变状态、ToolValidator 缺 enum/unknown 验证、ToolUseContext.extra 无类型、_dispatch_agent 硬编码存根、MCP ToolSpec 无 handler。

修复范围仅限 framework/agent_framework/，不涉及 backend/ 或 frontend/。

</domain>

<decisions>
## Implementation Decisions

### ASK/HITL 交互机制（FW-LOGIC-01）
- **D-01:** 真正连接 HITLManager — 将 HITLManager 注入 ToolRouter，ASK 决策时调用 create_pending() 挂起协程等待外部 resolve()。不再返回 error，而是实现完整的用户确认流程
- **D-02:** resolve 来源由 Claude 自行决定 — 用户委托 Claude 选择最合适的 HITL resolve 机制（回调注入、事件驱动等）。建议参考回调注入模式（与 Phase 16 一致的解耦风格），但不强制

### 复杂度降低策略（FW-LOGIC-03, 04, 09）
- **D-03:** 纯方法提取 — 不做管道/中间件重构，只将长方法拆分为更小的私有方法。最安全、可预测、测试改动小
- **D-04:** 严格达成 C901 目标 — AgentLoop.run < 20、ToolRouter.dispatch < 10。方法提取后可能需要多次拆分迭代，但目标数值是硬性要求

### 配置机制与存根处理（FW-LOGIC-02, 08）
- **D-05:** _CRITICAL_TOOLS 改为构造参数注入 — PermissionPipeline.__init__ 接受 critical_tools 参数，默认空集合。调用方（AgentLoop）通过配置注入。消除模块级全局状态，可测试
- **D-06:** 移除 _dispatch_agent 存根和 agent__ 路由 — agent__ 前缀从未被注册/使用，SubAgent 已通过内置工具路径（run_subagent）工作。移除死代码，同时降低 dispatch 复杂度（FW-LOGIC-04 也受益）

### extra 结构化与验证增强（FW-LOGIC-05, 06, 07, 10）
- **D-07:** ToolUseContext.extra 用 TypedDict 标注 — 定义 ToolContextExtra(TypedDict) 标注已知键和值类型。向后兼容（仍是 dict），有类型提示，无运行时开销。下游代码 .get() 不变
- **D-08:** ToolValidator 只添加 enum + unknown 参数验证 — 只加 enum 约束验证和 unknown 参数报错。其他 JSON Schema 关键字（minimum/maximum/pattern 等）留后续
- **D-09:** search_tools 改为类实例封装 — 将 _semaphore 和 _client 封装到 SearchClient 类中，ToolRegistry 注册类实例方法。消除模块级可变状态，可测试（mock 实例）
- **D-10:** MCP ToolSpec handler — 文档化 schema-only 设计 — 在 ToolSpec 或 _register_tools 中添加注释说明 MCP ToolSpec 是 schema-only 定义，handler 通过 mcp__ 前缀路由机制处理。零代码改动

### 验证策略
- **D-11:** 全量 pytest 验证 — 每个 plan 完成后运行 `cd framework && pytest tests/ -v` 确认 964+ 测试通过
- **D-12:** ruff 复杂度扫描 — `ruff check --select C901 framework/` 确认 AgentLoop.run < 20、ToolRouter.dispatch < 10

### Claude's Discretion
- HITL resolve 的具体实现方式（回调注入 vs 事件驱动）
- HITLManager 注入 ToolRouter 的具体方式（构造参数、set 方法等）
- AgentLoop.run / ToolRouter.dispatch 方法提取的具体拆分方式
- TypedDict 的具体字段定义和命名
- SearchClient 类的具体 API 设计
- 每个 plan 内部的修复顺序

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 审查报告（问题来源）
- `docs/reviews/REVIEW-FRAMEWORK.md` — 全部 FRMW-LOGIC issue 详情（含文件位置、影响分析、修复建议）
  - FRMW-LOGIC-01 (ASK 返回 error, HIGH)
  - FRMW-LOGIC-02 (_CRITICAL_TOOLS 为空, HIGH)
  - FRMW-LOGIC-03 (AgentLoop.run C901=30, MEDIUM)
  - FRMW-LOGIC-04 (dispatch C901=18, MEDIUM)
  - FRMW-LOGIC-05 (search_tools 全局状态, MEDIUM)
  - FRMW-LOGIC-06 (ToolValidator 缺验证, MEDIUM)
  - FRMW-LOGIC-07 (extra 无类型, MEDIUM)
  - FRMW-LOGIC-08 (_dispatch_agent 存根, MEDIUM)
  - FRMW-LOGIC-09 (_apply_changes 复杂度, MEDIUM)
  - FRMW-LOGIC-10 (MCP ToolSpec 无 handler, LOW)

### 需求定义
- `.planning/REQUIREMENTS.md` — FW-LOGIC-01~10 需求定义
- `.planning/ROADMAP.md` — Phase 17 目标、成功标准、范围定义

### 编码规范
- `.planning/codebase/CONVENTIONS.md` — Import 组织、TYPE_CHECKING guard、logging 模式
- `.planning/codebase/ARCHITECTURE.md` — 架构层次、数据流、关键抽象（含 Tool Dispatch Pipeline 流程图）

### 已知问题
- `.planning/codebase/CONCERNS.md` — 逻辑问题详情（_CRITICAL_TOOLS、Agent dispatch stub、Permission ASK 等）

### 框架源码（修改目标）
- `framework/agent_framework/tools/router.py` — ASK/HITL 修复（FW-LOGIC-01）、dispatch 复杂度拆分（FW-LOGIC-04）、移除 _dispatch_agent 存根（FW-LOGIC-08）
- `framework/agent_framework/agents/agent_loop.py` — AgentLoop.run 复杂度拆分（FW-LOGIC-03）
- `framework/agent_framework/safety/permissions.py` — _CRITICAL_TOOLS 改为构造参数（FW-LOGIC-02）
- `framework/agent_framework/safety/hitl.py` — HITLManager 连接到 ToolRouter
- `framework/agent_framework/tools/validator.py` — 添加 enum + unknown 参数验证（FW-LOGIC-06）
- `framework/agent_framework/tools/types.py` — ToolUseContext.extra TypedDict 标注（FW-LOGIC-07）
- `framework/agent_framework/tools/builtin/search_tools.py` — 类实例封装（FW-LOGIC-05）
- `framework/agent_framework/tools/mcp/config.py` — MCP ToolSpec schema-only 文档化（FW-LOGIC-10）
- `framework/agent_framework/tasks/manager.py` — _apply_changes 复杂度降低（FW-LOGIC-09）

### Phase 16 上下文（前置依赖）
- `.planning/phases/16-framework/16-CONTEXT.md` — 安全修复已完成，Phase 17 依赖已满足

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `framework/agent_framework/safety/hitl.py` — 完整的 HITLManager 实现（create_pending/resolve Future-based 机制），可直接连接到 ToolRouter
- `framework/agent_framework/agents/sub_agent.py` — SubAgent 系统已通过内置工具路径工作，证明 agent__ 前缀路由是冗余的
- logging 模式 — 所有模块使用 `logger = logging.getLogger(__name__)`，新增方法可直接复用
- Phase 16 的 aiofiles — memory/ 已全部 async，本次不需要再处理同步 I/O

### Established Patterns
- 构造参数注入 — Phase 16 已将 MCP env 改为白名单注入，PermissionPipeline.critical_tools 采用相同模式
- TypedDict 用于类型标注 — Python 3.11+ 内置支持，框架其他位置可用
- 类实例封装 — ToolSpec 本身就是类实例模式，SearchClient 遵循相同风格
- Pydantic BaseModel 用于配置 — ToolUseContext 是 Pydantic model，TypedDict extra 字段可以嵌套

### Integration Points
- HITLManager 注入 ToolRouter 后，AgentLoop 需要在创建 ToolRouter 时传入 HITLManager 实例
- PermissionPipeline 构造参数变更后，ToolRouter 和 AgentLoop 的初始化链需相应更新
- search_tools 改为类实例后，tool 注册方式需调整（从模块函数改为实例方法）
- _dispatch_agent 移除后，router.py 的 agent__ 前缀路由分支一并移除
- extra TypedDict 标注不影响运行时行为（仍兼容 dict），但 IDE 和类型检查器将受益

</code_context>

<specifics>
## Specific Ideas

- HITLManager 注入建议采用 ToolRouter 构造参数方式（与 registry、mcp_manager、hook_manager 一致）
- TypedDict 已知键：skill_registry、memory_dir、memory_store、planning_session、worker_manager
- AgentLoop.run 的 6 大职责区域（通知排水、context compaction、LLM 调用、工具调度、计划检查、收尾）可作为方法提取的自然分界线
- dispatch 的 4 层职责（权限、pre-hooks、执行+降级、post-hooks）也可作为方法提取的分界线
- _CRITICAL_TOOLS 默认为空集合，向后兼容。应用层可在创建 PermissionPipeline 时注入 {"rm", "execute_code"} 等
- 移除 agent__ 路由后，dispatch 复杂度约降低 3-4 点（去除 if/elif 分支和 try/except 块）

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 17-Framework 逻辑与架构修复*
*Context gathered: 2026-06-10*
