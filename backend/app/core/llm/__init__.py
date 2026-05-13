"""LLM Adapter 模块。

提供统一的 LLM 调用接口，归一化各 provider 的差异。
"""

from .base import (
    CircuitOpenError,
    ILLMAdapter,
    InvalidRequestError,
    LLMAdapterError,
    RateLimitError,
    ServiceUnavailableError,
)
from .resilient import ResilientLLMAdapter, create_adapter
from .types import (
    AssistantMessage,
    CompletionConfig,
    CompletionResult,
    ContentBlock,
    ImageBlock,
    ImageSource,
    Message,
    ProviderInfo,
    StopReason,
    StreamEvent,
    StreamEventType,
    SystemMessage,
    TextBlock,
    ThinkingBlock,
    ThinkingConfig,
    ToolDefinition,
    ToolMessage,
    ToolParameterSchema,
    ToolResultBlock,
    ToolUseBlock,
    UsageStats,
    UserMessage,
)

__all__ = [
    # Adapter interface
    "ILLMAdapter",
    "LLMAdapterError",
    "RateLimitError",
    "ServiceUnavailableError",
    "InvalidRequestError",
    "CircuitOpenError",
    # Resilient adapter
    "ResilientLLMAdapter",
    "create_adapter",
    # Content blocks
    "ContentBlock",
    "TextBlock",
    "ImageBlock",
    "ImageSource",
    "ToolUseBlock",
    "ToolResultBlock",
    "ThinkingBlock",
    # Messages
    "Message",
    "SystemMessage",
    "UserMessage",
    "AssistantMessage",
    "ToolMessage",
    # Tool definition
    "ToolDefinition",
    "ToolParameterSchema",
    # Config & Result
    "CompletionConfig",
    "CompletionResult",
    "ThinkingConfig",
    "StopReason",
    "UsageStats",
    "ProviderInfo",
    # Streaming
    "StreamEvent",
    "StreamEventType",
]

# Sub-modules available as app.core.llm.transform / app.core.llm.retry
