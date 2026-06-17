"""A3: CORS 通配源校验测试。"""

from __future__ import annotations

import pytest


def test_validate_cors_rejects_wildcard() -> None:
    """A3: allow_credentials=True 时禁止 '*' 源。"""
    from main import validate_cors_origins

    with pytest.raises(ValueError, match="ALLOWED_ORIGINS"):
        validate_cors_origins(["*"])


def test_validate_cors_rejects_wildcard_among_others() -> None:
    """A3: 混在显式源中的 '*' 也应拒绝。"""
    from main import validate_cors_origins

    with pytest.raises(ValueError):
        validate_cors_origins(["http://localhost:5173", "*"])


def test_validate_cors_accepts_explicit_origins() -> None:
    """A3: 显式源列表应通过。"""
    from main import validate_cors_origins

    validate_cors_origins(["http://localhost:5173", "https://app.example.com"])  # 不抛
