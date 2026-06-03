"""内建工具注册。"""

from __future__ import annotations

from agent_framework.llm.types import ToolParameterSchema
from agent_framework.tools.registry import ToolRegistry
from agent_framework.tools.types import ToolSpec

from .file_tools import read_file, write_file
from .memory_tools import handle_memory_search
from .plan_tools import handle_update_plan_status
from .search_tools import web_search


def create_builtin_registry() -> ToolRegistry:
    """创建包含所有内建工具的注册表。"""
    registry = ToolRegistry()

    registry.register(ToolSpec(
        name="read_file",
        description=(
            "读取指定路径的文件内容。"
            "适合：查看代码、配置文件、日志。"
            "不适合：二进制文件、目录。"
        ),
        parameters=ToolParameterSchema(
            properties={
                "path": {"type": "string", "description": "相对于工作目录的文件路径"},
            },
            required=["path"],
        ),
        handler=read_file,
        timeout_ms=10_000,
    ))

    registry.register(ToolSpec(
        name="write_file",
        description=(
            "将内容写入指定路径的文件。"
            "自动创建不存在的父目录。"
            "适合：创建文件、保存结果。"
            "不适合：追加内容（会覆盖）。"
        ),
        parameters=ToolParameterSchema(
            properties={
                "path": {"type": "string", "description": "相对于工作目录的文件路径"},
                "content": {"type": "string", "description": "要写入的文件内容"},
            },
            required=["path", "content"],
        ),
        handler=write_file,
        timeout_ms=10_000,
    ))

    registry.register(ToolSpec(
        name="web_search",
        description=(
            "搜索网页获取信息。"
            "适合：查找最新信息、技术文档、新闻。"
            "不适合：已存在于对话中的信息、纯计算任务。"
        ),
        parameters=ToolParameterSchema(
            properties={
                "query": {"type": "string", "description": "搜索关键词"},
            },
            required=["query"],
        ),
        handler=web_search,
        timeout_ms=15_000,
    ))

    registry.register(ToolSpec(
        name="memory_search",
        description=(
            "搜索历史记忆和工作记录。"
            "适合：回忆之前的决策、偏好、错误修复记录。"
            "不适合：当前对话中已有的信息。"
        ),
        parameters=ToolParameterSchema(
            properties={
                "query": {"type": "string", "description": "搜索关键词"},
                "top_k": {"type": "integer", "description": "返回结果数量，默认 10"},
            },
            required=["query"],
        ),
        handler=handle_memory_search,
        timeout_ms=10_000,
    ))

    registry.register(ToolSpec(
        name="update_plan_status",
        description=(
            "更新计划项的执行状态。"
            "在执行计划时，每完成或开始一个步骤时调用。"
        ),
        parameters=ToolParameterSchema(
            properties={
                "item_id": {"type": "string", "description": "计划项编号"},
                "status": {
                    "type": "string",
                    "enum": ["in_progress", "completed", "blocked"],
                    "description": "新状态：in_progress（开始）、completed（完成）、blocked（阻塞）",
                },
            },
            required=["item_id", "status"],
        ),
        handler=handle_update_plan_status,
        timeout_ms=5_000,
    ))

    return registry
