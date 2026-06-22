import asyncio
from pathlib import Path
from app.services.session import SessionManager, DEFAULT_BUCKET


def _seed_legacy(legacy: Path):
    legacy.mkdir(parents=True, exist_ok=True)
    (legacy / "history.jsonl").write_text(
        '{"session_id": "%s", "title": "old", "created_at": 1.0}\n' % ("a" * 32)
    )
    (legacy / ("%s.jsonl" % ("a" * 32))).write_text("")


def test_migration_copies_legacy_into_default_chat(tmp_path):
    legacy = tmp_path / "legacy"
    new_root = tmp_path / "new"
    _seed_legacy(legacy)
    sm = SessionManager(storage_dir=new_root)
    asyncio.run(sm.migrate_legacy_sessions(legacy))
    assert (new_root / DEFAULT_BUCKET / "history.jsonl").exists()
    assert (new_root / DEFAULT_BUCKET / ("%s.jsonl" % ("a" * 32))).exists()


def test_migration_idempotent(tmp_path):
    legacy = tmp_path / "legacy"
    new_root = tmp_path / "new"
    _seed_legacy(legacy)
    sm = SessionManager(storage_dir=new_root)
    asyncio.run(sm.migrate_legacy_sessions(legacy))
    asyncio.run(sm.migrate_legacy_sessions(legacy))  # 第二次不重复/不抛
    lines = (new_root / DEFAULT_BUCKET / "history.jsonl").read_text().strip().split("\n")
    assert len(lines) == 1


def test_migration_no_legacy_dir_is_noop(tmp_path):
    new_root = tmp_path / "new"
    sm = SessionManager(storage_dir=new_root)
    asyncio.run(sm.migrate_legacy_sessions(tmp_path / "nonexistent"))  # 不抛
    assert not (new_root / DEFAULT_BUCKET).exists() or not any((new_root / DEFAULT_BUCKET).iterdir())


def test_migration_history_entries_get_bucket_field(tmp_path):
    legacy = tmp_path / "legacy"
    new_root = tmp_path / "new"
    _seed_legacy(legacy)
    sm = SessionManager(storage_dir=new_root)
    asyncio.run(sm.migrate_legacy_sessions(legacy))
    import json
    line = (new_root / DEFAULT_BUCKET / "history.jsonl").read_text().strip()
    entry = json.loads(line)
    assert entry["bucket"] == DEFAULT_BUCKET
