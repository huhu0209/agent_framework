# ROADMAP.md — v0.0.1 彻底 Code Review

## Phase 1: Bug 修复审查

**目标：** 修复所有已知 Bug，确保代码正确性。

**依赖：** 无

**Plans:** 3/3 plans complete

Plans:
- [x] 01-01-PLAN.md — 修复 3 个独立单文件 Bug（Path import / deprecated API / normalize 变异）
- [x] 01-02-PLAN.md — 修复 TaskManager 类型注解 + 非原子性依赖清理

**验证：** 全部 630 测试通过，无 `NameError`、类型错误或数据不一致。

---

## Phase 2: 安全审查与修复

**目标：** 审查安全问题，修复 CRITICAL 级别。

**依赖：** Phase 1（Bug 修复完成后进行安全审查）

**Plans:** 2 plans

Plans:
- [ ] 02-01-PLAN.md — 修复路径沙箱（CRITICAL）+ MCP 环境注入（HIGH）
- [ ] 02-02-PLAN.md — SecretStr 迁移（MEDIUM）+ 产出 SECURITY-REVIEW.md

**验证：** 所有 CRITICAL 安全问题已修复，SECURITY-REVIEW.md 已生成。

---

## Phase 3: 架构与代码质量审查

**目标：** 系统性审查架构设计，产出改进建议。

**依赖：** Phase 1

**任务：**
1. 审查 AgentLoop 参数膨胀问题
2. 审查 ToolRouter.dispatch 职责划分
3. 审查 TaskManager._apply_changes 复杂度
4. 审查 ToolUseContext.extra 类型安全
5. 清理空文件（base.py）或明确标记为 scaffold
6. 产出 ARCH-REVIEW.md

**验证：** ARCH-REVIEW.md 已生成，包含具体改进建议和优先级。

---

## Phase 4: 性能与数据安全审查

**目标：** 修复影响数据安全的性能问题，记录其他性能优化建议。

**依赖：** Phase 1

**任务：**
1. 修复 MessageBus inbox 非原子读写（数据丢失风险）
2. 修复 _read_until_header_end 逐字节读取性能
3. 记录同步 I/O 阻塞问题及改进方案
4. 记录 TaskManager 全量扫描问题及改进方案
5. 产出 PERF-REVIEW.md

**验证：** 数据安全项已修复，PERF-REVIEW.md 已生成。

---

## Phase 5: 测试覆盖补充

**目标：** 补充关键路径测试，提高可靠性。

**依赖：** Phase 1, Phase 2

**任务：**
1. 补充 TeamManager loop 行为测试
2. 补充安全边界与工具执行集成测试
3. 补充 PermissionPipeline 完整流程测试
4. 运行全量测试确认无回归

**验证：** 新增测试全部通过，覆盖 HIGH 优先级缺口。
