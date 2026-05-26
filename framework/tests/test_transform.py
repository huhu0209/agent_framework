"""transform 模块纯函数测试。

覆盖 messages_to_openai / deepseek / anthropic、parse_*_response、
tools_to_*、normalize_messages 的核心路径。
"""

import json

import pytest

from agent_framework.llm.transform import (
    messages_to_anthropic,
    messages_to_deepseek,
    messages_to_openai,
    normalize_messages,
    parse_anthropic_response,
    parse_deepseek_response,
    parse_openai_response,
    tools_to_anthropic,
    tools_to_openai,
)
from agent_framework.llm.types import (
    AssistantMessage,
    ImageBlock,
    ImageSource,
    SystemMessage,
    TextBlock,
    ThinkingBlock,
    ToolDefinition,
    ToolMessage,
    ToolParameterSchema,
    ToolResultBlock,
    ToolUseBlock,
    UsageStats,
    UserMessage,
)


# ============================================================
# helpers
# ============================================================


def _sample_tool(name: str = "read_file", desc: str = "Read a file") -> ToolDefinition:
    return ToolDefinition(
        name=name,
        description=desc,
        parameters=ToolParameterSchema(
            properties={"path": {"type": "string", "description": "File path"}},
            required=["path"],
        ),
    )


# ============================================================
# messages_to_openai
# ============================================================


class TestMessagesToOpenai:
    """messages_to_openai 转换验证。"""

    def test_simple_text_user_message(self):
        msgs = [UserMessage(content=[TextBlock(text="hello")])]
        result = messages_to_openai(msgs)
        assert len(result) == 1
        assert result[0]["role"] == "user"
        assert result[0]["content"] == "hello"

    def test_system_message(self):
        msgs = [SystemMessage(content="You are helpful.")]
        result = messages_to_openai(msgs)
        assert result[0] == {"role": "system", "content": "You are helpful."}

    def test_tool_message(self):
        msgs = [ToolMessage(tool_call_id="tc_1", content="file content")]
        result = messages_to_openai(msgs)
        assert result[0] == {
            "role": "tool",
            "tool_call_id": "tc_1",
            "content": "file content",
        }

    def test_assistant_with_tool_use(self):
        msgs = [
            AssistantMessage(content=[
                TextBlock(text="I'll read the file."),
                ToolUseBlock(id="call_1", name="read_file", input={"path": "/tmp/a.txt"}),
            ])
        ]
        result = messages_to_openai(msgs)
        assert len(result) == 1
        assert result[0]["role"] == "assistant"
        assert result[0]["content"] == "I'll read the file."
        assert len(result[0]["tool_calls"]) == 1
        tc = result[0]["tool_calls"][0]
        assert tc["type"] == "function"
        assert tc["function"]["name"] == "read_file"
        assert json.loads(tc["function"]["arguments"]) == {"path": "/tmp/a.txt"}

    def test_thinking_block_discarded(self):
        """ThinkingBlock 在 OpenAI 格式中被丢弃。"""
        msgs = [
            AssistantMessage(content=[
                ThinkingBlock(thinking="let me think..."),
                TextBlock(text="answer"),
            ])
        ]
        result = messages_to_openai(msgs)
        assert len(result) == 1
        assert result[0]["content"] == "answer"
        assert "tool_calls" not in result[0]

    def test_empty_content_yields_empty_string(self):
        msgs = [AssistantMessage(content=[])]
        result = messages_to_openai(msgs)
        assert result[0]["content"] == ""

    def test_tool_use_only_no_text(self):
        """tool_calls 存在但无文本时 content 为 None。"""
        msgs = [
            AssistantMessage(content=[
                ToolUseBlock(id="c1", name="foo", input={})
            ])
        ]
        result = messages_to_openai(msgs)
        assert result[0]["content"] is None
        assert len(result[0]["tool_calls"]) == 1

    def test_multiple_text_blocks_joined_by_newline(self):
        """多个 TextBlock 用换行拼接。"""
        msgs = [
            UserMessage(content=[
                TextBlock(text="line1"),
                TextBlock(text="line2"),
            ])
        ]
        result = messages_to_openai(msgs)
        assert result[0]["content"] == "line1\nline2"

    def test_tool_calls_text_joined_by_space(self):
        """tool_calls 场景中多个 TextBlock 用空格拼接。"""
        msgs = [
            AssistantMessage(content=[
                TextBlock(text="part1"),
                TextBlock(text="part2"),
                ToolUseBlock(id="c1", name="fn", input={}),
            ])
        ]
        result = messages_to_openai(msgs)
        assert result[0]["content"] == "part1 part2"


