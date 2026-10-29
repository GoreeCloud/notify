"""Synthetic SQLite backup and restore contract (no live ntfy records)."""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import pytest

from tools.backup_ntfy_sqlite import (
    DATABASES, check_isolated_restore, snapshot_databases, verify_backup,
)


def fixture_data(tmp_path: Path) -> Path:
    source = tmp_path / "data"
    source.mkdir(mode=0o700)
    source.chmod(0o700)
    for name in DATABASES:
        path = source / name
        with sqlite3.connect(path) as db:
            db.execute("CREATE TABLE records (message TEXT)")
            db.execute("INSERT INTO records VALUES (?)", ("SYNTHETIC-" + name,))
        path.chmod(0o600)
    return source


def test_online_snapshot_and_independent_restore(tmp_path: Path):
    source = fixture_data(tmp_path)
    live = sqlite3.connect(source / "cache.db")
    live.execute("PRAGMA journal_mode=WAL")
    live.execute("INSERT INTO records VALUES ('latest')")
    live.commit()
    dest = snapshot_databases(source, tmp_path / "backups")
    try:
        assert dest.stat().st_mode & 0o077 == 0
        assert (tmp_path / "backups").stat().st_mode & 0o077 == 0
        assert sorted(path.name for path in dest.iterdir()) == sorted(DATABASES)
        for name in DATABASES:
            target = dest / name
            assert target.stat().st_mode & 0o077 == 0
            verify_backup(target)
        with sqlite3.connect(dest / "cache.db") as db:
            values = [row[0] for row in db.execute("SELECT message FROM records")]
        assert "latest" in values
        check_isolated_restore(dest)
    finally:
        live.close()


def test_reject_world_readable_and_symlink_sources(tmp_path: Path):
    source = fixture_data(tmp_path)
    (source / "auth.db").chmod(0o644)
    with pytest.raises(PermissionError):
        snapshot_databases(source, tmp_path / "backups")
    (source / "auth.db").chmod(0o600)
    (source / "auth.db").rename(source / "actual.db")
    (source / "auth.db").symlink_to(source / "actual.db")
    with pytest.raises(ValueError, match="symlink"):
        snapshot_databases(source, tmp_path / "backups")


def test_reject_backup_directory_inside_source(tmp_path: Path):
    source = fixture_data(tmp_path)
    with pytest.raises(ValueError):
        snapshot_databases(source, source / "backups")
    with pytest.raises(ValueError):
        snapshot_databases(source, tmp_path)


def test_corrupt_database_never_publishes_snapshot(tmp_path: Path):
    source = fixture_data(tmp_path)
    (source / "cache.db").write_bytes(b"not a sqlite database")
    (source / "cache.db").chmod(0o600)
    backup_dir = tmp_path / "backups"
    with pytest.raises(sqlite3.DatabaseError):
        snapshot_databases(source, backup_dir)
    assert backup_dir.is_dir()
    assert list(backup_dir.iterdir()) == []
