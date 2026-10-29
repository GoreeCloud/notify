"""Offline Debian package inspection without installing to the system."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys

import pytest

from tools.build_deb import build


@pytest.mark.skipif(shutil.which("dpkg-deb") is None, reason="dpkg-deb unavailable")
def test_native_debian_package_is_installable_structure(tmp_path):
    result = build(tmp_path / "output")
    assert result.is_file()
    info = subprocess.run(["dpkg-deb", "-f", str(result), "Package", "Version", "Architecture"],
                          check=True, capture_output=True, text=True).stdout
    assert "goreecloud-notify" in info
    assert "0.1.0~dev0" in info
    assert "all" in info
    extracted = tmp_path / "extracted"
    subprocess.run(["dpkg-deb", "-x", str(result), str(extracted)], check=True,
                   capture_output=True, text=True)
    package = extracted / "usr/lib/python3/dist-packages/goreecloud_notify"
    assert (package / "ui.py").is_file()
    assert (package / "health.py").is_file()
    launcher = extracted / "usr/bin/goreecloud-notify"
    assert launcher.stat().st_mode & 0o111
    assert (extracted / "usr/share/applications/com.goreecloud.Notify.desktop").is_file()
    assert (extracted / "usr/share/icons/hicolor/scalable/apps/com.goreecloud.Notify.svg").is_file()
    env = dict(os.environ, PYTHONPATH=str(extracted / "usr/lib/python3/dist-packages"))
    check = subprocess.run(
        [sys.executable, "-c",
         "from goreecloud_notify.health import HealthResult; print(HealthResult(True, 1))"],
        cwd=tmp_path, env=env, check=True, capture_output=True, text=True,
    )
    assert "HealthResult" in check.stdout


@pytest.mark.skipif(shutil.which("desktop-file-validate") is None, reason="desktop-file-utils unavailable")
def test_desktop_file_is_valid():
    from tools.build_deb import ROOT

    subprocess.run(
        ["desktop-file-validate", str(ROOT / "packaging/linux/com.goreecloud.Notify.desktop")],
        check=True, capture_output=True, text=True,
    )
