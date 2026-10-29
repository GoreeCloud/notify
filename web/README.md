# GoreeCloud Notify — Supplementary web application

> **Status: development preview only.** This is an original browser client that complements, **not replaces**, GoreeCloud Notify's native GTK4/Linux application. No public DNS, Caddy gateway route, live deployment or independently validated browser release has been established by this repository.

## First-run capabilities

- Responsive GC UI-aligned Canvas/Surface/Lens-inspired navigation with dark and light themes and accessible native HTML controls.
- All-topic and individual-topic live ntfy subscriptions, 10-minute initial replay, per-topic cursor resume, deduplication, and bounded reconnect delays.
- Browser-side message search and priority filtering, unread counts, and confirmation-based subscription removal.
- Compose text notifications with title, tags and priorities 1–5.
- Opt-in read-only ntfy /v1/health diagnostics; separate health, subscription and publishing statuses.
- No ads, analytics, unnecessary dependencies, service worker, message-body persistence, or automatic execution of remote notification actions.
- Optional Bearer token held in page memory only; cleared on reload. Only the non-secret endpoint/topic/theme preferences may be saved in localStorage.

## Run a local web preview

Python 3.11+ and a current browser are sufficient; Node 20+ is needed **only** to run protocol tests.

Without a backend (UI-only):

```bash
python3 web/dev_server.py --port 8765
# Open http://127.0.0.1:8765/
```

For a locally hosted ntfy service listening on loopback:

```bash
NTFY_UPSTREAM=http://127.0.0.1:8080 python3 web/dev_server.py --port 8765
```

The development server is **loopback-only**, serves static files, and proxies only the fixed, explicit `NTFY_UPSTREAM` with a narrow API allowlist. It does not discover services, edit production settings, expose private hosts publicly, or provision credentials.

For a protected remote server, use an HTTPS `NTFY_UPSTREAM` explicitly. Direct browser endpoint configuration is also supported if the server explicitly permits the browser origin via its CORS policy. Same-origin `/api/ntfy` is recommended.

## Check and test

```bash
cd web
npm run check
npm test
cd ..
python3 -m pytest -q
```

All tests are dependency-free on the JavaScript side (Node's built-in test runner). There is no build/compilation step for the web application.

## Proposed private hosting

Review [Caddyfile.example](Caddyfile.example). Its `notify-dev.goreecloud.com` host is **an illustration, not an assigned or deployed route**. Deploy only after authorization and validation of private DNS rewrites, access through NetBird/GoreeCloud VPN, appropriate firewall policies, TLS, host authorization, ntfy ACLs and Caddy/GoreeCloud Gateway configuration. The required `NTFY_UPSTREAM` Caddy environment variable must be set to a fixed authorized service origin.

Never place an ntfy access token inside this repository, Caddyfile, application URL, localStorage or test fixture. The browser runs under the origin that served it and uses a same-origin `/api/ntfy` route by default. A public frontend **does not authorize public exposure of the ntfy backend**.

## Backend and design attribution

ntfy is independently authored and retains its own licenses and upstream API semantics: [subscription documentation](https://docs.ntfy.sh/subscribe/api/) and [publishing](https://docs.ntfy.sh/publish/). Caddy is independent reverse-proxy software. GoreeCloud UI (GC UI) is the native and web design authority, while formal product-specific GC UI acceptance remains pending.

## Acceptance and known limitations

This is an early browser implementation, not verified as a production application. Before declaring support, complete real browser interaction, mobile viewport, keyboard/screen-reader, end-to-end protected ntfy integration, reverse-proxy stream buffering, multi-topic reconnection, session security, accessibility, performance and deployment checks. Browser push notifications and persistent offline inbox are intentionally **not** shipped; there is no service worker or background receiver.
