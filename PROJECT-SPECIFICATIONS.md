# GoreeCloud Notify — Project Specifications

**Repository:** `GoreeCloud/notify`  
**Former repository identity in the Drive source:** `GoreeCloud/goreecloud-notify`  
**Project type:** First-party centralized notification-delivery application and service  
**Lifecycle:** Release Candidate source line; production activation remains unaccepted  
**Version:** `0.2.0`  
**Migration baseline:** `d9d3163cb4ac65a3c13984eabb0a0830a090695b`  
**License:** `AGPL-3.0-only` for current and future GoreeCloud-owned source; copies previously distributed under MIT retain their prior grants  
**Owner:** GoreeCloud  
**Intended users:** GoreeCloud administrators, approved service producers, and authorized web/Linux/Android users  
**Deployment model:** Private Docker and Docker Compose service with FastAPI, SQLite persistent state, React/TypeScript web client, and first-party Flutter Linux/Android clients  
**Supported platforms:** Web, Linux, Android, and server runtime  
**Canonical authority:** This file becomes the authoritative project specification once accepted on the default branch.

## Migration and precedence

This file consolidates the former root `SPECIFICATIONS.md` with still-applicable requirements and historical context from Google Drive **Project Specification — Notify.docx** (file ID `1SguKQgzrTnKM1HF_qsyv1-2EP-IOiJYs`).

The Drive source contains normative requirements plus extensive exact-revision development and migration history. Normative/current requirements are reconciled here. Significant project history belongs in `PROJECT-RECORD.md`; detailed implementation chronology remains in `CHANGELOGS.md`, Git history, issues, pull requests, releases, and accepted evidence records.

Current verified repository/runtime state controls factual implementation claims. Historical source references to `GoreeCloud/goreecloud-notify`, ntfy as active production runtime, Uptime Kuma as current monitoring authority, earlier Glaze UI versions, or superseded candidate branches do not override accepted current `main`.

Current feature state is governed by `IMPLEMENTED-FEATURES.md`; remaining work by `PLANNED-FEATURES.md`; release/change chronology by `CHANGELOGS.md`.

## 1. Product role and purpose

GoreeCloud Notify is GoreeCloud's first-party centralized notification-delivery application and service.

Notify receives approved operational and application notifications, authorizes scoped producers, persists notification and per-user delivery state, routes notifications through approved user subscriptions/preferences, provides authenticated realtime inbox delivery, and presents notifications through approved web and native clients.

Notify is responsible for notification delivery. It does not replace the systems that detect outages, security conditions, backup failures, application events, or other source conditions.

The retired ntfy service is historical/recovery and migration context only. Its retirement does not by itself establish Notify production acceptance.

## 2. Development model and product boundaries

Notify is original GoreeCloud-owned software rather than a permanent ntfy fork or rebranded upstream application.

Narrow protocol/runtime/security foundations may be used where appropriate, but the product architecture, authorization model, data model, client experience, migration model, and lifecycle direction remain first-party GoreeCloud responsibilities.

Notify must not become:
- the sole source of operational truth;
- a monitoring system;
- the sole critical-outage reporting path;
- a substitute for producer-side authorization;
- a general message broker unrelated to notification delivery; or
- an unrestricted compatibility clone of ntfy.

The bounded ntfy-compatible ingestion path exists only to support controlled producer migration.

## 3. Current architecture

The accepted source architecture includes:

- **FastAPI backend**
  - human session APIs;
  - producer/service identity APIs;
  - native notification ingestion;
  - bounded ntfy-compatible ingestion;
  - notification history;
  - per-user Delivery state;
  - subscriptions;
  - administration and audit;
  - authenticated Server-Sent Events;
  - metadata and health.
- **SQLite persistent application store**
  - users and administrative authority;
  - web sessions;
  - service identities/tokens;
  - sources/channels/subscriptions;
  - notifications and Deliveries;
  - audit/security state;
  - migration state.
- **React / TypeScript / Vite web client**
  - authenticated inbox;
  - search/filtering;
  - subscription management;
  - read/unread and acknowledgement;
  - realtime updates;
  - appearance and accessibility behavior;
  - privacy-first browser alerts.
