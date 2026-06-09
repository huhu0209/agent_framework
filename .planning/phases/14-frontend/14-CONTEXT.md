# Phase 14: Frontend 代码审查 - Context

**Gathered:** 2026-06-09
**Status:** Ready for planning

<domain>
## Phase Boundary

对 frontend/ 前端代码进行系统性代码审查，产出 REVIEW-FRONTEND.md。
覆盖四个审查维度：死代码检测（FRNT-01）、逻辑漏洞（FRNT-02）、设计问题（FRNT-03）、安全审查（FRNT-04）。
本 phase 仅审查+报告，不执行重构或修复。

**重要：** 当前前端是 Chat UI（zustand + react-markdown + highlight.js + @tanstack/react-virtual），
与 ROADMAP 中提到的 PixiJS/WebSocket 已不一致。审查范围以当前实际代码为准。

</domain>

<decisions>
## Implementation Decisions

### 审查范围调整（代码演变差异）
- **D-01:** 完全覆盖当前代码 — 审查当前实际存在的 Chat UI 代码，忽略 ROADMAP 中 PixiJS/WebSocket 的要求（这些代码已不存在）
- **D-02:** 审查范围仅限源码 — frontend/src/ 下的 .ts/.tsx/.css 文件（约 25 个文件，1975 行），不含测试代码
- **D-03:** 全文件等权审查 — 所有源码文件同等深度审查，不因文件大小调整审查力度

### 审查方法与工具（沿用 Phase 12/13）
- **D-04:** ESLint 扫描 + 人工逐文件审查 — 先运行 ESLint 获取死代码/未使用 import 报告，再逐文件人工审查逻辑漏洞、设计问题、安全漏洞
- **D-05:** 工具先行 + 人工为主 — ESLint 结果是输入之一，不是唯一来源
- **D-06:** Issue ID 使用 FRNT- 前缀 — FRNT-SEC-（安全）、FRNT-LOGIC-（逻辑）、FRNT-ARCH-（设计）、FRNT-DEAD-（死代码）

### React/前端特定审查维度
- **D-07:** 全覆盖前端审查维度 — zustand store 设计合理性、组件结构与 props 传递、re-render 问题、错误边界、虚拟化列表使用、markdown 渲染安全（XSS）、事件处理
- **D-08:** 报告按目录分组 — 按代码目录结构组织（store/、components/、components/markdown/等），每组内按严重性排序
- **D-09:** 影响导向分级标准（沿用 Phase 12）：
  - CRITICAL = 数据丢失 / 安全漏洞 / 系统不可用
  - HIGH = 逻辑错误 / 竞态条件 / 严重设计缺陷
  - MEDIUM = 代码质量 / 可维护性问题 / 轻微设计不合理
  - LOW = 代码风格 / 命名 / 文档 / 微小优化

### 跨层交叉参照
- **D-10:** 专题章节 + 主题归类 — 在 REVIEW-FRONTEND.md 末尾设"跨层问题"章节，按主题归类，引用 REVIEW-FRAMEWORK.md 和 REVIEW-BACKEND.md 的具体 issue ID
- **D-11:** 单向参照（FRNT → BKND/FRMW） — 仅标注 Frontend 发现中与 Backend/Framework 有关的问题，不反向扩展
- **D-12:** 报告存放在 docs/reviews/ 目录 — 与 REVIEW-FRAMEWORK.md、REVIEW-BACKEND.md 同级集中管理

### Claude's Discretion
- ESLint 的具体规则配置和启用项
- 文件审查的先后顺序
- 跨层问题归类方式
- 前端安全审查的详细程度

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 审查需求定义
- `.planning/REQUIREMENTS.md` — FRNT-01~05 需求定义（死代码、逻辑漏洞、设计问题、安全审查、审查报告）
- `.planning/ROADMAP.md` — Phase 14 目标、成功标准、范围定义

### Phase 12/13 审查产出（交叉参照输入）
- `docs/reviews/REVIEW-FRAMEWORK.md` — Phase 12 框架层审查报告（跨层交叉参照的对照基准）
- `docs/reviews/REVIEW-BACKEND.md` — Phase 13 后端审查报告（跨层交叉参照的对照基准）
- `.planning/phases/12-framework/12-CONTEXT.md` — Phase 12 上下文（了解审查方法论和分级标准）
- `.planning/phases/13-backend/13-CONTEXT.md` — Phase 13 上下文（了解交叉参照模式）

### 代码库基线（参考，不对照）
- `docs/reviews/SECURITY-REVIEW.md` — v0.0.1 安全审查报告（了解历史审查格式，但不逐项对照）
- `docs/reviews/ARCH-REVIEW.md` — v0.0.1 架构审查报告（同上）

### 代码库智能
- `.planning/codebase/CONCERNS.md` — 已知问题清单（审查时参考）
- `.planning/codebase/CONVENTIONS.md` — 编码规范（含 TypeScript 前端规范）
- `.planning/codebase/TESTING.md` — 测试规范（审查时参考）
- `.planning/codebase/STRUCTURE.md` — 文件结构（注意：部分内容可能过时，以实际代码为准）
- `.planning/codebase/STACK.md` — 技术栈（含前端依赖信息）

### 前端源码
- `frontend/src/` — 审查目标目录（~25 个文件，~1975 行）
- `frontend/package.json` — 依赖定义（zustand, react-markdown, highlight.js, @tanstack/react-virtual 等）
- `frontend/eslint.config.js` — ESLint 配置（typescript-eslint + react-hooks + react-refresh）

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `docs/reviews/REVIEW-FRAMEWORK.md` — Phase 12 的报告格式、分级标准、issue 结构可直接复用
- `docs/reviews/REVIEW-BACKEND.md` — Phase 13 的交叉参照章节结构可直接复用
- `frontend/eslint.config.js` — 已有 ESLint 配置，可直接用于死代码检测

### Established Patterns
- 当前前端使用 zustand v5 状态管理（非 useReducer+Context）
- react-markdown + rehype-highlight + remark-gfm 处理 markdown 渲染
- @tanstack/react-virtual 处理虚拟化列表
- highlight.js 处理代码语法高亮
- Tailwind CSS 4 样式
- 前端代码量小（~1975 行，25 个文件），比 Framework（~10,475 行）和 Backend 都少

### Integration Points
- 前端通过 API 调用与 Backend 交互（lib/api.ts）
- 审查产出 REVIEW-FRONTEND.md 放在 `docs/reviews/` 目录
- v0.0.4 milestone 三个审查报告在此 phase 全部完成

</code_context>

<specifics>
## Specific Ideas

- 前端代码量小（25 个文件、1975 行），2 个 plan 应该足够覆盖所有审查维度
- store.ts (389 行) 是最复杂的文件，需要重点审查状态管理逻辑
- SessionSidebar.tsx (256 行) 是最大的组件，需要重点审查组件设计
- markdown 渲染安全（XSS via react-markdown）是前端独有的安全关注点
- 前端没有 WebSocket 代码（ROADMAP 中提到的），不需要审查 WebSocket 安全
- 作为 v0.0.4 milestone 的最后一个 phase，审查报告完成后 milestone 可关闭

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 14-Frontend 代码审查*
*Context gathered: 2026-06-09*
