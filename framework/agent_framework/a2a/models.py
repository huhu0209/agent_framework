"""A2A data models — AgentCard, A2ATask, A2AMessage, A2ATaskStatus."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel

from agent_framework.memory.frontmatter import parse_frontmatter


class A2ATaskStatus(str, Enum):
    """Task lifecycle states for A2A protocol."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"

    @property
    def is_terminal(self) -> bool:
        """True if the status is a terminal state (no further transitions)."""
        return self in (
            A2ATaskStatus.COMPLETED,
            A2ATaskStatus.FAILED,
            A2ATaskStatus.CANCELED,
        )


class AgentCard(BaseModel):
    """Agent metadata card — describes an agent's identity and capabilities."""

    name: str
    description: str = ""
    url: str
    version: str = "1.0"
    capabilities: list[str] = []


class A2ATask(BaseModel):
    """A task sent to a remote agent, with lifecycle tracking."""

    id: str
    status: A2ATaskStatus = A2ATaskStatus.PENDING
    result: Optional[str] = None
    error: Optional[str] = None
    created_at: str
    updated_at: str


class A2AMessage(BaseModel):
    """A message in the A2A protocol conversation."""

    role: str
    text: str


def load_agent_card(text: str, filename: str = "<unknown>") -> AgentCard:
    """Parse a .md frontmatter text block into an AgentCard instance.

    Raises ValueError if required fields (name, url) are missing.
    """
    meta = parse_frontmatter(text)

    name = meta.get("name", "")
    if not name:
        raise ValueError(f"AgentCard requires 'name' field in {filename}")

    url = meta.get("url", "")
    if not url:
        raise ValueError(f"AgentCard requires 'url' field in {filename}")

    raw_caps = meta.get("capabilities", "")
    capabilities = [c.strip() for c in raw_caps.split(",") if c.strip()] if raw_caps else []

    return AgentCard(
        name=name,
        description=meta.get("description", ""),
        url=url,
        version=meta.get("version", "1.0"),
        capabilities=capabilities,
    )
