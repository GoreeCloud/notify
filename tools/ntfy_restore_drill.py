#!/usr/bin/env python3
"""Restore a private ntfy SQLite snapshot into a disposable, offline container.

No changes to the live ntfy process, Compose project, SQLite databases, DNS,
gateway, authentication, or published ports. The drill creates a private copy
of existing snapshot files, launches the *pinned* ntfy image with no network,
probes HTTP from inside its own network namespace, stops that test container
and destroys only its new staging directory. Neither data nor Docker logs are
printed or uploaded. Docker access is required on the authorized VPS.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import stat
import subprocess
import tempfile
import time
import uuid
from pathlib import Path

IMAGE = ("binwiederhier/ntfy:v2.34.0@sha256:"
         "901e14503d3f605f445be0e68f2ac71f0aa73391897ce6ceb599f8c48d8b3792")
DB_NAMES = ("auth.db", "cache.db")
PREFIX = "goreecloud-ntfy-restore-test-"


def private(path: Path, *, folder: bool) -> Path:
    info = path.lstat()
    kind = stat.S_ISDIR if folder else stat.S_ISREG
    if not kind(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise PermissionError("Expected owner-only regular data or directory")
    return path.resolve(strict=True)


def validate_snapshot(snapshot: Path) -> None:
    private(snapshot, folder=True)
    for dbname in DB_NAMES:
        path = private(snapshot / dbname, folder=False)
        with sqlite3.connect("file:" + str(path) + "?mode=ro&immutable=1",
                             uri=True, timeout=5) as db:
            if db.execute("PRAGMA integrity_check").fetchone() != ("ok",):
                raise RuntimeError("Invalid SQLite snapshot")


def build_run_args(name: str, stage: Path) -> list[str]:
    if not name.startswith(PREFIX) or not name[len(PREFIX):].isalnum():
        raise ValueError("Invalid disposable container name")
    return [
        "docker", "run", "--detach", "--rm", "--pull=never", "--init",
        "--name", name, "--network", "none", "--read-only",
        "--user", "1001:1001", "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges:true",
        "--pids-limit", "64", "--memory", "128m", "--cpus", "0.50",
        "--log-driver", "none",
        "--tmpfs", "/tmp:rw,nosuid,noexec,size=16m",
        "--mount", "type=bind,src=" + str(stage) + ",dst=/var/lib/ntfy",
        "--env", "NTFY_LISTEN_HTTP=:8080",
        "--env", "NTFY_CACHE_FILE=/var/lib/ntfy/cache.db",
        "--env", "NTFY_AUTH_FILE=/var/lib/ntfy/auth.db",
        "--env", "NTFY_AUTH_DEFAULT_ACCESS=deny-all",
        "--env", "NTFY_BEHIND_PROXY=false",
        "--env", "NTFY_LOG_LEVEL=error",
        IMAGE, "serve",
    ]


def copied_snapshot(snapshot: Path, stage: Path) -> None:
    for name in DB_NAMES:
        src = private(snapshot / name, folder=False)
        dst = stage / name
        shutil.copyfile(src, dst)
        os.chmod(dst, 0o600)
    validate_snapshot(stage)


def run_checked(args: list[str], *, timeout: float = 12) -> subprocess.CompletedProcess:
    result = subprocess.run(args, capture_output=True, text=True,
                            check=False, timeout=timeout)
    if result.returncode:
        # Logs and command errors may include host paths or private records.
        raise RuntimeError("Container operation failed")
    return result


def verify_offline_http(name: str, attempts: int = 12) -> None:
    for _ in range(attempts):
        try:
            result = subprocess.run(
                ["docker", "exec", name, "wget", "-q", "-O", "-",
                 "http://127.0.0.1:8080/v1/health"],
                capture_output=True, text=True, timeout=3, check=False,
            )
            if result.returncode == 0:
                data = json.loads(result.stdout[:2048])
                if data.get("healthy") is True:
                    # Readiness must be up before counting the restoration.
                    ready = subprocess.run(
                        ["docker", "exec", name, "wget", "-q", "-O", "-",
                         "http://127.0.0.1:8080/v1/ready"],
                        capture_output=True, text=True, timeout=3, check=False,
                    )
                    if ready.returncode == 0:
                        return
        except (OSError, ValueError, subprocess.TimeoutExpired):
            pass
        time.sleep(0.4)
    raise RuntimeError("Restored ntfy process did not become healthy and ready")


def restoration_drill(snapshot: Path, staging_root: Path) -> None:
    validate_snapshot(snapshot)
    private(staging_root, folder=True)
    if snapshot == staging_root or staging_root in snapshot.parents or snapshot in staging_root.parents:
        raise ValueError("Staging and backup trees must not overlap")
    name = PREFIX + uuid.uuid4().hex[:12]
    with tempfile.TemporaryDirectory(prefix="ntfy-restore-drill-", dir=staging_root) as temp:
        stage = Path(temp)
        os.chmod(stage, 0o700)
        copied_snapshot(snapshot, stage)
        started = False
        try:
            run_checked(build_run_args(name, stage))
            started = True
            verify_offline_http(name)
        finally:
            try:
                if started:
                    subprocess.run(["docker", "stop", "--time", "3", name],
                                   capture_output=True, text=True, check=False, timeout=10)
            finally:
                # Also handle a Docker launch timeout after container creation.
                # Only the uniquely generated disposable test name is targeted.
                subprocess.run(["docker", "rm", "--force", name],
                               capture_output=True, text=True, check=False, timeout=8)
    print("PASS: isolated ntfy startup, healthy/ready, disposable restore cleaned")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--staging-root", type=Path, required=True)
    args = parser.parse_args()
    restoration_drill(args.snapshot, args.staging_root)


if __name__ == "__main__":
    main()
