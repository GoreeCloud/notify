# GoreeCloud Notify capability register

This is the implementation status of the requested native GoreeCloud Notify platform, not a claim of shipping all proposed features.

| Capability | Status (2026-11-03) | Notes |
| --- | --- | --- |
| Native GoreeCloud notification server | **Implemented (alpha)** | Original Go stdlib service |
| Topic-based messaging | **Implemented (alpha)** | Publish and subscribe by topic |
| Durable notifications and offline retrieval | **Implemented (alpha)** | Single-server JSONL; fail-closed storage errors, crash-conscious compaction, offline integrity checker |
| Streaming delivery | **Implemented (alpha)** | Authenticated SSE; 4 simultaneous streams per token, 64 total; capacity reclaimed on disconnect |
| Authenticated API and topic permissions | **Implemented (alpha)** | Admin + hashed subscriber/publisher tokens |
| Title, body, priority, tags, clickable URL | **Implemented (alpha)** | Strict JSON validation |
| Notification deduplication | **Implemented (alpha)** | Explicit persistent idempotency key |
| Web notification dashboard | **Implemented (alpha)** | Native responsive browser UI; no OS push |
| Health, readiness and metrics | **Implemented (alpha)** | Local endpoints |
| Container package, tests, CI definition | **Implemented (alpha)** | CI runtime results must be verified on GitHub |
| Scheduled and recurring delivery | **Planned** | Persistent scheduler and cancellation |
| Attachments and object storage | **Planned** | Authenticated media pipeline |
| User accounts, OIDC/SSO, MFA | **Planned** | GoreeCloud Identity integration |
| API tokens created/revoked at runtime | **Planned** | Admin lifecycle, audit log |
| Notifications updates, delete, acknowledgment | **Planned** | Controlled state transitions |
| Mobile native Android/iOS apps | **Planned** | Needs platform SDK and push gateways |
| Browser Web Push / PWA | **Planned** | Requires VAPID and subscriptions |
| UnifiedPush / FCM / APNs | **Planned** | External gateways with provider constraints |
| Email, SMS, voice gateways | **Planned** | Extensible adapters; SMS/voice incur cost |
| Webhooks, rules, routing and escalations | **Planned** | Security policy and rate limits first |
| Federation, distributed storage, HA | **Research** | Avoid unsupported exactly-once claims |
| AI assistance and intelligent filtering | **Future** | Privacy controls and human oversight |
| Enterprise organizations and audit | **Future** | Identity/tenant boundary design |
| ntfy protocol compatibility | **Optional future integration** | Not part of core, no ntfy runtime dependency |

## Next priority order

1. Security hardening: network rate limits, token lifecycle, audit and TLS reference deployment.
2. Persistence reliability: expand injected disk-failure/power-loss tests, add controlled restore tooling, expiration tests and larger-volume benchmarks; offline verifier now available.
3. Delivery lifecycle: scheduler, cancellation, update/clear/delete with controlled concurrency.
4. OS notifications: Web Push/PWA, UnifiedPush and native mobile clients.
5. Integrations: GoreeCloud Identity, service accounts, webhooks, email/SMS/voice adapters, routing and escalation.
6. Multi-tenant management, clustering, observability, optional intelligence.
