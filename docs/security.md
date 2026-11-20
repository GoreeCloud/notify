# GoreeCloud Notify — Security and Privacy

## Security model

This preview assumes a single trusted administrator. `NOTIFY_API_TOKEN` is required at startup and must contain at least 32 characters. The server hashes its configured token in memory and compares presented values in constant time. The token authorizes **every topic**. It cannot safely represent untrusted publishers, users or devices with distinct permission scopes.

The server listens on loopback by default. For remote clients, provide TLS and access controls through an appropriately configured and verified reverse proxy. Android refuses HTTP entirely; Linux allows HTTP only to localhost. The React app expects the API at the same origin. No cookies or CORS policy are used.

**Confidentiality limits:** Message bodies are available in plaintext to the server process and on disk, though the journal file is created mode 0600 and its directory mode 0700 when new. No end-to-end encryption or disk encryption is implemented. Do not publish real secrets, OTPs, credentials or other sensitive contents. Ensure backups, access to the host and file permissions are controlled.

## Input and resource controls

- Topic names are 1–64 ASCII letters/numbers/underscores/hyphens; path traversal is refused.
- JSON requests are capped at 8 KiB and validated with strict fields and only one JSON object.
- Publishing is limited to 120 messages per minute per process (shared across all clients); there is no distributed rate enforcement.
- The journal hard-caps at 10,000 records / 32 MiB. Exhaustion returns HTTP 507; do not silently overwrite data.
- Recent history is capped at 200 messages; untrusted text is rendered as text by native clients, not HTML.
- API responses have `Cache-Control: no-store`, `X-Content-Type-Options: nosniff`, and `Referrer-Policy: no-referrer`.
- Event streaming is authorized before subscription; subscribers are isolated by topic, and slow consumers cannot block publishes.

## Known preview limitations

- No scoped API tokens, Identity integration, per-topic ACLs or key rotation without restart.
- No external audit of token storage, journal crash consistency, retention/compaction, backups, or replay semantics.
- Token resides in process/browser memory during use; avoid shared/public terminals. Shell environment values and local process inspection require host protections.
- No authenticated web push, advanced abuse detection, retry queues, delivery receipts, background delivery guarantee, or independent failover.
- CORS intentionally disabled; third-party cross-origin websites cannot use the bearer API directly.
- Dependency and supply-chain assessment requires regular maintenance; static scans alone do not guarantee safety.

## Deployment and incident guidance

Run as a dedicated unprivileged service account; use HTTPS and restrict inbound ports; rotate the API token if exposed. Archive the journal securely while the process is **stopped**, then restore atomically and verify before changing data. Do not share real notification contents publicly or paste authorization headers in issue reports.

Historical alerts referring to an older, inaccessible `GoreeCloud/notify` source tree were observed during initialization. No old source or credentials were imported. Whether those alerts were previously remediated remains a separate investigation; recreating a repository does not rotate previously exposed secrets.

This document is a design review, **not** an assertion that a production host has been hardened, deployed, audited, or recovered.
