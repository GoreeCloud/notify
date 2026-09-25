# GoreeCloud Notify — Project Record

**Repository:** `GoreeCloud/notify`  
**Former repository identity in the Drive source:** `GoreeCloud/goreecloud-notify`  
**Lifecycle:** Release Candidate source line; production activation remains unaccepted  
**Migration baseline:** `d9d3163cb4ac65a3c13984eabb0a0830a090695b`  
**Record purpose:** Significant product history, architecture/governance decisions, predecessor retirement, source-release lineage, client evolution, recovery/security milestones, and project-document migration provenance  
**Canonical authority:** This file becomes the repository-local project record once accepted on the default branch.

## Original project direction

GoreeCloud Notify was established as an original GoreeCloud-owned centralized notification-delivery service rather than a permanent ntfy fork.

The original project specification established the core direction:
- first-party producer authorization;
- native notification persistence and user Delivery state;
- human sessions and subscriptions;
- web-first notification inbox;
- controlled ntfy-compatible migration support;
- private publication;
- backup/restore;
- monitoring and independent outage alerting;
- later native clients;
- evidence-backed migration and production acceptance.

The active source has since evolved substantially, but these first-party and least-privilege boundaries remain controlling.

## Early Development — native web/service foundation

The initial development stack established a FastAPI backend, React/TypeScript/Vite frontend, SQLite/SQLAlchemy persistence, scoped producer identities, native notification ingestion, producer history, bounded ntfy-compatible publishing, human authentication, subscriptions, per-user Delivery fanout, read/acknowledgement state, CSRF-protected mutations, administration, retention preview, and source-controlled CI.

A long stacked PR line preserved early implementation history. Those historical branch heads remain provenance only after later integration into authoritative `main`.

## August 16, 2026 — v0.2.0 source integration and prerelease marker

The validated source line was integrated to authoritative `main` through the v0.2.0 release-candidate sequence and later published through a guarded source-release workflow.

The v0.2.0 tag/release was bound to source-freeze commit `dd22a7ad0765c8ca62b401749265594bb0a06e23` and published as a prerelease rather than production acceptance.

That source release used the MIT License. Copies already distributed under that license retain those grants.

The source-release marker established immutable repository provenance; it did not establish production activation.

## August 18, 2026 — security, privacy, identity, and acceptance hardening

Post-v0.2.0 source hardening added:
- Wardveil Security presentation and privacy-minimized request correlation;
- stronger browser isolation and security headers;
- canonical cross-platform application identity;
- production serving of canonical icon/manifest assets;
- separation of production configuration from release/acceptance state;
- source-bound target monitoring evidence;
- recovery verification decoupled from normal runtime database startup;
- target-production preflight v2;
- manual browser/OS acceptance contracts;
- target backup/restore evidence contracts;
- exact-candidate monitoring evidence;
- coherent pre-cutover evidence composition;
- request-body enforcement.

These source controls intentionally fail closed and do not convert synthetic/disposable evidence into real production acceptance.

## August 23, 2026 — native Linux and Android client integration

PR #80, **Add native Linux and Android clients and ntfy retirement path**, merged exact head `cc1aeabbb240b7deffc469b5df1ab27aeaff2653` as `30b17069d8a90e25974ef6198e92c70c1f44c238`.

This established the shared first-party Flutter Linux/Android client foundation:
- authenticated human-session reuse;
- platform-secure storage for session/CSRF state;
- inbox and SSE consumption;
- read/acknowledgement actions;
- system appearance;
- privacy-redacted operating-system notifications;
- Linux Debian packaging;
- Android acceptance APK generation.

The merge was source integration, not native-client production acceptance.

## August 27, 2026 — persistent Android delivery foundation

PR #85, **Add persistent Android notification delivery foundation**, merged as `3a5b00715bb3dfa501b8a9c2e071a1e3a046bf0b`.

The accepted source added Android lifecycle/background-delivery foundations, including bounded persistent delivery/replay behavior and platform-specific runtime support.

