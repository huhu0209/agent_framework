"""McpTransport ABC 测试 — 接口契约验证。"""

import pytest

from agent_framework.tools.mcp.transport import McpTransport


def test_mcp_transport_is_abstract():
    """McpTransport 不能直接实例化。"""
    with pytest.raises(TypeError):
        McpTransport()


def test_mcp_transport_required_methods():
    """子类必须实现 connect / close / send / send_notification。"""
    methods = {"connect", "close", "send", "send_notification"}
    assert methods.issubset(dir(McpTransport))
