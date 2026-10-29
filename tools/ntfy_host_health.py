#!/usr/bin/env python3
"""Read-only, nonsecret local health assessment of GoreeCloud's private ntfy stack.

Requires the Docker CLI (never mounts Docker socket into a container).
No account tokens, auth records, message bodies, SMTP secrets or private
network routes are read or emitted. Suitable for an authorized host-level
monitor; an exit code is NOT evidence that an alert was delivered.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import stat
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import urlopen

AGE_LIMIT = timedelta(hours=36)
SNAPSHOT_NAME = re.compile(r"^ntfy-([0-9]{8}T[0-9]{6}Z)-[0-9a-f]{8}$")
DB_NAMES = ("auth.db", "cache.db")
CHECKS = ("backend", "backup_worker", "loopback_binding", "readiness", "recent_snapshot", "scheduled_backup", "snapshot_integrity")


def container_status(name: str, run=subprocess.run) -> tuple[str, str, str]:
    response = run(
        ["docker", "inspect", "--format",
         "{{.State.Status}}|{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}|{{.HostConfig.NetworkMode}}",
         name],
        text=True, capture_output=True, timeout=8, check=False,
    )
    if response.returncode:
        return "absent", "missing", "unknown"
    fields = response.stdout.strip().split("|")
    return tuple(fields) if len(fields) == 3 else ("error", "missing", "unknown")


def loopback_only(name: str, run=subprocess.run) -> bool:
    response = run(["docker", "port", name, "8080/tcp"], text=True, capture_output=True,
                   timeout=8, check=False)
    entries = [line.strip() for line in response.stdout.splitlines() if line.strip()]
    return response.returncode == 0 and bool(entries) and all(
        line.startswith("127.0.0.1:") for line in entries
    )


def ready(url: str = "http://127.0.0.1:8792/v1/health", fetch=urlopen) -> bool:
    try:
        with fetch(url, timeout=4) as response:
            payload = response.read(2048)
            return response.status == 200 and json.loads(payload).get("healthy") is True
    except (OSError, ValueError, TimeoutError):
        return False


def private_file(path: Path, directory: bool) -> bool:
    try:
        info = path.lstat()
    except OSError:
        return False
    kind = stat.S_ISDIR if directory else stat.S_ISREG
    return kind(info.st_mode) and info.st_uid == os.getuid() and not info.st_mode & 0o077


def latest_snapshot(backups: Path, when: datetime) -> tuple[bool, Path | None]:
    if not private_file(backups, directory=True):
        return False, None
    candidates = []
    for entry in backups.iterdir():
        match = SNAPSHOT_NAME.fullmatch(entry.name)
        if not match or not private_file(entry, directory=True):
            continue
        try:
            timestamp = datetime.strptime(match.group(1), "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        candidates.append((timestamp, entry))
    if not candidates:
        return False, None
    timestamp, chosen = max(candidates, key=lambda item: item[0])
    age = when - timestamp
    return timedelta(0) <= age <= AGE_LIMIT, chosen


def scheduled_backup_present(folder: Path | None, now: datetime) -> bool:
    """By 04:15 UTC, today's 03:15 UTC backup should exist."""
    now = now.astimezone(timezone.utc)
    cutoff = now.replace(hour=4, minute=15, second=0, microsecond=0)
    if now < cutoff:
        return True  # Still within today's run and recovery window.
    if folder is None:
        return False
    match = SNAPSHOT_NAME.fullmatch(folder.name)
    if match is None:
        return False
    captured = datetime.strptime(match.group(1), "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    return captured.date() == now.date() and captured <= now


def snapshot_integrity(folder: Path | None) -> bool:
    if folder is None or not private_file(folder, directory=True):
        return False
    for filename in DB_NAMES:
        path = folder / filename
        if not private_file(path, directory=False):
            return False
        try:
            with sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True, timeout=5) as db:
                result = db.execute("PRAGMA quick_check").fetchone()
            if not result or result[0] != "ok":
                return False
        except (sqlite3.DatabaseError, OSError):
            return False
    return True


def inspect(backups: Path, *, now: datetime | None = None,
            run=subprocess.run, fetch=urlopen) -> dict[str, bool]:
    now = now or datetime.now(timezone.utc)
    backend = container_status("goreecloud-ntfy", run)
    worker = container_status("goreecloud-ntfy-backup", run)
    recent, folder = latest_snapshot(backups, now)
    return {
        "backend": backend[0:2] == ("running", "healthy"),
        "backup_worker": worker[0:3] == ("running", "healthy", "none"),
        "loopback_binding": loopback_only("goreecloud-ntfy", run),
        "readiness": ready(fetch=fetch),
        "recent_snapshot": recent,
        "scheduled_backup": scheduled_backup_present(folder, now),
        "snapshot_integrity": snapshot_integrity(folder),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backups", type=Path, required=True)
    parser.add_argument("--json", action="store_true", help="Output only nonsecret status keys")
    args = parser.parse_args()
    try:
        result = inspect(args.backups)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print("Health probe failed: " + type(error).__name__, file=sys.stderr)
        return 2
    success = all(result.values())
    if args.json:
        print(json.dumps({"status": "ok" if success else "degraded", "checks": result}, sort_keys=True))
    else:
        for key in CHECKS:
            print(f"{key}: {'OK' if result[key] else 'FAIL'}")
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
