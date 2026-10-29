# GoreeCloud Notify — Architecture and Trust Boundaries

## Ownership and maturity

GoreeCloud Notify is the original client. Upstream ntfy remains independently authored and deployed. Linux GTK4/libadwaita is the initial native front end. No production service or supported device build is established by the repository.

## Components

| Component | Responsibility |
| --- | --- |
| `core.py` | ntfy validation, JSON event parsing, HTTP publish/stream, bearer auth headers, strict no-redirect behavior |
| `filters.py` | Pure, case-insensitive in-memory search and minimum-priority filtering without API requests |
| `health.py` | Bounded, read-only ntfy `/v1/health` probe with explicit unhealthy/error results |
| `storage.py` | Atomic 0600 metadata config and operating-system keyring access |
| `worker.py` | Per-topic background subscription, deduplication, cursor replay, bounded reconnect delay and generation fences |
| `ui.py` | Native GTK4/libadwaita layout, setup flow, topic navigation, text compose and message cards |
| `__main__.py` | Application launch |

## Data flow

1. User supplies ntfy server URL and optional bearer token.
2. Non-secret server and topics are stored in XDG config. Token is stored only in OS credential provider when supplied.
3. Each selected topic opens an authenticated `GET /<topic>/json?since=10m` streaming subscription.
4. Later reconnects use the most recent message ID in `since=` so the server can replay missed events.
5. Received `event=message` objects update GTK on the main loop; only the last 200 per topic are kept in process memory.
6. Publishing sends an HTTP POST to the selected topic with optional title, tags and priority.

The application can check the documented `/v1/health` endpoint, but a healthy server does not prove that topic ACLs, subscriptions, or publishing work. The probe is opt-in, bounded to 4 KiB, and does not perform writes.

The app does not implement server-side users, ACLs, attachments, arbitrary HTTP action execution, remote URL opening or automatic OS notification delivery. Each is a separately governed and testable follow-up.

## Threat model

- **Transport:** HTTPS required for nonloopback endpoints; Python's default TLS certificate verification remains enabled. No credential-bearing URL, token query parameter or disabled certificate validation.
- **Redirects:** Automatic redirects are disabled before the Authorization header can be forwarded to a new origin.
- **Credentials:** Store tokens in the OS keyring only. No fallback to plaintext metadata when keyring fails.
- **Output:** Untrusted notification text is inserted as escaped GTK Label text, not executed as markup or HTML. No remote-provided action or link automatically executes.
- **Resource bounds:** Reject oversized event lines, validate event types, retain at most 200 events per topic, and store at most 50 topics.
- **Reliability:** Background IO, bounded backoff, explicit status. Long-running connections may take up to 35 seconds to stop because reads are bounded by timeout; daemon threads cannot block process shutdown.
- **Privacy:** No telemetry, analytics, external icon fetches, message persistence, or background services.
- **Known limitations:** Background thread behavior, end-to-end ntfy permissions, status accuracy, GUI focus order, accessibility and credential-store failure paths require integration testing; no production readiness claim.

## ntfy protocol references

- [Subscription API](https://docs.ntfy.sh/subscribe/api/)
- [Publishing API](https://docs.ntfy.sh/publish/)
- [GoreeCloud UI](https://github.com/GoreeCloud/gc-ui)

## Topic removal and connection lifecycle

Unsubscribing requires confirmation, saves the new topic set first, stops older streams and clears that topic's in-memory history. Switching servers increments a UI generation so already-queued GTK callbacks from an older connection are discarded. The worker independently checks cancellation and captures per-generation callbacks. The setting update is atomic; no ntfy server-side delete is issued.

## Local search and priority filtering

The native search entry filters only the selected topic's at-most-200 messages currently in process memory. Each word must match case-insensitively within the title, body, tags or topic. The priority chooser limits results to all, high/urgent, or urgent-only. Search terms are not persisted, logged or transmitted, and a filtered-out message is not removed from memory. This is not a server-wide historical search.

## Supplementary web-client boundary

The separately developed [web application](../web/README.md) provides a browser experience while leaving the GTK4/Linux native app intact. It uses its own original HTML/CSS/JS controls; the common integration contract is ntfy's supported API, not a browser wrapper of the native app or an upstream UI rebrand.

The web app defaults to a same-origin `/api/ntfy` reverse proxy. In development, `web/dev_server.py` binds only to `127.0.0.1` and forwards explicitly allowlisted calls to a fixed `NTFY_UPSTREAM` with no automatic redirects. A Caddy example is supplied but **has not been deployed**. Private backend exposure and hostname assignment are independent, governed operations.

Browser-only token handling is deliberately different from native: a web bearer token stays in volatile page memory and is lost on reload, not in `localStorage`, cookies or service workers. Non-secret topic, endpoint and color-mode preferences may be retained in `localStorage`. Notifications and search terms remain in memory. Text is inserted into DOM nodes through `textContent` (not remote markup). No notification-provided actions or remote URLs automatically execute.

The web app is not a claim of native operating-system completion or a shipped background-notification implementation. Browser integration, streaming proxy buffering, accessibility, VPN/private DNS, Caddy authorization and production readiness require separate acceptance evidence.
