"""result_truncator 测试 — 小结果放行、大结果转储、错误保留。"""

import os

import pytest

from agent_framework.tools.context.result_truncator import (
    MAX_RESULT_CHARS,
    PREVIEW_HEAD_CHARS,
    PREVIEW_TAIL_CHARS,
    RESULT_DUMP_DIR,
    truncate_if_needed,
)
from agent_framework.tools.types import ToolResult


async def test_small_result_not_truncated(tmp_path):
    result = ToolResult(content="short")
    out = await truncate_if_needed(result, "call_1", str(tmp_path))
    assert out is result


async def test_exact_threshold_not_truncated(tmp_path):
    content = "x" * MAX_RESULT_CHARS
    result = ToolResult(content=content)
    out = await truncate_if_needed(result, "call_2", str(tmp_path))
    assert out is result


async def test_large_result_truncated_and_dumped(tmp_path):
    content = "A" * (MAX_RESULT_CHARS + 1)
    result = ToolResult(content=content)
    out = await truncate_if_needed(result, "call_3", str(tmp_path))

    assert out is not result
    assert "工具结果过大" in out.content
    assert out.metadata["truncated"] is True
    assert out.metadata["original_length"] == len(content)

    dump_path = out.metadata["dump_path"]
    assert os.path.isfile(dump_path)
    with open(dump_path, encoding="utf-8") as f:
        assert f.read() == content

    assert f"{RESULT_DUMP_DIR}/call_3.txt" in out.content


async def test_error_result_also_truncated(tmp_path):
    content = "E" * (MAX_RESULT_CHARS + 100)
    result = ToolResult(content=content, is_error=True)
    out = await truncate_if_needed(result, "call_4", str(tmp_path))

    assert out.is_error is True


async def test_preview_cut_at_threshold(tmp_path):
    content = "B" * (MAX_RESULT_CHARS + 1)
    result = ToolResult(content=content)
    out = await truncate_if_needed(result, "call_5", str(tmp_path))

    head = content[:PREVIEW_HEAD_CHARS]
    tail = content[-PREVIEW_TAIL_CHARS:]
    assert head in out.content
    assert tail in out.content
    assert f"{RESULT_DUMP_DIR}/call_5.txt" in out.content


async def test_traversal_tool_call_id_sanitized(tmp_path):
    """C1: 含路径分隔符的 tool_call_id 被消毒，dump 文件落在 dump_dir 内。"""
    result = ToolResult(content="X" * (MAX_RESULT_CHARS + 1))
    out = await truncate_if_needed(result, "../../etc/cron.d/evil", str(tmp_path))

    dump_path = out.metadata["dump_path"]
    # dump_path 必须在 dump_dir（tmp_path/.agent_results）内，不逃逸
    dump_dir = os.path.join(str(tmp_path), RESULT_DUMP_DIR)
    assert os.path.dirname(dump_path) == dump_dir
    # 文件确实写到 dump_dir 内
    assert os.path.isfile(dump_path)
    # 消毒后文件名无路径分隔符（路径遍历的本质防护；".." 子串无害因不构成路径）
    assert "/" not in os.path.basename(dump_path)
    assert "\\" not in os.path.basename(dump_path)


async def test_dotdot_only_tool_call_id_gets_uuid(tmp_path):
    """C1: tool_call_id 消毒后为 '..' 时用 uuid 兜底，不写成 ..txt。"""
    result = ToolResult(content="X" * (MAX_RESULT_CHARS + 1))
    out = await truncate_if_needed(result, "..", str(tmp_path))

    dump_path = out.metadata["dump_path"]
    basename = os.path.basename(dump_path)
    assert basename not in ("..txt", ".txt")
    assert os.path.isfile(dump_path)
