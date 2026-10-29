#!/usr/bin/env python3
"""Seal ntfy SQLite snapshots for off-host storage using a pinned GPG recipient.

No network transfers, key generation, deletion, plaintext staging, or implicit
recipient selection. The operator must separately provision and verify a
40-hex-digit OpenPGP encryption recipient fingerprint. Source and export
directories must be owner-only; auth/message data is never printed.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import sqlite3
import stat
import subprocess
import tarfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

FILES = ("auth.db", "cache.db")
MAX_DB_BYTES = 2 * 1024 ** 3
RECIPIENT = re.compile(r"^[0-9a-fA-F]{40}$")


def private(path: Path, *, directory: bool) -> Path:
    info = path.lstat()
    kind = stat.S_ISDIR if directory else stat.S_ISREG
    if not kind(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise PermissionError("Only owner-controlled regular files and directories are allowed")
    return path.resolve(strict=True)


def gpg_args(home: Path | None) -> list[str]:
    command = ["gpg", "--batch", "--no-tty", "--no-options"]
    if home is not None:
        command += ["--homedir", str(private(home, directory=True))]
    return command


def verify_recipient(fingerprint: str, home: Path | None = None) -> str:
    if not RECIPIENT.fullmatch(fingerprint):
        raise ValueError("Pin the complete 40-digit recipient fingerprint")
    fingerprint = fingerprint.upper()
    result = subprocess.run(gpg_args(home) + ["--with-colons", "--list-keys", fingerprint],
                            capture_output=True, timeout=10, check=False, text=True)
    if result.returncode:
        raise RuntimeError("Pinned recipient was not found in the local public keyring")
    fields = [line.split(":") for line in result.stdout.splitlines()]
    # Ensure the exact primary fingerprint exists with encryption capability.
    for index, row in enumerate(fields):
        if row[0] != "pub":
            continue
        following = next((r for r in fields[index + 1:] if r[0] in ("fpr", "pub")), None)
        if (following is not None and following[0] == "fpr"
                and following[9].upper() == fingerprint
                and len(row) > 11 and "e" in row[11].lower()):
            return fingerprint
    raise RuntimeError("Pinned key does not have a valid encryption-capable primary identity")


def verified_source(folder: Path) -> dict[str, dict[str, object]]:
    private(folder, directory=True)
    manifest = {}
    for filename in FILES:
        path = private(folder / filename, directory=False)
        if path.stat().st_nlink != 1:
            raise PermissionError("Refusing hardlinked snapshot database")
        with sqlite3.connect("file:" + str(path) + "?mode=ro&immutable=1",
                             uri=True, timeout=8) as db:
            if db.execute("PRAGMA integrity_check").fetchone() != ("ok",):
                raise RuntimeError("Invalid SQLite snapshot")
        hasher = hashlib.sha256()
        total = 0
        with path.open("rb") as stream:
            while piece := stream.read(1024 * 1024):
                total += len(piece)
                if total > MAX_DB_BYTES:
                    raise ValueError("Snapshot database exceeds export size limit")
                hasher.update(piece)
        manifest[filename] = {"size": total, "sha256": hasher.hexdigest()}
    return manifest


class VerifiedReader:
    """Check the snapshot cannot change while tar streams it to encryption."""
    def __init__(self, file, expected: dict[str, object]):
        self.file = file
        self.expected = expected
        self.hash = hashlib.sha256()
        self.size = 0

    def read(self, n: int = -1) -> bytes:
        chunk = self.file.read(n)
        self.hash.update(chunk)
        self.size += len(chunk)
        return chunk

    def check(self) -> None:
        if self.size != self.expected["size"] or self.hash.hexdigest() != self.expected["sha256"]:
            raise RuntimeError("Source snapshot changed during encrypted export")


def add_member(tar: tarfile.TarFile, name: str, file, size: int) -> None:
    member = tarfile.TarInfo(name)
    member.size = size
    member.mode = 0o600
    member.mtime = 0
    member.uid = member.gid = 0
    tar.addfile(member, file)


def sealed_export(snapshot: Path, exports: Path, fingerprint: str,
                  *, gpg_home: Path | None = None) -> Path:
    manifest = verified_source(snapshot)
    exports = private(exports, directory=True)
    snapshot = private(snapshot, directory=True)
    if snapshot == exports or snapshot in exports.parents or exports in snapshot.parents:
        raise ValueError("Export directory and snapshot directory must be independent")
    fingerprint = verify_recipient(fingerprint, gpg_home)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    name = "ntfy-sealed-" + stamp + "-" + uuid.uuid4().hex[:12] + ".tar.gpg"
    finished, pending = exports / name, exports / (name + ".pending")
    prior_umask = os.umask(0o077)  # GPG child inherits owner-only file creation.
    proc = None
    try:
        proc = subprocess.Popen(
            gpg_args(gpg_home) + [
                "--trust-model", "always", "--encrypt", "--recipient", fingerprint,
                "--output", str(pending),
            ],
            stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        if proc.stdin is None:
            raise RuntimeError("Unable to pipe archive to encryption")
        with tarfile.open(fileobj=proc.stdin, mode="w|") as tar:
            payload = json.dumps({"schema": 1, "files": manifest}, sort_keys=True).encode()
            add_member(tar, "manifest.json", io.BytesIO(payload), len(payload))
            for filename in FILES:
                with (snapshot / filename).open("rb") as source:
                    reader = VerifiedReader(source, manifest[filename])
                    add_member(tar, filename, reader, int(manifest[filename]["size"]))
                    reader.check()
        proc.stdin.close()
        if proc.wait(timeout=180) != 0:
            raise RuntimeError("Encryption failed")
        proc = None
        private(pending, directory=False)
        with pending.open("rb") as sealed:
            os.fsync(sealed.fileno())
        # Unique name and private destination; never overwrite a prior archive.
        if finished.exists():
            raise FileExistsError("Encrypted archive already exists")
        pending.rename(finished)
        return finished
    finally:
        if proc is not None:
            if proc.stdin is not None and not proc.stdin.closed:
                proc.stdin.close()
            if proc.poll() is None:
                proc.kill()
            proc.wait()
        pending.unlink(missing_ok=True)
        os.umask(prior_umask)


def verify_sealed_archive(archive: Path, *, gpg_home: Path | None = None) -> None:
    """Read and authenticate *without extracting* decrypted SQLite data to disk."""
    archive = private(archive, directory=False)
    proc = subprocess.Popen(gpg_args(gpg_home) + ["--decrypt", str(archive)],
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    if proc.stdout is None:
        raise RuntimeError("Cannot read encrypted archive")
    observed = {}
    expected = None
    try:
        with tarfile.open(fileobj=proc.stdout, mode="r|") as tar:
            for member in tar:
                if not member.isfile() or member.name not in ("manifest.json", *FILES):
                    raise ValueError("Unexpected archive member")
                if member.name in observed:
                    raise ValueError("Duplicate archive member")
                stream = tar.extractfile(member)
                if stream is None:
                    raise ValueError("Missing archive member content")
                if member.name == "manifest.json":
                    if expected is not None or member.size > 2048 or observed:
                        raise ValueError("Invalid manifest")
                    document = json.loads(stream.read(2049))
                    if (not isinstance(document, dict) or document.get("schema") != 1
                            or not isinstance(document.get("files"), dict)
                            or set(document["files"]) != set(FILES)):
                        raise ValueError("Invalid manifest schema")
                    expected = document["files"]
                    observed[member.name] = True
                else:
                    if expected is None or member.size > MAX_DB_BYTES:
                        raise ValueError("Missing manifest or oversized database")
                    digest = hashlib.sha256()
                    size = 0
                    while block := stream.read(1024 * 1024):
                        digest.update(block)
                        size += len(block)
                    observed[member.name] = (size, digest.hexdigest())
        if proc.wait(timeout=30) != 0:
            raise RuntimeError("Encrypted archive authentication failed")
        proc = None
        if set(observed) != {"manifest.json", *FILES}:
            raise ValueError("Incomplete sealed archive")
        for filename in FILES:
            target = expected[filename]
            if observed[filename] != (target["size"], target["sha256"]):
                raise ValueError("Encrypted archive digest mismatch")
    except (tarfile.TarError, EOFError, OSError, ValueError) as error:
        raise RuntimeError("Encrypted archive could not be validated") from None
    finally:
        if proc is not None:
            proc.stdout.close()
            if proc.poll() is None:
                proc.kill()
            proc.wait()


def main() -> None:
    cli = argparse.ArgumentParser(description=__doc__)
    commands = cli.add_subparsers(dest="action", required=True)
    seal = commands.add_parser("seal")
    seal.add_argument("--snapshot", required=True, type=Path)
    seal.add_argument("--exports", required=True, type=Path)
    seal.add_argument("--recipient-fingerprint", required=True)
    check = commands.add_parser("verify")
    check.add_argument("--archive", required=True, type=Path)
    for command in (seal, check):
        command.add_argument("--gpg-home", type=Path)
    args = cli.parse_args()
    if args.action == "seal":
        name = sealed_export(args.snapshot, args.exports, args.recipient_fingerprint,
                             gpg_home=args.gpg_home)
        print("PASS: encrypted, owner-only export created:", name.name)
    else:
        verify_sealed_archive(args.archive, gpg_home=args.gpg_home)
        print("PASS: encrypted archive integrity verified without plaintext extraction")


if __name__ == "__main__":
    main()
