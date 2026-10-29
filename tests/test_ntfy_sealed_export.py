"""Synthetic end-to-end OpenPGP backup export tests; no production data or keys."""
import json
import os
import shutil
import sqlite3
import subprocess
from pathlib import Path

import pytest

from tools.ntfy_sealed_export import (
    sealed_export, verify_sealed_archive, verify_recipient, verified_source,
)


@pytest.fixture
def synthetic(tmp_path):
    if not shutil.which("gpg"):
        pytest.skip("GnuPG is not installed")
    home = tmp_path / "keys"
    home.mkdir(mode=0o700)
    subprocess.run([
        "gpg", "--homedir", str(home), "--batch", "--no-tty", "--pinentry-mode", "loopback",
        "--passphrase", "", "--quick-gen-key",
        "GoreeCloud CI Fixture <synthetic@example.invalid>", "default", "default", "1d",
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, timeout=35)
    keys = subprocess.check_output([
        "gpg", "--homedir", str(home), "--batch", "--with-colons", "--list-keys",
    ], text=True, timeout=10)
    fingerprint = next(line.split(":")[9] for line in keys.splitlines()
                       if line.startswith("fpr:"))
    data = tmp_path / "snapshot"
    exports = tmp_path / "exports"
    data.mkdir(mode=0o700)
    exports.mkdir(mode=0o700)
    for name in ("auth.db", "cache.db"):
        with sqlite3.connect(data / name) as db:
            db.execute("CREATE TABLE synthetic_records (s TEXT)")
            db.execute("INSERT INTO synthetic_records VALUES (?)", ("FAKE-" + name,))
        (data / name).chmod(0o600)
    return home, fingerprint, data, exports


def test_encrypt_decrypt_and_verify_without_plaintext_export(synthetic):
    home, fingerprint, data, exports = synthetic
    assert verify_recipient(fingerprint.lower(), home) == fingerprint.upper()
    result = sealed_export(data, exports, fingerprint, gpg_home=home)
    assert result.exists() and result.stat().st_mode & 0o077 == 0
    assert result.name.endswith(".tar.gpg")
    assert b"FAKE-auth" not in result.read_bytes()
    assert b"FAKE-cache" not in result.read_bytes()
    assert b"auth.db" not in result.read_bytes()
    assert len(list(exports.iterdir())) == 1
    verify_sealed_archive(result, gpg_home=home)
    assert all((data / f).exists() for f in ("auth.db", "cache.db"))


def test_reject_wrong_or_untrusted_recipient(synthetic):
    home, fingerprint, data, exports = synthetic
    with pytest.raises(ValueError):
        sealed_export(data, exports, "abcd", gpg_home=home)
    with pytest.raises(RuntimeError):
        sealed_export(data, exports, "f" * 40, gpg_home=home)
    assert list(exports.iterdir()) == []


def test_reject_unsafe_storage(synthetic):
    home, fingerprint, data, exports = synthetic
    (data / "auth.db").chmod(0o644)
    with pytest.raises(PermissionError):
        sealed_export(data, exports, fingerprint, gpg_home=home)
    (data / "auth.db").chmod(0o600)
    exports.chmod(0o755)
    with pytest.raises(PermissionError):
        sealed_export(data, exports, fingerprint, gpg_home=home)
    assert list(exports.iterdir()) == []


def test_reject_corruption_before_any_export(synthetic):
    home, fingerprint, data, exports = synthetic
    (data / "cache.db").write_bytes(b"not a database")
    (data / "cache.db").chmod(0o600)
    with pytest.raises(sqlite3.DatabaseError):
        sealed_export(data, exports, fingerprint, gpg_home=home)
    assert list(exports.iterdir()) == []


def test_tampered_encrypted_archive_not_verified(synthetic):
    home, fingerprint, data, exports = synthetic
    result = sealed_export(data, exports, fingerprint, gpg_home=home)
    original = result.read_bytes()
    assert len(original) > 20
    result.write_bytes(original[:-15] + b"\0" * 15)
    result.chmod(0o600)
    with pytest.raises((ValueError, RuntimeError, OSError, EOFError)):
        verify_sealed_archive(result, gpg_home=home)


def test_never_encrypts_symlinked_database(synthetic):
    home, fingerprint, data, exports = synthetic
    (data / "auth.db").rename(data / "real.db")
    (data / "auth.db").symlink_to(data / "real.db")
    with pytest.raises(PermissionError):
        sealed_export(data, exports, fingerprint, gpg_home=home)
    assert not list(exports.iterdir())
