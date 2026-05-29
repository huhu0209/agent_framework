# Phase 7: 编排引擎 + 配置化 + 搜索 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-29
**Phase:** 07-orchestrator-config-search
**Areas discussed:** 复杂度评估规则, Orchestrator 架构, Agent 配置文件格式, 搜索错误处理

---

## 复杂度评估规则

| Option | Description | Selected |
|--------|-------------|----------|
| 字数阈值（推荐） | 任务描述超过 N 个字符即为复杂。实现最简单，零外部依赖 | ✓ |
| 关键词匹配 | 检测"计划""分析""对比"等关键词 | |
| 多信号组合 | 字数 + 关键词 + 问句数量综合评分 | |
| Claude 决定 | 交给你判断 | |

**User's choice:** 字数阈值，附详细理由
**Notes:** 用户提供了安全网论证：误判代价低（复杂→简单: ReAct 也能跑；简单→复杂: 空计划 fallback）。推荐代码形态为单条 if 语句，默认阈值 200 字符。

---

## Orchestrator 架构

### Q1: OrchestratorEngine 与 PlanAndSolveAgent 关系

| Option | Description | Selected |
|--------|-------------|----------|
| 委托给 PlanAndSolve（推荐） | OrchestratorEngine 评估+路由，复杂任务调用 PlanAndSolveAgent.run() | ✓ |
| 复用底层组件，自建执行循环 | 复用 PlanningState/parse_plan_response，自管理执行循环 | |
| Claude 决定 | 交给你判断 | |

**User's choice:** 委托给 PlanAndSolve

### Q2: agent_factory 职责范围

| Option | Description | Selected |
|--------|-------------|----------|
| 工厂创建 Agent 实例（推荐） | 创建 PlanAndSolve（复杂）或 AgentLoop（简单），传入配置 | ✓ |
| 预创建，复用实例 | 持有预配置实例直接调用 | |
| Claude 决定 | 交给你判断 | |

**User's choice:** 工厂创建 Agent 实例

### Q3: 偏离检测归属

| Option | Description | Selected |
|--------|-------------|----------|
| 依赖 PlanAndSolve 内部逻辑（推荐） | OrchestratorEngine 不做额外偏离检测 | ✓ |
| 双层偏离检测 | Orchestrator 在 PlanAndSolve 返回后做额外结果检查 | |
| Claude 决定 | 交给你判断 | |

**User's choice:** 依赖 PlanAndSolve 内部逻辑

---

## Agent 配置文件格式

### Q1: frontmatter vs body 布局

| Option | Description | Selected |
|--------|-------------|----------|
| frontmatter 元数据 + body prompt（推荐） | frontmatter: name, model, tools 等；body: system_prompt | ✓ |
| 全部 frontmatter | 所有字段包括 system_prompt 都在 frontmatter | |
| Claude 决定 | 交给你判断 | |

**User's choice:** frontmatter 元数据 + body prompt

### Q2: tools 字段引用方式

| Option | Description | Selected |
|--------|-------------|----------|
| 工具名列表（推荐） | 按名称引用，与 ToolRegistry name 对应 | ✓ |
| 通配符 / glob 模式 | 支持 file_* 或 all 等模式 | |
| Claude 决定 | 交给你判断 | |

**User's choice:** 工具名列表

### Q3: system_prompt 安全验证

| Option | Description | Selected |
|--------|-------------|----------|
| 关键词黑名单检查 | 检查"忽略前面指令"等注入模式 | |
| 仅非空检查 | 只确认 system_prompt 不为空，安全交给运行时 | ✓ |
| LLM 评估 | 用 LLM 评估 prompt 安全性 | |
| Claude 决定 | 交给你判断 | |

**User's choice:** 仅非空检查
**Notes:** 用户信任配置文件作者（开发者），将注入防护交给运行时 PermissionPipeline 和 Boundary。

---

## 搜索错误处理

| Option | Description | Selected |
|--------|-------------|----------|
| 返回错误结果（推荐） | ToolResult(is_error=True)，LLM 自行调整策略 | ✓ |
| 降级到空结果 | 返回"未找到结果" | |
| Fallback 到 mock | 回退到硬编码 mock 数据 | |
| Claude 决定 | 交给你判断 | |

**User's choice:** 返回错误结果

---

## Claude's Discretion

- OrchestratorEngine 是否实现 Agent 接口（可嵌套使用）
- frontmatter 必填/可选字段划分
- Semaphore 并发数
- Tavily client 配置细节
- 配置目录路径默认值

## Deferred Ideas

None — discussion stayed within phase scope
