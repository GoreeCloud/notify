# GoreeCloud Notify

**Original GoreeCloud clients for [ntfy](https://ntfy.sh): a native GTK4/libadwaita Linux desktop application and a supplementary responsive web application.**

> **Status:** Linux-native and companion web developer previews, not Stable or production-ready. Not a fork or rebranding of ntfy. No browser deployment, mobile apps, or production services are verified here.

GoreeCloud Notify is a privacy-first, self-hosting-friendly notification inbox. It connects to existing ntfy instances through their documented HTTP API and provides a native Linux desktop experience. This project follows the [GoreeCloud UI](https://github.com/GoreeCloud/gc-ui) design authority while using platform-native GTK4/libadwaita widgets and accessibility conventions. Cross-platform design parity and formal GC UI acceptance remain unverified.

## Implemented in this development foundation

- Native Linux GTK4/libadwaita navigation, message cards and contextual empty-state onboarding.
- HTTPS ntfy server selection, including reverse-proxy base paths; loopback-only HTTP for development.
- Multiple topic subscriptions, confirmation-based unsubscribe, and bounded local in-memory message history.
- Offline, case-insensitive topic-message search and minimum-priority filters. Search input stays on device and is never sent to the ntfy server.
- ndjson message streaming, ten-minute replay on first connect, resume from latest message ID, bounded reconnection delay, duplicate suppression, and stale-connection cancellation.
- Publish text notifications with title, priority (1–5), and tags.
- Optional Bearer token in the **OS keyring**, never in the local JSON settings file.
- Read-only ntfy server-health check with explicit healthy/unhealthy/error states, separate from subscription status.
- Failure states for authentication, rate limits, unexpected redirects, disconnection and oversized events.
- No ad tracking, analytics, paywalls, embedded browser, or outgoing calls other than the configured ntfy API.

The native UI is a **prototype** pending actual GUI interaction, accessibility and install/package testing. Its packaged-launch Xvfb smoke test uses an isolated process group and software renderer so CI can clean up reliably even on runners where the GTK process remains open. A passing unit test does not establish an operational deployment or cross-platform support.

## Upstream ntfy Docker backend (private preview)

A reproducible, source-controlled [private Docker backend template](deploy/ntfy/README.md) deploys the **upstream ntfy server** separately from the original native and companion web clients. It pins the verified v2.34.0 registry digest, requires persistent SQLite storage, denies anonymous topic access, and publishes its port to VPS loopback only.

A private VPS instance has passed health, readiness, anonymous-denial and restart checks. **No client account/token, external HTTPS route, VPN/DNS integration, real authenticated client acceptance or production release is verified.** The deployment does not replace the older independent GoreeCloud Notify stack.

## Companion web application (new)

A real, original, dependency-free **browser application** is provided in [web/](web/README.md), alongside—not replacing—the Linux native client. It has a responsive dark/light interface, all-topic and individual-topic feeds, streaming subscription/reconnect, in-memory search and priority filters, unread counts, text publishing, and read-only server health checks.

For a loopback-only web UI preview:

```bash
python3 web/dev_server.py --port 8765
# Visit http://127.0.0.1:8765/
```

For a locally managed ntfy instance running on loopback, start with `NTFY_UPSTREAM=http://127.0.0.1:8080`. For remote backends, use explicit HTTPS and a reviewed same-origin private reverse proxy. The web client does **not** store bearer tokens or message bodies persistently; only non-secret endpoint, topic, and theme settings may be stored. The browser app is **not** an installable native OS replacement.

See [web setup, controls, deployment safety and test instructions](web/README.md). The proposed Caddy development route is a **template only**—no DNS, access-control policy, gateway, production backend, or public exposure has been changed.

## Requirements and developer launch (Linux)

- Python 3.11+
- GTK 4 and libadwaita 1 with GObject introspection bindings (PyGObject)
- A working OS keyring / Secret Service provider for authenticated servers
- `keyring` Python package

On Ubuntu/Debian:

```bash
sudo apt install python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 python3-keyring python3-pytest
git clone https://github.com/GoreeCloud/notify.git
cd notify
/usr/bin/python3 -m goreecloud_notify
```

For an offline **unsigned native Debian/Ubuntu developer-preview package**, run `python3 tools/build_deb.py --output-dir dist` with `dpkg-deb` available. See [Linux packaging](docs/PACKAGING.md) for inspection and optional manual installation. This is not a verified production installer.

The source launch above is a developer launch, **not** proof of a verified installable package. No self-hosted server address, topic, or token is embedded in the source.

## First run

1. Open **Connection settings**, enter the HTTPS URL of the ntfy server, and optionally supply an access token. Server credentials must already be provisioned and authorized on that server.
2. Choose **Subscribe to a topic**. ntfy's public topics can be guessable: use a private, hard-to-guess topic or server-side access controls.
3. Select a topic in the sidebar to watch incoming notifications. Choose **New message** to publish a text notification.

Settings live at `$XDG_CONFIG_HOME/goreecloud/notify.json` (default: `~/.config/goreecloud/notify.json`) with mode 0600. Message bodies are **not** written to local disk. A configured server and topic are retained; cached messages are available only as the server's retention policy permits.

## Test

```bash
python3 -m compileall -q goreecloud_notify tests
python3 -m pytest -q
cd web && npm run check && npm test
```

## Architecture and roadmap

See [Architecture](docs/ARCHITECTURE.md), [Linux packaging](docs/PACKAGING.md), [companion web app](web/README.md), and [Roadmap](docs/ROADMAP.md). The ntfy API supports more capabilities than this client currently implements, including action buttons, attachment transfer, priority filters and delayed sends. Do not assume those capabilities are present here.

## Dependency attribution

ntfy is created and maintained by its respective upstream authors and is used as an API-compatible **backend**, not copied into this repository. GTK 4, libadwaita, PyGObject and keyring remain separate third-party dependencies under their own licenses. This original client source is MIT-licensed; see [LICENSE](LICENSE).
