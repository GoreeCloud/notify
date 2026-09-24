# Changelog

All notable source releases of GoreeCloud Notify are recorded here. Detailed operational history remains in the authoritative GoreeCloud change-log records.

## September 24, 2026 — Glaze UI 1.6.0 web and Flutter source-adoption stabilization

- Repinned Notify's web, Flutter Linux, and Flutter Android presentation contracts from Glaze UI 1.5.1 to current Official Stable Glaze UI 1.6.0.
- Bound the active adoption record to immutable tag `v1.6.0`, accepted release source `a7180679ea851389e0f3004515f9a25f420e716d`, qualification source `c7509c79256b04b0aa67cb9dd0737d7588e0ae4a`, GitHub release `392095913`, and release artifact SHA-256 `687268b5eb76917eccae9d935ffa1bead333d5dee50b6098e996a3f44cee50af`.
- Preserved presentation-only authority: Glaze does not grant notification permission, infer service/security/privacy/policy truth, choose provider precedence, navigate automatically, or execute recovery/consequential actions.
- Reconciled Platform Contract 0.4, web bootstrap/E2E coverage, Flutter identity tests, historical Glaze records, and current feature/planning records to the 1.6.0 source mapping.
- Notify remains nonconformant and not production-eligible until representative browser/native accessibility, semantic-state/recovery, Android device/background-delivery, performance, rollback, consumer-registry, platform-system, production, and later Stable gates pass.

---

## Unreleased

### Changed

- Migrated repository feature lifecycle authority to `IMPLEMENTED-FEATURES.md` and `PLANNED-FEATURES.md`, renamed the live repository changelog authority to `CHANGELOGS.md`, and retired the legacy synchronized roadmap/changelog model without changing Notify runtime or production acceptance.
- Recorded Glaze UI 1.0.0 as the web application's explicit design-system target and added an application-level semantic contract for shared target sizing, focus, motion, radii, semantic roles, and adaptive ranges.
- Aligned the primary responsive transformations with Glaze UI Compact, Medium, Expanded, and Wide ranges while preserving Notify's established notification-focused composition.
- Replaced stale development-milestone presentation with release-aware version, stage, immutable build-revision, and production-acceptance status from `/api/v1/meta`.
- Updated product metadata and browser theme-color metadata for the private Notify application experience.
- Integrated Wardveil Security presentation metadata without changing the authority of the application's underlying security controls.
- Added privacy-minimized structured HTTP observability with bounded `X-Request-ID` correlation, route-template/status/duration events, generic correlated unexpected-error responses, and deliberate exclusion of request secrets and personal network/browser metadata.
- Added a unique canonical GoreeCloud Notify application icon and made the in-application product marks, web favicon, installable-web manifest, Linux AppImage identity contract, and Android APK identity contract converge on the same source artwork.
- Added a source-controlled application-identity contract so platform-specific launcher assets may adapt required padding, masking, monochrome behavior, or rasterization without creating a separate Notify identity.
- Added an explicit production serving contract for the canonical icon and installable-web manifest with bounded revalidating public cache policies and exact media types.
- Separated runtime environment/configuration metadata from immutable product release-stage and production-acceptance metadata so target-validation deployments cannot silently promote themselves merely by using production-mode settings.
- Added explicit pending acceptance-gate metadata for backup/restore, independent monitoring, target runtime/private publication, and manual browser/OS validation while preserving the existing `production` field as the production-configuration compatibility indicator.
- Added a source-bound, read-only target monitoring evidence validator that requires concrete live Uptime Kuma retry/timeout values, notification assignment, observed Caddy source authorization, final private-HTTPS DOWN/RECOVERED evidence, administrator receipt, ntfy rollback preservation, and a tested independent Notify-down path without inventing target-specific defaults.
- Upgraded the issue #24 target monitoring evidence contract to schema v2 and bound every final monitoring evidence bundle to the exact candidate service identity and 40-character Git revision explicitly under acceptance.
- Separated SQLAlchemy declarative metadata from runtime engine initialization so recovery verification can load the current table contract without creating or opening the configured application database.
- Updated the read-only target production preflight to schema v2 so the real target path must satisfy the current Wardveil Security, request-correlation, browser-isolation, canonical application-identity, exact build-revision, release-candidate, and explicit pending production-acceptance contract rather than the older production-configuration-only check.
- Added a source-controlled issue #55 manual browser/OS acceptance contract and dependency-free evidence validator that requires exact browser, operating-system, viewport, HTTPS candidate, and Git-revision session metadata while preserving the distinction between human observation and automated evidence validation.
- Bound the final manual gate to explicit keyboard/focus, screen-reader, 200% zoom/reflow, Auto/Light/Dark, sidebar Read/Unread, two-tab realtime, permission lifecycle, redacted OS-alert, foreground-suppression, and alerts-enabled replay/backlog no-storm checks.
- Ignored generated manual acceptance JSON by default so real Internal acceptance evidence is reviewed and sanitized before any permanent storage decision.
- Added a source-controlled issue #23 target backup/restore evidence contract and read-only validator that binds the target database, backup repository, RPO/retention, independent failed/missed-backup monitoring, verified SQLite snapshot, alternate-location restore, observed recovery time, and security-state reconciliation to one exact candidate revision.
- Added a target recovery evidence procedure and ignored generated target recovery JSON by default so real recovery evidence is sanitized and reviewed before permanent storage.
- Added a source-controlled coherent pre-cutover acceptance contract that composes the real issue #23, #24, #25, and #55 evidence into one exact-candidate acceptance set without changing release or production state.
- Added SHA-256 pinning for each referenced subordinate evidence artifact and direct invocation of the source backup/restore, monitoring, and manual browser/OS validators, while requiring an all-scope passing target-preflight-v2 report for the same HTTPS candidate and Git revision.
- Strengthened the migration boundary so aggregate pre-cutover readiness requires parallel producer/consumer and authorization validation plus an exercised rollback while ntfy remains active, ntfy is not retired, and cutover remains unperformed.
- Ignored generated monitoring and aggregate pre-cutover acceptance JSON by default so Internal evidence is sanitized and reviewed before permanent storage.

