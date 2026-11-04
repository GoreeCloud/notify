# Native architecture and security model

## Components

- `cmd/notify`: main HTTP server, embedded original web client, configuration and shutdown.
- `internal/notify/model.go`: message schema and input validation.
- `internal/notify/auth.go`: bootstrap administrator credential and hashed role/topic ACL entries.
- `internal/notify/store.go`: append-only JSONL persistence, in-memory topic indexes, idempotency and bounded subscriber fan-out, compacting retention, fail-closed storage writes, and read-only offline verification.
- `internal/notify/http.go`: versioned HTTP API, SSE, admin metrics.

The initial persistence architecture is a single-instance event log. It is intentionally **not a distributed message broker**. Public multi-node clustering, active-active operation, end-to-end encryption, transport gateway integrations, attachments, scheduling, push to mobile OS, and identity federation are not yet implemented.

## Security defaults

1. The service refuses to start without `NOTIFY_ADMIN_TOKEN` of at least 32 characters.
2. All read/write topic APIs require bearer authorization; ACL grants only specified role/topic permissions. Anonymous topic subscriptions are denied.
3. Bootstrap secret is read from the environment, not persisted. Optional ACL entries contain SHA-256 hashes of tokens, not raw secrets. Comparisons use constant time.
4. Server listens on `127.0.0.1:8080` by default. Docker publishes on host loopback only.
5. Browser tokens are held in memory only, never saved in local storage or cookies. Restarting the tab requires reconnecting.
6. Untrusted message content is rendered with `textContent`, not `innerHTML`; click-through URLs are HTTP(S)-only.
7. HTTP security headers include CSP for web assets and `no-store` for the API. No permissive CORS policy is configured.
8. Bound request body sizes, bounded message history, validated topic names and tags, and hourly compaction limit resource use. SSE streams have **per-token (4)** and **process-wide (64)** budgets, released on disconnect. These do not replace edge DoS limits.
9. Container executes as unprivileged UID 65532 with dropped capabilities and a read-only root filesystem.

### Important risks / alpha restrictions

- TLS is **not** terminated by this service; remote deployment **requires** a trusted HTTPS reverse proxy or an appropriately restricted VPN.
- Local JSONL messages are not encrypted at rest; full-disk encryption/secure host permissions are needed for sensitive workloads.
- SHA-256 hashes in the ACL file protect against direct plaintext exposure, but weak tokens are vulnerable to offline guessing. Always generate long random tokens.
- ACL file is loaded at startup, not dynamically reloaded. Rotate and restart after editing it.
- In-memory indexing currently requires memory proportional to retained messages, and the single JSONL log is not suitable for multi-instance concurrent writers.
- The local log uses `fsync` per accepted message; performance at high volumes must be benchmarked. On append/fsync failure, further writes are refused pending recovery. Compaction syncs a temporary file, renames it atomically on a local Linux filesystem, and syncs the parent directory; the original writer remains usable after a staging/rename error. A directory sync failure stops writes because durability is uncertain. Power-loss fault injection remains a production gate.
- Health/readiness endpoints report process health, not verified cloud push delivery or end-to-end storage health.
- There is a basic in-memory limit of 120 publishing requests per token per minute and bounded SSE streams, but no comprehensive network DoS control, distributed rate limiting, incident escalation, strong identity federation, or server-managed user registration in this alpha. Restrict network exposure accordingly.
- Do not use this alpha as the sole channel for emergency or safety-critical alert delivery.

## Topic-scoped tokens

A `NOTIFY_ACL_FILE` file (not committed) may contain:

```json
[
  {"name":"backup-producer","sha256":"64_HEX_CHAR_SHA256_OF_RANDOM_TOKEN","role":"publisher","topics":["backup"]},
  {"name":"backup-reader","sha256":"64_HEX_CHAR_SHA256_OF_ANOTHER_RANDOM_TOKEN","role":"subscriber","topics":["backup"]}
]
```

Generate a token via `openssl rand -base64 48` and its hash using `printf '%s' "$TOKEN" | sha256sum`. For Docker, mount the private file read-only and set `NOTIFY_ACL_FILE` to its container path. A publisher cannot subscribe unless they also hold a separate subscriber token. Only the administrator token can read all topics or access metrics.

## GoreeCloud ecosystem integration

Other GoreeCloud services may publish via this API using dedicated publisher credentials. The architecture does not assume access to existing GoreeCloud Identity, Mesh, Vault, Backup, VPN, DNS, Location, or other services. Future integration needs explicit schema, authentication, authorization, and operational validation.
