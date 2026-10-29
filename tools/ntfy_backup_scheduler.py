#!/usr/bin/env python3
"""Offline, non-destructive daily scheduler for the private ntfy SQLite backup.

Runs only in an isolated Docker container with no network and read-only live DBs.
No secrets, message bodies, or database contents are written to logs.
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    from tools.backup_ntfy_sqlite import DATABASES, check_isolated_restore, require_private_db, require_private_directory, snapshot_databases
except ModuleNotFoundError:  # Standalone container mounts scripts under /app
    from backup_ntfy_sqlite import DATABASES, check_isolated_restore, require_private_db, require_private_directory, snapshot_databases

SOURCE = Path("/source")
BACKUPS = Path("/snapshots")
MAX_SNAPSHOTS = 45
MIN_FREE_BYTES = 1024 * 1024 * 1024
RUN_HOUR = 3
RUN_MINUTE = 15
MAX_BACKUP_AGE = timedelta(hours=36)
FILENAME = re.compile(r"^ntfy-([0-9]{8}T[0-9]{6}Z)-[0-9a-f]{8}$")


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def snapshot_times(folder: Path) -> list[datetime]:
    """Only consider real snapshots; reject symlink entries."""
    require_private_directory(folder)
    result = []
    for entry in folder.iterdir():
        match = FILENAME.fullmatch(entry.name)
        if not match or entry.is_symlink() or not entry.is_dir():
            continue
        try:
            timestamp = datetime.strptime(match.group(1), "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        result.append(timestamp)
    return sorted(result)


def next_run(now: datetime) -> datetime:
    if now.tzinfo is None:
        raise ValueError("Expected an aware timestamp")
    now = now.astimezone(timezone.utc)
    scheduled = now.replace(hour=RUN_HOUR, minute=RUN_MINUTE, second=0, microsecond=0)
    return scheduled if now < scheduled else scheduled + timedelta(days=1)


def run_once(source: Path, backups: Path, current: datetime) -> bool:
    require_private_directory(source)
    require_private_directory(backups)
    snapshots = snapshot_times(backups)
    if snapshots and snapshots[-1].date() == current.date():
        # A same-date snapshot is only accepted after validation. Never
        # silently skip a corrupt or partially missing backup.
        for folder in backups.iterdir():
            match = FILENAME.fullmatch(folder.name)
            if match and datetime.strptime(match.group(1), "%Y%m%dT%H%M%SZ").date() == current.date():
                require_private_directory(folder)
                check_isolated_restore(folder)
        print("Verified backup already exists for current UTC date; no new snapshot", flush=True)
        return False
    if len(snapshots) >= MAX_SNAPSHOTS:
        raise RuntimeError("Backup count limit reached; operator must review retention without automatic deletion")
    # One copy for the snapshot and one disposable restore copy. Keep 1 GiB
    # extra free; do not rely only on a fixed minimum with a growing cache.
    source_bytes = sum(require_private_db(source / name).stat().st_size for name in DATABASES)
    if shutil.disk_usage(backups).free < MIN_FREE_BYTES + 2 * source_bytes:
        raise RuntimeError("Insufficient disk space for verified backup and restoration")
    result = snapshot_databases(source, backups)
    check_isolated_restore(result)
    print("Daily SQLite snapshot and isolated restore verification succeeded", flush=True)
    return True


def healthcheck(backups: Path, current: datetime) -> bool:
    snapshots = snapshot_times(backups)
    if not snapshots:
        return False
    age = current - snapshots[-1]
    if not (timedelta(0) <= age <= MAX_BACKUP_AGE and len(snapshots) <= MAX_SNAPSHOTS):
        return False
    for folder in backups.iterdir():
        match = FILENAME.fullmatch(folder.name)
        if match and datetime.strptime(match.group(1), "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc) == snapshots[-1]:
            try:
                require_private_directory(folder)
                for name in DATABASES:
                    require_private_db(folder / name)
                return True
            except (OSError, ValueError, PermissionError):
                return False
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--healthcheck", action="store_true")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--backups", type=Path, default=BACKUPS)
    args = parser.parse_args()
    if args.healthcheck:
        try:
            return 0 if healthcheck(args.backups, now_utc()) else 1
        except (OSError, ValueError, PermissionError):
            return 1
    if args.once:
        run_once(args.source, args.backups, now_utc())
        return 0

    print("Private ntfy daily backup worker started: 03:15 UTC, no deletion", flush=True)
    while True:
        current = now_utc()
        try:
            run_once(args.source, args.backups, current)
        except Exception as error:
            # Error types are sufficient for diagnostics; raw paths or SQLite
            # messages can contain sensitive information.
            print("Daily backup failed: " + type(error).__name__, file=sys.stderr, flush=True)
        # Wake up at the UTC daily boundary, without tight retries.
        wait = max(60, (next_run(now_utc()) - now_utc()).total_seconds())
        time.sleep(wait)


if __name__ == "__main__":
    raise SystemExit(main())
