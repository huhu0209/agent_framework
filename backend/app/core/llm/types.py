"""LLM Adapter 统一类型定义。

内部消息格式设计原则：
- content 永远是 ContentBlock 数组（避免 OpenAI 的 string | array 二义性）
- tool_use / tool_result 按 Anthropic 的 content block 方式建模（更结构化、可扩展）
- thinking block 保留但标注 provider 限定
- system prompt 独立字符串（Anthropic 方式）
- 各家特有参数通过 providerExtras 透传，不做归一化
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal, Union

from pydantic import BaseModel, Field


# ============================================================
# Content Block 类型
# ============================================================


class TextBlock(BaseModel):
    """文本内容块。"""

    type: Literal["text"] = "text"
    text: str


class ImageSource(BaseModel):
    """图片数据源。"""

    type: Literal["base64", "url"]
    media_type: str = "image/png"
    data: str  # base64 编码数据或 URL


class ImageBlock(BaseModel):
    """图片内容块。"""

    type: Literal["image"] = "image"
    source: ImageSource


class ToolUseBlock(BaseModel):
    """工具调用块（assistant 发起）。"""

    type: Literal["tool_use"] = "tool_use"
    id: str
    name: str
    input: dict[str, Any]


class ToolResultBlock(BaseModel):
    """工具返回结果块（user 回传）。"""

    type: Literal["tool_result"] = "tool_result"
    tool_use_id: str
    content: str
    is_error: bool = False


class ThinkingBlock(BaseModel):
    """思考过程块（Anthropic extended thinking / DeepSeek reasoning_content）。"""

    type: Literal["thinking"] = "thinking"
    thinking: str
    signature: str | None = None  # Anthropic 特有签名，回传时需要


ContentBlock = Union[
    TextBlock,
    ImageBlock,
    ToolUseBlock,
    ToolResultBlock,
    ThinkingBlock,
]


# ============================================================
# 消息类型
# ============================================================


class SystemMessage(BaseModel):
    """系统指令消息。content 为纯文本字符串。"""

    role: Literal["system"] = "system"
    content: str


class UserMessage(BaseModel):
    """用户消息。content 为 ContentBlock 数组。"""

    role: Literal["user"] = "user"
    content: list[ContentBlock]


class AssistantMessage(BaseModel):
    """助手消息。content 为 ContentBlock 数组。"""

    role: Literal["assistant"] = "assistant"
    content: list[ContentBlock]


class ToolMessage(BaseModel):
    """工具结果消息（独立 role，类 OpenAI 格式）。

    在内部统一格式中使用独立 role。
    转换为 Anthropic/Gemini 格式时，会被合并到 user message 的 content blocks 中。
    """

    role: Literal["tool"] = "tool"
    tool_call_id: str
    content: str


Message = Union[SystemMessage, UserMessage, AssistantMessage, ToolMessage] 


# ============================================================
# 工具定义
# ============================================================


class ToolParameterSchema(BaseModel):
    """工具参数的 JSON Schema 定义。

    只使用 JSON Schema 的"最大公约子集"：
    type, properties, required, description, enum, items
    不使用 oneOf/anyOf/$ref（各家兼容性差）。
    """

    type: str = "object"
    properties: dict[str, dict[str, Any]] = Field(default_factory=dict)
    required: list[str] = Field(default_factory=list)
    description: str | None = None


class ToolDefinition(BaseModel):
    """统一的工具定义。"""

    name: str
    description: str
    parameters: ToolParameterSchema = Field(default_factory=ToolParameterSchema)


# ============================================================
# 采样与完成配置
# ============================================================


class StopReason(str, Enum):
    """模型停止原因。"""

    END_TURN = "end_turn"
    MAX_TOKENS = "max_tokens"
    TOOL_USE = "tool_use"
    STOP_SEQUENCE = "stop_sequence"


class ThinkingConfig(BaseModel):
    """思考模式配置（统一接口）。

    Anthropic: type=enabled, budget_tokens 精确控制
    DeepSeek V4: 映射到 extra_body={"thinking": {"type": "enabled"}}
    OpenAI: 不支持（隐藏推理）
    """

    type: Literal["enabled", "disabled"] = "enabled"
    budget_tokens: int | None = None  # Anthropic 用，其他家忽略


class CompletionConfig(BaseModel):
    """完成请求配置。"""

    model: str
    messages: list[Message]
    tools: list[ToolDefinition] = Field(default_factory=list)
    temperature: float | None = None
    max_tokens: int | None = None
    top_p: float | None = None
    stop: list[str] | None = None
    thinking: ThinkingConfig | None = None
    stream: bool = False
    provider_extras: dict[str, Any] = Field(default_factory=dict)


# ============================================================
# 完成结果
# ============================================================


class UsageStats(BaseModel):
    """Token 使用统计。"""

    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    thinking_tokens: int = 0


class CompletionResult(BaseModel):
    """非流式完成结果。"""

    id: str
    model: str
    content: list[ContentBlock] = Field(default_factory=list)
    stop_reason: StopReason = StopReason.END_TURN
    usage: UsageStats = Field(default_factory=UsageStats)
    raw_response: dict[str, Any] = Field(default_factory=dict)


# ============================================================
# 流式事件类型
# ============================================================


class StreamEventType(str, Enum):
    """流式事件类型。"""

    TEXT_DELTA = "text_delta"
    THINKING_DELTA = "thinking_delta"
    TOOL_USE_START = "tool_use_start"
    TOOL_USE_DELTA = "tool_use_delta"
    TOOL_USE_END = "tool_use_end"
    USAGE = "usage"
    DONE = "done"
    ERROR = "error"
    RAW = "raw"  # 原始 provider 事件，用于高级用途


class StreamEvent(BaseModel):
    """流式事件。"""

    type: StreamEventType
    data: dict[str, Any] = Field(default_factory=dict)
    provider_event: dict[str, Any] | None = None  # 原始事件保留


# ============================================================
# Provider 元信息
# ============================================================


class ProviderInfo(BaseModel):
    """Provider 描述信息。"""

    name: str
    base_url: str
    supported_features: list[str] = Field(default_factory=list)
    default_model: str
    max_context_tokens: int = 128000
    max_output_tokens: int = 8192
