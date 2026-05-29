---
phase: 6
phase_slug: 06-agent-types
created: 2026-05-29
---

# Phase 6: Agent 类型扩展 - Validation Strategy

## Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 |
| Config file | none — pytest 自动发现 tests/ 目录 |
| Quick run command | `cd framework && pytest tests/ -x -q` |
| Full suite command | `cd framework && pytest tests/ -v` |

## Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | Created In |
|--------|----------|-----------|-------------------|------------|
| AGENT-01 | AgentEvent dataclass 字段和默认值 | unit | `pytest tests/test_agent_base.py -x` | Plan 06-01 |
| AGENT-02 | Agent ABC 不可实例化，子类必须实现 run() | unit | `pytest tests/test_agent_base.py -x` | Plan 06-01 |
| AGENT-03 | LoopEvent 继承 AgentEvent, AgentLoop 继承 Agent | unit | `pytest tests/test_agent_loop.py -x` | Existing |
| AGENT-04 | 类型标注更新后 runner/manager/sub_agent 功能正常 | unit | `pytest tests/test_sub_agent.py tests/test_task_runner.py tests/test_teams_manager.py -x` | Existing |
| AGENT-05 | 687 测试全部通过 | regression | `pytest tests/ -v` | Existing |
| PLAN-01 | PlanAndSolveAgent 实例化和基本流程 | unit | `pytest tests/test_plan_and_solve.py -x` | Plan 06-02 |
| PLAN-02 | 计划生成调用 parse_plan_response | unit | `pytest tests/test_plan_and_solve.py::test_plan_generation -x` | Plan 06-02 |
| PLAN-03 | 每步独立 AgentLoop，步骤间无 context 累积 | unit | `pytest tests/test_plan_and_solve.py::test_step_isolation -x` | Plan 06-02 |
| PLAN-04 | 偏离检测 + replan 上限 2 次 | unit | `pytest tests/test_plan_and_solve.py::test_drift_detection -x` | Plan 06-02 |
| PLAN-05 | 空计划 fallback 到 ReAct | unit | `pytest tests/test_plan_and_solve.py::test_fallback -x` | Plan 06-02 |
| REFL-01 | ReflectionAgent 三阶段循环 | unit | `pytest tests/test_reflection.py -x` | Plan 06-03 |
| REFL-02 | ReflectionVerdict JSON 解析 + 容错 | unit | `pytest tests/test_reflection.py::test_verdict_parsing -x` | Plan 06-03 |
| REFL-03 | 改进轮次硬上限 2 次 | unit | `pytest tests/test_reflection.py::test_improvement_limit -x` | Plan 06-03 |
| REFL-04 | critique 注入下一轮用户消息 | unit | `pytest tests/test_reflection.py::test_critique_injection -x` | Plan 06-03 |

## Sampling Rate

- **Per task commit:** `cd framework && pytest tests/ -x -q`
- **Per wave merge:** `cd framework && pytest tests/ -v`
- **Phase gate:** Full suite green (687+ tests) before `/gsd:verify-work`

## Test Files to Create

| File | Requirements | Plan |
|------|-------------|------|
| `framework/tests/test_agent_base.py` | AGENT-01, AGENT-02 | 06-01 |
| `framework/tests/test_plan_and_solve.py` | PLAN-01~05 | 06-02 |
| `framework/tests/test_reflection.py` | REFL-01~04 | 06-03 |

## Test Infrastructure Dependencies

- MockAdapter 需要扩展：支持返回包含 `<plan>` 标签的响应（PlanAndSolve 测试用）
- MockAdapter 需要扩展：支持返回 JSON 格式的 ReflectionVerdict（Reflection 测试用）
