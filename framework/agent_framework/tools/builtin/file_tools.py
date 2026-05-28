"""文件操作工具。"""

from __future__ import annotations

from pathlib import Path

from agent_framework.safety.boundary import PathEscapesWorkspace, safe_path
from agent_framework.tools.types import ToolResult, ToolUseContext

_PATH_REJECTED = ToolResult(
    content="路径访问被拒绝: 不允许访问工作目录外的文件",
    is_error=True,
)


async def read_file(args: dict, ctx: ToolUseContext) -> ToolResult:
    path = args["path"]

    try:
        full_path = safe_path(path, Path(ctx.working_dir))
    except PathEscapesWorkspace:
        return _PATH_REJECTED

    if not full_path.exists():
        return ToolResult(content=f"文件不存在: {path}", is_error=True)

    try:
        content = full_path.read_text(encoding="utf-8")
        return ToolResult(content=content)
    except Exception as e:
        return ToolResult(content=f"读取文件失败: {e}", is_error=True)


async def write_file(args: dict, ctx: ToolUseContext) -> ToolResult:
    path = args["path"]
    content = args["content"]

    try:
        full_path = safe_path(path, Path(ctx.working_dir))
    except PathEscapesWorkspace:
        return _PATH_REJECTED

    try:
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding="utf-8")
        return ToolResult(content=f"成功写入 {path} ({len(content)} 字符)")
    except Exception as e:
        return ToolResult(content=f"写入文件失败: {e}", is_error=True)
