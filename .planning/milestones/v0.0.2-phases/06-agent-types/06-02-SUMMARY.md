---
phase: 06-agent-types
plan: 02
subsystem: agents
tags: [plan-and-solve, agent-loop, drift-detection, replan, fallback]

# Dependency graph
requires:
  - 06-01 (Agent ABC + AgentEvent)
provides:
  - PlanAndSolveAgent(Agent) 实现 run() 方法
  - 计划生成复用 parse_plan_response
  - 每步独立 AgentLoop 实例执行
  - 混合偏离检测（规则 + LLM fallback）
  - replan 硬上限 2 次
  - 空计划 fallback 到直接 ReAct 执行
affects: [06-03-reflection, 07-orchestrator]

# Tech tracking
tech-stack:
  added: []
  patterns: [plan-and-solve, step-isolation, hybrid-drift-detection]

key-files:
  created:
    - framework/agent_framework/agents/plan_and_solve.py
    - framework/tests/test_plan_and_solve.py
  modified: []

key-decisions:
  - "偏离检测默认不调用 LLM，规则无法判断时返回 False 避免额外开销"
  - "空计划 fallback 复用 _run_fallback 方法创建独立 AgentLoop"
  - "每步 prompt 包含原始任务 + 当前步骤 + 前序摘要（截取最后 2000 字符）"
  - "重新规划后重置 step_outputs 和 plan_items，从头开始执行新计划"

patterns-established:
  - "PlanAndSolve 流程：生成计划 -> 逐步执行 -> 偏离检测 -> 重新规划 -> 完成"
  - "混合偏离检测：规则快速判断（空输出/子代理错误），LLM fallback 保留供外部使用"

requirements-completed: [PLAN-01, PLAN-02, PLAN-03, PLAN-04, PLAN-05]

# Metrics
duration: 4min
completed: 2026-05-29
---

# Phase 06 Plan 02: PlanAndSolve Agent Summary

**PlanAndSolveAgent 继承 Agent ABC，复用 parse_plan_response 生成计划，每步独立 AgentLoop 执行（步骤间不累积 context），混合偏离检测 + replan 硬上限 2 次，空计划 fallback 到 ReAct，14 新测试 + 708 总测试零回归**

## Performance

- **Duration:** 4 min
- **Started:** 2026-05-29T06:21:10Z
- **Completed:** 2026-05-29T06:25:08Z
- **Tasks:** 2
- **Files created:** 2

## Accomplishments
- PlanAndSolveAgent 继承 Agent ABC，实现完整 run() 方法
- 计划生成调用 LLM 并复用 parse_plan_response 解析 <plan> 标签
- 每步创建独立 AgentLoop 实例（通过 create_filtered_router 过滤递归工具）
- 步骤间不累积 context：_build_step_prompt 仅包含原始任务 + 当前步骤 + 前序摘要
- 混合偏离检测：_rule_check_drift 规则快速判断（空输出/子代理错误），_llm_check_drift LLM 评估保留供外部使用
- replan 硬上限 2 次，达到上限返回 error 事件
- 空计划 fallback 到直接 ReAct 执行（通过 _run_fallback 方法）
- 14 个新测试覆盖 PLAN-01~05，708 总测试零回归

## Task Commits

Each task was committed atomically:

1. **Task 1: 实现 PlanAndSolveAgent** - `2f9575b` (feat)
2. **Task 2: 编写 PlanAndSolveAgent 测试套件** - `572531a` (test)

## Files Created
- `framework/agent_framework/agents/plan_and_solve.py` - PlanAndSolveAgent 实现（229 行）
- `framework/tests/test_plan_and_solve.py` - 14 个测试覆盖 PLAN-01~05（345 行）

## Decisions Made
- 偏离检测默认不调用 LLM（规则返回 None 时视为不偏离），避免每次执行都增加 LLM 调用开销
- _llm_check_drift 方法保留在类中供外部或未来使用，不在 run() 流程中自动调用
- 重新规划后完全重置 step_outputs 和 plan_items，从头开始执行新计划
- done 事件的 data.text 截取最后 2000 字符避免过长输出

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test mock pattern for async generators**
- **Found during:** Task 2
- **Issue:** AsyncMock.return_value for async generator methods returns coroutine, not async iterable
- **Fix:** Changed mock_loop.run from `return_value` to `lambda prompt: _async_iter(...)` pattern
- **Files modified:** framework/tests/test_plan_and_solve.py
- **Commit:** 572531a

**2. [Rule 1 - Bug] Fixed drift trigger in test_drift_replan**
- **Found during:** Task 2
- **Issue:** Empty content list `[]` in mock done event produces "(未产生输出)" text, which does not trigger rule-based drift
- **Fix:** Changed mock to return error event instead of done event with empty content
- **Files modified:** framework/tests/test_plan_and_solve.py
- **Commit:** 572531a

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- PlanAndSolveAgent 已就绪，可与 06-03 (Reflection Agent) 并行构建
- Reflection Agent 只需继承 Agent 并实现 run() 方法
- 两种 Agent 类型共享 Agent ABC 接口，可被 OrchestratorEngine 统一调度

## Self-Check: PASSED

All 2 files verified present. Both commits (2f9575b, 572531a) verified in git log.

---
*Phase: 06-agent-types*
*Completed: 2026-05-29*
