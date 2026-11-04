# GoreeCloud Notify

**Native, privacy-first, self-hosted notification service** for applications, devices, and infrastructure. Created and maintained as an original GoreeCloud product. The service is **not a repackaging, fork, or reverse proxy of ntfy**.

> **Status: functional alpha foundation (0.1.0), not production-certified.** The original extensive product specification is a roadmap, not a list of currently implemented behavior. No production deployment is included in this repository change.

## Implemented

- Original Go service using **only the Go standard library** (no external server dependencies).
- Authenticated JSON publish API, default-deny bearer-token authentication, role- and topic-scoped token hashes via optional ACL configuration; reject ambiguous authentication headers.
- Bounded in-process peer throttling (240 requests or 30 failed authentications/minute per socket peer), separate from per-token publish limits and SSE budgets.
- Durable, append-only local JSONL event storage; restart recovery; configurable retention and per-topic history limits; crash-conscious periodic compaction, fail-closed append errors, offline log verification, private journal permissions, OS-enforced single-writer locking, and an offline verified no-overwrite backup command.
- Real-time Server-Sent Events (SSE) subscriptions with replay, bounded per-subscriber queues, and connection budgets (4 per credential, 64 total); JSON notification history and topic listing.
- Five notification priorities, titles, tagged alerts, validated click-through links, and strict request validation.
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

**Do not expose the HTTP port to the public internet.** Per-peer throttling is intentionally based on the direct socket peer (never untrusted forwarding headers). Clients behind a reverse proxy share that peer budget; use a trusted edge proxy with independent per-client restrictions. The service refuses data directories with permissions broader than `0700` and journal files broader than `0600`; secure existing data directories offline before upgrading. **Do not run two instances against one journal.** The Compose port is bound to `127.0.0.1`. For remote access use an authenticated, configured HTTPS reverse proxy or a VPN, with appropriate network policies. A plain HTTP remote connection exposes bearer tokens.

## Offline integrity verification (maintenance)

Run only after stopping GoreeCloud Notify or using a consistent filesystem snapshot:

```bash
go run ./cmd/notifylog -file ./data/messages.jsonl
# Outputs only counts of records/topics and log size, without notification contents.
```

A malformed/truncated record or missing final newline prevents normal startup. **Never automatically truncate or repair this data**: preserve the original, identify the cause, then restore a verified backup or use a separately reviewed offline recovery process. See [operations](docs/OPERATIONS.md).

## Verified offline backup (no live writers)

Stop the service and confirm the source journal is quiescent, or use a point-in-time snapshot. Prepare an **independent private** destination directory (`chmod 0700 /secure/backups`) and use:

```bash
go run ./cmd/notifybackup -file ./data/messages.jsonl -out /secure/backups/notify-2026-11-03.jsonl
# Outputs only record count, topic count, size, and SHA-256 digest.
```

The backup tool checks the journal's lock, verifies both copies, compares a second source hash, and publishes the backup atomically without overwriting prior backups. It does **not** encrypt files or certify backup retention. For a previously verified immutable snapshot lacking a lock file, use `-snapshot` explicitly. Always store backups in access-controlled encrypted storage; see [operations](docs/OPERATIONS.md).

## Documentation

- [API reference](docs/API.md)
- [Architecture and security](docs/ARCHITECTURE.md)
- [Capabilities and phased roadmap](docs/FEATURES.md)
- [Operations and rollback](docs/OPERATIONS.md)
- [Deployment security checklist](deploy/SECURITY_CHECKLIST.md)
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
