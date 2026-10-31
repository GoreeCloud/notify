"""Synthetic integration and static isolation tests for the private daily backup worker."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sqlite3

import pytest

from tools.ntfy_backup_scheduler import (
    MAX_BACKUP_AGE, MAX_SNAPSHOTS, healthcheck, next_run, run_once,
    snapshot_times,
)


def now() -> datetime:
    return datetime(2026, 10, 29, 6, 0, tzinfo=timezone.utc)


def create_test_environment(tmp_path: Path):
    source, backups = tmp_path / "source", tmp_path / "backups"
    source.mkdir(mode=0o700)
    backups.mkdir(mode=0o700)
    source.chmod(0o700)
    backups.chmod(0o700)
    for file in ("auth.db", "cache.db"):
        with sqlite3.connect(source / file) as db:
            db.execute("CREATE TABLE foo (value TEXT)")
            db.execute("INSERT INTO foo VALUES ('synthetic-only')")
        (source / file).chmod(0o600)
    return source, backups


def test_schedule_is_utc_aware_and_resumes_after_missed_time():
    assert next_run(now()) == datetime(2026, 10, 30, 3, 15, tzinfo=timezone.utc)
    assert next_run(datetime(2026, 10, 29, 2, 1, tzinfo=timezone.utc)) == datetime(2026, 10, 29, 3, 15, tzinfo=timezone.utc)
    with pytest.raises(ValueError):
        next_run(datetime(2026, 10, 29))


def test_snapshot_today_is_not_duplicated_and_has_isolated_restore(tmp_path):
    source, backups = create_test_environment(tmp_path)
    assert run_once(source, backups, now()) is True
    assert len(snapshot_times(backups)) == 1
    captured = snapshot_times(backups)[-1]
    # Snapshot creation is based on live UTC; a fixed historical test clock
    # can legitimately precede the just-created snapshot.
    assert healthcheck(backups, captured + timedelta(minutes=1))
    assert run_once(source, backups, captured + timedelta(minutes=1)) is False
    assert len(snapshot_times(backups)) == 1
    assert all(f.stat().st_mode & 0o077 == 0 for folder in backups.iterdir() for f in folder.iterdir())


def test_stale_or_future_snapshot_fails_worker_health(tmp_path):
    source, backups = create_test_environment(tmp_path)
    assert run_once(source, backups, now()) is True
    captured = snapshot_times(backups)[-1]
    assert healthcheck(backups, captured + MAX_BACKUP_AGE)
    assert not healthcheck(backups, captured + MAX_BACKUP_AGE + timedelta(seconds=1))
    assert not healthcheck(backups, captured - timedelta(seconds=1))


def test_capacity_limit_refuses_new_snapshot_without_deleting_existing(tmp_path):
    source, backups = create_test_environment(tmp_path)
    start = now().date() - timedelta(days=MAX_SNAPSHOTS)
    for i in range(MAX_SNAPSHOTS):
        day = start + timedelta(days=i)
        (backups / f"ntfy-{day.strftime('%Y%m%d')}T031500Z-{i:08x}").mkdir(mode=0o700)
    with pytest.raises(RuntimeError, match="count limit"):
        run_once(source, backups, now())
    assert len(list(backups.iterdir())) == MAX_SNAPSHOTS


def test_symlink_snapshots_not_counted(tmp_path):
    source, backups = create_test_environment(tmp_path)
    other = tmp_path / "outside"
    other.mkdir()
    (backups / "ntfy-20261029T031500Z-1234abcd").symlink_to(other, target_is_directory=True)
    assert snapshot_times(backups) == []
    assert not healthcheck(backups, now())


def test_reject_unsafe_source_and_empty_backup(tmp_path):
    source, backups = create_test_environment(tmp_path)
    assert not healthcheck(backups, now())
    source.chmod(0o755)
    with pytest.raises(PermissionError):
        run_once(source, backups, now())


def test_compose_backup_worker_has_no_ingress_or_live_write_access():
    root = Path(__file__).resolve().parents[1]
    content = (root / "deploy/ntfy/backup.compose.yaml").read_text()
    assert "network_mode: none" in content
    assert "read_only: true" in content and "no-new-privileges:true" in content
    assert '"./data:/source:ro"' in content
    assert '"./backups:/snapshots:rw"' in content
    assert "cap_drop:" in content and "- ALL" in content
    assert "ports:" not in content
    assert "privileged: true" not in content
    assert "NTFY_PASSWORD" not in content and "NTFY_AUTH_TOKEN" not in content

def test_same_date_corrupt_snapshot_is_not_silently_skipped(tmp_path):
    source, backups = create_test_environment(tmp_path)
    assert run_once(source, backups, now())
    folder = next(backups.iterdir())
    (folder / "auth.db").write_bytes(b"damaged")
    (folder / "auth.db").chmod(0o600)
    # Snapshot filenames use the live UTC clock, not the test's fixed date.
    captured = snapshot_times(backups)[-1]
    with pytest.raises(sqlite3.DatabaseError):
        run_once(source, backups, captured)
    assert len(snapshot_times(backups)) == 1


def test_healthcheck_rejects_missing_snapshot_database(tmp_path):
    source, backups = create_test_environment(tmp_path)
    assert run_once(source, backups, now())
    folder = next(backups.iterdir())
    (folder / "auth.db").unlink()
    assert not healthcheck(backups, snapshot_times(backups)[-1])


def test_compose_uses_private_storage_for_large_temporary_restore():
    root = Path(__file__).resolve().parents[1]
    content = (root / "deploy/ntfy/backup.compose.yaml").read_text()
    assert "TMPDIR: /snapshots" in content
