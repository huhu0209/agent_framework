from pathlib import Path

from app.services.session import _bucket_for, _safe_basename, DEFAULT_BUCKET


def test_none_returns_default_bucket():
    assert _bucket_for(None) == DEFAULT_BUCKET
    assert DEFAULT_BUCKET == "default_chat"


def test_same_abspath_same_bucket(tmp_path):
    p = tmp_path / "agent_framework"
    p.mkdir()
    assert _bucket_for(str(p)) == _bucket_for(str(p))


def test_different_abspath_different_bucket(tmp_path):
    a = tmp_path / "app"
    a.mkdir()
    b = tmp_path / "app2"
    b.mkdir()
    assert _bucket_for(str(a)) != _bucket_for(str(b))


def test_bucket_name_format(tmp_path):
    p = tmp_path / "myapp"
    p.mkdir()
    name = _bucket_for(str(p))
    base, _, digest = name.rpartition("_")
    assert base == "myapp"
    assert len(digest) == 8


def test_safe_basename_strips_special_chars():
    assert _safe_basename(Path("/x/app framework")) == "app_framework"
    assert _safe_basename(Path("/x/...")) == "project"  # 空 → project
    assert _safe_basename(Path("/x/a.b.c")) == "a_b_c"
