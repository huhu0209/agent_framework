# Roadmap: Agent Framework

## Milestones

- ✅ **v0.0.1 彻底 Code Review** — Phases 1-5 (shipped 2026-05-29)
- 🚧 **v0.0.2 Agent 扩展与编排** — Phases 6-8 (in progress)

## Phases

<details>
<summary>✅ v0.0.1 彻底 Code Review (Phases 1-5) — SHIPPED 2026-05-29</summary>

- [x] Phase 1: Bug 修复审查 (3/3 plans) — completed
- [x] Phase 2: 安全审查与修复 (2/2 plans) — completed
- [x] Phase 3: 架构与代码质量审查 (2/2 plans) — completed
- [x] Phase 4: 性能与数据安全审查 (1/1 plan) — completed
- [x] Phase 5: 测试覆盖补充 (4/4 plans) — completed

</details>

### 🚧 v0.0.2 Agent 扩展与编排 (In Progress)

**Milestone Goal:** 从单一 ReAct Agent 扩展为多类型 Agent 体系，新增编排引擎和 A2A 协议支持

- [x] **Phase 6: Agent 类型扩展** — Agent ABC 抽象 + Plan-and-Solve + Reflection 三种 Agent (completed 2026-05-29)
- [x] **Phase 7: 编排引擎 + 配置化 + 搜索** — OrchestratorEngine + Agent 配置化 + 真实搜索 (completed 2026-05-29)
- [ ] **Phase 8: A2A 协议** — AgentCard + Client/Server 同步模式 + API-key 认证

## Phase Details

### Phase 6: Agent 类型扩展
**Goal**: 框架支持多种 Agent 类型，每种通过统一的 Agent 接口暴露，且现有 687 测试全部通过
**Depends on**: Phase 5 (v0.0.1 baseline)
**Requirements**: AGENT-01, AGENT-02, AGENT-03, AGENT-04, AGENT-05, PLAN-01, PLAN-02, PLAN-03, PLAN-04, PLAN-05, REFL-01, REFL-02, REFL-03, REFL-04
**Success Criteria** (what must be TRUE):
  1. AgentEvent 统一事件模型可用，支持 step/tool_result/done/max_steps/error 五种类型
  2. AgentLoop 实现了 Agent 接口，现有 687 测试全部通过（零回归）
  3. PlanAndSolveAgent 可以接收任务、生成计划、逐步执行，偏离时重新规划（最多 2 次），空计划时 fallback 到 ReAct
  4. ReflectionAgent 可以执行任务、自我评估输出质量、改进不满意的结果（最多 2 轮）
  5. 所有新增 Agent 类型通过各自的测试套件验证
**Plans:** 3/3 plans complete

Plans:
- [x] 06-01: Agent ABC + AgentEvent 基础设施（AGENT-01~05）
- [x] 06-02: Plan-and-Solve Agent（PLAN-01~05）
- [x] 06-03: Reflection Agent（REFL-01~04）

### Phase 7: 编排引擎 + 配置化 + 搜索
**Goal**: 框架具备 Agent 编排能力、声明式配置能力和真实搜索能力
**Depends on**: Phase 6
**Requirements**: ORCH-01, ORCH-02, ORCH-03, ORCH-04, ORCH-05, CONF-01, CONF-02, CONF-03, CONF-04, SRCH-01, SRCH-02, SRCH-03
**Success Criteria** (what must be TRUE):
  1. OrchestratorEngine 可以评估任务复杂度（启发式规则，无额外 LLM 调用），将简单任务路由到 ReAct、复杂任务路由到 Plan-and-Solve
  2. 执行偏离时触发计划修正，每条 Agent 链最多 3 个 Agent
  3. Agent 配置可以通过 .md 文件声明式定义，agent_from_config() 能创建完整可运行的 Agent 实例
  4. 搜索工具调用 Tavily API 返回真实结果，并发受 Semaphore 控制，API key 通过环境变量管理
  5. agent_factory 模式允许编排引擎按需创建新 Agent 实例
**Plans:** 3/1 plans complete

Plans:
- [x] 07-01: OrchestratorEngine 编排引擎（ORCH-01~05）
- [x] 07-02: Agent 配置化（CONF-01~04）
- [x] 07-03: 真实搜索工具（SRCH-01~03）

### Phase 8: A2A 协议
**Goal**: 框架支持 A2A 协议，本地 Agent 可暴露为 HTTP 端点，远程 Agent 可作为工具调用
**Depends on**: Phase 6
**Requirements**: A2A-01, A2A-02, A2A-03, A2A-04, A2A-05, A2A-06
**Success Criteria** (what must be TRUE):
  1. AgentCard 数据模型可描述 Agent 的能力（name, description, url, version, capabilities）
  2. A2AServer 可将本地 Agent 暴露为 HTTP 端点，支持 AgentCard 发现、任务创建和状态查询
  3. A2AClient 可向远程 Agent 提交任务、轮询状态、取消任务
  4. 同步模式（POST + 轮询）完整可用，不做流式和异步
  5. 所有 A2A 通信受 API-key 认证保护
**Plans:** 3 plans

Plans:
- [ ] 08-01: A2A 数据模型 + AgentCard（A2A-01, A2A-02）
- [ ] 08-02: A2AServer + A2AClient 实现（A2A-03, A2A-04, A2A-05）
- [ ] 08-03: API-key 认证（A2A-06）

## Progress

**Execution Order:**
Phases execute in numeric order: 6 → 7 → 8

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Bug 修复审查 | v0.0.1 | 3/3 | Complete | 2026-05-28 |
| 2. 安全审查与修复 | v0.0.1 | 2/2 | Complete | 2026-05-28 |
| 3. 架构与代码质量审查 | v0.0.1 | 2/2 | Complete | 2026-05-28 |
| 4. 性能与数据安全审查 | v0.0.1 | 1/1 | Complete | 2026-05-29 |
| 5. 测试覆盖补充 | v0.0.1 | 4/4 | Complete | 2026-05-29 |
| 6. Agent 类型扩展 | v0.0.2 | 3/3 | Complete   | 2026-05-29 |
| 7. 编排引擎 + 配置化 + 搜索 | v0.0.2 | 3/1 | Complete   | 2026-05-29 |
| 8. A2A 协议 | v0.0.2 | 0/3 | Not started | - |
