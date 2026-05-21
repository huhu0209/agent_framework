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


class MemorySearchResult(BaseModel):
    """memory_search 工具的返回。"""

    records: list[EpisodicRecord]
    scores: list[float]


class MemorySearchConfig(BaseModel):
    """搜索配置参数。"""

    vector_weight: float = 0.7
    decay_half_life_days: int = 30
    mmr_lambda: float = 0.7
    top_k: int = 10
