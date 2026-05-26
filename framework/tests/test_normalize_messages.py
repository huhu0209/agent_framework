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

    def test_orphan_tool_use_gets_placeholder(self):
        """tool_use without tool_result → placeholder appended."""
        messages = [
            SystemMessage(content="s"),
            UserMessage(content=[TextBlock(text="hi")]),
            AssistantMessage(content=[ToolUseBlock(id="t1", name="read", input={"p": "f"})]),
        ]
        result = normalize_messages(messages)
        assert len(result) == 4
        assert isinstance(result[3], ToolMessage)
        assert result[3].tool_call_id == "t1"
        assert result[3].content == "(cancelled)"

    def test_paired_tool_result_unchanged(self):
        """tool_use with tool_result → no change."""
        messages = [
            SystemMessage(content="s"),
            UserMessage(content=[TextBlock(text="hi")]),
            AssistantMessage(content=[ToolUseBlock(id="t1", name="read", input={"p": "f"})]),
            ToolMessage(tool_call_id="t1", content="file content"),
        ]
        result = normalize_messages(messages)
        assert len(result) == 4
        assert isinstance(result[3], ToolMessage)
        assert result[3].content == "file content"

    def test_multiple_orphans_each_get_placeholder(self):
        """Multiple tool_uses, some without results → each gets placeholder."""
        messages = [
            UserMessage(content=[TextBlock(text="go")]),
            AssistantMessage(content=[
                ToolUseBlock(id="t1", name="a", input={}),
                ToolUseBlock(id="t2", name="b", input={}),
            ]),
            ToolMessage(tool_call_id="t1", content="result a"),
        ]
        result = normalize_messages(messages)
        tool_msgs = [m for m in result if isinstance(m, ToolMessage)]
        assert len(tool_msgs) == 2
        ids = {m.tool_call_id for m in tool_msgs}
        assert ids == {"t1", "t2"}
        t2_msg = next(m for m in tool_msgs if m.tool_call_id == "t2")
        assert t2_msg.content == "(cancelled)"


class TestImmutability:
    """验证 normalize_messages 不修改原始输入。"""

    def test_original_messages_not_mutated(self):
        original_content_1 = [TextBlock(text="hello")]
        original_content_2 = [TextBlock(text="world")]

        msg1 = UserMessage(content=list(original_content_1))
        msg2 = UserMessage(content=list(original_content_2))

        original_id_1 = id(msg1.content)

        messages = [msg1, msg2]
        normalize_messages(messages)

        assert id(msg1.content) == original_id_1
        assert msg1.content == original_content_1
