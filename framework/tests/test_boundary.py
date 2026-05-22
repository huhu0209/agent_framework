"""执行边界测试。"""

from pathlib import Path

import pytest

from agent_framework.safety.boundary import PathEscapesWorkspace, safe_path


class TestSafePath:
    def test_normal_relative_path(self, tmp_path: Path):
        result = safe_path("src/main.py", tmp_path)
        assert str(result).startswith(str(tmp_path))

    def test_traversal_attack(self, tmp_path: Path):
        with pytest.raises(PathEscapesWorkspace):
            safe_path("../../../etc/passwd", tmp_path)

    def test_absolute_path_outside(self, tmp_path: Path):
        with pytest.raises(PathEscapesWorkspace):
            safe_path("/etc/passwd", tmp_path)

    def test_dot_path(self, tmp_path: Path):
        result = safe_path(".", tmp_path)
        assert result == tmp_path.resolve()

    def test_normal_subdirectory(self, tmp_path: Path):
        result = safe_path("a/b/c.txt", tmp_path)
        assert str(result).endswith("a/b/c.txt")

    def test_empty_path(self, tmp_path: Path):
        result = safe_path("", tmp_path)
        assert result == tmp_path.resolve()