- **First-party Flutter Linux and Android clients**
  - authenticated inbox;
  - SSE/replay integration;
  - read/acknowledgement actions;
  - platform-secure session storage;
  - system appearance;
  - privacy-minimized operating-system alerts.
- **Private production publication**
  - approved private DNS;
  - NetBird/private source path;
  - Gateway/Caddy-controlled HTTPS path until Gateway authority changes;
  - Docker `proxy` network;
  - no public backend host port.

## 4. Core data and identity model

First-class entities include, as applicable:
- User;
- WebSession;
- ServiceIdentity;
- AccessToken / producer credential;
- Source;
- Channel;
- Subscription;
- Notification;
- Delivery;
- Preference;
- administrative/security audit state.

Human sessions and producer credentials are separate authorization domains.

Producer identities must be individually scoped and least privilege. Reusable credentials must be represented through protected issuance/storage boundaries and must not be exposed through ordinary logs, exports, documentation, or client APIs.

## 5. Native producer API and compatibility ingestion

Notify provides a versioned native API for approved notification producers.

Producer publishing must be:
- authenticated;
- scoped to authorized source/channel ownership;
- bounded by request-size and validation limits;
- resistant to ambiguous or malformed input;
- idempotency-aware where the contract supports replay;
- privacy-minimized in logs/evidence.

The legacy-compatible `/{topic}` publishing surface is deliberately constrained. Compatibility behavior must never weaken authentication, authorization, input validation, request-size controls, or service-identity boundaries.

## 6. Human authentication, inbox, and subscriptions

Human users are administrator-provisioned unless a separately accepted identity/recovery model expands that boundary.

Requirements include:
- strong password hashing;
- opaque server-side sessions;
- secure cookie/session behavior;
- CSRF protection for human mutations;
- user deactivation/session revocation;
- administrator authorization with attributable actions;
- bounded login abuse/rate controls;
- administrator-controlled password reset/recovery;
- strict per-user Delivery isolation.

Users may manage approved channel subscriptions. Subscription changes affect future fanout and must not silently delete existing Delivery history.

The inbox must support bounded history, search/filtering, read/unread state, acknowledgement where applicable, pagination, and authoritative server-backed state.

## 7. Realtime delivery

Authenticated Server-Sent Events provide the current first-party realtime inbox path.

Realtime behavior must preserve:
- authenticated session validation;
- persisted replay cursor semantics;
- bounded reconnect behavior;
- offline/reconnect recovery;
- authoritative inbox/count state;
- multi-tab consistency protections;
- fail-closed behavior after session invalidation;
- privacy-safe keepalive and event payload handling.

Long-lived realtime behavior through the final target HTTPS path requires target acceptance and is not established solely by source tests.

## 8. Browser and operating-system alerts

Browser/system notification presentation is explicit opt-in.

System alerts must:
- request permission only after intentional user action;
- use generic privacy-redacted text by default;
- avoid silently exposing notification body/title/source/channel on a lock screen or operating-system surface;
- suppress duplicate foreground alerts where appropriate;
- remain fail-soft when browser permission/storage APIs are unavailable;
- avoid alert storms during replay/backlog recovery.

Manual browser/operating-system acceptance remains separately required.

## 9. Native Linux and Android clients

Notify maintains a shared first-party Flutter client for Linux and Android.

Linux packaging must remain traceable and reproducible for the approved distribution format.

Android delivery requires:
- secure platform storage for session state;
- explicit notification permission;
- privacy-safe notification presentation;
- bounded replay/reconnect behavior;
- lifecycle handling across backgrounding;
- controlled recovery after process/device restart;
- signing/distribution acceptance.

Accepted source includes persistent Android delivery foundations, but representative physical-device behavior, power-management/Doze/restricted-app conditions, reboot/process-termination behavior, lock-screen privacy, and production signing remain acceptance-gated.

iOS is not part of the currently accepted supported-platform set and requires separate architecture, signing, transport, privacy/security, maintenance, and acceptance work before inclusion.

## 10. Security requirements

Notify is private by default.

