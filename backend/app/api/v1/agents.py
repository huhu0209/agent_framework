"""Agent 管理 API — CRUD ~/.agent-framework/agents/<名>/ + GET /skills。"""

from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.api.v1.chat import verify_api_key

router = APIRouter(dependencies=[Depends(verify_api_key)])

_AGENT_NAME_RE = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")
_PERSONA_FILES = {
    "soul": "soul.md",
    "identity": "identity.md",
    "agents_rules": "agents.md",
    "tool_guidance": "tool_guidance.md",
}


def _agents_dir(request: Request) -> Path:
    return request.app.state.settings.agents_dir


def _validate_name(name: str) -> None:
    if not isinstance(name, str) or not _AGENT_NAME_RE.match(name):
        raise HTTPException(status_code=400, detail="invalid agent name (allowed: [a-zA-Z0-9_-]{1,64})")


def _read_meta(meta_path: Path) -> dict:
    try:
        return json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


class AgentWrite(BaseModel):
    name: str
    description: str = ""
    model: str | None = None
    skills: list[str] | None = None
    tools: list[str] | None = None
    permission_mode: Literal["accept", "ask", "deny"] = "ask"


class AgentCreate(AgentWrite):
    soul: str = ""
    identity: str = ""
    agents_rules: str = ""
    tool_guidance: str = ""


class AgentUpdate(BaseModel):
    """PUT 部分更新模型 — 仅非 None 字段覆盖(避免裸 PUT 清空 persona,LOW#1 review)。"""

    name: str
    description: str | None = None
    model: str | None = None
    skills: list[str] | None = None
    tools: list[str] | None = None
    permission_mode: Literal["accept", "ask", "deny"] | None = None
    soul: str | None = None
    identity: str | None = None
    agents_rules: str | None = None
    tool_guidance: str | None = None


def _read_existing_as_create(agent_dir: Path) -> AgentCreate:
    """读现有 agent 目录为 AgentCreate(供 PUT 部分更新合并基线,LOW#1)。"""
    meta = _read_meta(agent_dir / "agent.json")
    persona: dict[str, str] = {}
    for field_name, fname in _PERSONA_FILES.items():
        p = agent_dir / fname
        persona[field_name] = p.read_text(encoding="utf-8") if p.exists() else ""
    return AgentCreate(
        name=meta.get("name", agent_dir.name),
        description=meta.get("description", ""),
        model=meta.get("model"),
        skills=meta.get("skills"),
        tools=meta.get("tools"),
        permission_mode=meta.get("permission_mode", "ask"),
        **persona,
    )


def _write_agent(agent_dir: Path, body: AgentCreate) -> None:
    """原子写:先写临时目录,全部成功后用 rename 替换目标(防中途崩溃损坏)。

    PUT 更新已有 agent 时:旧目录先 rename 成 backup → tmp rename 到目标 → 删 backup。
    任一步失败可回滚(rename 在同文件系统原子)。比「rmtree 后 replace」更安全 —
    不存在「旧目录已删、新目录未就位」的丢数据窗口(LOW#2 review)。
    """
    parent = agent_dir.parent
    parent.mkdir(parents=True, exist_ok=True)
    tmp_dir = Path(tempfile.mkdtemp(dir=parent, prefix=f".{agent_dir.name}."))
    try:
        meta = {
            "name": body.name,
            "description": body.description,
            "model": body.model,
            "skills": body.skills,
            "tools": body.tools,
            "permission_mode": body.permission_mode,
        }
        (tmp_dir / "agent.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        for field_name, fname in _PERSONA_FILES.items():
            (tmp_dir / fname).write_text(getattr(body, field_name), encoding="utf-8")
        # 旧目录 → backup(同盘原子 rename),腾出目标位
        backup_dir: Path | None = None
        if agent_dir.exists():
            backup_dir = Path(tempfile.mkdtemp(dir=parent, prefix=f".{agent_dir.name}.old."))
            backup_dir.rmdir()  # mkdtemp 建了空目录,删掉作 rename 目标名
            os.rename(agent_dir, backup_dir)
        # tmp → 目标;失败则回滚 backup → 目标
        try:
            os.replace(tmp_dir, agent_dir)
        except OSError:
            if backup_dir is not None:
                os.rename(backup_dir, agent_dir)
            raise
        # 成功 → 清理 backup
        if backup_dir is not None:
            shutil.rmtree(backup_dir, ignore_errors=True)
    except BaseException:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise


@router.get("/agents")
async def list_agents(request: Request) -> list[dict]:
    root = _agents_dir(request)
    if not root.is_dir():
        return []
    out: list[dict] = []
    for child in sorted(root.iterdir()):
        if child.is_dir() and (child / "agent.json").exists():
            meta = _read_meta(child / "agent.json")
            out.append({"name": meta.get("name", child.name), "description": meta.get("description", "")})
    return out


@router.get("/agents/{name}")
async def get_agent(request: Request, name: str) -> dict:
    _validate_name(name)
    agent_dir = _agents_dir(request) / name
    meta_path = agent_dir / "agent.json"
    if not meta_path.exists():
        raise HTTPException(status_code=404, detail="agent not found")
    meta = _read_meta(meta_path)
    body: dict = {
        "name": meta.get("name", name),
        "description": meta.get("description", ""),
        "model": meta.get("model"),
        "skills": meta.get("skills"),
        "tools": meta.get("tools"),
        "permission_mode": meta.get("permission_mode", "ask"),
    }
    for field_name, fname in _PERSONA_FILES.items():
        p = agent_dir / fname
        body[field_name] = p.read_text(encoding="utf-8") if p.exists() else ""
    return body


@router.post("/agents", status_code=201)
async def create_agent(request: Request, body: AgentCreate) -> dict:
    _validate_name(body.name)
    agent_dir = _agents_dir(request) / body.name
    if agent_dir.exists():
        raise HTTPException(status_code=409, detail="agent already exists")
    _write_agent(agent_dir, body)
    return {"name": body.name}


@router.put("/agents/{name}")
async def update_agent(request: Request, name: str, body: AgentUpdate) -> dict:
    _validate_name(name)
    if body.name != name:
        raise HTTPException(status_code=400, detail="name in body must match path")
    agent_dir = _agents_dir(request) / name
    if not agent_dir.exists():
        raise HTTPException(status_code=404, detail="agent not found")
    # 部分更新:读现有 + 合并 body 中非 None 字段(LOW#1,防裸 PUT 清空 persona)
    existing = _read_existing_as_create(agent_dir)
    merged = existing.model_copy(update=body.model_dump(exclude_none=True))
    _write_agent(agent_dir, merged)
    return {"name": merged.name}


@router.delete("/agents/{name}", status_code=204)
async def delete_agent(request: Request, name: str) -> None:
    _validate_name(name)
    agent_dir = _agents_dir(request) / name
    if not agent_dir.exists():
        raise HTTPException(status_code=404, detail="agent not found")
    shutil.rmtree(agent_dir)


@router.get("/skills")
async def list_skills(request: Request) -> list[dict]:
    """列出全局可选 skill(供前端勾选)。从 app.state.config_loader 发现。"""
    loader = getattr(request.app.state, "config_loader", None)
    if loader is None:
        return []
    from agent_framework.skills.registry import SkillRegistry
    reg = SkillRegistry.from_loader(loader)
    out: list[dict] = []
    for skill_name in reg.get_names():
        manifest = reg.get_manifest(skill_name)
        out.append({"name": skill_name, "description": manifest.description if manifest else ""})
    return out
