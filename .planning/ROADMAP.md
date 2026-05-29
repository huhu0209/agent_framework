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

**Plans:** 2/2 plans complete

Plans:
- [x] 02-01-PLAN.md — 修复路径沙箱（CRITICAL）+ MCP 环境注入（HIGH）
- [x] 02-02-PLAN.md — SecretStr 迁移（MEDIUM）+ 产出 SECURITY-REVIEW.md

**验证：** 所有 CRITICAL 安全问题已修复，SECURITY-REVIEW.md 已生成。

---

## Phase 3: 架构与代码质量审查

**目标：** 系统性审查架构设计，产出改进建议。

**依赖：** Phase 1

**Plans:** 2/2 plans complete

Plans:
- [x] 03-01-PLAN.md — 产出 ARCH-REVIEW.md（12+ 架构发现，HIGH/MEDIUM/LOW 分级）
- [x] 03-02-PLAN.md — 3 个空文件添加 scaffold docstring

**验证：** ARCH-REVIEW.md 已生成，包含具体改进建议和优先级。

---

## Phase 4: 性能与数据安全审查

**目标：** 修复影响数据安全的性能问题，记录其他性能优化建议，产出 PERF-REVIEW.md。

**依赖：** Phase 1

**Plans:** 1/1 plan complete

Plans:
- [x] 04-01-PLAN.md — 修复 MessageBus 原子读写 + MCP header 高效读取 + 产出 PERF-REVIEW.md

**验证：** 675 测试通过。read_inbox 原子清零、MCP readline 替换、PERF-REVIEW.md（2 已修复 + 3 已记录）全部验证通过。

---

## Phase 5: 测试覆盖补充

**目标：** 补充关键路径测试，提高可靠性。

**依赖：** Phase 1, Phase 2

**Plans:** 4 plans

Plans:
- [ ] 05-01-PLAN.md — TeamManager _loop 深度行为测试（5 个测试，monkeypatch + AsyncMock）
- [ ] 05-02-PLAN.md — 安全边界集成测试（3 个 AgentLoop→ToolRouter→safe_path 全链路测试）
- [ ] 05-03-PLAN.md — PermissionPipeline 边界情况测试（4 个同步单元测试）
- [ ] 05-04-PLAN.md — 全量测试回归验证（675+ 测试通过）

**验证：** 新增 12 个测试全部通过，全量 675+ 测试无回归。
