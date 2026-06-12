# Phase 25: Address Tech Debt — Integration Warnings + Stale Docs - Context

**Gathered:** 2026-06-12
**Status:** Ready for planning

<domain>
## Phase Boundary

v0.0.6 的收尾清理阶段 — 解决两个技术债务：

1. **Asyncio 警告验证**（ROADMAP WR-01/02/03）— STATE.md deferred 列表中的 "asyncio timing/cleanup warnings"（pre-existing from v0.0.1）。当前 `pytest -W all` 运行 1146 测试零 asyncio 警告。需确认是否已自愈（pytest-asyncio 版本更新）或是否有隐藏场景仍存在警告。

2. **过时文档更新** — v0.0.4~v0.0.6 引入大量代码变更但文档未同步更新。具体涉及：
   - `README.md`：错误类名、缺失模块、过时 roadmap
   - `REQUIREMENTS.md`：14 项已完成需求标记为未完成、可追溯性表过时
   - `PROJECT.md`：Current State 停留在 v0.0.5，Phase 24 状态为 executing
   - `CONCERNS.md`：多条已知问题已解决但未更新
   - `STATE.md`：Deferred items 中 WR-01/02/03 需核实

**非本阶段范围：** 新功能、API 变更、代码重构。仅清理验证和文档同步。

</domain>

<decisions>
## Implementation Decisions

### Asyncio 警告验证
- **D-01:** 采用双层验证策略 — (1) 标准 `pytest -W all` 确认零 asyncio 警告；(2) `pytest -W error::DeprecationWarning -W error::PendingDeprecationWarning` 捕获潜在废弃警告。如两层均通过，确认 WR-01/02/03 已自愈
- **D-02:** 从 STATE.md Deferred Items 中移除 "WR-01/02/03 asyncio timing/cleanup" 条目，标记为 resolved-by-environment-update

### 过时文档更新策略
- **D-03:** 采用"全面刷新"策略 — 将所有过时文档更新至 v0.0.6 完成时的真实状态，而非最小修补。原因：(a) v0.0.6 是 milestone 收尾，文档应是里程碑状态的准确快照；(b) 下个 milestone 的参与者需依赖这些文档
- **D-04:** README.md 更新范围：(a) 修正 "CommandRouter" → "CommandDispatcher"；(b) 项目结构增加 config/ 和 rules/ 模块；(c) Roadmap 更新至 v0.0.6 完成状态；(d) 模块概览表增加 ConfigLoader、RuleLoader 条目；(e) 测试数量更新为 1146

### REQUIREMENTS.md 更新
- **D-05:** 将 Phase 23 完成的 5 项需求（ADP-04~08）标记为 `[x]`
- **D-06:** 将 Phase 24 完成的 6 项需求（INS-03, INS-06, INT-01~06）标记为 `[x]`（注：INT-05 的 "1002+" 已满足，实际 1146）
- **D-07:** 更新 Traceability 表 — 将 ADP-04~08 对应 Phase 23 状态改为 Complete，将 INS-03/INS-06/INT-01~06 对应 Phase 24 状态改为 Complete
- **D-08:** 更新 REQUIREMENTS.md 末尾的 "Last updated" 时间戳

### PROJECT.md 更新
- **D-09:** 更新 "Current State" 部分 — Phase 24 已完成，v0.0.6 仅剩 Phase 25
- **D-10:** 更新 "Shipped v0.0.5" 之后的段落 — 添加 v0.0.6 进展说明（Phases 20-24 完成，1146 测试）
- **D-11:** 更新 "Last updated" 时间戳

### CONCERNS.md 处理
- **D-12:** 标记已解决的问题为 ✅Resolved 而非直接删除。保留原始记录作为历史参考，添加解决时间和说明
- **D-13:** 需要标记为 Resolved 的问题：
  - "Backend is entirely scaffold" → 已在 v0.0.3~v0.0.6 逐步实现
  - "Orchestrator engine and router are empty" → 已在 v0.0.2 实现
  - "Agent tool dispatch is a stub" → 已在 v0.0.2 实现（Sub-Agent 委派）
  - "web_search is a mock" → 已在 v0.0.2 替换为 Tavily（AsyncTavilyClient）
  - "CommandPolicy is a placeholder" → 保留（确实仍为 placeholder）
- **D-14:** 不重新审计 CONCERNS.md 中尚未解决的问题 — 本阶段仅更新已知已解决条目

### STATE.md 更新
- **D-15:** 从 Deferred Items 表中移除 "WR-01/02/03 asyncio timing/cleanup" 行
- **D-16:** 更新 Current Position — Phase 25 context gathered
- **D-17:** 更新 progress 百分比 — 5/6 phases complete → 83%

