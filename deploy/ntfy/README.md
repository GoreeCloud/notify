# Upstream ntfy Docker backend for GoreeCloud Notify

**Status:** This is a source-controlled, security-first deployment template. It is **not** the old independent GoreeCloud Notify application, not a replacement for the native GTK/Linux or companion web clients, and not proof of an externally reachable production service.

The separate private-VPS instance was brought up with an equivalent configuration after verifying the host's Docker environment and existing workloads. Its health and readiness probes returned success. **No authorized ntfy users or client tokens were provisioned**, because the credential-creation action was blocked by the connector's safety controls; anonymous publishing/subscribing returns HTTP 403. No Caddy route, public/private DNS record or firewall was modified.

## Safe setup

1. Consult the current canonical GoreeCloud instructions, verify that the target VPS is authorized, inspect existing containers, ports, backup/data layout and the real Docker service version.
2. Copy `compose.yaml` **outside** the public repository into a private, owner-only deployment directory. Create its `data/` directory there with mode `0700`, owned by the UID/GID in Compose (1001:1001 by default). Never put live database or credential files in the Git checkout.
3. Check the image digest/version against the [official ntfy release page](https://github.com/binwiederhier/ntfy/releases), the compatibility notes, and relevant security advisories.
4. Validate locally: `docker compose -f compose.yaml config --quiet`. Confirm that `127.0.0.1:8792` is available. Do not substitute a public listen address or connect the service to an external reverse-proxy network without a separate review.
5. Start the dedicated backend only: `docker compose -f compose.yaml up -d --no-build`. The Docker healthcheck probes `/v1/ready`.

## Validation

Run the following from the **VPS**, not a public browser:

```sh
docker compose -f compose.yaml ps
curl --fail --silent --show-error http://127.0.0.1:8792/v1/health
curl --silent --output /dev/null --write-out '%{http_code}\n' -X POST --data 'denied' http://127.0.0.1:8792/validation
curl --silent --output /dev/null --write-out '%{http_code}\n' 'http://127.0.0.1:8792/validation/json?poll=1'
docker port goreecloud-ntfy
```

Expected: a healthy container, JSON health with `healthy: true`, HTTP **403** for both anonymous operations, and only a **127.0.0.1** host-port mapping.

## Authentication setup (still required)

The upstream `auth-default-access=deny-all` default prevents publishing or reading until authorized users and ACLs are provisioned. Use an approved secret-safe interactive workflow to create an administrator and separate least-privileged application principal; for example, the upstream CLI supports `ntfy user add --role=admin <username>`, `ntfy access <username> <topic-pattern> read-write`, and `ntfy token add --expires=90d <username>`. Never supply passwords or tokens on a command line that will be logged or copied into shell history, and never commit them, their raw stores, or private topic data.

ntfy access tokens inherit their user's access; they are not independently topic-scoped. Therefore, apply ACLs to the **regular user** and avoid giving application clients an administrator token. Verify authenticated publish, subscribe, ACL refusal, and revocation with **synthetic test topics** before configuring real clients.

## Privacy and security boundary

- Pin the image digest; upgrade only after verifying migration notes and an appropriate rollback/backup plan.
- The backend is reachable only through VPS localhost by default. A remote native app requires an approved private tunnel or separately designed HTTPS route.
- `NTFY_BEHIND_PROXY` is **false** until a trusted reverse-proxy path and forwarded-header trust rules are reviewed. Do not merely expose this port on `0.0.0.0`.
- SQLite message cache retention is 24 hours, and authentication and message databases are persistent. Owner-only host directory/file permissions are mandatory. Backup and restore those stores securely, without committing or exporting secrets into CI.
- Existing Caddy, VPN, DNS, old GoreeCloud Notify stack, and independent outage-monitor configuration remain unchanged by this setup.

## Online SQLite backup and isolated restore verification

The [backup utility](../../tools/backup_ntfy_sqlite.py) uses Python's standard-library SQLite online-backup API. It does **not** copy a live SQLite file while its write-ahead log may contain uncheckpointed data. It creates a private pending directory, snapshots `auth.db` and `cache.db`, normalizes only the **backup copies** to standalone files, runs SQLite integrity checks, and atomically publishes the completed backup. It then copies the result to an isolated temporary restore directory and validates both databases. It never reads out or prints rows, tokens, hashes, message bodies or other secrets.

On the VPS, copy the utility **outside the repository** into a private owner-only maintenance directory, and use an owner-owned directory to store snapshots. Run it as the owner of the databases:

```sh
python3 -B backup_ntfy_sqlite.py \
  --source /path/to/private/ntfy/data \
  --backups /path/to/private/ntfy/backups
```

Required filesystem permissions: source data directory `0700`, each database `0600`, backup root `0700`. The utility rejects symlink sources and unsafe permissions and removes only an incomplete staging snapshot when verification fails. **It never deletes old backups.** The database contents remain private on the destination machine; do not check backup files into GitHub or allow CI to upload them.

**Verified VPS execution (October 29, 2026):** One snapshot of the active instance succeeded with both databases intact, followed by an isolated restore/integrity check while ntfy remained healthy. The backup directory and nested snapshot use mode `0700`, database copies mode `0600`. This validates a *local* recoverable snapshot, not off-host disaster recovery, scheduled rotation, encrypted offsite storage, credential provisioning or a full service restoration. Check safe off-host backup storage and future restore/rotation before release acceptance.

## Optional offline daily backup worker

The [backup Compose override](backup.compose.yaml) runs a small **separate container** from a digest-pinned official Python image. It has no network, no host ports, a non-root UID, read-only root filesystem and the live SQLite bind mount is read-only. Its only writable persistent mount is the owner-only `backups/` directory. It runs the [daily backup scheduler](../../tools/ntfy_backup_scheduler.py) plus the online backup utility.

Copy both scripts to a private `maintenance/` directory alongside `compose.yaml`; store the override beside `compose.yaml` as `backup.compose.yaml`. Use `chmod 0700` on the private deployment, maintenance and backups directories, and `chmod 0600` on the scripts and Compose files. The Docker worker expects UID/GID 1001 (change both deployment templates only after confirming the actual host data ownership).

Start **only the worker** after a successful manual snapshot and isolated restore check:

```sh
docker compose -f compose.yaml -f backup.compose.yaml config --quiet
docker compose -f compose.yaml -f backup.compose.yaml up -d --no-deps --no-build backup
docker compose -f compose.yaml -f backup.compose.yaml ps
docker exec goreecloud-ntfy-backup python -B /app/ntfy_backup_scheduler.py --healthcheck
```

It checks for an existing snapshot on startup, then schedules a run at **03:15 UTC daily**. It skips redundant same-date snapshots, verifies both SQLite files and checks a disposable restore before reporting success. Docker's worker healthcheck fails if the latest snapshot is more than **36 hours** old. The worker makes no network connections.

The operator must regularly review the backup directory. This worker **never prunes or deletes snapshots**. Instead it stops creating more after **45 snapshots** or when available disk space is below **1 GiB**, logs a non-sensitive error type, and eventually becomes unhealthy. This is a deliberate fail-closed retention safeguard; an authorized retention/archival policy is required before the threshold is reached. Docker health state alone is not an alert-delivery mechanism.

To stop this worker without stopping ntfy:

```sh
docker compose -f compose.yaml -f backup.compose.yaml stop backup
```

**Verified October 29, 2026:** the worker started successfully on the authorized VPS, with network mode `none`, all capabilities dropped, read-only live database bind, healthy status and a successful explicit scheduler healthcheck. On its first start, it recognized the verified same-day snapshot and did not create a duplicate. The first future scheduled job has **not** yet been observed; daily continuity, recovery after reboots, alert routing, retention authorization, off-host encryption and disaster-recovery drills remain open.

## Read-only host assessment and failure signals

Use the [host health probe](../../tools/ntfy_host_health.py) to verify both containers, their expected non-root and capability-restricted Docker configurations, exact loopback-only port mapping, ntfy health, the latest SQLite snapshot's age, whether today's scheduled 03:15 UTC backup exists after a one-hour grace period, SQLite snapshot integrity, snapshot-count headroom, and a minimum free-disk reserve for the next verified backup and isolated restore. Install a copy of the script into the owner-only `maintenance/` directory; no Docker control socket is mounted in a container and no ntfy credentials are needed. Run as the same unprivileged owner that owns the backup files:

```sh
python3 -B ntfy_host_health.py --backups /path/to/private/ntfy/backups --json
```

The script exits **0** when all eleven checks pass, **1** if a check fails, and **2** on an unexpected probe error. JSON keys and Boolean results contain no secrets, server configuration values, topics, or message content. A red check should be triaged without restarting unrelated services. This probe is read-only and does **not** deliver alerts by itself.

**Observed October 29, 2026:** all eleven checks passed on the running private ntfy host, including Docker hardening and projected backup capacity. Separately, an unrelated older `netbird-ntfy-monitor.service` unit was found failed, with its timer inactive. That older monitoring path was not changed, and its recovery is tracked separately: a healthy new ntfy container cannot retroactively clear legacy alerts.

### Drift and capacity alerts

The extra checks detect operational risk before a conventional Docker healthcheck does:

- `backend_hardening`: verifies the expected UID, read-only root filesystem, no Linux capabilities or privileged mode, no-new-privileges, correct published port and data bind.
- `worker_hardening`: checks the offline network namespace, privilege restrictions, absent public ports, read-only live SQLite and maintenance mounts, and writable backup directory.
- `backup_slots_available`: becomes unhealthy at **40 snapshots**, leaving five slots before the worker's non-destructive **45-snapshot** hard limit; operators must establish authorized archival/retention instead of deleting silently.
- `backup_disk_reserve`: requires at least **1 GiB plus twice the current snapshot database sizes**, allowing space for an online snapshot and independent temporary restore.

All checks return nonsecret Boolean results and stop at *read-only detection*. Investigate failed checks using a separately authorized operational workflow; never automatically reconfigure Docker, open ports, delete snapshots, or restart other services. The worker itself remains non-destructive.

Monitoring still requires a genuinely scheduled external observer and a proven notification route. Until an observer is configured and has successfully delivered a controlled test alert, treat the monitoring capability as **probe-ready but not delivery-verified**.

## Operations and rollback

```sh
docker compose -f compose.yaml logs --tail 50 ntfy
docker compose -f compose.yaml restart ntfy
# Reversible rollback of the new instance only:
docker compose -f compose.yaml stop ntfy
# Start again:
docker compose -f compose.yaml up -d --no-build ntfy
```

Do not run `down -v` or delete the `data/` directory: that may destroy message and authentication state. If upgrading or migrating, first make an access-controlled, consistent SQLite backup and test a restore in isolation.

## Acceptance still open

- Initial account/token provisioning using a supported protected workflow.
- Authorized end-to-end publish/subscribe and reconnect acceptance.
- Full service recovery and off-host encrypted backup/retention acceptance (a verified local SQLite snapshot and isolated restore check are available).
- Native/web client connectivity, approved private HTTPS/NetBird gateway integration, DNS and network exposure review.
- Independent investigation of any historical GoreeCloud Notify watchdog alert (the older application is a separate service).

Upstream: [ntfy installation](https://docs.ntfy.sh/install/), [configuration and access control](https://docs.ntfy.sh/config/).
