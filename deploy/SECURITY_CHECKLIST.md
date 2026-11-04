# Deployment security acceptance checklist (alpha)

GoreeCloud Notify is **not approved for internet-facing production traffic**. This is an operator checklist, not evidence that any item has been completed on a GoreeCloud VPS.

## Before deploying

- [ ] Keep the application listener on `127.0.0.1` or an explicitly isolated container network. Do **not** expose plaintext bearer-token HTTP publicly.
- [ ] Terminate TLS with a maintained trusted reverse proxy. Validate current certificates, HSTS policy, request body limits, proxy stream buffering settings, and upstream access controls.
- [ ] Configure ingress limits for **trusted client source IPs**, including failed auth, connection counts, request rates, and burst traffic. Do not blindly trust incoming `Forwarded` or `X-Forwarded-For` headers.
- [ ] Generate high-entropy admin and service tokens; never put secrets in source control, logs, URLs, browser persistence or chat transcripts. Configure least-privilege topic ACLs.
- [ ] Confirm private filesystem ownership and modes: data dir `0700`, journal and `.notify.lock` `0600`; confirm a second service instance cannot open the same journal.
- [ ] Restore a recent verified backup to an isolated test service and run `notifylog` on a quiesced copy. Check that the journal survives restart with expected event IDs and idempotency behavior.
- [ ] Run the repository's race-enabled tests, vet, build and container checks on the precise release commit. Complete abuse/threat review and browser/device testing.
- [ ] Put independent alerts around Notify itself. Do not use Notify as its own only watchdog and do not depend on alpha Notify for safety-critical alerts.
- [ ] Prepare a reversible, reviewed deployment/rollback plan with an intact prior binary/image and known-compatible snapshot. Record monitored acceptance criteria and fallback procedures.

## Known limitations

No server-managed token rotation/revocation, end-to-end encryption, mobile push transport, durable scheduling, multi-node replication, distributed rate limits or tested power-loss durability is yet established. Linux `flock` only protects local cooperating writers. Reverse-proxy clients share a single in-process peer rate budget. Production TLS/edge settings and disaster recovery require environment-specific validation.