# ============================================================
# messages_to_deepseek
# ============================================================


class TestMessagesToDeepseek:
    """messages_to_deepseek 转换验证。"""

    def test_thinking_block_preserved_as_reasoning_content(self):
        """ThinkingBlock 映射为 reasoning_content 字段。"""
        msgs = [
            AssistantMessage(content=[
                ThinkingBlock(thinking="step-by-step reasoning"),
                TextBlock(text="the answer is 42"),
            ])
        ]
        result = messages_to_deepseek(msgs)
        assert len(result) == 1
        assert result[0]["reasoning_content"] == "step-by-step reasoning"
        assert result[0]["content"] == "the answer is 42"

    def test_thinking_block_not_in_user_message(self):
        """reasoning_content 只在 assistant 消息中出现。"""
        msgs = [
            UserMessage(content=[
                ThinkingBlock(thinking="should not appear"),
                TextBlock(text="hello"),
            ])
        ]
        result = messages_to_deepseek(msgs)
        assert "reasoning_content" not in result[0]
        assert result[0]["content"] == "hello"

    def test_tool_call_with_reasoning(self):
        """tool call 场景必须保留 reasoning_content。"""
        msgs = [
            AssistantMessage(content=[
                ThinkingBlock(thinking="I need to read a file"),
                ToolUseBlock(id="c1", name="read", input={"path": "/tmp"}),
            ])
        ]
        result = messages_to_deepseek(msgs)
        assert result[0]["reasoning_content"] == "I need to read a file"
        assert result[0]["tool_calls"]
        assert result[0]["content"] is None

    def test_multiple_thinking_blocks_joined(self):
        """多个 ThinkingBlock 用换行拼接。"""
        msgs = [
            AssistantMessage(content=[
                ThinkingBlock(thinking="step 1"),
                ThinkingBlock(thinking="step 2"),
                TextBlock(text="done"),
            ])
        ]
        result = messages_to_deepseek(msgs)
        assert result[0]["reasoning_content"] == "step 1\nstep 2"


# ============================================================
# messages_to_anthropic
# ============================================================


