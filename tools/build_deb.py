#!/usr/bin/env python3
"""Build a native Debian/Ubuntu Linux developer-preview package offline.

The package contains original GTK/Python source code; it is NOT a web wrapper.
Run in an isolated workspace and inspect the result before installing.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSION = "0.1.0~dev0"
PACKAGE = "goreecloud-notify"


def _copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)
    dst.chmod(0o644)


def build(output_dir: Path) -> Path:
    if not shutil.which("dpkg-deb"):
        raise RuntimeError("dpkg-deb is required to build the Debian package")
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    result = output_dir / f"{PACKAGE}_{VERSION}_all.deb"
    with tempfile.TemporaryDirectory(prefix="goreecloud-notify-deb-") as tmp:
        staging = Path(tmp) / "pkg"
        package_dest = staging / "usr/lib/python3/dist-packages/goreecloud_notify"
        for src in sorted((ROOT / "goreecloud_notify").glob("*.py")):
            _copy(src, package_dest / src.name)
        _copy(ROOT / "packaging/linux/com.goreecloud.Notify.desktop",
              staging / "usr/share/applications/com.goreecloud.Notify.desktop")
        _copy(ROOT / "packaging/linux/com.goreecloud.Notify.svg",
              staging / "usr/share/icons/hicolor/scalable/apps/com.goreecloud.Notify.svg")
        launcher = staging / "usr/bin/goreecloud-notify"
        launcher.parent.mkdir(parents=True, exist_ok=True)
        launcher.write_text(
            "#!/usr/bin/python3\nfrom goreecloud_notify.ui import main\n"
            "if __name__ == '__main__':\n    raise SystemExit(main())\n",
            encoding="utf-8",
        )
        launcher.chmod(0o755)
        control = staging / "DEBIAN/control"
        control.parent.mkdir(parents=True, exist_ok=True)
        control.write_text(
            "Package: goreecloud-notify\n"
            "Version: 0.1.0~dev0\n"
            "Section: utils\n"
            "Priority: optional\n"
            "Architecture: all\n"
            "Maintainer: GoreeCloud <295260680+GoreeCloud@users.noreply.github.com>\n"
            "Depends: python3 (>= 3.11), python3-gi, python3-keyring, gir1.2-gtk-4.0, gir1.2-adw-1\n"
            "Description: Native GTK4 desktop client for an ntfy server\n"
            " GoreeCloud Notify is a development-preview Linux application that\n"
            " subscribes and publishes notifications via an existing ntfy API.\n",
            encoding="utf-8",
        )
        control.chmod(0o644)
        subprocess.run(["dpkg-deb", "--root-owner-group", "--build", str(staging), str(result)],
                       check=True, capture_output=True, text=True)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    print(build(args.output_dir))


if __name__ == "__main__":
    main()
