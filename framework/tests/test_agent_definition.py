"""AgentDefinition — 从文件夹加载具名 agent(人格 + 元数据)。"""
import json
from pathlib import Path

import pytest

from agent_framework.agents.definition import AgentDefinition, discover_agent_dirs
from agent_framework.config.loader import ConfigLoader


def _make_agent_dir(root: Path, name: str, *, meta: dict, persona: dict | None = None) -> Path:
    d = root / name
    d.mkdir(parents=True)
    (d / "agent.json").write_text(json.dumps(meta), encoding="utf-8")
    persona = persona or {}
    for fname, content in persona.items():
        (d / fname).write_text(content, encoding="utf-8")
    return d


def test_from_directory_loads_meta_and_persona(tmp_path):
    d = _make_agent_dir(
        tmp_path, "code-reviewer",
        meta={"name": "code-reviewer", "description": "审查员", "model": "m1",
              "skills": ["web-search"], "tools": ["read"], "permission_mode": "ask"},
        persona={"soul.md": "我是审查员", "identity.md": "资深"},
    )
    ad = AgentDefinition.from_directory(d)
    assert ad.name == "code-reviewer"
    assert ad.description == "审查员"
    assert ad.model == "m1"
    assert ad.skills == ["web-search"]
    assert ad.profile.soul == "我是审查员"
    assert ad.profile.identity == "资深"
    assert ad.profile.allowed_tools == ["read"]
    assert ad.profile.permission_mode == "ask"


def test_from_directory_rejects_name_mismatch(tmp_path):
    d = _make_agent_dir(tmp_path, "alice", meta={"name": "bob"})
    with pytest.raises(ValueError, match="不一致"):
        AgentDefinition.from_directory(d)


def test_from_directory_missing_agent_json(tmp_path):
    d = tmp_path / "x"
    d.mkdir()
    with pytest.raises(FileNotFoundError):
        AgentDefinition.from_directory(d)


def test_from_directory_missing_persona_files_ok(tmp_path):
    d = _make_agent_dir(tmp_path, "minimal", meta={"name": "minimal"})
    ad = AgentDefinition.from_directory(d)
    assert ad.profile.soul == ""
    assert ad.skills is None
    assert ad.model is None


def test_discover_agent_dirs_finds_folders_with_agent_json(tmp_path):
    # ConfigLoader 把 project_dir 拼上 .agent-framework/agents;global 层留空
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    agents_dir = project_dir / ".agent-framework" / "agents"
    _make_agent_dir(agents_dir, "a", meta={"name": "a"})
    _make_agent_dir(agents_dir, "b", meta={"name": "b"})
    (agents_dir / "not-an-agent").mkdir()
    loader = ConfigLoader(global_dir=tmp_path / "global", project_dir=project_dir)
    dirs = discover_agent_dirs(loader)
    names = sorted(p.name for p in dirs)
    assert names == ["a", "b"]


def test_from_directory_rejects_invalid_permission_mode(tmp_path):
    """M2: agent.json 含非法 permission_mode → from_directory 校验失败(ValueError)。

    model_copy 默认不触发 pydantic 校验,故在 from_directory 显式校验,
    堵住 framework 独立被调用时读到被污染 agent.json 的漏洞。
    """
    d = _make_agent_dir(
        tmp_path, "bad", meta={"name": "bad", "permission_mode": "bogus"},
    )
    with pytest.raises(ValueError, match="permission_mode"):
        AgentDefinition.from_directory(d)
