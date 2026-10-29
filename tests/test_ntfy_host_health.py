"""Read-only host-health tests using synthetic local databases and fake Docker."""
import io
import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

from tools.ntfy_host_health import (
    backup_capacity, container_hardening, container_status, inspect, latest_snapshot, loopback_only,
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
        if "{{json .HostConfig}}" in cmd[3]:
            worker = cmd[-1] == "goreecloud-ntfy-backup"
            cfg = {
                "ReadonlyRootfs": True, "Privileged": False,
                "CapDrop": ["ALL"], "SecurityOpt": ["no-new-privileges:true"],
                "NetworkMode": "none" if worker else "goreecloud-ntfy_default",
                "PortBindings": None if worker else {
                    "8080/tcp": [{"HostIp": "127.0.0.1", "HostPort": "8792"}]},
            }
            mounts = (
                [{"Destination": "/source", "RW": False}, {"Destination": "/snapshots", "RW": True},
                 {"Destination": "/app/backup_ntfy_sqlite.py", "RW": False},
                 {"Destination": "/app/ntfy_backup_scheduler.py", "RW": False}]
                if worker else [{"Destination": "/var/lib/ntfy", "RW": True}]
            )
            return SimpleNamespace(returncode=0, stdout=json.dumps(cfg) + "|" + json.dumps(mounts) + "|1001:1001\n")
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

def test_hardening_guardrails_reject_escalation_and_unexpected_bindings(tmp_path):
    backups, _ = fixtures(tmp_path)
    assert container_hardening("goreecloud-ntfy", docker)
    assert container_hardening("goreecloud-ntfy-backup", docker)
    assert all(inspect(backups, now=NOW, run=docker, fetch=fetch).values())

    def unsafe(cmd, **kwargs):
        response = docker(cmd, **kwargs)
        if cmd[1] == "inspect" and "{{json .HostConfig}}" in cmd[3]:
            host, mounts, user = response.stdout.strip().split("|")
            cfg = json.loads(host)
            cfg["Privileged"] = True
            return SimpleNamespace(returncode=0, stdout=json.dumps(cfg) + "|" + mounts + "|" + user)
        return response

    assert not container_hardening("goreecloud-ntfy", unsafe)
    assert not container_hardening("goreecloud-ntfy-backup", unsafe)
    assert not inspect(backups, now=NOW, run=unsafe, fetch=fetch)["backend_hardening"]

    def bad_worker_mount(cmd, **kwargs):
        response = docker(cmd, **kwargs)
        if cmd[1] == "inspect" and "{{json .HostConfig}}" in cmd[3] and cmd[-1] == "goreecloud-ntfy-backup":
            host, mounts, user = response.stdout.strip().split("|")
            m = json.loads(mounts)
            m[0]["RW"] = True
            return SimpleNamespace(returncode=0, stdout=host + "|" + json.dumps(m) + "|" + user)
        return response

    assert not container_hardening("goreecloud-ntfy-backup", bad_worker_mount)


def test_capacity_warns_before_snapshot_limit_and_disk_exhaustion(tmp_path):
    backups, folder = fixtures(tmp_path)
    slots, reserve = backup_capacity(backups, folder)
    assert slots and reserve
    import shutil
    for i in range(39):
        (backups / f"ntfy-202610{i % 28 + 1:02d}T031500Z-{i:08x}").mkdir(mode=0o700)
    slots, reserve = backup_capacity(backups, folder)
    assert not slots and reserve
    assert inspect(backups, now=NOW, run=docker, fetch=fetch)["backup_slots_available"] is False
    # File size is nonzero but reserve must not use bogus disk capacity.
    low_disk = lambda _path: SimpleNamespace(free=100)
    assert backup_capacity(backups, folder, disk_usage=low_disk) == (False, False)


def test_other_port_and_public_binding_rejected():
    for value in ("127.0.0.1:8793\n", "0.0.0.0:8792\n", "127.0.0.1:8792\n0.0.0.0:8792\n"):
        def returned(cmd, **kwargs):
            if cmd[1] == "port":
                return SimpleNamespace(returncode=0, stdout=value)
            return docker(cmd, **kwargs)
        assert not loopback_only("goreecloud-ntfy", returned)


def test_invalid_docker_hardening_metadata_rejected():
    def malformed(cmd, **kwargs):
        return SimpleNamespace(returncode=0, stdout="not-json|[]|1001:1001")
    assert not container_hardening("goreecloud-ntfy", malformed)
