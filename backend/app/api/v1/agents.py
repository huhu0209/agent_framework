"""Agent 管理 API — CRUD ~/.agent-framework/agents/<名>/ + GET /skills。"""

from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
from pathlib import Path

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
    permission_mode: str = "ask"


class AgentCreate(AgentWrite):
    soul: str = ""
    identity: str = ""
    agents_rules: str = ""
    tool_guidance: str = ""


def _write_agent(agent_dir: Path, body: AgentCreate) -> None:
    """原子写:先写同文件系统临时目录,全部成功后替换目标(防中途崩溃损坏)。

    PUT 更新已有 agent 时尤其关键 — 非原子实现写到一半崩溃会留下混合/损坏状态。
    失败回滚(删临时目录),目标目录原样保留。
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
        # 全部写成功 → 替换目标(删旧 + rename)
        if agent_dir.exists():
            shutil.rmtree(agent_dir)
        os.replace(tmp_dir, agent_dir)
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
async def update_agent(request: Request, name: str, body: AgentCreate) -> dict:
    _validate_name(name)
    if body.name != name:
        raise HTTPException(status_code=400, detail="name in body must match path")
    agent_dir = _agents_dir(request) / name
    if not agent_dir.exists():
        raise HTTPException(status_code=404, detail="agent not found")
    _write_agent(agent_dir, body)
    return {"name": body.name}


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
