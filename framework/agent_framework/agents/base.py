"""Agent 基类协议定义，为不同 Agent 类型提供统一接口契约。

当前状态: scaffold（预留模块，尚未实现）。

预期功能:
- 定义 Agent 协议/接口（Protocol 或 ABC），规范 Agent 行为契约
- 为 SubAgent、TeamAgent 等派生类型提供共享基础类型
- 统一 Agent 的输入输出类型定义，便于编排引擎调用

相关模块:
- agent_framework.agents.agent_loop — 已实现的 ReAct Agent Loop
- agent_framework.agents.sub_agent — 子 Agent 管理
- agent_framework.teams.manager — 团队 Agent 管理
"""
