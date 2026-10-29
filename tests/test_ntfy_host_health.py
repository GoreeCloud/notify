"""Read-only host-health tests using synthetic local databases and fake Docker."""
import io
import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

from tools.ntfy_host_health import (
    container_status, inspect, latest_snapshot, loopback_only,
    private_file, ready, snapshot_integrity, scheduled_backup_present,
)


NOW = datetime(2026, 10, 29, 6, 4, tzinfo=timezone.utc)


def fixtures(tmp_path: Path):
    backups = tmp_path / "backups"
    backups.mkdir(mode=0o700)
    folder = backups / "ntfy-20261029T050000Z-123abcdd"
    folder.mkdir(mode=0o700)
    for name in ("auth.db", "cache.db"):
        path = folder / name
        with sqlite3.connect(path) as db:
            db.execute("CREATE TABLE tests(x INTEGER)")
            db.execute("INSERT INTO tests VALUES (42)")
        path.chmod(0o600)
    return backups, folder


def docker(cmd, **kwargs):
    if cmd[1] == "inspect":
        if cmd[-1] == "goreecloud-ntfy":
            return SimpleNamespace(returncode=0, stdout="running|healthy|goreecloud-ntfy_default\n")
        return SimpleNamespace(returncode=0, stdout="running|healthy|none\n")
    return SimpleNamespace(returncode=0, stdout="127.0.0.1:8792\n")


class DummyResponse:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, limit):
        return b'{"healthy":true}'


def fetch(url, timeout):
    assert url.startswith("http://127.0.0.1:")
    assert timeout == 4
    return DummyResponse()


def test_full_healthy_state(tmp_path):
    backups, folder = fixtures(tmp_path)
    assert private_file(folder, directory=True)
    assert snapshot_integrity(folder)
    results = inspect(backups, now=NOW, run=docker, fetch=fetch)
    assert all(results.values())
    assert results["loopback_binding"]


def test_non_loopback_binding_is_rejected(tmp_path):
    backups, _ = fixtures(tmp_path)

    def exposed(cmd, **kwargs):
        if cmd[1] == "port":
            return SimpleNamespace(returncode=0, stdout="0.0.0.0:8792\n")
        return docker(cmd, **kwargs)

    assert not loopback_only("goreecloud-ntfy", exposed)
    assert not inspect(backups, now=NOW, run=exposed, fetch=fetch)["loopback_binding"]


def test_unhealthy_or_missing_worker_is_not_accepted(tmp_path):
    backups, _ = fixtures(tmp_path)

    def stopped(cmd, **kwargs):
        if cmd[1] == "inspect" and cmd[-1] == "goreecloud-ntfy-backup":
            return SimpleNamespace(returncode=0, stdout="exited|unhealthy|none\n")
        return docker(cmd, **kwargs)

    assert not inspect(backups, now=NOW, run=stopped, fetch=fetch)["backup_worker"]


def test_stale_future_corrupt_and_symlinked_snapshots(tmp_path):
    backups, folder = fixtures(tmp_path)
    assert not latest_snapshot(backups, NOW + timedelta(hours=40))[0]
    assert not latest_snapshot(backups, NOW - timedelta(hours=3))[0]
    (folder / "cache.db").write_bytes(b"not sqlite")
    (folder / "cache.db").chmod(0o600)
    assert not snapshot_integrity(folder)
    (folder / "auth.db").unlink()
    (folder / "auth.db").symlink_to(folder / "cache.db")
    assert not snapshot_integrity(folder)


def test_private_files_enforced(tmp_path):
    backups, folder = fixtures(tmp_path)
    (folder / "auth.db").chmod(0o644)
    assert not snapshot_integrity(folder)
    (folder / "auth.db").chmod(0o600)
    backups.chmod(0o755)
    assert not latest_snapshot(backups, NOW)[0]


def test_bad_readiness_response_fails(tmp_path):
    assert ready(fetch=fetch)

    class Bad(DummyResponse):
        def read(self, limit):
            return b'{"healthy":false}'

    assert not ready(fetch=lambda *_args, **_kwargs: Bad())


def test_docker_invalid_metadata_not_accepted():
    def broken(cmd, **kwargs):
        return SimpleNamespace(returncode=1, stdout="")

    assert container_status("goreecloud-ntfy", broken)[0] == "absent"
    assert not loopback_only("goreecloud-ntfy", broken)

def test_daily_backup_due_check_detects_missed_schedule(tmp_path):
    backups, folder = fixtures(tmp_path)
    # Previous day's snapshot can be recent, but the 03:15 UTC job is due
    # after the 04:15 UTC grace window.
    tomorrow = NOW + timedelta(days=1)
    assert latest_snapshot(backups, tomorrow)[0]
    assert not scheduled_backup_present(folder, tomorrow)
    assert inspect(backups, now=tomorrow, run=docker, fetch=fetch)["scheduled_backup"] is False
    early = tomorrow.replace(hour=3, minute=45)
    assert scheduled_backup_present(folder, early)
    assert scheduled_backup_present(folder, NOW)
