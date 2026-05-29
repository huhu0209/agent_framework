# Requirements: Agent Framework v0.0.2

**Defined:** 2026-05-29
**Core Value:** 从单一 ReAct Agent 扩展为多类型 Agent 体系，新增编排引擎和 A2A 协议支持

## v0.0.2 Requirements

### Agent ABC

- [ ] **AGENT-01**: AgentEvent 统一事件模型（type, step, data dict），支持 step/tool_result/done/max_steps/error 五种类型
- [ ] **AGENT-02**: Agent 抽象基类定义 `run() -> AsyncGenerator[AgentEvent, None]`，不约束 init 签名
- [ ] **AGENT-03**: AgentLoop 实现 Agent 接口，LoopEvent 通过 AgentEvent 向后兼容（data dict 传递 plan 等扩展字段）
- [ ] **AGENT-04**: sub_agent.py、tasks/runner.py、teams/manager.py 类型标注更新为 Agent
- [ ] **AGENT-05**: 现有 687 测试全部通过，不破坏现有接口

### Plan-and-Solve Agent

- [ ] **PLAN-01**: PlanAndSolveAgent(Agent) 实现先规划后执行模式
- [ ] **PLAN-02**: 生成计划阶段调用 LLM 产出有序步骤列表，复用现有 PlanningState/parse_plan_response()
- [ ] **PLAN-03**: 每个步骤用独立 AgentLoop 实例执行，步骤间不累积 context
- [ ] **PLAN-04**: 偏离检测 + 重新规划，replan 硬上限 2 次
- [ ] **PLAN-05**: 空计划时 fallback 到直接 ReAct 执行

### Reflection Agent

- [ ] **REFL-01**: ReflectionAgent(Agent) 实现执行→反省→改进循环
- [ ] **REFL-02**: 反省阶段让 LLM 评估输出质量，结构化 verdict 判定是否满意
- [ ] **REFL-03**: 改进轮次硬上限 2 次，不让 LLM 自行决定是否继续
- [ ] **REFL-04**: 不满意时将 critique 注入下一轮用户消息

### OrchestratorEngine

- [ ] **ORCH-01**: OrchestratorEngine 实现复杂度评估→Agent 选择→执行→纠偏重规划的完整流水线
- [ ] **ORCH-02**: 复杂度评估使用启发式规则（不做额外 LLM 调用）
- [ ] **ORCH-03**: 简单任务直接路由到 AgentLoop，复杂任务生成计划后执行
- [ ] **ORCH-04**: 执行偏离时触发计划修正，每条 Agent 链最多 3 个 Agent
- [ ] **ORCH-05**: agent_factory 模式，每次步骤创建新 Agent 实例

### Agent 配置化

- [ ] **CONF-01**: AgentConfig dataclass 从 .md 文件解析 Agent 定义（name, description, system_prompt, tools, model, max_steps）
- [ ] **CONF-02**: load_agent_configs() 扫描目录解析所有 .md 文件，复用 parse_frontmatter_lines 模式
- [ ] **CONF-03**: agent_from_config() 从 AgentConfig 创建 AgentLoop 实例，含工具过滤
- [ ] **CONF-04**: 加载时验证 system_prompt 安全性（防注入）

### 真实搜索

- [ ] **SRCH-01**: search_tools.py handler 内部从 mock 改为 Tavily AsyncTavilyClient HTTP 调用
- [ ] **SRCH-02**: 异步并发控制（asyncio.Semaphore 防止 rate limit）
- [ ] **SRCH-03**: API key 通过环境变量管理（SecretStr 模式）

### A2A 协议

- [ ] **A2A-01**: AgentCard 数据模型（name, description, url, version, capabilities）
- [ ] **A2A-02**: A2ATask/A2AMessage/A2ATaskStatus 数据模型（独立于内部 PlanningState）
- [ ] **A2A-03**: A2AClient 实现远程 Agent 任务提交（send_task）+ 状态轮询（get_task）+ 取消（cancel_task）
- [ ] **A2A-04**: A2AServer 暴露本地 Agent 为 HTTP 端点（AgentCard 发现 + 任务创建 + 状态查询）
- [ ] **A2A-05**: 同步模式（POST + 轮询），Phase 8 不做流式和异步
- [ ] **A2A-06**: API-key 认证机制

## Future Requirements (v0.0.3+)

### A2A 扩展

- **A2A-F01**: A2A 流式模式（SSE streaming）
- **A2A-F02**: A2A 异步模式（Webhook callback）
- **A2A-F03**: A2A 多 Agent 联邦（multi-agent federation）

### 高级编排

- **ORCH-F01**: DAG 调度模式（LLMCompiler / ReWOO）
- **ORCH-F02**: LLM 动态路由（基于任务语义选择 Agent 类型）

## Out of Scope

| Feature | Reason |
|---------|--------|
| LangGraph / CrewAI / AutoGen 集成 | 竞争架构，与现有 Tool System 冲突 |
| Backend API 功能开发 | 脚手架阶段，非本 milestone 范围 |
| Frontend 功能开发 | 脚手架阶段，非本 milestone 范围 |
| pyyaml 依赖 | flat frontmatter 足够，无需引入 |
| SSE / WebSocket 传输 | Phase 8 只做同步 HTTP |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| AGENT-01 | Phase 6 | Pending |
| AGENT-02 | Phase 6 | Pending |
| AGENT-03 | Phase 6 | Pending |
| AGENT-04 | Phase 6 | Pending |
| AGENT-05 | Phase 6 | Pending |
| PLAN-01 | Phase 6 | Pending |
| PLAN-02 | Phase 6 | Pending |
| PLAN-03 | Phase 6 | Pending |
| PLAN-04 | Phase 6 | Pending |
| PLAN-05 | Phase 6 | Pending |
| REFL-01 | Phase 6 | Pending |
| REFL-02 | Phase 6 | Pending |
| REFL-03 | Phase 6 | Pending |
| REFL-04 | Phase 6 | Pending |
| ORCH-01 | Phase 7 | Pending |
| ORCH-02 | Phase 7 | Pending |
| ORCH-03 | Phase 7 | Pending |
| ORCH-04 | Phase 7 | Pending |
| ORCH-05 | Phase 7 | Pending |
| CONF-01 | Phase 7 | Pending |
| CONF-02 | Phase 7 | Pending |
| CONF-03 | Phase 7 | Pending |
| CONF-04 | Phase 7 | Pending |
| SRCH-01 | Phase 7 | Pending |
| SRCH-02 | Phase 7 | Pending |
| SRCH-03 | Phase 7 | Pending |
| A2A-01 | Phase 8 | Pending |
| A2A-02 | Phase 8 | Pending |
| A2A-03 | Phase 8 | Pending |
| A2A-04 | Phase 8 | Pending |
| A2A-05 | Phase 8 | Pending |
| A2A-06 | Phase 8 | Pending |

**Coverage:**
- v0.0.2 requirements: 32 total
- Mapped to phases: 32
- Unmapped: 0 ✓

---
*Requirements defined: 2026-05-29*
*Last updated: 2026-05-29 after v0.0.2 milestone start*