Representative physical-device acceptance, Doze/battery/restricted-app behavior, reboot/process-termination behavior, lock-screen privacy, production signing/distribution, and final Android release qualification remain separate acceptance gates.

## September 2, 2026 — AGPL-3.0-only relicensing

PR #99, **Relicense current GoreeCloud Notify source to AGPL-3.0-only**, merged exact candidate head `777b58b168016195cfa35cc8346909b5e12f7805` as `ade2996d2995ea6711d95e9058be9a2310cca057`.

Current and future GoreeCloud-owned source became `AGPL-3.0-only`.

The previously published MIT-licensed v0.2.0 source and copies already distributed under MIT retain their prior grants. Third-party dependencies retain their own licenses.

## September 18, 2026 — ntfy retirement and source reconciliation

ntfy was permanently retired from `goreecloud-vps-01` through the governed recovery-gated retirement process.

Its active container, stack, appdata, image, service publication, and related runtime integration were removed. The `notify.goreecloud.com` identity remains reserved for GoreeCloud Notify but ntfy is no longer the ordinary runtime or rollback service.

Retirement recovery evidence references Kopia snapshot `189b1dce96e3d222f7ba4ad9678a4d2b`, which passed verification and isolated restore checks before destructive cleanup.

Retirement does **not** establish Notify production acceptance.

## September 18–19, 2026 — post-retirement platform/source stabilization

PR #103, **Reconcile Notify after ntfy retirement and require Glaze UI 1.5.1**, merged as `7f76867ba650fc8a261bdca20832516af2f5e185`.

PR #104, **Adopt Glaze UI 1.5.1 presentation contract in Notify**, merged as `ac3777d20bdd850b3b42e810ab46048250643f3a`.

PR #105, **Reconcile Notify monitoring acceptance after ntfy and Uptime Kuma retirement**, merged as `ffb8ba907a35700bc5eb60cb3b7215764dab332b`.

Together these source integrations:
- reconciled the repository to predecessor retirement;
- established Platform Contract 0.4 / nine-system fail-closed evaluation;
- advanced then-current Glaze source adoption;
- updated monitoring acceptance to require an exact accepted Monitor revision;
- preserved independent Notify-down alerting;
- kept production acceptance false.

These 1.5.1 design-system checkpoints are now historical because later accepted source advanced to 1.6.0.

## September 19, 2026 — mandatory repository controls

PR #106, **Add mandatory Notify repository root controls**, merged as `510d8ae40d7d87bdacad436093671c69d4ca0d5f`.

It established the then-required repository-control baseline without changing runtime acceptance.

Later repository reconciliation corrected the canonical repository identity from the historical `GoreeCloud/goreecloud-notify` name to live `GoreeCloud/notify`.

## September 20, 2026 — repository identity and license metadata corrections

PR #108, **Correct Notify repository identity metadata**, merged as `eadcab8c736a2d8664144a7e12326f14b797297a`.

PR #109, **Align Notify release license metadata**, merged as `1d34789319088af919e2d979c2cfeb9a01360ddb`.

These corrections aligned machine-readable/current repository identity and current licensing metadata without rewriting historical source-release facts.

## September 24, 2026 — Git-native feature and changelog governance

PR #111, **Migrate Notify feature and changelog governance**, merged exact head `34ba9023e2295b87bec5b0ea34b7d6b87287dea1` as `c8a4272f9537351c800daa36a351b1255a3406a1`.

It established:
- `IMPLEMENTED-FEATURES.md`;
- `PLANNED-FEATURES.md`;
- `CHANGELOGS.md`;
- repository-local feature/change authority;
- retirement of the former synchronized roadmap/changelog authority model.

Routine feature state and chronology must remain in those records rather than being duplicated into this project record.

## September 24, 2026 — Glaze UI 1.6.0 source adoption

PR #112, **Stabilize Notify on Glaze UI 1.6.0**, merged exact candidate head `a5fa70dcfaea63877abb71d28dfc1a1eba16f7c0` as current migration baseline `d9d3163cb4ac65a3c13984eabb0a0830a090695b`.

