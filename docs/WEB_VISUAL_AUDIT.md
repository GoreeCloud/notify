# GoreeCloud Notify — Web visual audit (development preview)

- **Audit date:** October 28–29, 2026 (local/UTC crossover).
- **Device:** Authorized GoreeCloud Linux development laptop.
- **Tool:** Previously cached headless Chromium, rendering a loopback-only GoreeCloud Notify web preview with no ntfy upstream configured.
- **Status:** Evidence for a visual design pass only. Not an accessibility, browser-interaction, screen-reader, production deployment or native OS acceptance.

## Captured states

| State | Artifact | Observation |
| --- | --- | --- |
| Desktop light, 1440 × 900 | [web-desktop-light.png](screenshots/web-desktop-light.png) | Calm sidebar and panel hierarchy; cards, toolbar, help text and focusable controls display with readable contrast after first-render transition correction |
| Desktop dark, 1440 × 900 | [web-desktop-dark.png](screenshots/web-desktop-dark.png) | Semantic dark palette displays readable surface, text and selected navigation contrast; a temporary local debug-only theme selection was used to capture this state and removed afterward |
| Mobile light, 390 × 844 | [web-mobile-light.png](screenshots/web-mobile-light.png) | Responsive stacked statistics, visible settings and compose controls; breadcrumb shortened to the active context at narrow widths |

The screenshots contain only the new-user empty state with the default `/api/ntfy` proxy path. No production backend, access token, user message, server name or personal data was used or captured.

## Corrected observations

1. The first Chromium screenshot showed dark-background/light-mode card transition artifacts with unreadable dark-on-dark foreground. The root variables had updated, but card/button transitions were still beginning from the initial dark palette. The code now sets the system-preference palette before JavaScript theme initialization and activates transitions only after the first frame.
2. The first mobile capture cut off the last part of the breadcrumb. The narrow layout now displays the current topic/overview context without redundant navigation text.
3. An HTML CSP meta directive attempted to specify `frame-ancestors`, which browsers ignore in a meta element. The duplicate directive was removed from the HTML; frame protection remains in actual HTTP response headers of the development server and in the example Caddyfile.

## Remaining visual and functional acceptance

- Real interactive desktop/mobile browser journeys: connection configuration, dialogs, long messages, errors, loading, topic removal, live message updates and notification publishing
- Keyboard, focus-order, contrast-ratio, forced-colors, high-zoom, screen-reader and reduced-motion assessments
- Device-level visual validation on supported real browsers and viewport sizes beyond the captures above
- ntfy ACL integration, private DNS/VPN, upstream and reverse-proxy buffering behavior, and authorization boundaries
- GC UI formal semantic token audit and explicit release acceptance

Screenshots alone do not prove the accessibility or runtime behavior of interactive components. The related outstanding work is tracked at [web acceptance issue #7](https://github.com/GoreeCloud/notify/issues/7).
