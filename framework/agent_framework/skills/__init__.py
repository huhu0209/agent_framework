"""Skills 系统。"""

from agent_framework.skills.discovery import SkillDiscovery
from agent_framework.skills.registry import SkillRegistry
from agent_framework.skills.tool import create_load_skill_spec
from agent_framework.skills.types import (
    SkillDocument,
    SkillLoadResult,
    SkillManifest,
    SkillSource,
)

__all__ = [
    "SkillDiscovery",
    "SkillDocument",
    "SkillLoadResult",
    "SkillManifest",
    "SkillRegistry",
    "SkillSource",
    "create_load_skill_spec",
]
