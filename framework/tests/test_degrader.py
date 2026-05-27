"""ToolDegrader 测试 — 工具降级映射。"""

from agent_framework.tools.degrader import ToolDegrader


def test_get_fallback_returns_registered():
    d = ToolDegrader()
    d.register("write_file", "bash_echo")
    assert d.get_fallback("write_file") == "bash_echo"


def test_get_fallback_returns_none_when_not_registered():
    d = ToolDegrader()
    assert d.get_fallback("write_file") is None


def test_register_overwrites():
    d = ToolDegrader()
    d.register("write_file", "bash_echo")
    d.register("write_file", "bash_write")
    assert d.get_fallback("write_file") == "bash_write"


def test_empty_by_default():
    d = ToolDegrader()
    assert d.get_fallback("any_tool") is None
