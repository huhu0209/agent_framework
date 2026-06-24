"""文件系统浏览 API —— 供前端选项目目录。"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.v1.chat import verify_api_key

router = APIRouter(dependencies=[Depends(verify_api_key)])

_MAX_ENTRIES = 500


@router.get("/list")
async def list_dirs(path: str = Query(...)) -> list[dict]:
    """列出 path 下的子目录(隐藏过滤,仅目录,限量,防遍历)。"""
    try:
        resolved = Path(path).expanduser().resolve(strict=True)
    except (FileNotFoundError, ValueError):
        raise HTTPException(status_code=400, detail="invalid or missing path")
    if not resolved.is_dir():
        raise HTTPException(status_code=400, detail="not a directory")
    entries: list[dict] = []
    for child in sorted(resolved.iterdir()):
        if len(entries) >= _MAX_ENTRIES:
            break
        if child.name.startswith("."):
            continue
        if child.is_dir():
            entries.append({"name": child.name, "path": str(child)})
    return entries
