# GoreeCloud Notify — Architecture and Acceptance

## Scope and data contract

The server is an independently deployable Go executable with no runtime third-party Go modules. Data is an append-only private JSON Lines journal and is loaded into process memory for recent-history queries. One server process must own the data file. It is **not** a multi-node database, not a write-ahead log with guaranteed power-loss recovery, and not a queue with acknowledgements.

A message has `id` (cryptographically random hex), `topic` (ASCII token), `title` (optional), `body`, `priority` (1–5), and UTC `created_at`. Request bodies are bounded at 8192 bytes; titles at 160 Unicode code points and bodies at 4096. The journal stops accepting new writes at 10,000 messages or 32 MiB rather than silently deleting user data. Manual archive/rotation is required and must preserve data and stop the service first.

## HTTP API (v1)

| Method | Path | Behavior |
| --- | --- | --- |
| GET | `/healthz` | Basic process health, no secret |
| POST | `/api/v1/topics/{topic}/messages` | Create validated message (201) |
| GET | `/api/v1/topics/{topic}/messages?limit=50` | Latest messages first (up to 200) |
| GET | `/api/v1/topics/{topic}/events` | Authorized SSE new-message events |

All API endpoints require `Authorization: Bearer <token>`. The server intentionally has no browser cookies, wildcard CORS, remote webhooks, or unscoped topic enumeration. The initial server is single-tenant with all-topic administrator access. The SSE broker is process-local, does not replay messages, and drops events for slow subscribers; clients must reconcile from history.

## Platform boundaries

- **GoreeCloud UI:** canonical design tokens in `GoreeCloud/gc-ui`. Web pins the Git source revision; Android includes a provenance-tagged Kotlin theme snapshot; Linux's token snapshot references the same revision pending generator integration.
- **GoreeCloud Mesh:** the documented HTTP/JSON/SSE contract is an integration surface. Actual Mesh discovery, registration, and lifecycle control are **not yet implemented**.
- **GoreeCloud Identity:** the current environment-supplied server token is a bootstrap authentication mechanism, **not** an Identity implementation.
- **GoreeShield:** no telemetry, token persistence disabled in UI clients, private-topic default, bounded data, no body in Android banners. User-configurable retention and per-topic consent are pending.
- **Wardveil:** constant-time token comparison, bounded requests, path validation, HTTPS-only remote clients, no secrets in repository, rate limiting and basic headers. Threat intelligence/incident integration is pending.

## Suggested development milestones

1. Replace the JSONL prototype with transactional storage (SQLite via audited dependency, migrations, backup and restore checks); add configurable retention.
2. Add scoped credentials, topic ACLs, refresh/rotation, and GoreeCloud Identity interoperability.
3. Add Android UnifiedPush/FCM-free foreground service or compliant background transport where supported, optional browser Web Push, and Linux notification daemon integration; make delivery guarantees explicit.
4. Add ntfy-compatible publishing and subscription adapters under explicit versioned contracts. Matrix gateway/webhooks only with validated origin allowlists and signing.
5. Add encrypted-at-rest/optional E2EE plans without claiming encryption of server-visible messages today.
6. Add integration tests, load/rate tests, browser and real-device acceptance, restore drills, and signed builds before any Stable declaration.

## Delivery acceptance

Currently: source with tested Go protocol paths, browser build and native-client source. To declare release readiness, require successful Linux Qt 6.12 build/runtime, Android APK/permission/background test, supported-browser accessibility test, HTTPS reverse proxy security test, journal recovery behavior, dependency/SBOM/license review, passing CI, protected main, and founder review. Record each independently, not as a single inferred green check.
