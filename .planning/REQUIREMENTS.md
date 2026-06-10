# Requirements: Agent Framework

## v0.0.3 Requirements (Shipped)

### EVNT — EventBus 事件系统

- [x] **EVNT-01**: EventBus 发布/订阅事件（asyncio.Queue pub-sub）
- [x] **EVNT-02**: 订阅获取 asyncio.Queue，异步循环消费
- [x] **EVNT-03**: 取消订阅自动清理 Queue 引用
- [x] **EVNT-04**: VizEvent 数据模型 + JSON 序列化
- [x] **EVNT-05**: AgentRunner 包装 AgentLoop → VizEvent 广播
- [x] **EVNT-06**: 事件映射覆盖所有状态
- [x] **EVNT-07**: AgentRunner yield 原始事件

### WSRV — WebSocket 服务

- [x] **WSRV-01**: WebSocket 服务端订阅 EventBus 实时推送
- [x] **WSRV-02**: 断开自动取消订阅
- [x] **WSRV-03**: start_team 控制命令
- [x] **WSRV-04**: stop_team 控制命令
- [x] **WSRV-05**: websockets 库 ping/pong 心跳

### RNDR — Canvas 渲染层

- [x] **RNDR-01~07**: PixiJS v8 三层 Container + 几何猫精灵 + 帧动画 + lerp 移动

### CNFG — React 配置面板

- [x] **CNFG-01~04**: Agent 创建表单 + Team 控制 + 状态灯

### CONC — WebSocket 客户端

- [x] **CONC-01~05**: WebSocket 连接 + reducer + ref 桥接 + 连接指示器 + 事件日志

---

## v0.0.4 Requirements (Shipped)

- [x] **FRMW-01~05**: Framework 全面代码审查（133 issues）
- [x] **BKND-01~05**: Backend 全面代码审查（25 issues）
- [x] **FRNT-01~05**: Frontend 全面代码审查（31 issues）

---

## v0.0.5 Requirements — Review 问题修复

**Goal:** 修复 v0.0.4 审查中发现的 HIGH 和关键 MEDIUM 级别 issue
**Source:** docs/reviews/REVIEW-FRAMEWORK.md, REVIEW-BACKEND.md, REVIEW-FRONTEND.md

### FW-DEAD — Framework 死代码清理

- [ ] **FW-DEAD-01**: 移除 llm/ 层 16 个未使用 import
- [ ] **FW-DEAD-02**: 移除 llm/transform/ 未使用 import
- [ ] **FW-DEAD-03**: 移除 agents/ 未使用 import
- [ ] **FW-DEAD-04**: 移除 tools/ 未使用 import
- [ ] **FW-DEAD-05**: 移除其他模块未使用 import（hooks, orchestrator, tasks, teams）
- [ ] **FW-DEAD-06**: 修复 agent_loop.py logger 未定义（运行时 NameError）

### FW-SEC — Framework 安全修复

- [ ] **FW-SEC-01**: 修复 httpx 引用在 TYPE_CHECKING guard 外使用
- [ ] **FW-SEC-02**: 修复 memory/ 全模块同步文件 I/O 阻塞事件循环
- [ ] **FW-SEC-03**: 修复 MCP 子进程继承全部环境变量
- [ ] **FW-SEC-04**: 修复 Skill 内容注入漏洞
- [ ] **FW-SEC-05**: 修复 Prompt injection via profile
- [ ] **FW-SEC-06**: 修复 WebSocket 无认证
- [ ] **FW-SEC-07**: 修复 result_truncator.py 同步文件 I/O
- [ ] **FW-SEC-08**: 修复 MCP 敏感环境变量过滤不完整
- [ ] **FW-SEC-09**: 修复 try-except-pass 静默吞异常（4处）

### FW-LOGIC — Framework 逻辑修复

- [ ] **FW-LOGIC-01**: 修复 ASK 权限决策返回 error（HITL 失效）
- [ ] **FW-LOGIC-02**: 修复 _CRITICAL_TOOLS 始终为空
- [ ] **FW-LOGIC-03**: 降低 AgentLoop 复杂度（C901=30）
- [ ] **FW-LOGIC-04**: 拆分 ToolRouter.dispatch 职责（C901=18）
- [ ] **FW-LOGIC-05**: 消除 search_tools 模块级可变全局状态
- [ ] **FW-LOGIC-06**: 增强 ToolValidator 验证（unknown 参数 + enum）
- [ ] **FW-LOGIC-07**: 结构化 ToolUseContext.extra
- [ ] **FW-LOGIC-08**: 修复 _dispatch_agent hardcoded stub
- [ ] **FW-LOGIC-09**: 降低 _apply_changes 复杂度
- [ ] **FW-LOGIC-10**: 修复 MCP ToolSpec 无 handler 问题

