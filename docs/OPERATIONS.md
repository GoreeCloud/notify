# Operations, backup, and rollback

## Start safely

Read README quickstart. Use a random admin secret; never commit `.env` or ACL files. The process defaults to loopback. Avoid public traffic until a TLS proxy, independent trusted-edge rate limits, firewall, hardened auth and an operational review are in place. Direct-peer limits cannot distinguish clients behind a reverse proxy.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `NOTIFY_ADMIN_TOKEN` | **Required** | Administrator secret, >= 32 chars |
| `NOTIFY_ADDR` | `127.0.0.1:8080` | HTTP listen address |
| `NOTIFY_DATA_DIR` | `./data` | Durable local message store |
| `NOTIFY_ACL_FILE` | unset | Optional private JSON ACL file |
| `NOTIFY_RETENTION_HOURS` | `168` | Retained message age (1–8760h) |
| `NOTIFY_MAX_MESSAGES_PER_TOPIC` | `5000` | Retained per-topic limit (1–100000) |

## Single-writer and filesystem requirements

- The data directory must be a non-symlink directory with permissions `0700`. The journal and `.notify.lock` must be regular private files with permissions `0600`; a symlink or overly broad permissions prevents startup.
- A local Linux kernel `flock` is held on `.notify.lock` while the process runs. A second instance pointed at the same directory fails rather than risking concurrent JSONL writes. Never bypass that protection or place the active journal on a shared/network filesystem as a substitute for database coordination.
- Before upgrading an existing **stopped** installation, take a secure backup, inspect ownership and modes, and adjust them only as intended (`chmod 0700 DATA_DIR`, `chmod 0600 DATA_DIR/messages.jsonl DATA_DIR/.notify.lock` when the files exist). Confirm the service runs as the data owner. Do not change permissions on an active production directory without a controlled maintenance window.
- The app has no live reload or horizontal replication of the journal. Rotation and recovery must be coordinated with a full service stop.

## Request and authentication abuse limits

- The server restricts each direct socket peer to 240 initial HTTP requests/minute and 30 invalid bearer authentications/minute. The fixed-window table is bounded at 10,000 peers; an exhausted table fails closed for new peers. IPv6 addresses in one `/64` share a budget.
- `Forwarded` and `X-Forwarded-For` are ignored for this throttle. With a reverse proxy, all clients may appear as one peer; enforce additional trusted **client-IP-aware** rate limits at the proxy/firewall before traffic reaches Notify. Failed-login suppression may impact legitimate users on shared networks; monitor local traffic while tuning ingress policy.
- The limits reset on process restart, do not protect against distributed traffic, and are not production DDoS mitigation. Only local liveness/readiness are exempt from server peer limits.

## Offline verified backup

1. Quiesce publishing and **stop** the process, or take a verified point-in-time filesystem snapshot. Never copy a moving JSONL journal and call it a successful backup. The backup tool attempts a non-blocking shared advisory lock and refuses access when a normal Notify writer is active.
2. Prepare an **independent** private backup directory (`0700`) on a local filesystem with adequate capacity, protected by access controls and encryption appropriate to the notification data. The CLI output includes only record count, topic count, bytes and SHA-256 digest; it does not encrypt or upload data.
3. Execute the tool against a stopped instance:

   ```bash
   go run ./cmd/notifybackup -file ./data/messages.jsonl -out /private/backup/notify-2026-11-03.jsonl
   ```

   For a separately verified **immutable** snapshot without `.notify.lock`, the explicit `-snapshot` option is required. Never use `-snapshot` to bypass an active service's lock.
4. The tool checks the source format; writes a private temporary destination; syncs it; verifies its records/topics/size; compares the source hash again; and publishes the backup atomically without overwriting an existing path using an on-filesystem hard link followed by directory sync. The source file remains unchanged. If a sync operation fails, durability is uncertain: preserve and verify the result before retrying with a *new* destination name.
5. Include application configuration and ACL secrets through **separate approved encrypted secret-backup processes**; the journal backup does not contain those external materials. Store the manifest/digest separately and protect backup access.
6. Drill restoration into an isolated private directory with `0600` journal file, run `go run ./cmd/notifylog -file /path/to/restored/messages.jsonl`, start a fresh instance, and verify known IDs, idempotent replays and authenticated retrieval. Never restore over an active service's journal. Record the observed loss window.

The tool is a local validated copy primitive, not a disaster recovery service: it cannot independently prove backup encryption, off-site replication, storage reliability, or snapshot consistency. Keep independent Notify-down monitoring and an operator-approved recovery plan.

## Persistence incident recovery

1. Stop the Notify process and block new publishers at the trusted ingress. Never force a live repair.
2. Capture a **read-only forensic copy** of the affected data directory with host permissions and timestamps preserved, stored in restricted encrypted storage.
3. Run `go run ./cmd/notifylog -file /path/to/copy/messages.jsonl` against that **stopped/snapshotted copy**. A malformed record, missing final newline, or duplicate record ID is an integrity failure. The original service does not auto-truncate or silently heal its journal.
4. Restore a previously verified, point-in-time snapshot to a separate private directory; verify it offline, then start a **local isolated** test instance against it. Compare expected event IDs, timestamps, idempotent replays, and subscriber behavior.
5. Record the data-loss window and cause before any authorized production restore. Never mix two independently active writers against a JSONL log. A successful verifier alone is not sufficient to declare a disaster-recovery drill passed.

On a failed staging step of compaction, the current file descriptor stays open. If append/fsync or directory sync fails, the process refuses further publishing until an operator performs controlled recovery. A successful compaction includes temporary file sync, atomic rename, and parent directory sync on the supported local Linux filesystem. Network filesystem crash guarantees are **not verified**.

## Upgrade / rollback

Take a verified backup before upgrading. Preserve the existing image or binary and configuration. Run Go tests and smoke tests against a staging instance. If a new version fails, stop it, restore the prior binary/image **and** known-compatible data snapshot, and verify access and event retrieval. No automated database schema migration exists in alpha.

## Logs and troubleshooting

`go run ./cmd/notify` emits server lifecycle logs. The API returns JSON errors. Missing or invalid tokens return 401; insufficient topic role returns 403. If login works but channels are empty, publish the first message or use a token with subscriber/admin privileges. SSE requires an HTTP proxy configured for streaming and low buffering. The `/metrics` endpoint requires the administrator token.

## No production deployment claim

The repository contains an example secure-by-default container arrangement but does not imply a hosted service has been installed, verified, or deployed to any VPS. Existing GoreeCloud production infrastructure must be inspected and backed up before a separately authorized migration.
