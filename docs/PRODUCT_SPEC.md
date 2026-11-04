# GoreeCloud Notify — Product specification

**Document class:** Founder-directed target product capabilities. **Product:** Original native GoreeCloud Notify service. **Implementation authority:** Verified repository source/tests, not this specification. **Status:** Roadmap/requirements, with a separately tracked functional alpha.

GoreeCloud Notify aims to unify notification publishing, event distribution, actionable alerts, delivery orchestration, and self-hosted operations across people, devices, applications, and GoreeCloud services. This specification preserves the broad product vision while clearly separating intended capabilities from verified functionality. For what actually works today, see [FEATURES.md](FEATURES.md); for the implemented API, see [API.md](API.md).

## 1. Core notification and messaging

Topic-based pub/sub; one-to-one, one-to-many and many-to-many delivery; authorized topic creation and ownership; private/shared/hierarchical channels; cross-device subscriptions; real-time message IDs, metadata, caching, replay, retention, and lifecycle management. Support person-to-person, system-to-person, and system-to-system events.

## 2. Rich content and presentation

Custom title, Unicode/multiline body, Markdown rendering with sanitization, tags/emoji, icons, images, timestamps, source identity, links, custom payload metadata, JSON schemas, localization, templates, preview, grouping, and threads. Never render untrusted content as executable HTML.

## 3. Priority and urgency

Five levels: minimum (1), low (2), normal (3), high (4), critical (5). Add device sounds, channels, filtering, quiet hours, interruption policy, retention rules, digests, and authorized critical escalations.

## 4. Interactive actions

Authenticated action buttons, HTTPS requests, deep links, clipboard actions, native platform intents, acknowledgment, snoozing, resolution and approval/rejection actions. Sensitive actions require fresh authorization, anti-replay controls, and audit records.

## 5. Scheduling and lifecycle

Immediate, delayed, recurring and timezone-aware delivery; absolute/relative schedules; update, cancel, clear, delete, archive, read/unread, acknowledgment, snoozing, and replay operations; configurable expiration and notification batching.

## 6. Attachments and media

Secure file uploads, external links, images/video/audio/documents/logs, previews, download authorization, MIME validation, checksums, antivirus integration, local/S3-compatible storage, quotas, retention, and encrypted-attachment option.

## 7. Publishing APIs

Versioned JSON/HTTP POST/PUT APIs, input validation, authentication, idempotency keys, structured errors, upload endpoints, client SDKs, OpenAPI schemas, correlation identifiers, and API compatibility policies. Legacy protocol adapters should remain optional and isolated.

## 8. Real-time subscriptions

SSE, JSONL streaming, WebSockets, polling, topic aggregation, subscriber filtering, replay from cursors/time, backpressure limits, keepalives, reconnection, explicit delivery guarantees, and subscription revocation.

## 9. Command-line and scripting

Native `goreecloud-notify` CLI for publish, subscribe, status, history, schedule, user/token administration, process-completion alerts, cron/systemd integration, configuration profiles, JSON output, and documented exit codes.

## 10. Android

Native Android client with subscriptions, background notifications, priority channels, action buttons, battery-conscious reconnect, Android Sharesheet/intents, Tasker/MacroDroid, UnifiedPush option, certificate support, accessibility, offline state, and GC UI design.

## 11. iOS and iPadOS

Native Apple client with APNs-compatible gateway, topic subscriptions, media previews, Quick Look, account/session controls, supported actions, notification grouping, background behavior documentation, accessibility, and platform-specific privacy controls.

## 12. Web and Progressive Web App

Premium GC UI responsive dashboard, installable PWA, notifications feed, composer, browser Web Push, offline-aware state, search/filter, badge counts, actions, onboarding, account preferences, accessibility and localization.

## 13. Desktop and Linux

Linux/Windows/macOS desktop notification pathways, background client, autostart, clipboard/shortcut support, file opening, system-tray option, native packaging where warranted, keyboard navigation, and secure credential storage.

## 14. Push infrastructure

Web Push/VAPID, UnifiedPush, FCM, APNs, Matrix-compatible push gateway, application registration, stale-subscription cleanup, gateway retries, provider metrics, and minimum external-service dependencies.

## 15. Identity and access

GoreeCloud Identity integration, user registration/recovery, MFA/SSO/OIDC, service accounts, credential rotation, role-based and topic-scoped access, wildcard restrictions, user/team permissions, sessions, explicit deny policies and audit trails.

## 16. Privacy and security

Privacy-first self-hosting, TLS/mTLS, optional application-level E2EE, encryption-at-rest integration, least privilege, secret management, log redaction, secure webhook signatures, replay protection, file scanning, access review, rate limiting, Zero Trust/VPN readiness, and explicit retention controls.

## 17. Email delivery

SMTP send/receive, email-to-topic and topic-to-email, templates, verified identities, delivery reports, retries, quotas, TLS, attachment linking and provider-independent configuration.

## 18. SMS, voice, and telephone

Provider-pluggable SMS, phone verification, text-to-speech calls, critical escalation, call templates, retry policy, compliance controls, spend limits and explicit opt-in. External costs and legal requirements must be considered before enabling.

## 19. Webhooks and ingestion

Inbound/outbound webhook endpoints, source authentication, HMAC verification, replay protection, JSON transformation, schema normalization, SSRF defenses, delivery retries, events from monitoring/CI/services, audit traces, and integration adapters.

## 20. Templates and transformation

Reusable safe templates, structured payload mapping, conditionals, string/number/date formatting, variables, preview, versioning, shared libraries, bounded execution and localization.

## 21. Intelligent routing

