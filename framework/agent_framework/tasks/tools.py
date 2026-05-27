"""Task 系统 — 4 个工具。"""

from __future__ import annotations

from agent_framework.llm.types import ToolParameterSchema
from agent_framework.tasks.manager import (
    MAX_ACTIVE_TASKS,
    TaskConflictError,
    TaskLimitError,
    TaskManager,
    TaskNotFoundError,
    TaskStatusError,
)
from agent_framework.tools.types import ToolResult, ToolSpec, ToolUseContext


def create_task_tools(task_manager: TaskManager) -> list[ToolSpec]:
    """创建 4 个 task 工具。"""

    async def handle_create(args: dict, ctx: ToolUseContext) -> ToolResult:
        try:
            task = task_manager.create(
                subject=args["subject"],
                description=args.get("description", ""),
            )
            return ToolResult(
                content=(
                    f"任务 #{task.id} 已创建: {task.subject}\n"
                    f"状态: {task.status.value}\n"
                    f"活跃任务: {task_manager.count_active()}/{MAX_ACTIVE_TASKS}"
                )
            )
        except TaskLimitError as e:
            return ToolResult(content=str(e), is_error=True)

    async def handle_update(args: dict, ctx: ToolUseContext) -> ToolResult:
        try:
            changes: dict = {}
            if "status" in args:
                changes["status"] = args["status"]
            if "owner" in args:
                changes["owner"] = args["owner"]
            if "add_blocked_by" in args:
                changes["add_blocked_by"] = args["add_blocked_by"]
            if "add_blocks" in args:
                changes["add_blocks"] = args["add_blocks"]

            task = task_manager.update(args["id"], **changes)
            return ToolResult(
                content=f"任务 #{task.id} 已更新: {task.subject} → {task.status.value}"
            )
        except (TaskNotFoundError, TaskConflictError, TaskStatusError) as e:
            return ToolResult(content=str(e), is_error=True)

    async def handle_list(args: dict, ctx: ToolUseContext) -> ToolResult:
        return ToolResult(content=task_manager.list_all())

    async def handle_get(args: dict, ctx: ToolUseContext) -> ToolResult:
        task = task_manager.get(args["id"])
        if task is None:
            return ToolResult(content=f"任务 #{args['id']} 不存在", is_error=True)
        return ToolResult(content=(
            f"任务 #{task.id}: {task.subject}\n"
            f"描述: {task.description}\n"
            f"状态: {task.status.value}\n"
            f"负责人: {task.owner or '无'}\n"
            f"等待: {', '.join(task.blocked_by) or '无'}\n"
            f"阻塞: {', '.join(task.blocks) or '无'}\n"
            f"创建: {task.created_at}\n"
            f"更新: {task.updated_at}"
        ))

    return [
        ToolSpec(
            name="task_create",
            description="创建新的持久化任务",
            parameters=ToolParameterSchema(
                properties={
                    "subject": {"type": "string", "description": "任务标题"},
                    "description": {"type": "string", "description": "任务详细描述"},
                },
                required=["subject"],
            ),
            handler=handle_create,
        ),
        ToolSpec(
            name="task_update",
            description="更新任务状态、负责人或依赖关系",
            parameters=ToolParameterSchema(
                properties={
                    "id": {"type": "string", "description": "任务 ID"},
                    "status": {
                        "type": "string",
                        "description": "新状态: pending/in_progress/completed/failed/cancelled",
                    },
                    "owner": {"type": "string", "description": "负责人名称"},
                    "add_blocked_by": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "添加阻塞此任务的任务 ID",
                    },
                    "add_blocks": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "添加被此任务阻塞的任务 ID",
                    },
                },
                required=["id"],
            ),
            handler=handle_update,
        ),
        ToolSpec(
            name="task_list",
            description="列出所有任务状态",
            parameters=ToolParameterSchema(properties={}, required=[]),
            handler=handle_list,
        ),
        ToolSpec(
            name="task_get",
            description="查看单个任务详情",
            parameters=ToolParameterSchema(
                properties={
                    "id": {"type": "string", "description": "任务 ID"},
                },
                required=["id"],
            ),
            handler=handle_get,
        ),
    ]
