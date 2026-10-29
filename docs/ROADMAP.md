# GoreeCloud Notify — Planned work (not shipped)

| Priority | Workstream | Acceptance evidence needed |
| --- | --- | --- |
| P0 | Linux GUI smoke test / keyboard accessibility / screen-reader review | Successful native window launch, screenshots, keyboard and Orca review |
| P0 | Integration tests against an isolated ntfy container with ACLs | End-to-end read/publish, auth denial, reconnect, rate limit |
| P0 | Stop subscriptions on server change and validate clean shutdown | No obsolete-stream messages after switch, bounded thread counts |
| P0 | Native Linux packaging, desktop entry, icon, application ID | Installed package, start/stop, uninstall, runtime verification |
| P1 | Expand connection diagnostics and independent service health view | The read-only health probe exists; live diagnostics, ACL tests and independent watchdog integration remain unverified |
| P1 | Notification filtering, search, mute, unread, retention controls | Model and interaction tests; no private-text leakage |
| P1 | ntfy actions and attachments under explicit authorization | Consent, safe destinations, local file security, permissions tests |
| P1 | Native desktop notification integration | Opt-in OS notifications and verified permission/lifecycle |
| P1 | Additional native OS implementations | Separate Windows/macOS/Android/iOS/iPadOS source, builds and platform acceptance |
| P2 | Documented governed API/MCP/SSH/webhook integration boundaries | Least-privilege integration implementation and controls |
| P2 | GC UI formal native token audit and visual QA | Native token mapping and accessibility evidence |
| P2 | Releases / signed update and rollback | Reproducible build, signature, update/rollback tested |

**No additional platform support is claimed** until that operating system's target package, native integration, installation and runtime acceptance are verified.