class TestMessagesToAnthropic:
    """messages_to_anthropic 转换验证。"""

    def test_system_extracted_to_top_level(self):
        """SystemMessage 被提取为顶层 system_prompt。"""
        msgs = [
            SystemMessage(content="Be helpful."),
            UserMessage(content=[TextBlock(text="hi")]),
        ]
        system_prompt, api_msgs = messages_to_anthropic(msgs)
        assert system_prompt == "Be helpful."
        assert all(m["role"] != "system" for m in api_msgs)

    def test_multiple_system_messages_concatenated(self):
        """多个 SystemMessage 用双换行拼接。"""
        msgs = [
            SystemMessage(content="Part one."),
            SystemMessage(content="Part two."),
            UserMessage(content=[TextBlock(text="hi")]),
        ]
        system_prompt, _ = messages_to_anthropic(msgs)
        assert system_prompt == "Part one.\n\nPart two."

    def test_tool_result_as_user_content_block(self):
        """ToolMessage 被转换为 user 消息的 tool_result content block。"""
        msgs = [
            UserMessage(content=[TextBlock(text="go")]),
            AssistantMessage(content=[ToolUseBlock(id="tu1", name="fn", input={})]),
            ToolMessage(tool_call_id="tu1", content="result data"),
        ]
        _, api_msgs = messages_to_anthropic(msgs)
        tool_result_msg = api_msgs[-1]
        assert tool_result_msg["role"] == "user"
        assert any(
            b["type"] == "tool_result" and b["tool_use_id"] == "tu1"
            for b in tool_result_msg["content"]
        )

    def test_tool_use_arguments_as_object(self):
        """Anthropic 格式 tool_use 的 arguments 是 object 而非 JSON 字符串。"""
        msgs = [
            UserMessage(content=[TextBlock(text="go")]),
            AssistantMessage(content=[
                ToolUseBlock(id="c1", name="read", input={"path": "/tmp/a.txt"}),
            ])
        ]
        _, api_msgs = messages_to_anthropic(msgs)
        # api_msgs: [user, assistant]
        assistant_msg = next(m for m in api_msgs if m["role"] == "assistant")
        block = assistant_msg["content"][0]
        assert block["type"] == "tool_use"
        assert isinstance(block["input"], dict)
        assert block["input"] == {"path": "/tmp/a.txt"}

    def test_starts_with_user(self):
        """如果没有 user 消息开头，自动补一个 user 占位。"""
        msgs = [
            AssistantMessage(content=[TextBlock(text="hello")]),
        ]
        _, api_msgs = messages_to_anthropic(msgs)
        assert api_msgs[0]["role"] == "user"
        assert len(api_msgs) == 2

    def test_empty_messages_gets_placeholder(self):
        """空消息列表返回一条 user 占位消息。"""
        _, api_msgs = messages_to_anthropic([])
        assert len(api_msgs) == 1
        assert api_msgs[0]["role"] == "user"

    def test_thinking_block_preserved(self):
        """ThinkingBlock 被保留为 content block。"""
        msgs = [
            UserMessage(content=[TextBlock(text="go")]),
            AssistantMessage(content=[
                ThinkingBlock(thinking="inner monologue", signature="sig123"),
            ])
        ]
        _, api_msgs = messages_to_anthropic(msgs)
        assistant_msg = next(m for m in api_msgs if m["role"] == "assistant")
        block = assistant_msg["content"][0]
        assert block["type"] == "thinking"
        assert block["thinking"] == "inner monologue"
        assert block["signature"] == "sig123"


# ============================================================
# parse_openai_response
# ============================================================