Requirements include:
- authenticated administrative access;
- scoped producer authorization;
- CSRF-protected human mutations;
- strong password/session controls;
- trusted-proxy validation;
- bounded login throttling;
- bounded request-body enforcement before application parsing;
- input normalization/validation;
- least-privilege non-root runtime;
- read-only root filesystem where applicable;
- dropped Linux capabilities;
- no-new-privileges;
- protected production configuration;
- secure transport;
- dependency/container vulnerability review;
- exact build-revision identity;
- privacy-safe structured error/request correlation.

Wardveil Security presentation must not manufacture technical security state. Underlying application/runtime controls remain authoritative.

## 11. Privacy requirements

Notification content can contain sensitive operational or personal information.

Notify must minimize routine evidence and must not expose reusable credentials, session values, CSRF values, authorization headers, raw sensitive notification bodies, private keys, protected environment values, or unnecessary client/network metadata through logs, monitoring evidence, error responses, or documentation.

Private/authenticated responses should remain non-cacheable unless a narrowly approved static/identity resource contract requires otherwise.

Browser/native operating-system alert content must remain privacy-minimized.

Privacy Shield source adapters do not establish accepted central/runtime Privacy Shield integration.

## 12. Storage, retention, export, and portability

SQLite is the current authoritative application database for the accepted server architecture.

Retention must be explicit, bounded, understandable, and recoverable. Destructive retention behavior must have accepted policy, authorization, backup/recovery, scheduling, cascade, and failure semantics.

Notify should provide understandable migration/export paths for supported configuration and user-facing state without exporting active reusable credentials.

Data must remain portable enough to restore or migrate Notify without undocumented proprietary dependencies.

## 13. Backup, restore, and recovery

Production acceptance requires a real target backup/recovery design that proves:
- authoritative database path and restrictive ownership/permissions;
- consistent SQLite snapshot creation;
- protected backup repository separate from primary runtime/application storage;
- independently recoverable backup credentials;
- defined frequency/RPO and retention;
- failed/missed-backup monitoring through a separate failure domain;
- exact candidate revision and migration revision;
- integrity and foreign-key validation;
- alternate-location non-destructive restore;
- measured recovery duration;
- restored application-state validation;
- restored security-state reconciliation.

Restored web sessions must not silently become current authority. Producer-token/user/admin/recovery/security state must be reconciled against current authoritative identity state.

The retired ntfy runtime is not the ordinary rollback target. Rollback/recovery must use an accepted prior Notify revision/data/configuration unless separately authorized otherwise.

## 14. Monitoring and independent outage alerting

GoreeCloud Monitor is the intended primary GoreeCloud availability-monitoring consumer only after Monitor is independently accepted for that role.

Notify production acceptance requires:
- final private HTTPS `/healthz` monitoring;
- concrete live retry/timeout behavior;
- approved notification assignment;
- controlled DOWN then RECOVERED evidence;
- approved administrator receipt;
- evidence bound to the exact Notify revision under acceptance; and
- a separately tested Notify-down path in a materially independent failure domain that depends on neither Notify nor the same runtime host.

Notify must never depend on itself as its only failure-reporting mechanism.

## 15. Glaze UI and product identity

The current official Stable design-system baseline is **Glaze UI 1.6.0**.

Accepted `main` carries repository-local Glaze UI 1.6.0 source mappings for web, Flutter Linux, and Flutter Android with immutable release provenance. This is presentation/source adoption, not whole-application or production acceptance.

Notify-specific acceptance requires representative:
- web accessibility and keyboard behavior;
- screen-reader behavior;
- 200% zoom/reflow;
- Auto/Light/Dark behavior;
- responsive task continuity;
- realtime/multi-tab behavior;
- browser permission lifecycle;
- operating-system notification privacy;
- Linux client acceptance;
- Android physical-device/lifecycle acceptance;
- performance;
- rollback;
- governed consumer evidence;
- Human Visual Excellence review.

The canonical Notify application icon must remain one recognizable product identity across web/installable web/Linux/Android, with only platform-required masking, monochrome, safe-area, or rasterization adaptations.

## 16. Integral Platform Systems

Notify evaluates all nine Integral Platform Systems fail-closed.