### BK-SEC — Backend 安全修复

- [ ] **BK-SEC-01**: 修复 SSE 异常消息泄漏到客户端
- [ ] **BK-SEC-02**: 修复 session_id path 参数未验证
- [ ] **BK-SEC-03**: 收紧 CORS methods 和 headers
- [ ] **BK-SEC-04**: 修复 Redis 连接失败被静默吞掉
- [ ] **BK-SEC-05**: 修复 API key 存储为 plain string

### BK-LOGIC — Backend 逻辑修复

- [ ] **BK-LOGIC-01**: 修复 TTL eviction 竞态条件导致消息丢失
- [ ] **BK-LOGIC-02**: 修复 JSONL 非原子读写
- [ ] **BK-LOGIC-03**: 修复 Shared ToolUseContext 跨会话消息泄漏
- [ ] **BK-LOGIC-04**: 修复 AgentFactory 未设置 working_dir
- [ ] **BK-LOGIC-05**: 修复 chat.py 访问 framework 私有属性

### FT-SEC — Frontend 安全修复

- [ ] **FT-SEC-01**: 修复 SSE event data 解析无 schema 验证
- [ ] **FT-SEC-02**: 修复 react-markdown 无显式 HTML 消毒

### FT-LOGIC — Frontend 逻辑修复

- [ ] **FT-LOGIC-01**: 修复 res.body! 非空断言崩溃
- [ ] **FT-LOGIC-02**: 修复 JSON.parse(eventData) 无错误处理
- [ ] **FT-LOGIC-03**: 修复 Virtual list 不自动滚动到新消息
- [ ] **FT-LOGIC-04**: 修复 hoverRef timeout 组件卸载时未清理

### FT-ARCH — Frontend 架构修复

- [ ] **FT-ARCH-01**: 修复 toFrontendBlocks 不安全类型断言
- [ ] **FT-ARCH-02**: 修复 store 错误处理静默吞异常（3处）
- [ ] **FT-ARCH-03**: 修复 SSE _map_to_sse 静默丢弃未知 stop reason
- [ ] **FT-ARCH-04**: 修复 groupBlocks 不处理孤立 tool_result
- [ ] **FT-ARCH-05**: 替换内联 hover 样式为 Tailwind

---

## Future Requirements

| ID | Description | Target |
|----|-------------|--------|
| EVNT-F01 | EventBus topic 过滤机制 | v0.0.6+ |
| EVNT-F02 | 事件持久化到文件/数据库 | v0.0.6+ |
| RNDR-F01 | 多动物形象选择 | v0.0.6+ |
| RNDR-F02 | 消息气泡飞行动画 | v0.0.6+ |
| CNFG-F01 | 拖拽编排 Agent 工作流 | v0.0.6+ |

## Out of Scope

| Feature | Reason |
|---------|--------|
| API 认证系统（登录/注册） | BKND-SEC-06 架构级改动，需单独 milestone |
| 前端单元测试补写 | 需专门 milestone |
| LOW 级 issue 修复 | 留后续 milestone（35 个） |
| Provider 基类提取 | LOW 级代码重复，不影响正确性 |
| AgentLoop 参数重构 | PLR0913=19，架构级重构 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| FW-DEAD-01~06 | Phase 15 | Pending |
| FW-SEC-01 | Phase 15 | Pending |
| FW-SEC-02~09 | Phase 16 | Pending |
| FW-LOGIC-01~10 | Phase 17 | Pending |
| BK-SEC-01~05 | Phase 18 | Pending |
| BK-LOGIC-01~05 | Phase 18 | Pending |
| FT-SEC-01~02 | Phase 19 | Pending |
| FT-LOGIC-01~04 | Phase 19 | Pending |
| FT-ARCH-01~05 | Phase 19 | Pending |

**Coverage:**
- v0.0.5 requirements: 46 total
- Mapped to phases: 46
- Unmapped: 0 ✓

---
*Last updated: 2026-06-10 — v0.0.5 roadmap created*