### Claude's Discretion
- 各文档更新的具体措辞和详细程度
- README.md 是否需要添加 v0.0.6 Config System 使用示例
- CONCERNS.md 已解决标记的格式（时间戳 + 解决版本号）
- 是否需要更新 `.planning/codebase/` 下的其他文档（ARCHITECTURE.md、STRUCTURE.md 等）
- 测试文件是否需要新增验证文档一致性的测试

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 需要更新的文档（本阶段目标）
- `README.md` — 项目主文档，需修正错误、更新模块列表和 roadmap
- `.planning/REQUIREMENTS.md` — 需求文档，14 项已完成需求需打勾 + 可追溯性表更新
- `.planning/PROJECT.md` — 项目文档，Current State 需反映 v0.0.6 进展
- `.planning/codebase/CONCERNS.md` — 已知问题清单，多条已解决需标记
- `.planning/STATE.md` — 项目状态，deferred items 和 current position 需更新

### 参考文档（了解当前状态）
- `.planning/ROADMAP.md` — Phase 25 目标和成功标准
- `.planning/codebase/ARCHITECTURE.md` — 框架架构，了解 config/ 和 rules/ 模块位置
- `.planning/codebase/STRUCTURE.md` — 文件结构，验证 README 项目结构是否一致

### Phase 24 完成（文档更新的依据）
- `.planning/phases/24-backend-integration-e2e-wiring-path-scoped-rules/24-REVIEW.md` — Phase 24 代码审查结果（WR-01/02/03 已修复）
- `.planning/phases/24-backend-integration-e2e-wiring-path-scoped-rules/24-01-SUMMARY.md` — Phase 24 执行摘要
- `.planning/phases/24-backend-integration-e2e-wiring-path-scoped-rules/24-02-SUMMARY.md`
- `.planning/phases/24-backend-integration-e2e-wiring-path-scoped-rules/24-03-SUMMARY.md`

</canonical_refs>

<code_context>
## Existing Code Insights

### 当前测试状态
- 1146 tests pass，零 asyncio 警告（`pytest -W all` 验证）
- v0.0.6 新增 144 测试（从 1002 增至 1146），覆盖 config、adapters、rules、assembler、e2e

### 过时文档具体问题清单

**README.md:**
- Line 84: `CommandRouter` → 实际代码 `CommandDispatcher`
- Line 56-71: 项目结构缺少 `config/`（Phase 20-21）和 `rules/`（Phase 24）
- Line 94-103: Roadmap 止于 Phase 13，缺少 v0.0.4~v0.0.6
- Line 76-90: 模块概览表缺少 ConfigLoader、RuleLoader
- 测试数量应为 1146（非 964）

**REQUIREMENTS.md:**
- Lines 76, 79: INS-03, INS-06 应为 `[x]`（Phase 24 完成）
- Lines 86-90: ADP-04~08 应为 `[x]`（Phase 23 完成）
- Lines 95-100: INT-01~06 应为 `[x]`（Phase 24 完成）
- Lines 150-162: Traceability 表 ADP-04~08、INT-01~06 状态应为 Complete

**PROJECT.md:**
- Line 165: "Shipped v0.0.5" 之后需添加 v0.0.6 进展
- Line 167: "Current: v0.0.6" 描述需更新
- Line 50: Active requirements 中 v0.0.6 描述可能需要更新

**CONCERNS.md:**
- Lines 7-10: "Backend entirely scaffold" → 已实现（v0.0.3~v0.0.6）
- Lines 12-18: "Orchestrator engine and router empty" → 已实现（v0.0.2）
- Lines 20-23: "Agent tool dispatch stub" → Sub-Agent 已实现（v0.0.2）
- Lines 32-35: "web_search mock" → Tavily 真实搜索（v0.0.2）

### Established Patterns
- v0.0.6 所有 phase 零回归约束 — 本 phase 不修改任何源码，仅文档更新
- CONCERNS.md 使用 Issue/Files/Impact/Fix approach 格式 — 已解决条目追加 ✅ 标记和解决说明

</code_context>

<specifics>
## Specific Ideas

- Asyncio 警告验证命令：
  ```bash
  # 标准验证
  cd framework && pytest tests/ -v -W all 2>&1 | grep -iE "(warning|asyncio.*cleanup|timing)"

  # 严格模式（将废弃警告转为错误）
  cd framework && pytest tests/ -W error::DeprecationWarning -W error::PendingDeprecationWarning
  ```

- REQUIREMENTS.md 批量更新（Phase 23 完成的 5 项 + Phase 24 完成的 6 项 = 11 项 `[ ]` → `[x]`，加上 INS-03/INS-06 共 13 项）
- 注意：ADP-04~08 在 Phase 23 的 REVIEW.md 中标记完成，INT-01~06 在 Phase 24 的 SUMMARY.md 中确认通过

- CONCERNS.md 已解决标记格式：
  ```markdown
  **✅ RESOLVED (v0.0.2):** Web search replaced with Tavily AsyncTavilyClient integration.
  ```

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 25-Address Tech Debt — Integration Warnings + Stale Docs*
*Context gathered: 2026-06-12*
