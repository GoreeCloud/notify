"""Tests use only synthetic SQLite files and command construction."""
import sqlite3
from pathlib import Path
from types import SimpleNamespace

import pytest

from tools.ntfy_restore_drill import (
    PREFIX, build_run_args, copied_snapshot, validate_snapshot, verify_offline_http,
)


def fixture(tmp_path: Path):
    folder = tmp_path / "snapshot"
    folder.mkdir(mode=0o700)
    for name in ("auth.db", "cache.db"):
        path = folder / name
        with sqlite3.connect(path) as db:
            db.execute("CREATE TABLE synthetic (value INTEGER)")
            db.execute("INSERT INTO synthetic VALUES (42)")
        path.chmod(0o600)
    return folder


def test_valid_sqlite_snapshot_and_private_copy(tmp_path):
    source = fixture(tmp_path)
    validate_snapshot(source)
    copy = tmp_path / "isolated"
    copy.mkdir(mode=0o700)
    copied_snapshot(source, copy)
    validate_snapshot(copy)
    assert all((copy / name).stat().st_mode & 0o077 == 0 for name in ("auth.db", "cache.db"))


def test_reject_public_permissions_and_links(tmp_path):
    source = fixture(tmp_path)
    (source / "auth.db").chmod(0o644)
    with pytest.raises(PermissionError):
        validate_snapshot(source)
    (source / "auth.db").chmod(0o600)
    (source / "auth.db").rename(source / "actual.db")
    (source / "auth.db").symlink_to(source / "actual.db")
    with pytest.raises(PermissionError):
        validate_snapshot(source)


def test_offline_container_has_no_exposure(tmp_path):
    source = fixture(tmp_path)
    command = build_run_args(PREFIX + "abcd1234", source)
    text = " ".join(command)
    for required in ("--network none", "--read-only", "--pull=never",
                     "--cap-drop ALL", "--user 1001:1001",
                     "NTFY_AUTH_DEFAULT_ACCESS=deny-all", "--log-driver none"):
        assert required in text
    assert "-p" not in command
    assert "--privileged" not in command
    with pytest.raises(ValueError):
        build_run_args("goreecloud-ntfy", source)


def test_internal_health_and_ready_required(monkeypatch):
    import tools.ntfy_restore_drill as drill
    seen = []

    def fake_run(args, **kwargs):
        seen.append(args[-1])
        if args[-1].endswith("health"):
            return SimpleNamespace(returncode=0, stdout='{"healthy":true}')
        return SimpleNamespace(returncode=0, stdout='{"ready":true}')

    monkeypatch.setattr(drill.subprocess, "run", fake_run)
    verify_offline_http(PREFIX + "abcd1234", attempts=1)
    assert len(seen) == 2


def test_corrupt_backup_is_rejected(tmp_path):
    source = fixture(tmp_path)
    (source / "cache.db").write_bytes(b"corrupted sqlite file")
    (source / "cache.db").chmod(0o600)
    with pytest.raises(sqlite3.DatabaseError):
        validate_snapshot(source)


def test_docker_mount_uses_supported_bind_syntax(tmp_path):
    source = fixture(tmp_path)
    args = build_run_args(PREFIX + "probe1234", source)
    mount = args[args.index("--mount") + 1]
    assert mount.startswith("type=bind,src=")
    assert mount.endswith(",dst=/var/lib/ntfy")
    assert ",rw" not in mount
    assert "--network" in args and args[args.index("--network") + 1] == "none"


def test_failed_disposable_health_check_leaves_source_intact(tmp_path, monkeypatch):
    import tools.ntfy_restore_drill as drill
    snapshot = fixture(tmp_path)
    staging = tmp_path / "staging"
    staging.mkdir(mode=0o700)
    seen = []
    monkeypatch.setattr(drill, "run_checked", lambda *_args, **_kw: None)

    def fail_probe(_name):
        raise RuntimeError("test-only readiness failure")

    def dummy_docker(args, **_kw):
        seen.append(args)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(drill, "verify_offline_http", fail_probe)
    monkeypatch.setattr(drill.subprocess, "run", dummy_docker)
    with pytest.raises(RuntimeError, match="test-only"):
        drill.restoration_drill(snapshot, staging)
    assert [args[1] for args in seen] == ["stop", "rm"]
    assert list(staging.iterdir()) == []
    assert all((snapshot / name).exists() for name in ("auth.db", "cache.db"))


def test_failed_docker_launch_has_bounded_disposable_cleanup(tmp_path, monkeypatch):
    import tools.ntfy_restore_drill as drill
    source = fixture(tmp_path)
    stage = tmp_path / "stage"
    stage.mkdir(mode=0o700)
    calls = []

    def failed_launch(*args, **kwargs):
        raise RuntimeError("test-only Docker launch failure")

    def fake_process(args, **kwargs):
        calls.append(args)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(drill, "run_checked", failed_launch)
    monkeypatch.setattr(drill.subprocess, "run", fake_process)
    with pytest.raises(RuntimeError, match="test-only"):
        drill.restoration_drill(source, stage)
    assert len(calls) == 1 and calls[0][1] == "rm"
    assert calls[0][-1].startswith(PREFIX)
    assert not list(stage.iterdir())
    assert (source / "auth.db").exists()
