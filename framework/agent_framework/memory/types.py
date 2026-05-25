"""记忆系统核心类型定义。"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class MemoryLayer(str, Enum):
    """记忆层：语义（启动注入）vs 情景（按需搜索）。"""

    SEMANTIC = "semantic"
    EPISODIC = "episodic"


class EventType(str, Enum):
    """每日日志中的事件类型，影响搜索权重。"""

    DECISION = "决策"
    PREFERENCE = "偏好"
    ERROR = "错误"
    CONVENTION = "约定"
    PROGRESS = "进展"


class EpisodicRecord(BaseModel):
    """每日日志中的一条记录。"""

    timestamp: datetime
    content: str
    source_file: str
    line_range: tuple[int, int]


class MemorySearchConfig(BaseModel):
    """搜索配置参数。"""

    top_k: int = 10


class MemoryType(str, Enum):
    """语义记忆的四种类型。"""

    USER = "user"
    FEEDBACK = "feedback"
    PROJECT = "project"
    REFERENCE = "reference"


class SemanticMemoryDraft(BaseModel):
    """LLM 提取的语义记忆候选。"""

    name: str
    description: str
    type: MemoryType
    body: str