class TestParseOpenaiResponse:
    """parse_openai_response 解析验证。"""

    def test_simple_text_response(self):
        data = {
            "choices": [{"message": {"content": "Hello!"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        }
        blocks, stop, usage = parse_openai_response(data)
        assert len(blocks) == 1
        assert isinstance(blocks[0], TextBlock)
        assert blocks[0].text == "Hello!"
        assert usage.input_tokens == 10
        assert usage.output_tokens == 5

    def test_tool_call_response(self):
        data = {
            "choices": [{
                "message": {
                    "content": None,
                    "tool_calls": [{
                        "id": "call_1",
                        "function": {
                            "name": "read_file",
                            "arguments": '{"path": "/tmp/a"}',
                        },
                    }],
                },
                "finish_reason": "tool_calls",
            }],
            "usage": {},
        }
        blocks, stop, usage = parse_openai_response(data)
        assert len(blocks) == 1
        assert isinstance(blocks[0], ToolUseBlock)
        assert blocks[0].id == "call_1"
        assert blocks[0].name == "read_file"
        assert blocks[0].input == {"path": "/tmp/a"}

    def test_null_content_no_text_block(self):
        """content 为 null 时不生成 TextBlock。"""
        data = {
            "choices": [{"message": {"content": None}, "finish_reason": "stop"}],
            "usage": {},
        }
        blocks, _, _ = parse_openai_response(data)
        text_blocks = [b for b in blocks if isinstance(b, TextBlock)]
        assert len(text_blocks) == 0

    def test_invalid_json_arguments_fallback(self):
        """tool_calls 的 arguments 解析失败时用 fallback dict。"""
        data = {
            "choices": [{
                "message": {
                    "tool_calls": [{
                        "id": "c1",
                        "function": {"name": "fn", "arguments": "{broken json"},
                    }],
                },
                "finish_reason": "tool_calls",
            }],
            "usage": {},
        }
        blocks, _, _ = parse_openai_response(data)
        assert blocks[0].input == {"_raw_arguments": "{broken json"}

    def test_cache_tokens(self):
        data = {
            "choices": [{"message": {"content": "hi"}, "finish_reason": "stop"}],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 10,
                "prompt_tokens_details": {"cached_tokens": 80},
            },
        }
        _, _, usage = parse_openai_response(data)
        assert usage.cache_read_tokens == 80


# ============================================================
# parse_deepseek_response
# ============================================================


class TestParseDeepseekResponse:
    """parse_deepseek_response 解析验证。"""

    def test_reasoning_content_becomes_thinking_block(self):
        """reasoning_content 被转换为 ThinkingBlock。"""
        data = {
            "choices": [{
                "message": {
                    "content": "the answer",
                    "reasoning_content": "step-by-step reasoning",
                },
                "finish_reason": "stop",
            }],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20},
        }
        blocks, _, _ = parse_deepseek_response(data)
        thinking = [b for b in blocks if isinstance(b, ThinkingBlock)]
        assert len(thinking) == 1
        assert thinking[0].thinking == "step-by-step reasoning"

    def test_no_reasoning_content(self):
        """无 reasoning_content 时没有 ThinkingBlock。"""
        data = {
            "choices": [{"message": {"content": "hi"}, "finish_reason": "stop"}],
            "usage": {},
        }
        blocks, _, _ = parse_deepseek_response(data)
        assert all(not isinstance(b, ThinkingBlock) for b in blocks)

    def test_text_and_tool_call_plus_reasoning(self):
        """同时有文本、tool_call 和 reasoning_content。"""
        data = {
            "choices": [{
                "message": {
                    "content": "I'll call the tool.",
                    "reasoning_content": "need to look up data",
                    "tool_calls": [{
                        "id": "c1",
                        "function": {"name": "search", "arguments": "{}"},
                    }],
                },
                "finish_reason": "tool_calls",
            }],
            "usage": {},
        }
        blocks, stop, _ = parse_deepseek_response(data)
        assert isinstance(blocks[0], TextBlock)
        assert isinstance(blocks[1], ToolUseBlock)
        assert isinstance(blocks[2], ThinkingBlock)


# ============================================================
# parse_anthropic_response
# ============================================================


class TestParseAnthropicResponse:
    """parse_anthropic_response 解析验证。"""

    def test_simple_text_response(self):
        data = {
            "content": [{"type": "text", "text": "Hello!"}],
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 10, "output_tokens": 5},
        }
        blocks, stop, usage = parse_anthropic_response(data)
        assert len(blocks) == 1
        assert isinstance(blocks[0], TextBlock)
        assert blocks[0].text == "Hello!"
        assert usage.input_tokens == 10
        assert usage.output_tokens == 5

    def test_tool_use_block(self):
        data = {
            "content": [
                {"type": "text", "text": "calling tool"},
                {"type": "tool_use", "id": "tu1", "name": "search", "input": {"q": "test"}},
            ],
            "stop_reason": "tool_use",
            "usage": {},
        }
        blocks, stop, _ = parse_anthropic_response(data)
        assert stop.value == "tool_use"
        tool_use = [b for b in blocks if isinstance(b, ToolUseBlock)]
        assert len(tool_use) == 1
        assert tool_use[0].id == "tu1"
        assert tool_use[0].input == {"q": "test"}

    def test_thinking_block(self):
        data = {
            "content": [
                {"type": "thinking", "thinking": "hmm...", "signature": "sig"},
            ],
            "stop_reason": "end_turn",
            "usage": {},
        }
        blocks, _, _ = parse_anthropic_response(data)
        assert len(blocks) == 1
        assert isinstance(blocks[0], ThinkingBlock)
        assert blocks[0].thinking == "hmm..."
        assert blocks[0].signature == "sig"

    def test_empty_text_discarded(self):
        """text block 内容为空字符串时不生成 TextBlock。"""
        data = {
            "content": [{"type": "text", "text": ""}],
            "stop_reason": "end_turn",
            "usage": {},
        }
        blocks, _, _ = parse_anthropic_response(data)
        assert len(blocks) == 0

    def test_cache_tokens(self):
        data = {
            "content": [{"type": "text", "text": "hi"}],
            "stop_reason": "end_turn",
            "usage": {
                "input_tokens": 100,
                "output_tokens": 10,
                "cache_read_input_tokens": 50,
                "cache_creation_input_tokens": 30,
            },
        }
        _, _, usage = parse_anthropic_response(data)
        assert usage.cache_read_tokens == 50
        assert usage.cache_write_tokens == 30

    def test_unknown_stop_reason_defaults_to_end_turn(self):
        data = {
            "content": [{"type": "text", "text": "hi"}],
            "stop_reason": "unknown_reason",
            "usage": {},
        }
        _, stop, _ = parse_anthropic_response(data)
        from agent_framework.llm.types import StopReason
        assert stop == StopReason.END_TURN


