# Phase 1: Bug 修复审查 - Context

**Gathered:** 2026-05-28
**Status:** Ready for planning

<domain>
## Phase Boundary

修复框架层（`framework/agent_framework/`）5 个已知 Bug，每个修复有对应测试验证，全量测试通过无回归。

**Bug 列表：**
1. `agent_loop.py` 缺少 `Path` import
2. `TaskManager._apply_changes` 类型注解错误（`pending_writes`）
3. `HITLManager.create_pending` 使用已废弃 `get_event_loop`
4. `normalize_messages` 原地变异 Pydantic 模型
5. `_apply_changes` 非原子性依赖清理

</domain>

<decisions>
## Implementation Decisions

### _apply_changes 原子性策略
- **D-01:** 使用 batch writes in lock — 在 lock 内收集所有待写的依赖清理变更，最后一次性写入，避免中途失败导致部分写入
- **D-02:** Batch write 失败时 log warning + retry later（不回滚已完成的 task 状态变更）。原因：失败极罕见，回滚会丢失有效变更，依赖清理不完整不影响正确性

### pending_writes 类型修复
- **D-03:** 类型注解修正为 `list[Task]`。代码只 append Task 对象、for 循环直接当 Task 用，`list[tuple[Task]]` 为笔误

### 测试验证
- **D-04:** 每个 bug 修复新增针对性测试（TDD: RED → GREEN）。符合 REQUIREMENTS.md "每个修复有对应测试验证"

### Claude's Discretion
- Bug #1（Path import）、#3（deprecated API）、#4（normalize 变异）修复方向明确，Claude 可自行选择最佳修复方式
- 测试组织方式由 planner 决定（新测试文件 vs 追加到现有文件）

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Bug 详情与位置
- `.planning/codebase/CONCERNS.md` §Known Bugs — 5 个已知 Bug 的触发条件、文件位置、影响分析
- `.planning/REQUIREMENTS.md` §R2: Bug 修复审查 — 验收标准和已知 Bug 列表

### 架构与代码结构
- `.planning/codebase/STRUCTURE.md` — 文件结构、模块位置、命名规范
- `.planning/codebase/ARCHITECTURE.md` — 模块依赖关系和数据流

### 可复用模式
- `.planning/codebase/CONVENTIONS.md` — 编码规范，修复需遵循

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `framework/tests/test_task_manager.py` — 现有 TaskManager 测试，修复 #2 和 #5 的测试可参考其 fixture 和 assertion 模式
- `framework/tests/test_normalize_messages.py` — 现有 normalize 测试，修复 #4 需扩展
- `framework/tests/test_hitl.py` — 现有 HITL 测试，修复 #3 需扩展

### Established Patterns
- AsyncIO Lock 模式：`TaskManager` 使用 `self._lock = asyncio.Lock()` 序列化文件写入
- Pydantic v2 不可变模式：`model_copy(update={...})` 创建新对象而非原地变异
- 测试组织：每个模块对应 `test_{module}.py`，测试函数命名 `test_{scenario}_{expected}`

### Integration Points
- `framework/agent_framework/tasks/manager.py:185-226` — `_apply_changes` 方法（Bug #2 + #5）
- `framework/agent_framework/tasks/manager.py:228-236` — `_clear_dependency` 方法
- `framework/agent_framework/llm/transform/_normalize.py:45` — `normalize_messages` 变异行（Bug #4）
- `framework/agent_framework/safety/hitl.py:47` — `create_pending` deprecated API（Bug #3）
- `framework/agent_framework/agents/agent_loop.py:87` — `skill_dirs: list[Path]` 缺少 import（Bug #1）

</code_context>

<specifics>
## Specific Ideas

无特定参考 — 修复方案遵循最小改动原则，仅修复 Bug 本身，不做额外重构。

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 1-Bug 修复审查*
*Context gathered: 2026-05-28*