### Fixed and hardened

- Browser system-alert permission state now observes supported Permissions API change events and retains focus, pageshow, and visibility reconciliation as compatibility fallbacks.
- Externally blocked browser notification permission now clears the local opt-in promptly and is visible in the collapsed settings summary instead of appearing as an unrequested permission.
- System-alert privacy remains explicit opt-in, foreground-suppressed, backlog-suppressed, and limited to generic redacted operating-system text.
- Actionable controls enforce the Glaze UI 44-pixel minimum target contract, with forced-colors and existing reduced-motion/transparency resilience preserved.
- Invalid caller-supplied request identifiers are replaced instead of being trusted as log correlation input.
- Unexpected server errors no longer require exposing raw exception text to the client; the generic response carries only a sanitized correlation identifier.
- Response hardening now additionally declares same-origin opener/resource isolation, origin-agent clustering, and denial of legacy cross-domain policy files.
- Replaced the visible generic `G` product placeholder treatment with the canonical Notify mark without adding a remote image, font, script, analytics, or tracking dependency.
- Fixed the production-runtime gap where Vite copied the canonical icon and `manifest.webmanifest` into the image but FastAPI exposed only `/assets/*` and `/`, causing the favicon and installable-web identity resources to be unavailable through the final application server.
- Restricted production identity delivery to the exact canonical icon and manifest routes rather than widening the runtime into a general-purpose public static-file tree; missing identity artifacts remain private, non-cacheable failures.
- Tightened cache classification so only successful immutable build assets or approved identity resources retain public caching while static-resource errors fall back to `no-store`/`no-cache` protection.
- Fixed `/api/v1/meta` incorrectly reporting `release_stage: production` solely because `GOREECLOUD_NOTIFY_ENVIRONMENT=production`; the current source line now remains explicitly `release_candidate` with production acceptance pending until a future accepted release intentionally changes source metadata.
- Hardened monitoring acceptance so placeholder values, disabled TLS, backend-only probing, unassigned notifications, unauthorized observed monitor sources, missing administrator receipt, missing ntfy preservation, and same-failure-domain/self-dependent outage alerting fail closed instead of being accepted as production evidence.
- Closed the stale-monitoring-evidence gap by rejecting legacy schema-v1 records and requiring issue #24 evidence to match the explicitly expected candidate revision and release-candidate acceptance state.
- Removed recovery-verifier coupling to normal database-engine startup, eliminating the need for an unrelated writable placeholder application database when verifying a restored artifact in a restricted read-only recovery environment.
- Fixed target preflight drift that could accept a production-configured candidate without verifying the newer release/acceptance boundary, Wardveil response identity, `X-Request-ID`, same-origin opener/resource isolation, origin-agent clustering, legacy cross-domain-policy denial, or canonical manifest/icon delivery through the final HTTPS path.
- Hardened manual acceptance evidence so missing/duplicated checks, placeholder session metadata, revision drift, non-HTTPS or query-bearing candidate URLs, screen-reader claims without a real reader/version, failed checks without dedicated defects, failed final checks, sensitive-data fields, or privacy-contract violations cannot be accepted as issue #55 completion evidence.
- Hardened target recovery acceptance so stale candidate revisions, permissive database modes, same-host/same-storage backup dependence, missing repository recoverability, invalid RPO/retention, self-dependent backup alerts, unverifiable snapshot identity, destructive restore testing, missing observed recovery time, incomplete application validation, unreconciled restored security state, or secret-bearing evidence cannot satisfy issue #23.
- Hardened aggregate acceptance against evidence skew, path traversal, artifact substitution, digest mismatch, duplicate artifact reuse, partial target preflight, subordinate validator failure, early ntfy retirement, unexercised rollback, premature cutover, and secret-bearing manifest fields.

