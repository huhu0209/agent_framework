"""H-G7: help 命令封装边界测试——不跨模块访问 skill_registry._documents。"""

import inspect

from agent_framework.commands.builtins import help as help_mod


def test_help_handler_uses_public_is_active_not_private_documents():
    """H-G7: _handler 通过公共 is_active 查询，不访问私有 _documents。"""
    source = inspect.getsource(help_mod._handler)
    assert "_documents" not in source  # 不再跨模块访问私有属性
    assert "is_active" in source  # 改用公共方法
