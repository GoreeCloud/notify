# GoreeCloud Notify — Glaze UI 1.6.0 consumer adoption and conformance record

## Current required target

The current official Stable GoreeCloud design-system target is **Glaze UI 1.6.0**.

Shared Stable authority is defined by the canonical `GoreeCloud/glaze-ui` records including `contracts/v1.6/stable-release.json`, `acceptance/v1.6-stable.json`, and the immutable `v1.6.0` release.

The accepted V1.6.0 release source is `a7180679ea851389e0f3004515f9a25f420e716d`. The V1.6 source-qualification anchor is `c7509c79256b04b0aa67cb9dd0737d7588e0ae4a`; the published source/runtime archive SHA-256 is `687268b5eb76917eccae9d935ffa1bead333d5dee50b6098e996a3f44cee50af`.

Shared Stable status does not certify GoreeCloud Notify. Notify requires its own exact-revision implementation and acceptance for every supported user-facing surface.

## Current Notify source state

Notify now carries a repository-local **Glaze UI 1.6.0 source adoption candidate** for:

- web;
- Flutter Linux;
- Flutter Android.

The historical 1.3.0 mapping remains preserved in `docs/glaze-ui-v1.3-adoption.json` only as migration provenance.

The current source candidate does not claim completed Glaze conformance or production eligibility.

## Web mapping

The web client now resolves bounded presentation from actual application/runtime/accessibility state:

- viewport width drives single, stacked, or split presentation;
- Reduced Motion drives reduced presentation motion;
- Reduced Transparency, increased contrast, and Forced Colors take precedence over decorative optical treatment;
- actual Notify health state is represented as service capability state;
- actual SSE connection state is represented as realtime capability/connectivity presentation;
- actual browser Notification permission plus the user's local Notify opt-in are represented as system-alert capability state.

The resolver does not grant browser permission, authenticate users, change server state, execute fallback actions, or infer authorization. Browser notification permission is still requested only by the existing explicit user action.

The web source records the exact 1.6.0 shared release/source anchors and exposes presentation/capability state through bounded document data attributes consumed by the repository-local CSS. Raw notification content and provider identity are not added to Glaze diagnostics or presentation metadata.

## Flutter Linux and Android mapping

The Flutter client now identifies Glaze UI 1.6.0 and binds the same accepted-release/shared qualification anchors.

Native presentation resolution uses Flutter `MediaQuery` state for:

- pane/layout mode;
- large-text-aware density;
- high-contrast material fallback;
- reduced-animation preference.

`GlazeChrome` becomes solid when the authoritative Flutter accessibility context requests high contrast rather than forcing translucent material.

Android persistent-system-alert state is recorded only from actual platform/plugin outcomes:

- previously enabled persistent alerts → available;
- permission denial → restricted;
- failed persistent-alert activation → temporarily unavailable;
- not-yet-established permission → unknown.

The Glaze presentation layer never grants permission. Permission is still requested only inside the user-initiated Enable flow.

## Authority boundaries

Glaze UI is presentation and interaction authority only. It does not infer authorization, create consent, grant permission, determine authenticated identity, redefine Privacy Shield requirements, reinterpret Wardveil Security state, manufacture service health, create GoreeCloud Policy decisions, or alter GoreeCloud Observability evidence.

Provider/capability state used by this consumer mapping is derived only from the owning application, browser/runtime, Flutter runtime, or platform API already responsible for that state.

## Accessibility and resilience

Existing resilient fallbacks remain in force, including:

- no-backdrop-filter fallback;
- Reduced Transparency;
- Reduced Motion;
- increased contrast;
- Forced Colors;
- responsive layout;
- large-text/native density mapping;
- minimum target-size floors.

Automated browser/native source evidence does not substitute for representative manual keyboard, screen-reader, zoom/reflow, operating-system notification, physical-device, or visual-excellence acceptance.

## Platform-system boundary

The root `goreecloud.platform.yaml` uses Platform Contract 0.4 and declares all nine Integral Platform Systems. Glaze UI is `applicable-blocked`: source migration is present, while application-specific acceptance remains incomplete.

Other blocked platform systems remain independent blockers. Source adoption of Glaze UI does not satisfy Manager, Privacy Shield, Wardveil Security, Everkeep, Mesh, Identity, Policy, or Observability acceptance.

## Remaining acceptance

The exact candidate still requires applicable:

- representative browser/OS accessibility and visual acceptance;
- Flutter Linux native accessibility and performance acceptance;
- Android physical-device, accessibility, background-delivery, posture/rotation where applicable, and signing acceptance;
- application-specific performance-budget evidence;
- known-good application rollback validation;
- governed Glaze consumer-registry acceptance;
- exact-revision production approval.

Until those gates are accepted, Notify must not claim current Glaze UI conformance, Stable product qualification, complete platform conformance, or production eligibility based on source adoption alone.