The change:
- repinned web, Flutter Linux, and Flutter Android presentation contracts to Official Stable Glaze UI 1.6.0;
- bound current presentation mappings to immutable release/source/artifact provenance;
- updated Platform Contract evidence;
- preserved presentation-only authority;
- kept application conformance/production eligibility fail-closed.

Shared Glaze Stable status does not automatically establish Notify application acceptance.

## Current accepted source state

At migration baseline `d9d3163cb4ac65a3c13984eabb0a0830a090695b`, accepted source includes:
- native FastAPI/SQLite notification service;
- scoped producer identities and bounded compatibility ingestion;
- human users/sessions/administration;
- subscriptions and per-user Delivery fanout;
- authenticated inbox and Server-Sent Events;
- privacy-first browser notifications;
- security/privacy/observability hardening;
- source-controlled backup/recovery and exact-candidate evidence tooling;
- private production-runtime candidate;
- first-party Flutter Linux and Android clients;
- persistent Android delivery foundation;
- Platform Contract 0.4 nine-system evaluation;
- Git-native feature/changelog governance;
- Glaze UI 1.6.0 source mappings.

Notify remains a Release Candidate and is not production-accepted.

## Current production-acceptance boundary

Outstanding acceptance includes:
- final target runtime/image/filesystem verification;
- target SQLite backup and alternate-location restore;
- private Gateway/Caddy, DNS, NetBird, and network-path verification;
- accepted primary availability monitoring;
- independent Notify-down alerting;
- coherent exact-candidate issue #23/#24/#25/manual acceptance evidence;
- active producer migration to scoped Notify identities;
- long-lived realtime/session/network interruption behavior on the final target path;
- representative manual browser/OS acceptance;
- Linux native acceptance where required;
- representative Android lifecycle/device/power/privacy/signing acceptance;
- remaining Integral Platform System acceptance;
- rollback/recovery exercise;
- explicit production activation approval.

Source integration, a source prerelease, and predecessor retirement do not substitute for those target gates.

## Repository protection gap

At this migration baseline, GitHub reports `main` as unprotected with no active rulesets. GitHub issue #113 tracks branch-protection and required-check remediation.

The connected GitHub application does not expose branch-protection/ruleset mutation, so this record must not claim protection is enforced.

## September 25, 2026 — Project specifications/project record migration candidate

**Migration branch:** `docs/project-governance-migration-20260925` → `main`

This migration:
- creates root `PROJECT-SPECIFICATIONS.md`;
- creates root `PROJECT-RECORD.md`;
- reconciles the complete active Drive **Project Specification — Notify.docx** with current accepted repository state;
- corrects the historical repository identity to live `GoreeCloud/notify`;
- reconciles historical ntfy/Uptime Kuma/current-service language against verified retirement state;
- reconciles the design-system requirement to accepted current Glaze UI 1.6.0 source authority;
- preserves significant historical milestones without turning old candidate heads into current authority;
- updates README project-governance and stale Glaze wording; and
- retires root `SPECIFICATIONS.md` on the migration branch only after its still-relevant content is incorporated.

**Drive source:** Project Specification — Notify.docx  
**Drive file ID:** `1SguKQgzrTnKM1HF_qsyv1-2EP-IOiJYs`  
**Drive deletion status:** **Blocked.** The source must remain until this migration is reviewed as required, accepted on `main`, read back from the authoritative default branch, verified complete, and free of unresolved reconciliation discrepancies.

The archived Drive source **Project Specification — Notify** (file ID `1Uhca09M1TfelcGRfWTDcOQjXLiAxjo0QuunDEw-qU-o`) remains historical migration input only and must not override the active source or current repository state.

## Ongoing maintenance

Update this record for significant architecture, authorization, repository identity, licensing, client-platform, storage, security/privacy, recovery, production activation, migration, incident, platform-integration, lifecycle, predecessor-retirement, or eventual Notify-retirement events.

Routine feature/change chronology remains in `CHANGELOGS.md`; current feature inventory remains in `IMPLEMENTED-FEATURES.md` and `PLANNED-FEATURES.md`.