### Validation

- Expanded Playwright coverage records the Glaze UI target, core semantic contract values, minimum actionable target size, release-candidate presentation, and Permissions API revocation reconciliation.
- Added backend regression coverage for Wardveil response metadata, generated and preserved request IDs, unsafe request-ID replacement, privacy-minimized structured log events, stronger browser-isolation headers, and secret-safe correlated unexpected-error handling.
- Added regression coverage for canonical icon safety, browser/installable-web metadata, visible product-mark usage, and cross-platform web/AppImage/APK icon-source consistency.
- Added runtime regression coverage for canonical icon/manifest status, media type, cache behavior, browser-security headers, private failure behavior, and denial of arbitrary `/brand/*` files.
- Extended the disposable production-readiness HTTPS client to prove the final Caddy/application topology can actually serve the manifest and canonical icon with the expected identity reference and cache/security contract.
- Added backend and production-readiness regression assertions that production-mode configuration remains distinct from release stage, acceptance state, and the four outstanding production-acceptance gates.
- Added target-monitor evidence regression coverage for safe passing evidence, exact candidate identity/revision binding, legacy schema rejection, TLS and notification-assignment failures, concrete retry/timeout enforcement, Caddy allowlist/source matching, ntfy baseline preservation, administrator receipt, independent failure-domain proof, placeholder rejection, and sensitive-field rejection.
- Added a standalone backup-verifier regression that points the configured application database at a deliberately non-creatable `/proc` path and requires recovery-artifact verification to succeed solely from the supplied backup path.
- Added target-preflight regression coverage that requires current Wardveil/correlation/isolation headers and rejects release-state promotion, accepted production status, altered acceptance-gate state, or inconsistent Wardveil/observability metadata before real target evidence can pass.
- Added regression coverage for the issue #55 contract, complete passing evidence, exact revision/session binding, required-check completeness, defect linkage, screen-reader session integrity, HTTPS candidate identity, privacy assertions, placeholder rejection, and sensitive-field rejection.
- Added regression coverage for the issue #23 target recovery contract, exact candidate/snapshot/restore revision binding, backup independence and recoverability, RPO/retention enforcement, independent backup monitoring, SQLite snapshot identity/integrity, non-destructive hash-bound alternate restore, restrictive database permissions, security reconciliation, privacy assertions, and sensitive-field rejection.
- Added coherent pre-cutover regression coverage for a complete same-candidate set, explicit revision mismatch, subordinate evidence revision skew, SHA-256 mismatch, non-all-scope target preflight, duplicate artifact reuse, ntfy/parallel-validation/rollback/cutover boundary failures, and sensitive aggregate fields.
- Existing WCAG A/AA automation, Compact overflow checks, realtime/offline recovery, multi-tab behavior, and production/disposable readiness gates remain part of the pull-request validation set.

