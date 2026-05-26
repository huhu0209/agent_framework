"""Skills 系统 — 渐进式 Skill 加载。"""

from agent_framework.skills.manifest import SkillDocument, SkillLoadResult, SkillManifest
from agent_framework.skills.registry import SkillRegistry
from agent_framework.skills.tool import create_load_skill_spec

__all__ = [
    "SkillDocument",
    "SkillLoadResult",
    "SkillManifest",
    "SkillRegistry",
    "create_load_skill_spec",
]
