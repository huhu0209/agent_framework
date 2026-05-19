"""上下文管理模块 — Token 估算、大结果处理、自动压缩。"""

from .compactor import CompactConfig, compact, should_compact
from .result_truncator import MAX_RESULT_CHARS, RESULT_DUMP_DIR, truncate_if_needed
from .token_counter import estimate_tokens, estimate_with_usage, get_effective_window

__all__ = [
    "CompactConfig",
    "MAX_RESULT_CHARS",
    "RESULT_DUMP_DIR",
    "compact",
    "estimate_tokens",
    "estimate_with_usage",
    "get_effective_window",
    "should_compact",
    "truncate_if_needed",
]
