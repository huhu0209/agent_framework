# Phase 15: Framework 死代码与快速修复 - Context

**Gathered:** 2026-06-10
**Status:** Ready for planning

<domain>
## Phase Boundary

清理 framework/agent_framework/ 中所有未使用 import（32 个 F401/F821 问题），修复 agent_loop.py logger 未定义 NameError，修复 llm/base.py httpx 在 TYPE_CHECKING guard 外引用。

本 phase 纯机械性清理，无功能变更。覆盖 FW-DEAD-01~06（6 项死代码清理）和 FW-SEC-01（1 项 httpx 修复）。

</domain>

<decisions>
## Implementation Decisions

### httpx TYPE_CHECKING 修复（FW-SEC-01）
- **D-01:** 优先使用 `from __future__ import annotations` — llm/base.py 已有约 75% 的框架文件使用此特性，保持一致性。如果该文件已有此 import 则只需将 httpx import 移入 TYPE_CHECKING guard

### 执行策略
- **D-02:** 单 plan 一次完成 — 32 个问题全是简单删除 import 行或添加 logger 定义，预计 30 分钟内完成
- **D-03:** 使用 ruff --fix 自动修复 F401（未使用 import），手动验证 F821（logger 和 httpx）

### 验证策略
- **D-04:** ruff check 验证 + 全量 pytest 双重验证 — 先 `ruff check --select F401,F821 framework/` 确认零 warning，再 `cd framework && pytest tests/ -v` 确认 964+ 测试通过

### Claude's Discretion
- 具体 import 删除的顺序和分批方式
- llm/base.py 的 httpx 修复具体方案（`from __future__ import annotations` 或移入 TYPE_CHECKING guard）
- 是否需要补充测试覆盖 logger 修复后的行为

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 审查报告（问题来源）
- `docs/reviews/REVIEW-FRAMEWORK.md` — ruff 基线 32 个 F401/F821 问题清单（带文件:行号精确定位）

### 需求定义
- `.planning/REQUIREMENTS.md` — FW-DEAD-01~06, FW-SEC-01 需求定义
- `.planning/ROADMAP.md` — Phase 15 目标、成功标准、范围定义

### 编码规范
- `.planning/codebase/CONVENTIONS.md` — Import 组织顺序、TYPE_CHECKING guard 模式、logging 模式

### 框架源码（修改目标）
- `framework/agent_framework/llm/` — 16 个未使用 import + httpx 引用问题
- `framework/agent_framework/llm/transform/` — 3 个未使用 import
- `framework/agent_framework/agents/agent_loop.py` — logger 未定义 + dataclasses.field 未使用
- `framework/agent_framework/tools/context/token_counter.py` — 2 个未使用 import
- `framework/agent_framework/hooks/manager.py` — 1 个未使用 import
- `framework/agent_framework/orchestrator/worker_agent.py` — 1 个未使用 import
- `framework/agent_framework/tasks/runner.py` — 1 个未使用 import
- `framework/agent_framework/teams/manager.py` — 1 个未使用 import
- `framework/agent_framework/agents/config.py` — 1 个未使用 import
- `framework/agent_framework/agents/reflection.py` — 1 个未使用 import
- `framework/agent_framework/agents/sub_agent.py` — 1 个未使用 import

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- ruff 0.15.16 — 已在 Phase 12 中使用，可直接用于自动修复 F401
- REVIEW-FRAMEWORK.md ruff 基线 — 精确定位每个问题（文件:行号），无需重新扫描

### Established Patterns
- `from __future__ import annotations` 在 62/83 源文件中使用（~75%）
- `import logging; logger = logging.getLogger(__name__)` 是框架标准 logging 模式
- TYPE_CHECKING guard 模式在 agent_loop.py, router.py, manager.py, assembler.py 中使用

### Integration Points
- 本 phase 修改不改变任何公共 API 或行为
- Phase 16（Framework 安全修复）依赖本 phase 先清理死代码

</code_context>

<specifics>
## Specific Ideas

- 32 个 F401 问题中，llm/ 层占 16 个（items 7-24），是最密集的区域
- F821 有 2 个：logger 未定义（agent_loop.py:288）和 httpx 引用（llm/base.py:173）
- agent_loop.py 同时有 F401（dataclasses.field）和 F821（logger）问题
- 所有修改都是删除 import 行或添加一行 logger 定义，无逻辑变更

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 15-Framework 死代码与快速修复*
*Context gathered: 2026-06-10*
