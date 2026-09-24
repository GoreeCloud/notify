# GoreeCloud Notify — Implemented Features

**Record type:** Repository implemented-feature authority  
**Repository:** `GoreeCloud/notify`  
**Lifecycle:** Release Candidate source line; production acceptance remains false  
**Evidence baseline:** `1d34789319088af919e2d979c2cfeb9a01360ddb` and later commits merged through this repository

## Authority boundary

This file records capabilities verified in the current source line. It does not by itself establish target deployment, production activation, application-specific platform-system acceptance, or Stable qualification.

## Backend and delivery

- Versioned GoreeCloud Notify API under `/api/v1`.
- Scoped producer identities and authenticated producer publishing.
- Bounded authenticated ntfy-compatible producer migration endpoint.
- SQLite-backed durable notification, delivery, account, session, audit, and security state.
- User inbox delivery, read/unread state, acknowledgement state, and subscription fanout.
- Authenticated Server-Sent Events with persisted replay cursors and reconnect recovery.
- Health endpoint, release metadata, target-preflight support, and source-controlled production-readiness contracts.
- SQLite backup/restore, integrity verification, migration validation, and restored-session invalidation.
- Privacy-minimized structured request observability and hardened browser/security response policy.

## Web application

- React/TypeScript authenticated inbox.
- Search, filtering, cursor pagination, subscription, and preference workflows.
- System/Light/Dark presentation.
- Browser system-alert integration with explicit opt-in and generic redacted operating-system content.
- Responsive Glaze UI **1.5.1 source-adoption candidate** with browser/accessibility automation.
- Reduced Motion, Reduced Transparency, contrast, and Forced Colors presentation handling.
- Current source remains a 1.5.1 adoption candidate; current shared Stable Glaze UI 1.6.0 reconciliation is tracked separately and is not claimed here.

## Native clients

- Flutter Linux and Android client source.
- Secure local session storage.
- Android persistent/system alert capability flow.
- Glaze UI **1.5.1 native source-adoption candidate**.
- Native accessibility/context presentation mapping.
- Linux and Android CI build/test coverage.

## Operational, privacy, security, and release controls

- Reproducible production image and least-privilege Compose runtime contract.
- No-production-claim release metadata with immutable build-revision handling.
- Private-publication acceptance runbook and read-only target preflight tooling.
- Source-controlled monitoring readiness and independent Notify-down alerting requirement.
- Wardveil Security source-adoption evidence.
- Privacy Shield source adapter candidate.
- Everkeep source acceptance-policy candidate.
- Platform Contract 0.4 declaration covering all nine Integral Platform Systems.
- CI covering backend/frontend, browser accessibility, native clients, monitoring readiness, production readiness, and Platform Contract validation.
- Current AGPL-3.0-only source license metadata, while preserving the historical MIT grant for published v0.2.0 source.

## Acceptance still open

The following are not implemented production acceptance claims and remain controlled by `PLANNED-FEATURES.md` and the linked GitHub issues:

- current Glaze UI 1.6.0 repository-local adoption and downstream acceptance;
- live VPS activation and final private Gateway/DNS/NetBird publication;
- target backup/restore evidence;
- accepted GoreeCloud Monitor deployment and independent out-of-band Notify-down delivery;
- migration of actually active producers;
- representative Android background-delivery and signing acceptance;
- remaining Integral Platform System acceptance;
- final manual browser/OS/native acceptance;
- explicit production-activation approval and Stable qualification.
