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
- Data backup/restore exercise and monitoring acceptance.
- Native/web client connectivity, approved private HTTPS/NetBird gateway integration, DNS and network exposure review.
- Independent investigation of any historical GoreeCloud Notify watchdog alert (the older application is a separate service).

Upstream: [ntfy installation](https://docs.ntfy.sh/install/), [configuration and access control](https://docs.ntfy.sh/config/).
