# Phase 13: Backend 代码审查 - Context

**Gathered:** 2026-06-09
**Status:** Ready for planning

<domain>
## Phase Boundary

对 backend/ 应用层进行系统性代码审查，产出 REVIEW-BACKEND.md。
覆盖四个审查维度：死代码检测（BKND-01）、逻辑漏洞（BKND-02）、设计问题（BKND-03）、安全审查（BKND-04）。
本 phase 仅审查+报告，不执行重构或修复。

</domain>

<decisions>
## Implementation Decisions

### 审查方法论（沿用 Phase 12）
- **D-01:** 完全沿用 Phase 12 审查方法论 — ruff 自动扫描 + 人工逐文件审查，不重复讨论已确立的流程
- **D-02:** Issue ID 使用 BKND- 前缀 — BKND-SEC-（安全）、BKND-LOGIC-（逻辑）、BKND-ARCH-（设计）、BKND-DEAD-（死代码）
- **D-03:** Scaffold 空文件仅标记确认，跳过详细审查 — 节省审查资源
- **D-04:** 报告存放在 docs/reviews/ 目录 — 与 REVIEW-FRAMEWORK.md 同级集中管理

### Backend 安全审查维度
- **D-05:** Web 安全全覆盖 — API 端点认证、输入验证、CORS、SQL 注入、认证绕过、敏感信息泄露、会话管理
- **D-06:** 完整数据流追踪 — 每个 API 端点追踪 HTTP 请求→参数解析→服务层调用→框架层调用→响应构建
- **D-07:** 审查对框架层的调用方式 — 检查 Backend 是否正确使用框架层 API、是否有误用或不必要的耦合（不审查框架层内部实现）

### 跨层交叉参照
- **D-08:** 专题章节 + 主题归类 — 在 REVIEW-BACKEND.md 末尾设"跨层问题"章节，按主题归类（如"错误处理不匹配"、"安全策略不连续"），引用 REVIEW-FRAMEWORK.md 的具体 issue ID
- **D-09:** 单向参照（BKND → FRMW） — 仅标注 Backend 发现中与 Framework 有关的问题，不反向扩展

### 审查范围与分 Plan 策略
- **D-10:** 2 个 plan — Plan 1: ruff 扫描 + 逐文件人工审查 + 数据流追踪；Plan 2: 跨层交叉参照 + 报告汇总 + 质量检查
- **D-11:** 审查范围仅限源码 — backend/app/ 和 backend/main.py，不含 tests/ 测试代码

### Claude's Discretion
- ruff 的具体规则配置和启用项
- 文件审查的先后顺序
- 跨层问题归类方式
- 数据流追踪的详细程度

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 审查需求定义
- `.planning/REQUIREMENTS.md` — BKND-01~05 需求定义（死代码、逻辑漏洞、设计问题、安全审查、审查报告）
- `.planning/ROADMAP.md` — Phase 13 目标、成功标准、范围定义

### Phase 12 审查产出（交叉参照输入）
- `docs/reviews/REVIEW-FRAMEWORK.md` — Phase 12 框架层审查报告（跨层交叉参照的对照基准）
- `.planning/phases/12-framework/12-CONTEXT.md` — Phase 12 上下文（了解审查方法论和分级标准）

### 代码库基线（参考，不对照）
- `docs/reviews/SECURITY-REVIEW.md` — v0.0.1 安全审查报告（了解历史审查格式，但不逐项对照）
- `docs/reviews/ARCH-REVIEW.md` — v0.0.1 架构审查报告（同上）

### 代码库智能
- `.planning/codebase/CONCERNS.md` — 已知问题清单（CONCERNS.md 曾说"Backend 完全 scaffold"，需验证当前状态）
- `.planning/codebase/CONVENTIONS.md` — 编码规范（审查时参考）
- `.planning/codebase/TESTING.md` — 测试规范（审查时参考）
- `.planning/codebase/ARCHITECTURE.md` — 架构分析（理解 Backend 在系统中的位置）

### Backend 源码
- `backend/app/` — 审查目标目录（API 端点、服务层、配置、模型、工具）
- `backend/main.py` — FastAPI 应用入口

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `docs/reviews/REVIEW-FRAMEWORK.md` — Phase 12 的报告格式、分级标准、issue 结构可直接复用
- Phase 12 的 ruff 配置可直接用于 Backend 死代码检测

### Established Patterns
- Backend 约 16 个 Python 源文件（远少于框架层 ~60 个）
- 部分文件可能是 scaffold 空文件（CONCERNS.md 曾记录）
- Backend 通过 `pyproject.toml` 依赖本地 framework 包，import 时使用 `from agent_framework.xxx import ...`
- v0.0.3 新增了 `session.py`、`agent_factory.py` 等有实现的服务层文件

### Integration Points
- Backend API 端点调用框架层 AgentLoop、ToolSystem 等
- Backend 服务层封装框架层调用（agent_factory.py 创建 Agent 实例）
- 审查产出 REVIEW-BACKEND.md 放在 `docs/reviews/` 目录
- Phase 14 (Frontend 审查) 会参考此报告的格式

</code_context>

<specifics>
## Specific Ideas

- Backend 代码量小，2 个 plan 应该足够覆盖所有审查维度
- 数据流追踪是 Phase 13 的关键增值点（ROADMAP 明确要求）
- 跨层交叉参照是 Phase 13 独有的需求（Phase 12 不需要，Phase 14 会参考此模式）
- Scaffold 空文件确认后跳过，重点审查有实质代码的文件

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 13-Backend 代码审查*
*Context gathered: 2026-06-09*
