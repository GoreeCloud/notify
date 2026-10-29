"""Smoke a Debian payload from an extracted tree, never install system-wide."""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from tools.build_deb import build


@pytest.mark.skipif(
    not shutil.which("dpkg-deb") or not shutil.which("xvfb-run") or not shutil.which("timeout"),
    reason="requires Debian packaging and Xvfb",
)
def test_extracted_linux_launcher_remains_running(tmp_path: Path):
    pkg = build(tmp_path / "dist")
    root = tmp_path / "unpacked"
    subprocess.run(["dpkg-deb", "-x", str(pkg), str(root)], check=True)
    launcher = root / "usr/bin/goreecloud-notify"
    env = dict(os.environ)
    env["PYTHONPATH"] = str(root / "usr/lib/python3/dist-packages")
    env["XDG_CONFIG_HOME"] = str(tmp_path / "empty-config")
    env["XDG_CACHE_HOME"] = str(tmp_path / "empty-cache")
    completed = subprocess.run(
        ["xvfb-run", "-a", "timeout", "4s", "/usr/bin/python3", str(launcher)],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=12,
    )
    assert completed.returncode == 124, completed.stderr
    assert "Traceback" not in completed.stderr
