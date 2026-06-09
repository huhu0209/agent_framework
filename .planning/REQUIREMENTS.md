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

## v0.0.4 Requirements

**Goal:** 对三个模块（backend/、frontend/、agent_framework/）进行系统性代码审查

### Framework 审查（agent_framework/）

- [ ] **FRMW-01**: 检测框架层所有未使用的函数、类、import、变量、文件
- [ ] **FRMW-02**: 查找框架层逻辑漏洞、竞态条件、错误处理缺陷
- [ ] **FRMW-03**: 审查框架层不合理设计模式、违反原则、过度工程
- [ ] **FRMW-04**: 审查框架层安全漏洞（注入、信息泄露、路径遍历等）
- [ ] **FRMW-05**: 产出框架层审查报告（含优先级分级和修复建议）

### Backend 审查（backend/）

- [x] **BKND-01**: 检测后端所有未使用的函数、类、import、变量、文件
- [x] **BKND-02**: 查找后端逻辑漏洞、竞态条件、错误处理缺陷
- [x] **BKND-03**: 审查后端不合理设计模式、违反原则、过度工程
- [x] **BKND-04**: 审查后端安全漏洞（注入、信息泄露、认证问题等）
- [ ] **BKND-05**: 产出后端审查报告（含优先级分级和修复建议）

### Frontend 审查（frontend/）

- [x] **FRNT-01**: 检测前端所有未使用的函数、组件、import、变量、文件
- [x] **FRNT-02**: 查找前端逻辑漏洞、状态管理缺陷、错误处理缺陷
- [x] **FRNT-03**: 审查前端不合理设计模式、违反原则、过度工程
- [x] **FRNT-04**: 审查前端安全漏洞（XSS、敏感信息暴露等）
- [x] **FRNT-05**: 产出前端审查报告（含优先级分级和修复建议）

## Future Requirements

| ID | Description | Target |
|----|-------------|--------|
| EVNT-F01 | EventBus topic 过滤机制 | v0.0.5+ |
| EVNT-F02 | 事件持久化到文件/数据库 | v0.0.5+ |
| RNDR-F01 | 多动物形象选择 | v0.0.5+ |
| RNDR-F02 | 消息气泡飞行动画 | v0.0.5+ |
| CNFG-F01 | 拖拽编排 Agent 工作流 | v0.0.5+ |

## Out of Scope

| Feature | Reason |
|---------|--------|
| 代码重构/修复执行 | 本 milestone 仅审查+报告，修复留后续 |
| 新增测试覆盖 | 依赖审查结果决定 |
| 性能优化 | v0.0.1 已有 PERF-REVIEW |
| 前端单元测试补写 | 需专门 milestone |
| 依赖版本升级 | 不在代码审查范围 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| FRMW-01 | Phase 12 | Pending |
| FRMW-02 | Phase 12 | Pending |
| FRMW-03 | Phase 12 | Pending |
| FRMW-04 | Phase 12 | Pending |
| FRMW-05 | Phase 12 | Pending |
| BKND-01 | Phase 13 | Complete |
| BKND-02 | Phase 13 | Complete |
| BKND-03 | Phase 13 | Complete |
| BKND-04 | Phase 13 | Complete |
| BKND-05 | Phase 13 | Pending |
| FRNT-01 | Phase 14 | Complete |
| FRNT-02 | Phase 14 | Complete |
| FRNT-03 | Phase 14 | Complete |
| FRNT-04 | Phase 14 | Complete |
| FRNT-05 | Phase 14 | Complete |

**Coverage:**
- v0.0.4 requirements: 15 total
- Mapped to phases: 15
- Unmapped: 0 ✓

---
*Last updated: 2026-06-09 — v0.0.4 requirements defined*