## 0.2.0 — Release candidate

### Added

- FastAPI notification service with SQLite/SQLAlchemy persistence and Alembic migrations.
- Scoped producer identities, tokens, sources, channels, native ingestion, producer history, and an initial ntfy-compatible publishing path.
- Human users, Argon2id passwords, opaque server-side sessions, CSRF protection, administrator authorization/audit, login abuse controls, and administrator password reset.
- User subscriptions, Delivery fanout, authenticated inbox history/detail, read/unread state, acknowledgement, search, filtering, and cursor pagination.
- Glaze UI authenticated inbox with responsive system/light/dark appearance, subscription management, accessibility-oriented interaction, and privacy-first browser system alerts.
- Authenticated Server-Sent Events with persisted replay cursors, authoritative inbox state, reconnect/offline recovery, multi-tab reconciliation protections, and long-lived session revalidation.
- SQLite Online Backup API recovery tooling, integrity/foreign-key/Alembic verification, restored-session invalidation, and alternate-location synthetic restore validation.
- Reproducible multi-stage production image, non-root/read-only Compose runtime, external proxy-network publication model, production configuration template, private Caddy contract, monitoring readiness, and read-only target preflight tooling.
- Deterministic Python/npm dependency-license inventory, response privacy headers, browser isolation policy, immutable build-revision metadata, and pinned CI/runtime baselines.
- MIT application license and OCI source/version/license metadata.
- Guarded manual GitHub Actions source-prerelease publication for `v0.2.0`, restricted to an exact current-main commit SHA and verified after publication.

### Fixed and hardened

- Fail-closed security-sensitive configuration parsing and session timing validation.
- SQLite foreign-key enforcement and UTC timestamp canonicalization.
- Required administrative-name and notification-title normalization.
- Inactive-user session revocation persistence.
- Realtime/REST ordering and reconnect races.
- Auto/System Glaze appearance on light operating-system themes.
- Browser preference behavior when local storage is unavailable.
- Browser-alert state changes no longer restart the realtime SSE transport.
- Production Compose now requires the immutable Git build revision and propagates it to both application and migration image builds, preventing production-tagged images from retaining the `development` revision fallback.
- Production HTTPS publication adds one-year HSTS without `includeSubDomains` or preload expansion, and both disposable readiness and real target preflight tooling verify the HSTS response contract.

### Validation

The final source line passed backend regression tests, locked frontend lint/type/build validation, Chromium/browser-accessibility tests, production-readiness validation, monitoring-alert readiness, dependency/license verification, and target-preflight self-tests. The production-readiness gate additionally proves fail-closed build-revision handling, exact revision propagation, HSTS, private-network authorization, persistence, and synthetic secret-leak protections.

Production activation remains a separate controlled operation. ntfy remains the active production notification service until target backup/restore, monitoring/out-of-band alerting, private-publication/runtime, manual browser/OS acceptance, migration, and rollback evidence are complete.