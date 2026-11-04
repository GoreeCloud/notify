# GoreeCloud Notify

**Native, privacy-first, self-hosted notification service** for applications, devices, and infrastructure. Created and maintained as an original GoreeCloud product. The service is **not a repackaging, fork, or reverse proxy of ntfy**.

> **Status: functional alpha foundation (0.1.0), not production-certified.** The original extensive product specification is a roadmap, not a list of currently implemented behavior. No production deployment is included in this repository change.

## Implemented

- Original Go service using **only the Go standard library** (no external server dependencies).
- Authenticated JSON publish API, default-deny bearer-token authentication, role- and topic-scoped token hashes via optional ACL configuration.
- Durable, append-only local JSONL event storage; restart recovery; configurable retention and per-topic history limits; crash-conscious periodic compaction, fail-closed append errors, and offline log verification.
- Real-time Server-Sent Events (SSE) subscriptions with replay, bounded per-subscriber queues, and connection budgets (4 per credential, 64 total); JSON notification history and topic listing.
- Five notification priorities, titles, tagged alerts, validated click-through links, and strict request validation and a basic per-token publishing limit.
- Idempotent publishing keys with persistent conflict detection; stable random event identifiers.
- Go-embedded, responsive **GoreeCloud UI**-aligned web console: channel selection, live timeline, compose, priority filtering, and tab-only token handling.
- `/healthz`, `/readyz`, admin-only `/metrics`, Docker deployment with non-root runtime and localhost-only host binding by default.
- Automated unit/integration tests and CI source checks.

## Quick start (local development)

Requires Go 1.23+.

```bash
export NOTIFY_ADMIN_TOKEN="$(openssl rand -base64 48)"
go run ./cmd/notify
# Open http://127.0.0.1:8080 in your browser, and paste the token to connect.
```

In another terminal, using the same token:

```bash
curl --fail-with-body -H "Authorization: Bearer $NOTIFY_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"Backup complete","body":"The latest backup passed verification.","priority":4,"tags":["backup"]}' \
  http://127.0.0.1:8080/api/v1/topics/backup/messages

curl -N -H "Authorization: Bearer $NOTIFY_ADMIN_TOKEN" \
  http://127.0.0.1:8080/api/v1/topics/backup/events
```

## Docker (local-only by default)

```bash
cp .env.example .env
# Edit .env: replace the example secret with: openssl rand -base64 48
docker compose up --build -d
# Open http://127.0.0.1:8787
```

**Do not expose the HTTP port to the public internet.** The Compose port is bound to `127.0.0.1`. For remote access use an authenticated, configured HTTPS reverse proxy or a VPN, with appropriate network policies. A plain HTTP remote connection exposes bearer tokens.

## Offline integrity verification (maintenance)

Stop the service or use a **consistent filesystem snapshot** before checking its log:

```bash
go run ./cmd/notifylog -file ./data/messages.jsonl
# Prints only counts of records/topics and log size, not notification content.
```

Malformed or truncated records and missing final newlines prevent startup. **Do not automatically truncate or repair** the original event log. Preserve the evidence and recover from a verified backup or an independently reviewed offline repair. See [operations](docs/OPERATIONS.md).

## Documentation

- [API reference](docs/API.md)
- [Architecture and security](docs/ARCHITECTURE.md)
- [Capabilities and phased roadmap](docs/FEATURES.md)
- [Complete 40-section product specification](docs/PRODUCT_SPEC.md)
- [Operations and rollback](docs/OPERATIONS.md)
- [GoreeCloud UI design conformance](docs/UI.md)

## Verified commands

```bash
go test -race ./...
go vet ./...
go build ./...
node --check cmd/notify/web/app.js
```

## Design, privacy, and provenance

The interface follows the verified **GoreeCloud UI** (`GoreeCloud/gc-ui`) language and semantic role conventions, but is currently an independent CSS implementation, not a verified consumption of the published package. The native service uses no ntfy libraries or servers. The project will evaluate interoperability separately. No license terms have yet been approved for redistribution; source visibility does not itself grant reuse rights.