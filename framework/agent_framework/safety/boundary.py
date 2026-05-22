"""执行边界 — 路径沙箱、命令策略。"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel


class PathEscapesWorkspace(Exception):
    """路径逃出工作目录。"""

    def __init__(self, path: str) -> None:
        super().__init__(f"路径 '{path}' 逃出工作目录范围")


def safe_path(p: str, workdir: Path) -> Path:
    """解析路径并验证不逃出工作目录。防 ../../ 和符号链接绕过。"""
    resolved = (workdir / p).resolve()
    workdir_resolved = workdir.resolve()

    if not resolved.is_relative_to(workdir_resolved):
        raise PathEscapesWorkspace(p)

    return resolved


class CommandPolicy(BaseModel):
    """命令沙箱策略（预留接口，bash 工具实现后启用）。"""

    allowed_commands: list[str] = []
    blocked_commands: list[str] = []
    allow_pipes: bool = False
    allow_redirects: bool = False
    safe_env_vars: list[str] = []
