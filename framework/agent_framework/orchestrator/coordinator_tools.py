"""Coordinator tools — spawn_worker, send_message, list_workers。

协调者 Agent 拥有的三个编排工具。每个工具通过 ToolUseContext.extra["worker_manager"]
访问 WorkerManager 实例。
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from agent_framework.llm.types import ToolParameterSchema
from agent_framework.tools.types import ToolResult, ToolSpec

if TYPE_CHECKING:
    from agent_framework.orchestrator.worker_agent import WorkerManager


def _get_manager(ctx) -> WorkerManager | None:
    from agent_framework.orchestrator.worker_agent import WorkerManager
    manager = ctx.extra.get("worker_manager")
    if not isinstance(manager, WorkerManager):
        return None
    return manager


async def _handle_spawn_worker(args: dict, ctx) -> ToolResult:
    manager = _get_manager(ctx)
    if manager is None:
        return ToolResult(content="WorkerManager not available", is_error=True)
    worker_name = args["worker_name"]
    prompt = args["prompt"]
    try:
        handle = await manager.spawn(worker_name, prompt)
        return ToolResult(content=json.dumps({
            "worker_id": handle.id,
            "worker_name": handle.worker_name,
            "status": handle.status,
            "output": handle.output,
            "error": handle.error,
        }, ensure_ascii=False))
    except KeyError:
        return ToolResult(
            content=f"Worker '{worker_name}' not found in registry",
            is_error=True,
        )


async def _handle_send_message(args: dict, ctx) -> ToolResult:
    manager = _get_manager(ctx)
    if manager is None:
        return ToolResult(content="WorkerManager not available", is_error=True)
    worker_id = args["worker_id"]
    message = args["message"]
    try:
        handle = await manager.send_message(worker_id, message)
        return ToolResult(content=json.dumps({
            "worker_id": handle.id,
            "worker_name": handle.worker_name,
            "status": handle.status,
            "output": handle.output,
            "error": handle.error,
        }, ensure_ascii=False))
    except KeyError:
        return ToolResult(
            content=f"Worker '{worker_id}' not found",
            is_error=True,
        )


async def _handle_list_workers(args: dict, ctx) -> ToolResult:
    manager = _get_manager(ctx)
    if manager is None:
        return ToolResult(content="WorkerManager not available", is_error=True)
    status_filter = args.get("status", "all")
    workers = manager.list_workers(status=status_filter)
    items = []
    for w in workers:
        item = {"id": w.id, "worker_name": w.worker_name, "status": w.status}
        if w.status == "completed" and w.output:
            item["output_preview"] = w.output[:200]
        if w.error:
            item["error"] = w.error
        items.append(item)
    return ToolResult(content=json.dumps({"workers": items}, ensure_ascii=False))


def create_coordinator_tools(manager: WorkerManager) -> list[ToolSpec]:
    """创建协调者工具列表。"""
    return [
        ToolSpec(
            name="spawn_worker",
            description=(
                "派生一个 Worker 执行子任务。"
                "worker_name 必须是已注册的 Worker 名称。"
                "prompt 必须自包含所有上下文——Worker 看不到你的对话历史。"
                "返回 Worker 的执行结果。"
            ),
            parameters=ToolParameterSchema(
                properties={
                    "worker_name": {
                        "type": "string",
                        "description": "要派生的 Worker 名称（必须已注册）",
                    },
                    "prompt": {
                        "type": "string",
                        "description": "给 Worker 的完整任务指令，必须自包含所有上下文",
                    },
                },
                required=["worker_name", "prompt"],
            ),
            handler=_handle_spawn_worker,
            timeout_ms=120_000,
        ),
        ToolSpec(
            name="send_message",
            description=(
                "向已完成的 Worker 发送追加指令。"
                "Worker 会基于之前的输出继续工作。"
                "适合：调整方向、补充信息、深入分析。"
            ),
            parameters=ToolParameterSchema(
                properties={
                    "worker_id": {
                        "type": "string",
                        "description": "目标 Worker 的 ID（由 spawn_worker 返回）",
                    },
                    "message": {
                        "type": "string",
                        "description": "追加给 Worker 的指令",
                    },
                },
                required=["worker_id", "message"],
            ),
            handler=_handle_send_message,
            timeout_ms=120_000,
        ),
        ToolSpec(
            name="list_workers",
            description=(
                "查看所有已派生 Worker 的状态。"
                "适合：检查进度、回顾结果。"
            ),
            parameters=ToolParameterSchema(
                properties={
                    "status": {
                        "type": "string",
                        "description": "过滤状态：running、completed、failed、all（默认 all）",
                    },
                },
                required=[],
            ),
            handler=_handle_list_workers,
            timeout_ms=5_000,
        ),
    ]
