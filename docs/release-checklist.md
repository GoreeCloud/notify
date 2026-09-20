# GoreeCloud Notify Release Checklist

This checklist distinguishes source-release readiness from production activation.

## Source release

- [x] Milestones 1–4 source implementation complete for the current web/API scope.
- [x] Required authentication/authorization/input/database hardening integrated.
- [x] Reproducible frontend lock/install/build path.
- [x] Reproducible constrained backend dependency closure.
- [x] Production multi-stage image and least-privilege runtime contract.
- [x] Private-publication source contract and disposable Production readiness gate.
- [x] Monitoring source contract and disposable DOWN/RECOVERED readiness gate.
- [x] Application-specific SQLite backup/restore tooling and synthetic alternate-location restore validation.
- [x] Immutable Git build-revision identity.
- [x] Production Compose fails closed without the exact immutable build revision and propagates that revision into application and migration builds.
- [x] Response privacy and browser-isolation security headers.
- [x] HSTS is present in the proposed production Caddy contract and verified by disposable readiness plus target preflight tooling.
- [x] Browser/accessibility automation.
- [x] Glaze UI system/light/dark appearance resilience.
- [x] Browser preference/storage resilience and stream-stable system-alert state.
- [x] Current repository source license is `AGPL-3.0-only` and the production image carries the same OCI license metadata; the published `v0.2.0` release at `dd22a7ad0765c8ca62b401749265594bb0a06e23` retains its historical MIT grant.
- [x] Release README, changelog, deployment runbook, and dependency-license review.
- [x] Final integration PR exact-head CI/browser/Production readiness/Monitoring alert readiness green — PR #61 head `b96b23eea57fc6bcb69147ac28671b749b72e38b`.
- [x] Production-contract stabilization PR #64 exact-head validation green — head `10496ffd961086f46740aec292962c206b743ade`; CI run `31967591068`, Production readiness run `31967591067`, Monitoring alert readiness run `31967591082`.
- [x] PR #64 merged as `235bbb7f08c5e18fdf116c1acfa75e86a6d06abd`; post-merge main CI run `31967680856` is green.
- [x] Guarded manual `Publish source release` workflow is available and requires `v0.2.0` to target the exact current `main` SHA; it publishes the current release-candidate line as a GitHub prerelease and verifies tag/release metadata.
- [x] `v0.2.0` tag and GitHub prerelease created from source-freeze commit `dd22a7ad0765c8ca62b401749265594bb0a06e23` and independently verified. Manual `Publish source release` run `31991914921` completed successfully; the tag resolves exactly to the frozen commit and the release is non-draft and marked prerelease. Tracked by issue #63.

## Manual browser/OS acceptance

- [ ] Keyboard/focus acceptance.
- [ ] Screen-reader acceptance.
- [ ] Zoom/reflow and practical visual/contrast acceptance.
- [ ] Real multi-tab realtime acceptance.
- [ ] Browser permission grant/deny/revoke acceptance.
- [ ] Actual OS notification privacy/redaction acceptance.
- [ ] Reconnect/backlog duplicate-alert acceptance.

Tracked by issue #55.

## Target runtime/private publication

- [ ] Candidate deployed on approved target host.
- [ ] Target runtime/filesystem/secret-file evidence passes.
- [ ] Private DNS/TLS/Caddy/NetBird approved-source behavior passes.
- [ ] Final Caddy HTTPS path returns the approved HSTS policy.
- [ ] Unauthorized-source behavior passes.
- [ ] Long-lived SSE/session revocation/expiry through final Caddy path passes.
- [ ] Prolonged real-network interruption/recovery passes.

Tracked by issue #25.

## Target backup/recovery

- [ ] Backup repository/destination approved.
- [ ] Backup frequency/RPO approved.
- [ ] Recovery-point retention approved.
- [ ] Independent failed/missed-backup monitoring configured.
- [ ] Target backup verified.
- [ ] Alternate-location target application restore passes and observed recovery time is recorded.

Tracked by issue #23.

## Target monitoring/outage alerting

- [ ] Final private HTTPS Uptime Kuma monitor registered.
- [ ] Healthy/no-alert behavior verified.
- [ ] Controlled DOWN and RECOVERED sequence verified.
- [ ] Administrator receipt verified.
- [ ] Independent Notify-down alert path deployed and tested.

Tracked by issue #24.

## Migration and rollback

- [ ] Producer inventory reconciled.
- [ ] Consumer/subscription inventory reconciled.
- [ ] Producers migrated incrementally with delivery verification.
- [ ] Final hostname cutover validated.
- [ ] ntfy rollback tested and retained through the approved rollback window.
- [ ] ntfy retirement separately approved.

Production is not considered complete until every applicable unchecked target/manual item above has evidence tied to the exact deployed build.
