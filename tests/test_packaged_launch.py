"""Smoke extracted native GTK package without installing or leaking child processes.

xvfb-run creates a process tree, so a nested GNU timeout can leave inherited
output pipes alive on slow CI runners. Use a dedicated process group instead,
capture diagnostics in a file and always tear down the whole group.
"""
from __future__ import annotations

import os
import shutil
import signal
import subprocess
import time
from pathlib import Path

import pytest

from tools.build_deb import build


@pytest.mark.skipif(
    not shutil.which("dpkg-deb") or not shutil.which("xvfb-run"),
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
    env["GSK_RENDERER"] = "cairo"  # headless software rendering; no GPU/DRI3 assumptions
    output = tmp_path / "gtk-launch.log"
    with output.open("wb") as log:
        process = subprocess.Popen(
            ["xvfb-run", "-a", "/usr/bin/python3", str(launcher)],
            cwd=tmp_path, env=env, stdout=log, stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        try:
            # Verify it stays alive for a short bounded period. This is a
            # process-start smoke test, not UI/device/accessibility acceptance.
            deadline = time.monotonic() + 3.0
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    pytest.fail("Extracted native client exited early: " + output.read_text(errors="replace"))
                time.sleep(0.1)
        finally:
            # SIGTERM alone is not reliable in the xvfb-run process tree.
            # Forcefully terminate the entire isolated test group, including
            # the virtual display and client, without touching unrelated PIDs.
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                pass
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2)
    assert "Traceback" not in output.read_text(errors="replace")
