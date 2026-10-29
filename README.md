# GoreeCloud Notify

**An original, native GTK4/libadwaita desktop client for [ntfy](https://ntfy.sh).**

> **Status:** Linux developer preview, not Stable or production-ready. Not a fork, replacement, or rebranding of the upstream ntfy server. No binaries, mobile apps, or deployed GoreeCloud Notify service have been verified as delivered.

GoreeCloud Notify is a privacy-first, self-hosting-friendly notification inbox. It connects to existing ntfy instances through their documented HTTP API and provides a native Linux desktop experience. This project follows the [GoreeCloud UI](https://github.com/GoreeCloud/gc-ui) design authority while using platform-native GTK4/libadwaita widgets and accessibility conventions. Cross-platform design parity and formal GC UI acceptance remain unverified.

## Implemented in this development foundation

- Native Linux GTK4/libadwaita navigation, message cards and contextual empty-state onboarding.
- HTTPS ntfy server selection, including reverse-proxy base paths; loopback-only HTTP for development.
- Multiple topic subscriptions, confirmation-based unsubscribe, and bounded local in-memory message history.
- Offline, case-insensitive topic-message search and minimum-priority filters. Search input stays on device and is never sent to the ntfy server.
- ndjson message streaming, ten-minute replay on first connect, resume from latest message ID, bounded reconnection delay, duplicate suppression, and stale-connection cancellation.
- Publish text notifications with title, priority (1–5), and tags.
- Optional Bearer token in the **OS keyring**, never in the local JSON settings file.
- Failure states for authentication, rate limits, unexpected redirects, disconnection and oversized events.
- No ad tracking, analytics, paywalls, embedded browser, or outgoing calls other than the configured ntfy API.

The native UI is a **prototype** pending actual GUI interaction, accessibility and install/package testing. A passing unit test does not establish an operational deployment or cross-platform support.

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

This is a source developer launch, **not** a verified installable package. No self-hosted server address, topic, or token is embedded in the source.

## First run

1. Open **Connection settings**, enter the HTTPS URL of the ntfy server, and optionally supply an access token. Server credentials must already be provisioned and authorized on that server.
2. Choose **Subscribe to a topic**. ntfy's public topics can be guessable: use a private, hard-to-guess topic or server-side access controls.
3. Select a topic in the sidebar to watch incoming notifications. Choose **New message** to publish a text notification.

Settings live at `$XDG_CONFIG_HOME/goreecloud/notify.json` (default: `~/.config/goreecloud/notify.json`) with mode 0600. Message bodies are **not** written to local disk. A configured server and topic are retained; cached messages are available only as the server's retention policy permits.

## Test

```bash
python3 -m compileall -q goreecloud_notify tests
python3 -m pytest -q
```

## Architecture and roadmap

See [Architecture](docs/ARCHITECTURE.md) and [Roadmap](docs/ROADMAP.md). The ntfy API supports more capabilities than this client currently implements, including action buttons, attachment transfer, priority filters and delayed sends. Do not assume those capabilities are present here.

## Dependency attribution

ntfy is created and maintained by its respective upstream authors and is used as an API-compatible **backend**, not copied into this repository. GTK 4, libadwaita, PyGObject and keyring remain separate third-party dependencies under their own licenses. This original client source is MIT-licensed; see [LICENSE](LICENSE).
