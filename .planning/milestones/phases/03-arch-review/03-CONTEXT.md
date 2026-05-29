# Phase 3: 架构与代码质量审查 - Context

**Gathered:** 2026-05-28
**Status:** Ready for planning

<domain>
## Phase Boundary

系统性审查框架层（`framework/agent_framework/`）全部模块的架构设计，产出 ARCH-REVIEW.md 结构化报告，包含改进建议和优先级。

**范围：**
- 以 ROADMAP 列出的 5 个已知问题为骨架（AgentLoop 参数膨胀、ToolRouter 职责划分、TaskManager 复杂度、ToolUseContext 类型安全、空文件处理）
- 全面扫描所有模块，补充发现新的架构问题
- 标记 3 个空文件为 scaffold（base.py、engine.py、router.py）
- 仅审查+记录，不执行重构

**不包含：**
- 实际重构代码
- 性能问题（Phase 4 范围）
- 测试覆盖（Phase 5 范围）
- 安全问题（Phase 2 已完成）

</domain>

<decisions>
## Implementation Decisions

### 报告组织方式
- **D-01:** ARCH-REVIEW.md 按问题驱动组织 — 以 ROADMAP 列出的 5 个已知问题为骨架，每个问题包含「现状分析 + 改进建议 + 优先级」，全面扫描补充的新发现附在后面
- **D-02:** 架构问题分 3 级：HIGH（影响开发效率，短期内应重构）、MEDIUM（设计不够优，但可用）、LOW（锦上添花）。与 SECURITY-REVIEW.md 的分级风格保持一致

### 改进建议深度
- **D-03:** 方向级 — 每个问题记录：问题描述 + 改进方向（如"考虑 Builder 模式"）+ 优先级。不写具体接口设计、代码片段或迁移路径

### 空文件处理
- **D-04:** 3 个空文件全部保留（不删除），添加 module docstring 标记为 scaffold
- **D-05:** Docstring 格式：包含模块用途、当前状态（scaffold）、预期功能、相关模块引用。不添加占位类或函数签名

### 审查范围
- **D-06:** 全面扫描 — 5 个已知问题作为主体骨架，同时审查所有模块发现新问题。新发现也纳入 ARCH-REVIEW.md

### Claude's Discretion
- 全面扫描的具体发现由 reviewer 自行判断
- ARCH-REVIEW.md 的详细排版由 planner 决定
- Scaffold docstring 的具体措辞由 executor 决定

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 已知问题来源
- `.planning/codebase/CONCERNS.md` §Fragile Areas — 5 个已知架构问题的详细分析（文件位置、为何脆弱、安全修改建议）
- `.planning/codebase/CONCERNS.md` §Tech Debt — 其他技术债务（空文件、stub 实现、未接入功能）
- `.planning/REQUIREMENTS.md` §R3: 架构与设计审查 — 验收标准和重点审查列表
- `.planning/ROADMAP.md` §Phase 3 — 任务列表和验证标准

### 架构与代码结构
- `.planning/codebase/ARCHITECTURE.md` — 完整的模块依赖关系、数据流、组件职责、反模式分析
- `.planning/codebase/STRUCTURE.md` — 文件结构、模块位置、命名规范
- `.planning/codebase/CONVENTIONS.md` — 编码规范（命名、import、类型注解、不可变性模式）

### 核心源文件（审查目标）
- `framework/agent_framework/agents/agent_loop.py:71-93` — AgentLoop.__init__ 15 参数
- `framework/agent_framework/tools/router.py:58-156` — ToolRouter.dispatch 4 层职责
- `framework/agent_framework/tasks/manager.py:185-226` — _apply_changes 复杂变异逻辑
- `framework/agent_framework/tools/types.py:48-57` — ToolUseContext.extra dict[str, Any]
- `framework/agent_framework/agents/base.py` — 空文件（需标记 scaffold）
- `framework/agent_framework/orchestrator/engine.py` — 空文件（需标记 scaffold）
- `framework/agent_framework/orchestrator/router.py` — 空文件（需标记 scaffold）

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `.planning/codebase/CONCERNS.md` — 已有完整的架构问题清单，包含每个问题的文件位置、影响分析和改进方向。这是审查的核心输入，无需从头分析
- `.planning/codebase/ARCHITECTURE.md` §Pattern Overview / §Anti-Patterns — 已有模式总结和已知反模式
- Phase 2 的 `docs/reviews/SECURITY-REVIEW.md` — 可参考其格式和分级风格

### Established Patterns
- 框架使用 dataclass(frozen=True) 做不可变值对象，mutable dataclass 做状态对象
- Pydantic BaseModel 用于跨模块边界的数据和需序列化的数据
- 工具返回 ToolResult(is_error=True) 而非抛异常
- 每个 module 有中文 docstring 描述用途

### Integration Points
- ARCH-REVIEW.md 是 Phase 4（性能审查）和 Phase 5（测试覆盖）的输入
- 空文件 scaffold 标记影响 orchestrator 模块的未来实现计划

</code_context>

<specifics>
## Specific Ideas

无特定参考 — 这是一个审查+记录 phase，不涉及新功能设计。

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 3-架构与代码质量审查*
*Context gathered: 2026-05-28*
