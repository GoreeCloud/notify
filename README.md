# GoreeCloud Notify

**Development preview — not Stable, production-ready, or a substitute for emergency alerts.**

GoreeCloud Notify is an independent, open-source, self-hosted notification platform with a Go HTTP service and native web, Linux, and Android clients. It follows GoreeCloud's privacy-first design while keeping each MIPS responsibility distinct.

## Current functionality

- **Go service:** private topic publishing, per-topic recent history, authenticated Server-Sent Events, persistent bounded JSONL journal, health endpoint, input validation, and per-process publish rate limiting.
- **React web app:** GoreeCloud UI token/component integration, notification composer, priority selector, topic inbox, live event stream, periodic history reconciliation, and keyboard-friendly controls.
- **Qt Quick Linux app:** native Qt 6.12.0 interface, API-token entry, topic history, message composer and foreground refresh.
- **Jetpack Compose Android app:** native Material 3 Expressive interface using an attributed GoreeCloud UI source snapshot, topic history, publishing, foreground polling, and opt-in, content-suppressed local notifications.

This is a **single-administrator** server today. The bearer token authorizes all topics; there is no account system, topic ACL, multi-node federation, E2EE, background Android push, desktop background daemon, browser push, attachment storage, scheduled delivery, or full ntfy protocol compatibility yet. Do not present those as shipped features.

## Quick start (development)

Requires Go 1.23+.

```bash
git clone https://github.com/GoreeCloud/notify.git
cd notify
export NOTIFY_API_TOKEN="$(openssl rand -hex 32)"
export NOTIFY_DATA_FILE="./data/messages.jsonl"
go run ./cmd/notifyd
```

The service binds **127.0.0.1:8080** by default. Set `NOTIFY_LISTEN` to another address only behind your own access-controlled HTTPS gateway. The token is never embedded in source, committed, or printed by the service. Keep the token in a trusted secret manager; the shell example creates a transient session token.

Publish a message:

```bash
curl --fail-with-body -X POST 'http://127.0.0.1:8080/api/v1/topics/system/messages' \
  -H "Authorization: Bearer $NOTIFY_API_TOKEN" \
  -H 'Content-Type: application/json' \
  --data '{"title":"Backup complete","body":"The nightly backup finished.","priority":3}'
```

Read recent messages:

```bash
curl --fail-with-body 'http://127.0.0.1:8080/api/v1/topics/system/messages?limit=20' \
  -H "Authorization: Bearer $NOTIFY_API_TOKEN"
```

Watch live events (new messages only, no history replay):

```bash
curl -N 'http://127.0.0.1:8080/api/v1/topics/system/events' \
  -H "Authorization: Bearer $NOTIFY_API_TOKEN"
```

Web app:

```bash
cd web
npm ci
npm run dev
# open http://127.0.0.1:5173
```

The Vite development server proxies the API to 127.0.0.1:8080. For other clients, place the API behind an **HTTPS** reverse proxy such as GoreeCloud Gateway. Serve built web assets and API under the **same origin**; do not enable wildcard CORS or put an API token in a URL. The server does not serve static assets itself.

Linux app (Qt 6.12.0 Qt Quick/Qt Quick Controls 2/Qt Network development SDK required):

```bash
cmake -S linux -B build/linux -DCMAKE_PREFIX_PATH=/path/to/Qt/6.12.0/gcc_64
cmake --build build/linux
./build/linux/goreecloud-notify
```

Android app (JDK 17+, Android SDK 36):

```bash
cd android
./gradlew :app:assembleDebug
```

Android requires an HTTPS origin, refuses cleartext traffic, and never persists the token. Foreground polling is not background push; do not rely on it for critical alarms. The Linux client allows plain HTTP only for localhost.

## Architecture, safety and roadmap

See [Architecture](docs/architecture.md), [Security and privacy](docs/security.md), and [Dependencies / attribution](docs/dependencies.md).

All source files, CI, build inputs, client applications and documentation are maintained in this repository. External dependencies remain subject to their upstream licenses. No ntfy source was imported. GoreeCloud UI is the design authority, not an independently invented palette.

## Testing

```bash
go test -race ./...
go vet ./...
cd web && npm ci && npm run build
```

Qt and Android require their platform toolchains. A successful test or build is not device qualification or release acceptance.

## License

GoreeCloud-authored code: [Apache License 2.0](LICENSE). See [dependency attributions](docs/dependencies.md) for upstream rights, including MIT-licensed GoreeCloud UI source and Qt's separate LGPL/GPL/commercial obligations. Public source visibility is not evidence of deployment.
