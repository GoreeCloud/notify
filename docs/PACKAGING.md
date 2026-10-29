# GoreeCloud Notify — Linux package and validation

## My Linux delivery approach

I am developing GoreeCloud Notify as a first-party **native GTK4/libadwaita Linux application**, connecting to an independently managed ntfy backend. The `.deb` is a **development preview**, not a signed Stable release, a mobile build, or a replacement for the ntfy server.

I use a dependency-free offline package builder rather than an embedded website. It stages original Python/GTK source, an operating-system desktop entry, a scalable GoreeCloud icon, and a launcher. Dependencies are supplied by Debian/Ubuntu system packages; I do not bundle or download an ntfy server, token, or private configuration.

The unsigned developer-preview `.deb` includes the GTK executable `goreecloud-notify` and the separate native Python CLI executable `goreecloud-notify-cli`. The CLI uses the system OS keyring and does not require a GTK process. See [CLI usage](CLI.md).

## Build without changing system state

On a supported Debian/Ubuntu developer machine with `dpkg-deb`:

```bash
python3 tools/build_deb.py --output-dir dist
dpkg-deb --info dist/goreecloud-notify_0.1.0~dev0_all.deb
dpkg-deb --contents dist/goreecloud-notify_0.1.0~dev0_all.deb
desktop-file-validate packaging/linux/com.goreecloud.Notify.desktop
```

The generated binary is excluded from Git. The builder produces a package in the specified directory and stages only declared source files.

## Optional manual install on an explicitly authorized Linux device

Only after independent package validation and with suitable authorization:

```bash
sudo apt install ./dist/goreecloud-notify_0.1.0~dev0_all.deb
goreecloud-notify
sudo apt remove goreecloud-notify
```

Installation, removal, environment compatibility, and upgrade/rollback are **not** verified simply by building or inspecting the package. Do not install this test package on production hosts by default.

## Run tests and headless smoke launch

```bash
/usr/bin/python3 -m compileall -q goreecloud_notify tools tests
/usr/bin/python3 -m pytest -q
xvfb-run -a timeout 4s /usr/bin/python3 -m goreecloud_notify
```

Exit code 124 from `timeout` indicates that the deliberately time-boxed app remained alive; it is not a full GUI interaction test. CI also builds and inspects a Debian artifact, but a passing build does not establish native device lifecycle or accessibility acceptance.

## Security and privacy

- HTTPS required for remote ntfy servers; only loopback HTTP is permitted for local development.
- Optional tokens use the operating-system keyring, not the package or local JSON settings.
- Message history is bounded in memory and is not packaged or uploaded.
- The read-only health probe is a separate status signal from authorization to subscribe or publish.
- Generated `.deb` files are **unsigned previews**. No apt repository or automated update trust has been established.

I will not claim a production-ready or universally supported Linux package until install/uninstall, runtime, accessibility, lifecycle, and recovery gates have been verified on target systems.
