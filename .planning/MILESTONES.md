# Milestones

## v0.0.1 彻底 Code Review (Shipped: 2026-05-29)

**Phases completed:** 5 phases, 12 plans, 14 tasks
**Timeline:** 2026-05-12 → 2026-05-29 (17 days)
**Tests:** 630 → 687 (57 new, 0 regressions)

**Key accomplishments:**

1. **Bug 修复** — 修复 Path import 缺失、TaskManager 类型注解、normalize_messages 原地变异等 3 个 Bug
2. **安全加固** — 路径沙箱 (safe_path)、MCP 环境注入黑名单、API Key SecretStr 迁移，产出 SECURITY-REVIEW.md
3. **架构审查** — 产出 ARCH-REVIEW.md（12 项发现，HIGH/MEDIUM/LOW 分级），3 个空文件添加 scaffold docstring
4. **性能修复** — MessageBus 原子读写 (os.replace)、MCP readline 替换逐字节读取，产出 PERF-REVIEW.md
5. **测试补充** — 新增 12 个关键路径测试（TeamManager loop、安全边界集成、PermissionPipeline 边界情况），全量 687 测试通过

**Tech Debt:** 14 项 (all LOW/informational, no blockers)

**Known deferred items at close:** See v0.0.1-MILESTONE-AUDIT.md Tech Debt section

---

## v0.0.2 Agent 扩展与编排 (Shipped: 2026-05-29)

**Phases completed:** 3 phases, 9 plans
**Timeline:** 2026-05-29 (same day as v0.0.1)
**Tests:** 687 → 812 (125 new, 0 regressions)
**LOC:** +11,640 lines across 120 files

**Key accomplishments:**

1. **Agent 类型体系** — Agent ABC + AgentEvent 统一事件模型，PlanAndSolveAgent（先规划后执行 + replan ≤ 2）和 ReflectionAgent（自我评估 + 改进 ≤ 2 轮）
2. **编排引擎** — OrchestratorEngine 启发式复杂度评估，简单任务路由 ReAct、复杂任务路由 Plan-and-Solve，Agent 链最多 3 个
3. **声明式配置** — flat frontmatter .md 文件定义 Agent，agent_from_config() 创建完整可运行实例
4. **真实搜索** — Tavily AsyncTavilyClient 替换 mock，Semaphore 并发控制
5. **A2A 协议** — 纯 ASGI 实现（无 FastAPI 依赖），AgentCard + 同步模式 + API-key 认证

**Tech Debt:** v0.0.1 遗留 14 项 (all LOW) + Orchestrator 复杂度评估启发式可升级为 LLM 动态路由

**Known deferred items at close:** A2A 流式/异步模式、DAG 调度、LLM 动态路由

---

## v0.0.3 Agent 可视化平台 MVP (Shipped: 2026-05-31)

**Phases completed:** 3 phases, 9 plans
**Timeline:** 2026-05-29 → 2026-05-31 (3 days)
**Tests:** 812 → 845 (33 new, 0 regressions)

**Key accomplishments:**

1. **EventBus 事件总线** — asyncio.Queue pub-sub + 有界队列 drop-oldest + VizEvent Pydantic 模型 (EVNT-01~07)
2. **AgentRunner 包装层** — LoopEvent → VizEvent 6 条映射全覆盖，异常安全 idle/shutdown 发布 (EVNT-05~07)
3. **WebSocket 服务端** — websockets 16 asyncio API，双任务模式 recv+push，连接断开自动清理 (WSRV-01~05)
4. **PixiJS v8 办公室场景** — 三层 Container 架构 + 几何猫精灵 + 4 种 Ticker 帧动画 + lerp 移动系统 (RNDR-01~07)
5. **React 集成** — useReducer+Context 状态管理 + WebSocket 客户端 + useRef PixiJS 桥接 + 事件日志 (CNFG-01~04, CONC-01~05)

**Tech Debt:** 前端单元测试缺失、start_team/stop_team 仅接收确认未接实际执行

**Known deferred items at close:** EventBus topic 过滤、事件持久化、多动物形象、消息气泡飞行、拖拽编排

---

## v0.0.6 路径文件的统一 (Shipped: 2026-06-12)

**Phases completed:** 6 phases, 13 plans
**Timeline:** 2026-06-11 → 2026-06-12 (2 days)
**Tests:** 1002 → 1146 (144 new, 0 regressions)
**Framework LOC:** 11,332

**Key accomplishments:**

1. **ConfigLoader 统一入口** — Settings Pydantic 模型 + `_merge_settings()` 合并引擎 + 四级覆盖链 (env > local > project > global)
2. **8 模块类型自动发现** — `discover_paths()` 支持 skills/agents/commands/hooks/rules/profiles/memory/mcp
3. **8 个 `from_loader()` 工厂方法** — 所有模块适配器完成，保持向后兼容
4. **AGENTS.md 指令链 + RuleLoader** — 5 层指令加载 + frontmatter path-scoped 规则过滤
5. **Backend 集成 + E2E 验证** — `AgentFactory.from_configloader()` 一键初始化全部注册表
6. **零回归 + 文档刷新** — README/PROJECT/REQUIREMENTS/CONCERNS 全部更新

**Tech Debt:** 7 WARNING integration items (adapters loaded but not consumed in production paths)

**Known deferred items at close:** 7 items (INT-W01~W07) — see v0.0.6-MILESTONE-AUDIT.md

---
