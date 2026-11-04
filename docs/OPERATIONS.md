# Operations, backup, and rollback

## Start safely

Read README quickstart. Use a random admin secret; never commit `.env` or ACL files. The process defaults to loopback. Avoid public traffic until a TLS proxy, rate limits, firewall, hardened auth and an operational review are in place.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `NOTIFY_ADMIN_TOKEN` | **Required** | Administrator secret, >= 32 chars |
| `NOTIFY_ADDR` | `127.0.0.1:8080` | HTTP listen address |
| `NOTIFY_DATA_DIR` | `./data` | Durable local message store |
| `NOTIFY_ACL_FILE` | unset | Optional private JSON ACL file |
| `NOTIFY_RETENTION_HOURS` | `168` | Retained message age (1–8760h) |
| `NOTIFY_MAX_MESSAGES_PER_TOPIC` | `5000` | Retained per-topic limit (1–100000) |

## Backup

1. Quiesce publishing and stop the process (or take an atomic filesystem snapshot).
2. Copy the private `NOTIFY_DATA_DIR/messages.jsonl` file, secrets managed externally, configuration and ACL file into access-controlled encrypted backup storage.
3. Verify backup integrity and test restoration in a disposable environment.
4. Restore into a **stopped** process, with correct private permissions. Restart and verify `/readyz`, authenticated history and replay.

Do not copy active JSONL files blindly while writes are happening; such copies can end with a partially written record. A partial record causes startup to fail closed rather than silently drop data.

## Upgrade / rollback

Take a verified backup before upgrading. Preserve the existing image or binary and configuration. Run Go tests and smoke tests against a staging instance. If a new version fails, stop it, restore the prior binary/image **and** known-compatible data snapshot, and verify access and event retrieval. No automated database schema migration exists in alpha.

## Logs and troubleshooting

`go run ./cmd/notify` emits server lifecycle logs. The API returns JSON errors. Missing or invalid tokens return 401; insufficient topic role returns 403. If login works but channels are empty, publish the first message or use a token with subscriber/admin privileges. SSE requires an HTTP proxy configured for streaming and low buffering. The `/metrics` endpoint requires the administrator token.

## No production deployment claim

The repository contains an example secure-by-default container arrangement but does not imply a hosted service has been installed, verified, or deployed to any VPS. Existing GoreeCloud production infrastructure must be inspected and backed up before a separately authorized migration.
