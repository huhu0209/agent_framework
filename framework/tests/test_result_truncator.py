"""result_truncator 测试 — 小结果放行、大结果转储、错误保留。"""

import os

import pytest

from agent_framework.tools.context.result_truncator import (
    MAX_RESULT_CHARS,
    PREVIEW_CHARS,
    RESULT_DUMP_DIR,
    truncate_if_needed,
)
from agent_framework.tools.types import ToolResult


def test_small_result_not_truncated(tmp_path):
    result = ToolResult(content="short")
    out = truncate_if_needed(result, "call_1", str(tmp_path))
    assert out is result


def test_exact_threshold_not_truncated(tmp_path):
    content = "x" * MAX_RESULT_CHARS
    result = ToolResult(content=content)
    out = truncate_if_needed(result, "call_2", str(tmp_path))
    assert out is result


def test_large_result_truncated_and_dumped(tmp_path):
    content = "A" * (MAX_RESULT_CHARS + 1)
    result = ToolResult(content=content)
    out = truncate_if_needed(result, "call_3", str(tmp_path))

    assert out is not result
    assert "工具结果过大" in out.content
    assert out.metadata["truncated"] is True
    assert out.metadata["original_length"] == len(content)

    dump_path = out.metadata["dump_path"]
    assert os.path.isfile(dump_path)
    with open(dump_path, encoding="utf-8") as f:
        assert f.read() == content

    assert f"{RESULT_DUMP_DIR}/call_3.txt" in out.content


def test_error_result_also_truncated(tmp_path):
    content = "E" * (MAX_RESULT_CHARS + 100)
    result = ToolResult(content=content, is_error=True)
    out = truncate_if_needed(result, "call_4", str(tmp_path))

    assert out.is_error is True


def test_preview_cut_at_threshold(tmp_path):
    content = "B" * (MAX_RESULT_CHARS + 1)
    result = ToolResult(content=content)
    out = truncate_if_needed(result, "call_5", str(tmp_path))

    preview = content[:PREVIEW_CHARS]
    assert preview in out.content
    assert f"{RESULT_DUMP_DIR}/call_5.txt" in out.content
