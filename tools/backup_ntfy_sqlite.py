#!/usr/bin/env python3
"""Make a consistent, owner-only online SQLite snapshot of private ntfy data.

This uses SQLite's backup API (not a raw file copy while ntfy is running).
It never emits rows, tokens, passwords, auth records, or message content.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sqlite3
import stat
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

DATABASES = ("auth.db", "cache.db")


def require_private_directory(path: Path, *, create: bool = False) -> Path:
    if create:
        path.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or path.is_symlink():
        raise ValueError("Expected a real directory, not a symlink")
    if info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise PermissionError("Directory must be owned by the caller and mode 0700")
    return path.resolve(strict=True)


def require_private_db(path: Path) -> Path:
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or path.is_symlink():
        raise ValueError("Expected a regular SQLite database, not a symlink")
    if info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise PermissionError("SQLite database must be owned by the caller and mode 0600")
    return path


def connection_readonly(path: Path) -> sqlite3.Connection:
    return sqlite3.connect("file:" + quote(str(path), safe="/") + "?mode=ro", uri=True, timeout=15)


def verify_backup(path: Path) -> None:
    require_private_db(path)
    connection = connection_readonly(path)
    try:
        status = connection.execute("PRAGMA integrity_check").fetchone()
        if not status or status[0] != "ok":
            raise RuntimeError("SQLite integrity check failed")
    finally:
        connection.close()


def snapshot_databases(source: Path, backups: Path) -> Path:
    source = require_private_directory(source)
    if source == backups.resolve() or source in backups.resolve().parents:
        raise ValueError("Backup directory must not be inside the source data directory")
    for name in DATABASES:
        require_private_db(source / name)
    backups = require_private_directory(backups, create=True)
    if backups == source or backups in source.parents:
        raise ValueError("Backup directory must not contain the source data directory")

    staging = Path(tempfile.mkdtemp(prefix=".pending-", dir=backups))
    os.chmod(staging, 0o700)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destination = backups / ("ntfy-" + timestamp + "-" + uuid.uuid4().hex[:8])
    try:
        for name in DATABASES:
            target = staging / name
            original = connection_readonly(source / name)
            try:
                copy = sqlite3.connect(target, timeout=30)
                try:
                    os.chmod(target, 0o600)
                    original.backup(copy, pages=32, sleep=0.05)
                    # Destination may inherit WAL mode from source. Convert the
                    # private snapshot itself (never the live source) so the
                    # deliverable is complete without sidecar -wal/-shm files.
                    mode = copy.execute("PRAGMA journal_mode=DELETE").fetchone()
                    if mode[0].lower() != "delete":
                        raise RuntimeError("Cannot finalize standalone SQLite snapshot")
                finally:
                    copy.close()
            finally:
                original.close()
            verify_backup(target)
        staging.rename(destination)
        staging = None
        return destination
    finally:
        if staging is not None:
            shutil.rmtree(staging)


def check_isolated_restore(snapshot: Path) -> None:
    """Restore into disposable private storage and open the copies independently."""
    snapshot = require_private_directory(snapshot)
    with tempfile.TemporaryDirectory(prefix="ntfy-restore-") as temp:
        restore = Path(temp)
        os.chmod(restore, 0o700)
        for name in DATABASES:
            original = require_private_db(snapshot / name)
            target = restore / name
            shutil.copyfile(original, target)
            os.chmod(target, 0o600)
            verify_backup(target)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path, help="Private live ntfy data directory (mode 0700)")
    parser.add_argument("--backups", required=True, type=Path, help="Private local snapshot directory (mode 0700)")
    args = parser.parse_args()
    saved = snapshot_databases(args.source, args.backups)
    check_isolated_restore(saved)
    print("Snapshot and isolated restore check succeeded; 2 SQLite databases verified.")
    print("Backup path:", saved)


if __name__ == "__main__":
    main()