# ============================================================
# tools_to_openai
# ============================================================


class TestToolsToOpenai:
    """tools_to_openai 转换验证。"""

    def test_basic_conversion(self):
        tools = [_sample_tool()]
        result = tools_to_openai(tools)
        assert len(result) == 1
        t = result[0]
        assert t["type"] == "function"
        assert t["function"]["name"] == "read_file"
        assert t["function"]["description"] == "Read a file"
        assert "path" in t["function"]["parameters"]["properties"]

    def test_empty_tools(self):
        assert tools_to_openai([]) == []

    def test_parameters_exclude_none(self):
        """parameters model_dump 排除 None 字段。"""
        tool = ToolDefinition(
            name="simple",
            description="no params",
            parameters=ToolParameterSchema(description=None),
        )
        result = tools_to_openai([tool])
        assert "description" not in result[0]["function"]["parameters"]


# ============================================================
# tools_to_anthropic
# ============================================================


class TestToolsToAnthropic:
    """tools_to_anthropic 转换验证。"""

    def test_basic_conversion(self):
        tools = [_sample_tool()]
        result = tools_to_anthropic(tools)
        assert len(result) == 1
        t = result[0]
        assert t["name"] == "read_file"
        assert t["description"] == "Read a file"
        assert "input_schema" in t
        assert "path" in t["input_schema"]["properties"]

    def test_empty_tools(self):
        assert tools_to_anthropic([]) == []

    def test_uses_input_schema_not_parameters(self):
        """Anthropic 用 input_schema 而非 parameters。"""
        tools = [_sample_tool()]
        result = tools_to_anthropic(tools)
        assert "parameters" not in result[0]
        assert "input_schema" in result[0]


# ============================================================
# normalize_messages (additional coverage beyond test_normalize_messages.py)
# ============================================================


class TestNormalizeMessagesAdditional:
    """补充 normalize_messages 测试（主测试在 test_normalize_messages.py）。"""

    def test_empty_list_returns_empty(self):
        assert normalize_messages([]) == []

    def test_single_system_message(self):
        msgs = [SystemMessage(content="sys")]
        result = normalize_messages(msgs)
        assert len(result) == 1
        assert isinstance(result[0], SystemMessage)

    def test_immutability_original_not_modified(self):
        original = [UserMessage(content=[TextBlock(text="hi")])]
        original_content_id = id(original[0].content)
        normalize_messages(original)
        assert id(original[0].content) == original_content_id

    def test_cancelled_placeholder_inserted_after_last_tool_message(self):
        """placeholder 插入在最后一个 ToolMessage 之后。"""
        msgs = [
            UserMessage(content=[TextBlock(text="go")]),
            AssistantMessage(content=[ToolUseBlock(id="t1", name="a", input={})]),
            ToolMessage(tool_call_id="t1", content="r1"),
            AssistantMessage(content=[ToolUseBlock(id="t2", name="b", input={})]),
        ]
        result = normalize_messages(msgs)
        # t1 有 result，t2 没有 → t2 的 placeholder 应在最后一个 ToolMessage(t1) 之后
        tool_msgs = [m for m in result if isinstance(m, ToolMessage)]
        assert len(tool_msgs) == 2
        cancelled = [m for m in tool_msgs if m.content == "(cancelled)"]
        assert len(cancelled) == 1
        assert cancelled[0].tool_call_id == "t2"

    def test_cancelled_placeholder_when_no_tool_message_exists(self):
        """没有 ToolMessage 时，placeholder 在最后一个 AssistantMessage 之后。"""
        msgs = [
            UserMessage(content=[TextBlock(text="go")]),
            AssistantMessage(content=[ToolUseBlock(id="t1", name="a", input={})]),
        ]
        result = normalize_messages(msgs)
        assert isinstance(result[-1], ToolMessage)
        assert result[-1].content == "(cancelled)"
