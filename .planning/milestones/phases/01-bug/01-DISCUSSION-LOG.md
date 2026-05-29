# Phase 1: Bug 修复审查 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-28
**Phase:** 01-Bug 修复审查
**Areas discussed:** _apply_changes 原子性策略, pending_writes 类型语义, 测试验证粒度

---

## _apply_changes 原子性策略

### Q1: 原子性保证方式

| Option | Description | Selected |
|--------|-------------|----------|
| Batch writes in lock | 在 lock 内收集所有待写变更，最后一次性写入 | ✓ |
| Atomic rename per write | 用 temp file + os.replace 模式，参考 MemoryIndexManager._atomic_write | |
| Write with rollback | 收集变更后 try/except + rollback：先备份，写入失败则恢复 | |

**User's choice:** Batch writes in lock（推荐）

### Q2: 失败处理策略

| Option | Description | Selected |
|--------|-------------|----------|
| Fail all, 抛异常 | batch write 失败时回滚整个 _apply_changes 操作 | |
| Log + retry later | batch write 失败时 log warning，保留已完成的 task 变更 | ✓ |

**User's choice:** 推荐 Log + retry later（用户委托 Claude 决定）
**Notes:** 失败极罕见（磁盘满/权限错误），回滚会丢失有效变更，依赖清理不完整不影响正确性

---

## pending_writes 类型语义

### Q1: 类型修正方向

| Option | Description | Selected |
|--------|-------------|----------|
| list[Task] | 变量用法是 for dep_task in pending_writes: ...，直接是 Task 对象 | ✓ |
| list[tuple[...]] | 可能意图是 (task, reason) 元组，但代码从未构造 tuple | |

**User's choice:** list[Task]（推荐）
**Notes:** 原始 `list[tuple[Task]]` 为注解笔误

---

## 测试验证粒度

### Q1: 每个 bug 修复的验证方式

| Option | Description | Selected |
|--------|-------------|----------|
| 每个修复新增测试 | 为每个 bug 写针对性测试，先 RED 再 GREEN | ✓ |
| 仅运行全量测试 | 修复后跑 630 个现有测试确认不回归 | |
| 分级：复杂 bug 新增测试 | 只为 Bug #4、#5 新增测试，简单的依赖全量测试 | |

**User's choice:** 每个修复新增测试（推荐）
**Notes:** 符合 REQUIREMENTS.md "每个修复有对应测试验证"

---

## Claude's Discretion

- Bug #1（Path import）、#3（deprecated API）、#4（normalize 变异）修复方向明确，Claude 可自行选择最佳修复方式
- 测试组织方式（新文件 vs 追加到现有文件）由 planner 决定
- batch write 失败处理策略由 Claude 推荐（Log + retry later）

## Deferred Ideas

None — discussion stayed within phase scope
