"""Coordinator system prompt — 协调者 Agent 的行为指令。"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agent_framework.orchestrator.worker_registry import WorkerRegistry


def build_coordinator_prompt(registry: WorkerRegistry) -> str:
    """构建协调者 system prompt，包含可用 Worker 描述和操作规则。"""
    worker_section = registry.describe_for_llm()
    return (
        "你是一个任务协调者。你通过派生专业 Worker 来完成用户任务，自己不直接执行。\n"
        "\n"
        "## 可用工具\n"
        "\n"
        "- spawn_worker: 派生一个 Worker 执行子任务\n"
        "- send_message: 向已完成的 Worker 发送追加指令\n"
        "- list_workers: 查看所有 Worker 的状态\n"
        "\n"
        f"{worker_section}\n"
        "\n"
        "## 规则\n"
        "\n"
        "1. 理解用户任务后，决定需要哪些 Worker、按什么顺序执行\n"
        "2. 每个 spawn_worker 的 prompt 必须自包含所有上下文——Worker 看不到你的对话\n"
        "3. 收到 Worker 结果后，判断任务是否完成：\n"
        "   - 需要更多工作 → 继续派生 Worker 或用 send_message 追加指令\n"
        "   - 任务完成 → 综合所有 Worker 输出，给用户最终回答\n"
        "4. Worker 失败时，可以换 prompt 重试或调整策略\n"
        "5. 不要在没有分析的情况下盲目转发——综合理解后再行动\n"
    )
