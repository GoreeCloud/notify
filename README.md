# GoreeCloud Notify

GoreeCloud Notify is the GoreeCloud-native centralized notification-delivery service intended to replace the ntfy service that was permanently retired from `goreecloud-vps-01` on September 18, 2026.

The application combines a FastAPI backend, SQLite persistence, a React/TypeScript Glaze UI inbox, authenticated Server-Sent Events, scoped producer identities, human web sessions, subscription fanout, read/acknowledgement state, and privacy-first browser system alerts.

## Release status

The current source line is a **release candidate**. Source-level CI, browser/accessibility validation, production-runtime readiness, monitoring-readiness, backup/restore tooling, security hardening, and target-preflight tooling are implemented and validated.

It is deployable to an approved GoreeCloud target, but production activation is intentionally separate from source readiness. ntfy is no longer running on the VPS. The `notify.goreecloud.com` identity remains reserved for GoreeCloud Notify and must not be treated as production-ready until target backup/restore, independent monitoring/out-of-band alerting, private Caddy/NetBird/DNS validation, current Stable Glaze UI 1.6.0 adoption and Notify-specific acceptance, nine-system platform evaluation, and final manual browser/OS/native acceptance are recorded.

## Core capabilities

- Native scoped producer API for notification ingestion.
- Initial authenticated ntfy-compatible `POST`/`PUT` topic publishing.
- Producer-scoped notification history.
- Administrator-provisioned human users with Argon2id password hashing.
- Opaque server-side web sessions with CSRF-protected mutations.
- Human administrator authorization, attributable audit events, login abuse controls, and administrator password reset.
- User-owned channel subscriptions and Delivery fanout.
- Authenticated inbox with search, filters, cursor pagination, read/unread, and acknowledgement state.
- Authenticated SSE delivery with persisted replay cursors, authoritative counts, reconnect recovery, and session revalidation.
- Privacy-first browser system alerts with explicit opt-in and generic redacted content.
- Responsive Glaze UI with system/light/dark appearance and automated browser/accessibility coverage.
- SQLite backup/restore tooling, integrity validation, migration checks, and restored-session invalidation.
- Reproducible production image, least-privilege Compose runtime, private-publication readiness, monitoring readiness, and read-only target preflight tooling.

## Architecture

```text
Approved NetBird client
        |
        v
AdGuard Home private DNS
        |
        v
Caddy HTTPS / private-source restriction
        |
        v
Docker proxy network
        |
        v
GoreeCloud Notify
  FastAPI + static Vite build
        |
        v
SQLite persistent data
```

The application does not require a public backend host port. The intended production path is private DNS + NetBird + Caddy + the approved Docker `proxy` network, with application authentication remaining an additional control.

## Repository structure

```text
.
├── backend/                       FastAPI application, models, migrations, tests, recovery tooling
├── frontend/                      React + TypeScript + Vite Glaze UI and Playwright tests
├── deploy/                        Production, Caddy, monitoring, readiness, and target-preflight assets
├── docs/                          Architecture, security, recovery, migration, and acceptance records
├── docker-compose.yml             Development topology
├── docker-compose.production.yml  Production runtime contract
├── Dockerfile.production          Reproducible multi-stage production image
├── PROJECT-SPECIFICATIONS.md      Canonical project requirements and acceptance boundary
├── PROJECT-RECORD.md              Significant project history and governance record
├── IMPLEMENTED-FEATURES.md        Evidence-backed implemented feature authority
├── PLANNED-FEATURES.md            Planned feature and acceptance authority
├── CHANGELOGS.md                  Repository change-history authority
├── LICENSE                        AGPL-3.0-only license grant
├── LICENSE-NOTICE.md              Prior MIT grants and third-party licensing boundary
└── .github/workflows/             CI, browser, production-readiness, and monitoring-readiness gates
```

## Development

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
alembic -c alembic.ini upgrade head
pytest
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Frontend

```bash
cd frontend
npm ci --ignore-scripts
npm run lint
npm run check
npm run build
npm run dev -- --host 127.0.0.1
```

### Browser validation

```bash
cd frontend
npx playwright install --with-deps chromium
npm run test:browser
```

## Production deployment contract

Production uses `docker-compose.production.yml` and `Dockerfile.production`.

Required deployment inputs are intentionally external to source control:

- `GOREECLOUD_NOTIFY_IMAGE_TAG` — approved release/build identifier.
- `GOREECLOUD_NOTIFY_ENV_FILE` — protected production environment file.
- `GOREECLOUD_NOTIFY_DATA_DIR` — approved persistent data directory.
- existing external Docker network `proxy` — shared only with the central Caddy path.

The runtime is non-root (`10001:10001`), read-only except for `/data` and a protected `/tmp` tmpfs, drops all Linux capabilities, enables `no-new-privileges`, applies a PID limit, and publishes no application host port.

Before first start or any schema upgrade, create and verify the required recovery point according to `docs/backup-recovery.md` and the GoreeCloud backup policy.

A controlled production sequence is:

```bash
export GOREECLOUD_NOTIFY_IMAGE_TAG=<approved-release-or-git-revision>
export GOREECLOUD_NOTIFY_ENV_FILE=/path/to/protected/runtime.env
export GOREECLOUD_NOTIFY_DATA_DIR=/path/to/persistent/data

docker compose -f docker-compose.production.yml config

docker compose -f docker-compose.production.yml build \
  --build-arg GOREECLOUD_NOTIFY_BUILD_REVISION="$GOREECLOUD_NOTIFY_IMAGE_TAG" app

docker compose -f docker-compose.production.yml \
  --profile maintenance run --rm migrate

docker compose -f docker-compose.production.yml up -d app

docker compose -f docker-compose.production.yml ps
```

