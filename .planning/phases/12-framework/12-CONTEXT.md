# Phase 12: Framework 代码审查 - Context

**Gathered:** 2026-06-09
**Status:** Ready for planning

<domain>
## Phase Boundary

对 agent_framework/ 框架层进行系统性代码审查，产出 REVIEW-FRAMEWORK.md。
覆盖四个审查维度：死代码检测（FRMW-01）、逻辑漏洞（FRMW-02）、设计问题（FRMW-03）、安全审查（FRMW-04）。
本 phase 仅审查+报告，不执行重构或修复。

</domain>

<decisions>
## Implementation Decisions

### 审查基线与覆盖度
- **D-01:** 全面重新审查 — 逐文件审查所有框架层源码，不依赖 v0.0.1 审查基线，独立发现所有问题
- **D-02:** 全模块等权审查 — 所有模块同等深度审查，不偏重新增模块或高风险模块
- **D-03:** 独立审查 — 不与 v0.0.1 SECURITY-REVIEW.md / ARCH-REVIEW.md 逐项对照，完全独立产出

### 审查方法与工具
- **D-04:** ruff 做死代码检测 — 利用 ruff 的未使用 import/变量/函数检测能力
- **D-05:** 工具先行 + 人工审查 — 先 ruff 自动扫描全量代码获取死代码报告，再逐模块人工审查逻辑漏洞、设计问题、安全漏洞。工具结果是输入之一，不是唯一来源
- **D-06:** 审查范围仅限框架源码 — agent_framework/ 下的 .py 文件，不含 tests/ 测试代码

### 报告格式与分级标准
- **D-07:** 影响导向分级标准：
  - CRITICAL = 数据丢失 / 安全漏洞 / 系统不可用
  - HIGH = 逻辑错误 / 竞态条件 / 严重设计缺陷
  - MEDIUM = 代码质量 / 可维护性问题 / 轻微设计不合理
  - LOW = 代码风格 / 命名 / 文档 / 微小优化
- **D-08:** 按模块分组 — 每个模块一个章节（llm/, tools/, agents/, teams/, memory/, safety/, orchestrator/, prompts/, skills/, tasks/, hooks/, commands/, viz/），模块内按严重性排序
- **D-09:** 详细 issue 字段 — 每个 issue 包含：ID（如 FRMW-SEC-01）、描述、文件位置（文件:行号）、影响、修复建议、优先级。与 REQUIREMENTS.md FRMW-01~05 需求追踪关联

### Claude's Discretion
- ruff 的具体规则配置和启用项
- 模块审查的先后顺序
- 具体 issue ID 编号方案
- 跨模块问题的归类方式

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 审查需求定义
- `.planning/REQUIREMENTS.md` — FRMW-01~05 需求定义（死代码、逻辑漏洞、设计问题、安全审查、审查报告）
- `.planning/ROADMAP.md` — Phase 12 目标、成功标准、范围定义

### 代码库基线（参考，不对照）
- `docs/reviews/SECURITY-REVIEW.md` — v0.0.1 安全审查报告（了解历史审查格式，但不逐项对照）
- `docs/reviews/ARCH-REVIEW.md` — v0.0.1 架构审查报告（同上）

### 代码库智能
- `.planning/codebase/CONCERNS.md` — 已知问题清单（作为审查参考输入，帮助确保不遗漏已知问题）
- `.planning/codebase/CONVENTIONS.md` — 编码规范（审查时参考）
- `.planning/codebase/TESTING.md` — 测试规范（审查时参考）

### 框架源码
- `framework/agent_framework/` — 审查目标目录（~60 源文件、12,500 行）

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `docs/reviews/SECURITY-REVIEW.md` — 可参考 v0.0.1 审查报告的 issue 格式（描述/文件位置/影响/修复建议）
- `docs/reviews/ARCH-REVIEW.md` — 同上，按严重性分组的格式可参考
- `.planning/codebase/CONCERNS.md` — 已有详细的已知问题清单，可作为审查输入确保覆盖

### Established Patterns
- 框架层代码全部在 `framework/agent_framework/` 下，按功能模块组织（llm/, tools/, agents/ 等）
- 所有数据模型用 Pydantic v2 或 frozen dataclass
- 异步操作用 asyncio 单线程事件循环
- 错误处理用 typed exceptions（LLMAdapterError 层次结构）

### Integration Points
- 审查产出 REVIEW-FRAMEWORK.md 放在 `docs/reviews/` 目录
- Phase 13 (Backend 审查) 和 Phase 14 (Frontend 审查) 会参考此报告的格式
- 修复工作在后续 milestone 中执行，不在本 phase

</code_context>

<specifics>
## Specific Ideas

- 框架层约 60 个源文件，全模块等权审查意味着每个文件都要逐行审查
- ruff 扫描可以在人工审查前运行，输出作为死代码检测的基础数据
- 报告按模块分组便于后续分模块修复和追踪
- 每个 issue 的 ID 前缀可用 FRMW-SEC-（安全）、FRMW-LOGIC-（逻辑）、FRMW-ARCH-（设计）、FRMW-DEAD-（死代码）区分类型

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 12-Framework 代码审查*
*Context gathered: 2026-06-09*