Current repository evidence records:
- **Manager:** applicable; accepted integration incomplete.
- **Privacy Shield:** source adapter candidate; runtime/central acceptance incomplete.
- **Wardveil Security:** source adoption evidence exists; target/runtime acceptance incomplete.
- **Everkeep:** source recovery-policy/evidence exists; target restore acceptance incomplete.
- **Glaze UI:** 1.6.0 source adoption; application acceptance incomplete.
- **Mesh:** applicable; accepted integration incomplete.
- **Identity:** applicable; local application authentication is not equivalent to accepted GoreeCloud Identity integration.
- **Policy:** applicable; accepted decision/enforcement coordination incomplete.
- **Observability:** application-local evidence exists; accepted shared integration incomplete.

Names, badges, metadata, or documentation-only declarations do not satisfy integration.

## 17. Deployment and private publication

Production deployment uses the source-controlled Docker/Compose contract.

The target must preserve:
- exact approved image/build revision;
- protected production environment/configuration;
- persistent `/data` storage;
- non-root runtime identity;
- read-only runtime filesystem except approved writable paths;
- dropped capabilities;
- no-new-privileges;
- bounded process resources;
- no public application host port;
- approved Docker network attachments only;
- private DNS and private-network publication;
- HTTPS through the approved central gateway path.

Production-mode configuration cannot self-promote the product lifecycle. Release stage and production acceptance are separate authorities.

## 18. Testing and acceptance

Automated/source validation must cover, as applicable:
- backend tests and database migrations;
- frontend lint/type/build;
- browser/accessibility automation;
- realtime/replay behavior;
- dependency and license closure;
- request limits/security controls;
- recovery tooling;
- production image/build identity;
- least-privilege Compose topology;
- monitoring readiness;
- native Linux/Android builds;
- Platform Contract validation.

Source automation does not prove target production acceptance.

Production acceptance additionally requires coherent exact-candidate evidence for:
- target backup/restore;
- target runtime/private publication;
- independent monitoring/outage alerting;
- manual browser/OS/native acceptance;
- active-producer migration;
- rollback/recovery;
- remaining platform-system acceptance;
- explicit production approval.

## 19. Current accepted implementation boundary

At migration baseline `d9d3163cb4ac65a3c13984eabb0a0830a090695b`, accepted `main` includes:
- FastAPI + SQLite notification service;
- scoped producer identities and native/compatibility publishing;
- human users/sessions/administration;
- subscriptions and per-user Delivery fanout;
- authenticated inbox and SSE;
- privacy-first browser alerts;
- source-controlled backup/restore and target evidence tooling;
- private production-runtime candidate;
- Wardveil/privacy/observability source hardening;
- canonical cross-platform Notify identity;
- first-party Flutter Linux/Android client;
- persistent Android delivery foundation;
- Platform Contract 0.4 nine-system evaluation;
- Git-native feature/changelog governance;
- Glaze UI 1.6.0 source mappings.

Notify remains Release Candidate / non-production. No production acceptance is implied by source integration or by ntfy retirement.

## 20. Maintenance and retirement

Significant architecture, authorization, repository identity, licensing, client-platform, compatibility, storage, security/privacy, recovery, platform-integration, lifecycle, deployment, incident, or retirement decisions must update `PROJECT-RECORD.md`.

Routine feature/change chronology belongs in `CHANGELOGS.md`; current feature inventory belongs in `IMPLEMENTED-FEATURES.md` and `PLANNED-FEATURES.md`.

## Related repository documentation

- [README.md](README.md)
- [PROJECT-RECORD.md](PROJECT-RECORD.md)
- [IMPLEMENTED-FEATURES.md](IMPLEMENTED-FEATURES.md)
- [PLANNED-FEATURES.md](PLANNED-FEATURES.md)
- [CHANGELOGS.md](CHANGELOGS.md)
- [FEATURES.md](FEATURES.md)
- [SECURITY.md](SECURITY.md)
- [PRIVACY POLICY.md](PRIVACY%20POLICY.md)
- [USER-MANUAL.md](USER-MANUAL.md)
- [goreecloud.platform.yaml](goreecloud.platform.yaml)
