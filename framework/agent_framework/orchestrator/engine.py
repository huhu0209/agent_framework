"""多 Agent 编排引擎，协调多个 Agent 的执行策略与任务分配。

当前状态: scaffold（预留模块，尚未实现）。

预期功能:
- 支持多种编排策略（顺序、并行、层级），按场景选择执行模式
- 任务分配与结果聚合，管理 Agent 间的上下文传递
- 全局上下文管理，维护跨 Agent 的共享状态与通信

相关模块:
- agent_framework.orchestrator.planner — Session 规划与状态管理
- agent_framework.orchestrator.router — LLM 路由与 Provider 选择
- agent_framework.agents.agent_loop — ReAct Agent Loop
- agent_framework.teams.manager — 团队 Agent 管理
"""