After startup, validate the target with the read-only preflight documented in `docs/target-production-acceptance.md`. Evidence must come from the actual GoreeCloud Notify candidate runtime; the retired ntfy service is historical/recovery context only.

## Production environment

Start from `deploy/production/runtime.env.example`; do not copy active secrets into the repository.

Production must use:

- secure session cookies;
- only the approved HTTPS origin(s) for credentialed CORS;
- protected bootstrap/recovery values only where required;
- explicit trusted-proxy CIDRs matching the actual Caddy path;
- a persistent SQLite URL rooted in `/data`;
- fail-closed security-sensitive configuration.

## Private publication

The expected final private access model is:

```text
notify.goreecloud.com
  -> AdGuard Home private rewrite
  -> NetBird-only source path
  -> Caddy HTTPS
  -> goreecloud-notify:8000 on Docker proxy network
```

Caddy, private DNS, and NetBird changes are target-environment operations and are deliberately not applied by CI. Use the source-controlled Caddy/readiness contracts under `deploy/` and the target acceptance runbook before enabling the final hostname.

## Health and monitoring

`GET /healthz` validates application/database availability. Production acceptance requires an approved independent monitoring path, with GoreeCloud Monitor as the intended GoreeCloud-native consumer once Monitor itself is accepted; the retired Uptime Kuma service is not an active dependency.

Notify must not be the sole destination for alerts about Notify itself. Production approval requires a tested independent outage-alert path plus validated DOWN/RECOVERED monitoring behavior.

## Backup and recovery

The repository includes application-specific SQLite backup/restore tooling based on a consistent SQLite snapshot mechanism rather than an unconditional copy of a changing database.

Recovery validation includes integrity checks, foreign-key checks, required-table checks, Alembic revision verification, alternate-location application restore testing, and restored web-session invalidation. Target production still requires an approved backup repository/schedule/retention and an actual recorded target restore exercise.

See `docs/backup-recovery.md`.

## Security model

- Producer credentials and human sessions are separate authentication domains.
- Reusable producer tokens and session tokens are stored as digests rather than plaintext.
- Human mutations are protected by session-bound CSRF tokens.
- Routine administrator actions require an attributable human administrator session.
- Login throttling uses bounded persistent state and sanitized digests.
- Non-asset HTTP responses are `no-store` and carry privacy/browser-isolation headers.
- Browser system-alert content is generic and does not expose notification title/body/source/channel.
- Production secrets remain outside source control and image layers.

See `SECURITY.md` and `docs/security.md`.

## Key API routes

### System

- `GET /healthz`
- `GET /api/v1/meta`

### Human sessions and inbox

- `POST /api/v1/session`
- `DELETE /api/v1/session`
- `GET /api/v1/me`
- `GET /api/v1/csrf`
- `GET /api/v1/inbox`
- `GET /api/v1/inbox/state`
- `GET /api/v1/inbox/stream`
- `GET /api/v1/inbox/{delivery_id}`
- `POST /api/v1/inbox/{delivery_id}/read`
- `DELETE /api/v1/inbox/{delivery_id}/read`
- `POST /api/v1/inbox/{delivery_id}/acknowledge`
- `GET /api/v1/subscriptions`
- `PUT /api/v1/subscriptions/{channel_slug}`
- `DELETE /api/v1/subscriptions/{channel_slug}`

### Producers

- `POST /api/v1/notifications`
- `GET /api/v1/notifications`
- `GET /api/v1/notifications/{id}`
- `POST|PUT /{topic}` — initial authenticated ntfy-compatible publishing

## Stable-release boundary

Source readiness is not the same as production activation. Before GoreeCloud Notify can become the production notification service, GoreeCloud still requires:

1. current Stable Glaze UI **1.6.0** repository-local source adoption and representative web/Linux/Android acceptance; 1.6.0 source mapping is integrated, while application-specific acceptance remains pending;
2. explicit evaluation of all nine Integral Platform Systems, with unsupported or unaccepted systems remaining fail-closed rather than implied complete;
3. manual keyboard, screen-reader, zoom/reflow, browser-permission, real OS notification, native-client, and practical multi-tab acceptance;
4. target backup repository/schedule/retention plus a successful recorded target restore;
5. approved independent health monitoring plus a tested out-of-band Notify-down alert path that does not depend entirely on Notify itself;
6. final target Caddy, private DNS, NetBird, runtime/filesystem, long-lived SSE/session, and real-network interruption/recovery evidence;
7. controlled migration of actually active producers away from retired ntfy configuration to scoped GoreeCloud Notify identities and tokens;
8. a tested rollback/recovery path to the last known-good GoreeCloud Notify candidate and preserved predecessor recovery evidence where applicable;
9. explicit production-activation approval for the exact release/runtime state.

ntfy retirement is verified historical state, not proof that GoreeCloud Notify has completed these gates.


## Project governance

The authoritative project requirements and significant project history are repository-local:

- [PROJECT-SPECIFICATIONS.md](PROJECT-SPECIFICATIONS.md)
- [PROJECT-RECORD.md](PROJECT-RECORD.md)

Current feature state is governed by [IMPLEMENTED-FEATURES.md](IMPLEMENTED-FEATURES.md) and [PLANNED-FEATURES.md](PLANNED-FEATURES.md); repository chronology is governed by [CHANGELOGS.md](CHANGELOGS.md). Historical Google Drive project specifications are migration sources only until the project-record migration is accepted and the standard deletion gate is satisfied.

## License

Current and future GoreeCloud-owned GoreeCloud Notify source is licensed under the **GNU Affero General Public License, version 3 only (`AGPL-3.0-only`)**. The published `v0.2.0` source release remains available under the MIT License granted for that release. See [`LICENSE`](LICENSE) and [`LICENSE-NOTICE.md`](LICENSE-NOTICE.md).