Rule-based routing by topic, source, priority, user, device, location consent, team, quiet hours, maintenance windows, and delivery availability. Include escalation policies, fallback channels, grouping, deduplication, alert-storm suppression, digests, and routing simulation.

## 22. Optional AI intelligence

Privacy-preserving summarization, classification, alert correlation, anomaly detection, suggested actions, natural-language history, routing recommendations, translation, and explainable event triage. Human review for high-impact actions.

## 23. Automation and workflows

API/webhook-driven triggers, authorized task and workflow actions, completion/error alerts, multi-step conditions, retries, external automation adapters, failure escalation, auditability and GoreeCloud workflow integration.

## 24. Infrastructure and DevOps integrations

Monitoring from GitHub Actions, CI/CD, Docker, Kubernetes, systemd, cron, Prometheus/Grafana, Uptime Kuma, Gatus, Netdata, Healthchecks, Proxmox, storage, DNS/VPN, security, backups, deploys and certificate monitors through verified integration contracts.

## 25. GoreeCloud ecosystem

Notification events and cross-service links for Identity, Vault, Backup, Sync, VPN, DNS, Location, Search, Workspace/Teams and GC UI. Integrate only against verified APIs; preserve location consent and prevent secret disclosure through notification content.

## 26. Unified notification center

Cross-application inbox, topics and favorites, filters/search, priority badges, history, grouped events, read/unread, pin/snooze/archive/dismiss/delete, bulk actions, digest settings, device subscriptions, preference control and accessible layouts.

## 27. Self-hosted deployment

First-class Linux binary, systemd, Docker/Compose, ARM/x86 builds, private networking, TLS reverse proxy, config validation, healthchecks, multiple listeners where appropriate, upgrades, backup/restore, reproducible packages and minimal privilege.

## 28. Databases and retention

Small-instance embedded persistence, optional PostgreSQL for scaling, connection pooling, read replicas where justified, retention tier policy, encryption, migration/rollback, durable scheduling, attachment storage, housekeeping, backup verification and restore drills.

## 29. High availability and scale

Load balancing, multi-node fan-out, consistent authorization, shared durable storage, leader coordination for singleton jobs, bounded caches, reconnect recovery, cluster observability and tested failure recovery. Never claim clustering is ready without fault-injection validation.

## 30. Delivery reliability

Retries/backoff, delivery attempts and receipts where transport allows, explicit at-most/at-least-once semantics, deduplication, idempotency, queue saturation controls, per-channel status, dead-letter handling, fallback delivery and end-to-end tests.

## 31. Administration

Central management of users, tokens, topics, roles, subscriptions, delivery gateways, quotas, abuse controls, configuration, health, backup, audit events, service settings and organizational delegation.

## 32. Rate limiting and quotas

Per-user/service/token/IP limits, topic creation quotas, subscriber connection limits, message size and attachment storage/bandwidth caps, channel-specific sending policies, Retry-After headers, durable usage tracking, reporting, optional billing integration and abuse mitigation.

## 33. Monitoring and observability

Health/readiness, Prometheus metrics, structured logs, OpenTelemetry, traces, delivery/latency/error statistics, resource usage, gateway status, storage performance, cluster metrics, audits, Grafana dashboards and diagnostic exports.

## 34. Personal, household, team, enterprise

Personal workspaces, family groups, teams, organizations, tenant isolation, invitations, delegated administrators, shared/private topics, provisioning, SSO, compliance-supporting retention/audit, data residency and billing boundaries where applicable.

## 35. Developer extensibility

SDKs, API schemas, streaming clients, CLI, test fixtures, mock endpoints, integration guides, provider plugins, custom event transformers, semantic versioning and stable compatibility policy.

## 36. GoreeCloud UI and accessibility

Adopt `GoreeCloud/gc-ui` as sole design authority: semantic tokens, consistent responsive navigation, sophisticated composition, visible focus, keyboard/screen-reader support, accessible contrast, dark/light modes, reduced motion, localization and high-quality empty/error states. Require visual acceptance, not just technical tests.

## 37. Source independence and interoperability

Own the native GoreeCloud implementation and interfaces, keep data portable, avoid unnecessary proprietary runtime dependencies, support standards-based protocols, published source, migration paths, auditable supply chain and a founder-approved explicit license before calling the project licensed open source.

## 38. Future extensions

Optional federation, edge gateways, multi-region operation, end-to-end encrypted conversation threads, automated disaster recovery, policy simulation, secure approvals, advanced incident orchestration and AI-assisted troubleshooting.

## 39. Architectural principles

Privacy by design; secure defaults; local-first, self-hostable core; versioned APIs; modular services; explicit event ordering; transparent delivery semantics; maintainability; accessibility; interoperable adapters; authorized automation; reproducible verification and reversible operations.

## 40. Platform vision

One secure, unified, intelligent, modular and self-hosted notification infrastructure for GoreeCloud users, devices, services and future integrations, with a polished, consistent GC UI experience.

---

## Delivery and acceptance policy

Every proposed capability transitions through **planned → implemented → locally tested → integration tested → reviewed → release-ready → deployed** as independently verified. Requirements in this document are not claims of implementation. Do not infer native Android/iOS app availability, public service deployment, provider credentials, high availability, end-to-end encryption or critical alert guarantees from the vision alone.

**Current verified baseline:** See [FEATURES.md](FEATURES.md), [API.md](API.md), and the repository's GitHub Actions checks. **Next priorities:** [security](https://github.com/GoreeCloud/notify/issues/1), [persistence](https://github.com/GoreeCloud/notify/issues/2), [lifecycle](https://github.com/GoreeCloud/notify/issues/3), [mobile push](https://github.com/GoreeCloud/notify/issues/4), and [integrations](https://github.com/GoreeCloud/notify/issues/5).