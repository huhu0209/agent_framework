# Retrospective

## Milestone: v0.0.1 — 彻底 Code Review

**Shipped:** 2026-05-29
**Phases:** 5 | **Plans:** 12 | **Tasks:** 14

### What Was Built

对框架层全部已实现代码做了系统性 Code Review：
- 修复 3 个 Bug（Path import、类型注解、immutability）
- 安全加固 3 项（路径沙箱、环境注入、SecretStr）
- 产出 3 份结构化审查报告（SECURITY-REVIEW.md、ARCH-REVIEW.md、PERF-REVIEW.md）
- 补充 12 个关键路径测试，总计 687 测试通过

### What Worked

- **Phase 分层策略** — Bug→安全→架构→性能→测试 的依赖链避免了返工
- **TDD 流程** — 每个 Bug 修复先写 RED 测试，保证了正确性
- **Wave 并行执行** — Phase 5 的 3 个无冲突 plan 并行运行，节省时间
- **审查报告分级** — HIGH/MEDIUM/LOW 分级让后续改进有优先级参考

### What Was Inefficient

- **Phase 01 有 3 个 plan 但 ROADMAP 只列了 2 个** — 01-03 是执行中追加的，tracking 不一致
- **Phase 05-02 SUMMARY 叙述误导** — 声称 auto-fixed safe_path 但 Phase 02 已完成，造成信息噪音
- **Nyquist validation 不完整** — 仅 2/5 phases 有 VALIDATION.md

### Patterns Established

- `safe_path()` 作为文件操作的标准安全入口
- `model_copy()` 作为 Pydantic 不可变性的标准模式
- `os.replace()` 作为原子文件写入的标准模式
- scaffold docstring 格式：中文标记 purpose/status/expected functionality

### Key Lessons

1. 审查型 milestone 的价值：结构化报告比 ad-hoc 修复更有长期价值
2. 测试数量不是唯一指标 — 关键路径覆盖比总数更重要
3. Tech Debt 命名要精确 — LOW 级别不等于可以忽略，需要跟踪

### Cost Observations

- 5 个 phase，每个 phase 含 discuss→plan→execute→verify
- 大量并行 agent 调用用于研究和验证
- Phase 5 wave 并行显著减少了 wall-clock 时间

---

## Milestone: v0.0.2 — Agent 扩展与编排

**Shipped:** 2026-05-29
**Phases:** 3 | **Plans:** 9

### What Was Built

从单一 ReAct Agent 扩展为多类型 Agent 体系：
- Agent ABC + AgentEvent 统一事件模型（AgentLoop/PlanAndSolve/Reflection 三种 Agent）
- OrchestratorEngine 编排引擎（启发式复杂度评估 + agent_factory）
- 声明式 Agent 配置（.md frontmatter → 可运行实例）
- Tavily 真实搜索工具替换 mock
- A2A 协议（纯 ASGI + AgentCard + API-key 认证）
- 125 个新测试，总计 812 测试通过

### What Worked

- **Agent ABC 设计** — 仅约束 run() 不约束 __init__，子类自由度极高
- **TDD 红-绿循环** — 每个 plan 严格 RED→GREEN→verify，零回归
- **Phase 并行** — Phase 7 的 3 个 plan 按 wave 顺序执行，无返工
- **Phase 6→7→8 依赖链** — Agent 类型 → 编排 → 跨 Agent 通信，自然递进

### What Was Inefficient

- **同日完成两个 milestone** — v0.0.1 和 v0.0.2 同日归档，文档压力大
- **MILESTONES.md 遗漏** — 归档流程跳过了 MILESTONES.md 条目写入
- **RETROSPECTIVE.md 遗漏** — v0.0.2 回顾未及时记录

### Patterns Established

- Agent 类型层次：Agent(ABC) → AgentLoop/PlanAndSolve/Reflection
- AgentEvent → LoopEvent 继承链（向后兼容）
- agent_factory 模式：编排引擎按需创建 Agent 实例
- flat frontmatter Agent 配置（不引入 pyyaml）
- 纯 ASGI 实现协议（不依赖 FastAPI）

### Key Lessons

1. 继承设计要尽早确立 — Agent ABC 一旦定下，后续 3 个子类和编排引擎都顺畅
2. 硬上限防循环 — replan ≤ 2、reflection ≤ 2、agent chain ≤ 3，防止 LLM 无限循环
3. 归档流程要完整执行 — 跳过步骤（如 MILESTONES.md）会导致后续补录

### Cost Observations

- 3 个 phase，每个含 discuss→plan→execute→verify
- Phase 8 (A2A) 3 个 plan 全天完成，executor 并行高效
- 框架层 ~12,500 行源码 + ~9,000 行测试

---

## Cross-Milestone Trends

| Metric | v0.0.1 | v0.0.2 |
|--------|--------|--------|
| Phases | 5 | 3 |
| Plans | 12 | 9 |
| Tests (start→end) | 630 → 687 | 687 → 812 |
| Tech Debt items | 14 (all LOW) | 14 + 1 (orchestrator heuristic) |
| Timeline (days) | 17 | <1 |
| Reports produced | 3 (SEC/ARCH/PERF) | 0 (building phase) |
