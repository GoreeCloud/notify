# GoreeCloud Notify — Current Features

**Document Internal Version Number:** 2026.09.18.1  
**Document External Version Number:** 1.0.0  
**Status:** Current implemented-source feature record  
**As of:** September 18, 2026

## Purpose

This file is the product capability overview. Evidence-backed implementation authority lives in `IMPLEMENTED-FEATURES.md`, while planned or recommended work belongs in `PLANNED-FEATURES.md`.

A feature listed here is not automatically production-accepted.

## Implemented backend and delivery features

- Versioned GoreeCloud Notify API under `/api/v1`.
- Scoped producer identities and authenticated producer publishing.
- Bounded authenticated ntfy-compatible producer migration endpoint.
- SQLite-backed durable notification, delivery, account, session, audit, and security state.
- User inbox delivery and read/acknowledgement state.
- Subscription fanout.
- Authenticated Server-Sent Events inbox stream.
- Delivery replay/reconnection support tied to authoritative delivery state.
- Health endpoint at `/healthz`.
- Release metadata and target-preflight support.
- Backup/restore and migration tooling.
- Source-level security and privacy-minimized observability controls.

## Implemented web features

- React/TypeScript authenticated inbox.
- Subscription and preference workflows.
- System/Light/Dark appearance support.
- Browser system-alert integration with explicit user permission flow.
- Foreground/replay-aware notification presentation controls.
- Responsive Glaze UI 1.5.1 source-adoption candidate.
- Reduced Motion, Reduced Transparency, contrast, and Forced Colors presentation handling.
- Accessibility/browser automated validation coverage.

## Implemented native-client features

- Flutter Linux client source.
- Flutter Android client source.
- Secure local session storage.
- Android persistent/system alert capability flow.
- Glaze UI 1.5.1 native source-adoption candidate.
- Native accessibility/context presentation mapping.
- Linux and Android CI build/test coverage.

## Implemented operational and release controls

- Hardened target container/runtime validation.
- No-production-claim release metadata.
- Private-publication acceptance runbook.
- Source-controlled monitoring contract.
- Post-retirement GoreeCloud Monitor integration contract.
- Independent Notify-down alerting requirement.
- Wardveil Security source-adoption evidence.
- Privacy Shield source adapter candidate.
- Everkeep source acceptance-policy candidate.
- Platform Contract 0.4 declaration covering all nine Integral Platform Systems.
- CI for backend/frontend, browser accessibility, native builds, monitoring readiness, production readiness, and Platform Contract validation.

## Not yet production-accepted

The following remain incomplete acceptance work rather than implemented production features:

- live VPS activation;
- final private Gateway/DNS/NetBird publication;
- target backup/restore evidence;
- accepted GoreeCloud Monitor deployment;
- independent out-of-band Notify-down mechanism;
- migration of all actually active legacy producers;
- physical-device Android background-delivery/signing acceptance;
- application-specific Glaze UI accessibility/performance/rollback/consumer-registry acceptance;
- remaining platform-system acceptance;
- explicit production approval.

