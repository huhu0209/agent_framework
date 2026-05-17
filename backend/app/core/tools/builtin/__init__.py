"""内建工具注册。"""

from __future__ import annotations

from app.core.llm.types import ToolParameterSchema
from app.core.tools.registry import ToolRegistry
from app.core.tools.types import ToolSpec

from .file_tools import read_file, write_file
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

    return registry
