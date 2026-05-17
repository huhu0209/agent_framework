"""消息规范化测试。"""

import pytest
from agent_framework.llm.transform import normalize_messages
from agent_framework.llm.types import (
    AssistantMessage,
    SystemMessage,
    TextBlock,
    ToolMessage,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)


class TestNormalizeMessages:
    def test_empty_messages(self):
        result = normalize_messages([])
        assert result == []

    def test_normal_sequence_passes_through(self):
        messages = [
            SystemMessage(content="system"),
            UserMessage(content=[TextBlock(text="hello")]),
            AssistantMessage(content=[TextBlock(text="hi")]),
        ]
        result = normalize_messages(messages)
        assert len(result) == 3

    def test_consecutive_user_messages_merged(self):
        messages = [
            UserMessage(content=[TextBlock(text="first")]),
            UserMessage(content=[TextBlock(text="second")]),
        ]
        result = normalize_messages(messages)
        assert len(result) == 1
        assert isinstance(result[0], UserMessage)
        texts = [b.text for b in result[0].content if isinstance(b, TextBlock)]
        assert "first" in texts
        assert "second" in texts

    def test_consecutive_assistant_messages_merged(self):
        messages = [
            AssistantMessage(content=[TextBlock(text="first")]),
            AssistantMessage(content=[TextBlock(text="second")]),
        ]
        result = normalize_messages(messages)
        assert len(result) == 1
        assert isinstance(result[0], AssistantMessage)

    def test_tool_message_kept_after_assistant(self):
        messages = [
            UserMessage(content=[TextBlock(text="hello")]),
            AssistantMessage(content=[ToolUseBlock(id="tc_1", name="read_file", input={"path": "/tmp"})]),
            ToolMessage(tool_call_id="tc_1", content="file content"),
        ]
        result = normalize_messages(messages)
        assert len(result) == 3

    def test_system_message_always_first(self):
        messages = [
            SystemMessage(content="system prompt"),
            UserMessage(content=[TextBlock(text="hello")]),
        ]
        result = normalize_messages(messages)
        assert isinstance(result[0], SystemMessage)

    def test_different_roles_not_merged(self):
        messages = [
            UserMessage(content=[TextBlock(text="hello")]),
            AssistantMessage(content=[TextBlock(text="hi")]),
            UserMessage(content=[TextBlock(text="follow up")]),
        ]
        result = normalize_messages(messages)
        assert len(result) == 3
