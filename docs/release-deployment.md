# GoreeCloud Notify 0.2.0 Release Deployment

## Purpose

This runbook defines the controlled path from the accepted GoreeCloud Notify source release to a target-environment deployment candidate. It does not authorize replacing ntfy merely because source validation is green.

## Release identity

Every deployment must record:

- the exact Git commit SHA;
- GoreeCloud Notify application version;
- the exact production image identity built from that SHA;
- the OCI revision/version/license/source labels;
- the target host and persistent data path;
- the production environment-file path without recording its secret values.

Use the exact Git SHA as both `GOREECLOUD_NOTIFY_IMAGE_TAG` and `GOREECLOUD_NOTIFY_BUILD_REVISION`. The production Compose contract requires the build revision explicitly and refuses to render when it is omitted, preventing an operator from accidentally building a production-tagged image that still carries the `development` revision fallback.

## Preconditions

Before touching the target runtime:

1. Exact-head CI, browser/accessibility, Production readiness, and Monitoring alert readiness must be green.
2. The root `LICENSE`, README, changelog, and release metadata must agree on the release license/version.
3. The external Docker `proxy` network must exist on the target host.
4. The persistent data directory must be approved, owned for runtime UID/GID `10001:10001`, and protected from broad access.
5. The production environment file must be created from `deploy/production/runtime.env.example`, stored outside source control, and protected with restrictive permissions.
6. The actual Caddy Docker-network CIDR must be supplied through `GOREECLOUD_NOTIFY_TRUSTED_PROXY_CIDRS`.
7. A verified recovery point must exist before a migration or replacement of an existing candidate database.
8. The current ntfy runtime and routing must remain available as rollback until cutover is explicitly accepted.

## Build

From the exact release checkout:

```bash
export GOREECLOUD_NOTIFY_IMAGE_TAG="$(git rev-parse HEAD)"
export GOREECLOUD_NOTIFY_BUILD_REVISION="$GOREECLOUD_NOTIFY_IMAGE_TAG"
export GOREECLOUD_NOTIFY_ENV_FILE=/approved/protected/goreecloud-notify.env
export GOREECLOUD_NOTIFY_DATA_DIR=/approved/persistent/goreecloud-notify

docker compose -f docker-compose.production.yml config

docker compose -f docker-compose.production.yml build app
```

The Compose build passes `GOREECLOUD_NOTIFY_BUILD_REVISION` into `Dockerfile.production`; no additional ad hoc `--build-arg` is required when the required environment variable is set correctly.

Verify the image labels before deployment:

```bash
docker image inspect "goreecloud-notify:${GOREECLOUD_NOTIFY_IMAGE_TAG}" \
  --format '{{json .Config.Labels}}'
```

Required release metadata includes:

- `org.opencontainers.image.title=GoreeCloud Notify`
- `org.opencontainers.image.version=0.2.0`
- `org.opencontainers.image.revision=<exact Git SHA>`
- `org.opencontainers.image.source=https://github.com/GoreeCloud/notify`
- `org.opencontainers.image.licenses=MIT`

## Backup and migration

For a fresh deployment, confirm the persistent directory is empty or contains only intentionally initialized candidate data.

For an upgrade or replacement candidate, create and verify the application snapshot according to `docs/backup-recovery.md` before migration.

Run the explicit migration service:

```bash
docker compose -f docker-compose.production.yml \
  --profile maintenance run --rm migrate
```

A migration failure blocks startup/cutover until resolved or rolled back from the verified recovery point.

## Start candidate

```bash
docker compose -f docker-compose.production.yml up -d app
docker compose -f docker-compose.production.yml ps
```

The application container must:

- run as `10001:10001`;
- have a read-only root filesystem;
- expose no host port;
- attach only to the required `proxy` network;
- use `/data` for persistent SQLite state;
- report healthy before publication acceptance continues.

## Private publication

Do not alter the live `notify.goreecloud.com` ntfy route merely to test the candidate.

Use an approved isolated candidate/staging hostname or a separately approved cutover window. The final path must follow the GoreeCloud private-publication model:

```text
approved NetBird client
  -> AdGuard Home private DNS
  -> Caddy HTTPS
  -> Docker proxy network
  -> goreecloud-notify:8000
```

The approved Caddy path must add `Strict-Transport-Security: max-age=31536000` to HTTPS responses. Do not add `includeSubDomains` or `preload` without a separate domain-wide decision because those directives expand the HSTS policy beyond this service boundary.

Validate the full Caddy configuration before a reload/recreate. Preserve the prior ntfy site/routing configuration as the rollback source.

## Target preflight

Run `deploy/target/preflight.py` according to `docs/target-production-acceptance.md` from the appropriate evidence locations:

- host scope on the target Docker host;
- network scope from an approved NetBird client using the normal private DNS/TLS path.

A passing source-level Production readiness workflow does not substitute for this target evidence.

## Manual acceptance

Before production classification/cutover, complete issue #55 against the exact deployed build revision, including:

- keyboard/focus review;
- screen-reader review;
- zoom/reflow and practical visual/contrast review;
- real multi-tab realtime behavior;
- browser permission grant/deny/revoke behavior;
- actual operating-system notification privacy/redaction;
- reconnect/backlog behavior without duplicate alert storms.

Record browser/OS/build identity and pass/fail results.

## Monitoring

Before replacing ntfy:

- register the final private HTTPS `/healthz` target in Uptime Kuma;
- verify healthy/no-alert behavior;
- perform controlled DOWN then RECOVERED validation;
- verify administrator receipt;
- prove at least one Notify-down alert path that does not depend on the Notify runtime itself.

## Backup/restore acceptance

Before production approval:

- configure the approved backup destination/repository, frequency, and recovery-point retention;
- verify missed/failed backup monitoring through an independent path;
- perform at least one alternate-location target restore using the release procedure;
- record the observed recovery time and restored application validation.

## Controlled ntfy cutover

Only after all release and target gates pass:

1. Record the current ntfy runtime, Caddy route, monitoring target, and rollback commands.
2. Verify the GoreeCloud Notify candidate is healthy through the final private path.
3. Migrate producers/consumers one at a time with delivery verification.
4. Change the final `notify.goreecloud.com` route only in the approved cutover window.
5. Validate authentication, SSE, notification delivery, monitoring, and independent outage alerting after cutover.
6. Keep ntfy available until the rollback window closes by explicit decision.

## Rollback

If target acceptance or post-cutover validation fails:

- restore the prior Caddy/route configuration;
- restore the prior ntfy monitor state where changed;
- stop the GoreeCloud Notify candidate if necessary;
- if application data must be reverted, use the verified application recovery procedure rather than ad hoc SQLite copying;
- record the failed evidence and defect before another cutover attempt.

## Final boundary

A GitHub release, successful container build, or green CI result makes the source reproducible and deployable. GoreeCloud considers the service successfully deployed only after target DNS/TLS/access controls, application behavior, monitoring, backup/recovery, manual browser/OS acceptance, migration, and rollback evidence have been validated.
