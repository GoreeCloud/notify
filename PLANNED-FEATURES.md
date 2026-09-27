# GoreeCloud Notify — Planned Features and Acceptance Work

**Record type:** Repository planned-feature authority  
**Repository:** `GoreeCloud/notify`  
**Lifecycle:** Release Candidate source line; production acceptance remains false  
**Tracking:** GitHub issues are the operational task authority for active repository work.

## Current high-priority obligations

### Glaze UI 1.6.0 downstream acceptance

**Tracking:** #101

- Complete application-specific acceptance of the implemented web and Flutter Glaze UI 1.6.0 source-adoption candidate against the current shared Stable release.
- Preserve presentation-only authority and fail closed on unsupported capability/context mappings.
- Re-run exact-head browser/native/accessibility/rollback and Platform Contract validation.
- Keep representative device/performance, consumer acceptance, production deployment, release, and Stable qualification separately gated.

### Production runtime and private publication

**Tracking:** #25, #83

- Validate the exact release candidate on the approved GoreeCloud target.
- Complete private Caddy/Gateway, DNS, NetBird, filesystem/runtime, long-lived SSE/session, and real-network interruption/recovery evidence.
- Migrate actually active producers to scoped GoreeCloud Notify identities/tokens only after their acceptance path is verified.
- Preserve rollback evidence and do not treat the retired ntfy service as proof that Notify itself is production accepted.

### Backup, restore, monitoring, and outage alerting

**Tracking:** #24, #55

- Record the target backup repository, schedule, retention, and successful isolated restore for the exact candidate.
- Accept GoreeCloud Monitor only when Monitor's own deployment/acceptance is valid for this dependency.
- Establish and test an independent out-of-band Notify-down alert path that does not depend entirely on Notify.
- Complete the remaining manual browser/OS acceptance evidence.

### Android background delivery

**Tracking:** #81

- Prove persistent Android background notification delivery on representative physical devices.
- Validate lifecycle, power-management, permission, delivery, restart/reboot, and recovery behavior without overstating emulator/source results.
- Complete production-signing and distribution acceptance separately.

### Integral Platform Systems and release qualification

- Evaluate and accept all nine Integral Platform Systems where applicable: Manager, Privacy Shield, Wardveil Security, Everkeep, Glaze UI, Mesh, Identity, Policy, and Observability.
- Keep unsupported or unaccepted systems fail-closed in `goreecloud.platform.yaml`.
- Complete final production-activation approval, release evidence, rollback acceptance, and Stable qualification for the exact artifact/runtime state.

## Governance rule

Feature lifecycle authority lives in `IMPLEMENTED-FEATURES.md` and this file. `FEATURE-ROADMAP.md` is retired and must not be recreated as an active control. Repository change history lives in `CHANGELOGS.md`. Google Drive roadmap/changelog copies are not parallel authoritative mirrors.


## Legacy Drive roadmap identifier traceability

This table preserves the material identifiers and source-state wording from the retired Google Drive roadmap. The current lifecycle classification and authoritative feature truth remain the `IF-*` and `PF-*` records above; this table is migration traceability only and must not be used to revive Drive as a synchronization target.

| Legacy ID | Legacy obligation | Priority | Source state at migration |
| --- | --- | --- | --- |
| FR-001 | Reconcile and maintain every current planned or recommended GoreeCloud Notify feature from the authoritative project record and verified repository evidence in this roadmap. | High | Ongoing control |
| FR-002 | Move actionable feature obligations into GoreeCloud Tasks Management when required, preserving priority, dependency, and lifecycle disposition. | High | Ongoing control |
| FR-003 | Do not mark features implemented, complete, cancelled, or superseded without authoritative evidence and synchronized authoritative feature records under the governance in force at the time; the former Drive copy is now retired. | High | Ongoing control |
