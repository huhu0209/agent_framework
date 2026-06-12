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

## v0.0.5 Requirements (Shipped)

- [x] **FW-DEAD-01~06**: Framework 死代码清理
- [x] **FW-SEC-01~09**: Framework 安全修复
- [x] **FW-LOGIC-01~10**: Framework 逻辑修复
- [x] **BK-SEC-01~05**: Backend 安全修复
- [x] **BK-LOGIC-01~05**: Backend 逻辑修复
- [x] **FT-SEC-01~02**: Frontend 安全修复
- [x] **FT-LOGIC-01~04**: Frontend 逻辑修复
- [x] **FT-ARCH-01~05**: Frontend 架构修复

---

## v0.0.6 Requirements — 路径文件的统一

**Goal:** 参照 Claude Code 路径机制，实现统一配置层级体系和模块自动发现
**Source:** docs/plans/2026-06-11-config-path-mechanism-design.md

### CFG — Core Config（配置核心）

- [x] **CFG-01**: ConfigLoader 支持四级覆盖链加载 settings.json（env > local > project > global）
- [x] **CFG-02**: _merge_settings() 实现三种合并策略 — 数组并集（去重保序）、对象浅合并、标量覆盖
- [x] **CFG-03**: Settings Pydantic BaseModel 定义（model/llm/server/logging/permissions 字段）
- [x] **CFG-04**: discover_paths(module_name) 返回优先级从低到高的目录路径列表
- [x] **CFG-05**: discover() 支持 8 种模块类型（skills/agents/commands/hooks/rules/profiles/memory/mcp）
- [x] **CFG-06**: 环境变量覆盖支持 APP_ 前缀 + env_nested_delimiter='__'（仅标量值）

### INS — Instructions（指令链）

- [x] **INS-01**: AGENTS.md 指令链按顺序加载（全局 → 项目 → local → 父目录链 → user.md）
- [x] **INS-02**: 父目录链遍历从 CWD 到 root，遇到 .git/ 边界停止
- [x] **INS-03**: rules/*.md 收集全局 + 项目路径，支持 paths 前言条件匹配
- [x] **INS-04**: Profile 加载 profiles/<name>/ 目录下 soul.md/agents.md/identity.md/tool_guidance.md
- [x] **INS-05**: load_agents_md() 拼接全部指令返回完整字符串
- [x] **INS-06**: PromptAssembler 集成 — 指令链注入 <user-provided> 块，Profile 注入对应标签

### ADP — Module Adapters（模块适配器）

- [x] **ADP-01**: SkillRegistry.from_loader() 工厂方法，从 discover("skills") 路径列表加载
- [x] **ADP-02**: HookManager.from_loader() 工厂方法，从 discover("hooks") 路径列表合并 hooks.json
- [x] **ADP-03**: CommandRegistry.from_loader() 工厂方法，从 discover("commands") 路径列表加载
- [x] **ADP-04**: AgentProfile.from_loader() 工厂方法，从 discover("agents") 路径列表加载，同名项目覆盖全局并 warning
- [x] **ADP-05**: AgentProfile.from_profile() 支持 discover("profiles") 目录加载
- [x] **ADP-06**: McpManager.from_loader() 工厂方法，从 discover("mcp") 合并 servers.json
- [x] **ADP-07**: TaskManager 集成 — tasks_dir 默认值改为 .agent-framework/tasks/
- [x] **ADP-08**: PermissionPipeline 从 settings.permissions 自动注入 allow/deny 列表
- [x] **ADP-09**: 所有适配器保持向后兼容 — 现有构造函数签名不变，工厂方法为新增 API

### INT — Integration & Testing（集成与测试）

- [x] **INT-01**: backend/app/config/ 从 ConfigLoader.load_settings() 获取默认值
- [x] **INT-02**: backend AgentFactory 使用 ConfigLoader 初始化模块注册表
- [x] **INT-03**: config/ 模块作为叶依赖 — 不导入框架其他模块，避免循环依赖
- [x] **INT-04**: 端到端验证 — ConfigLoader 加载 settings → discover 模块 → 适配器创建注册表
- [x] **INT-05**: 全部 1002+ 现有测试通过（零回归）
- [x] **INT-06**: Path-scoped rules — rules/*.md 支持 frontmatter paths 条件匹配加载

---

## Future Requirements

| ID | Description | Target |
|----|-------------|--------|
| CFG-F01 | ConfigLoader async aiofiles 支持 | v0.0.7+ |
| CFG-F02 | Settings schema 版本迁移 | v0.0.7+ |
| CFG-F03 | 配置热重载（mtime 检测） | v0.0.7+ |
| INS-F01 | 托管/企业级配置层 | v0.0.7+ |
| INS-F02 | AGENTS.md 变更自动重载 PromptAssembler | v0.0.7+ |
| ADP-F01 | Memory 模块 discover("memory") 按 MEMORY.md 加载 | v0.0.7+ |
| ADP-F02 | MCP servers.json schema 验证 | v0.0.7+ |
| EVNT-F01 | EventBus topic 过滤机制 | v0.0.7+ |
| EVNT-F02 | 事件持久化到文件/数据库 | v0.0.7+ |
| RNDR-F01 | 多动物形象选择 | v0.0.7+ |
| RNDR-F02 | 消息气泡飞行动画 | v0.0.7+ |
| CNFG-F01 | 拖拽编排 Agent 工作流 | v0.0.7+ |

## Out of Scope

| Feature | Reason |
|---------|--------|
| 托管/企业级配置层 | 框架是库非 SaaS，不需要企业级管理 |
| 配置热重载 | 设计文档未定义，v0.0.7 考虑 |
| YAML/TOML 配置格式 | 与 Claude Code 保持一致用 JSON |
| 深度合并嵌套对象 | 设计文档明确浅合并，避免过度复杂 |
| 前端单元测试 | 需专门 milestone |
| LOW 级 issue 修复 | v0.0.5 已处理 HIGH+MEDIUM，LOW 留后续 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| CFG-02 | Phase 20 | Complete |
| CFG-03 | Phase 20 | Complete |
| CFG-06 | Phase 20 | Complete |
| CFG-01 | Phase 21 | Complete |
| CFG-04 | Phase 21 | Complete |
| CFG-05 | Phase 21 | Complete |
| INS-01 | Phase 21 | Complete |
| INS-02 | Phase 21 | Complete |
| INS-04 | Phase 21 | Complete |
| INS-05 | Phase 21 | Complete |
| ADP-01 | Phase 22 | Complete |
| ADP-02 | Phase 22 | Complete |
| ADP-03 | Phase 22 | Complete |
| ADP-09 | Phase 22 | Complete |
| ADP-04 | Phase 23 | Complete |
| ADP-05 | Phase 23 | Complete |
| ADP-06 | Phase 23 | Complete |
| ADP-07 | Phase 23 | Complete |
| ADP-08 | Phase 23 | Complete |
| INS-03 | Phase 24 | Complete |
| INS-06 | Phase 24 | Complete |
| INT-01 | Phase 24 | Complete |
| INT-02 | Phase 24 | Complete |
| INT-03 | Phase 24 | Complete |
| INT-04 | Phase 24 | Complete |
| INT-05 | Phase 24 | Complete |
| INT-06 | Phase 24 | Complete |

**Coverage:**
- v0.0.6 requirements: 26 total
- Mapped to phases: 26
- Unmapped: 0

---
*Requirements defined: 2026-06-11*
*Last updated: 2026-06-12 — v0.0.6 traceability updated (Phases 23-24 completed)*
