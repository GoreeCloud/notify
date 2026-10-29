# GoreeCloud Notify — Architecture and Trust Boundaries

## Ownership and maturity

GoreeCloud Notify is the original client. Upstream ntfy remains independently authored and deployed. Linux GTK4/libadwaita is the initial native front end. No production service or supported device build is established by the repository.

## Components

| Component | Responsibility |
| --- | --- |
| `core.py` | ntfy validation, JSON event parsing, HTTP publish/stream, bearer auth headers, strict no-redirect behavior |
| `storage.py` | Atomic 0600 metadata config and operating-system keyring access |
| `worker.py` | Per-topic background subscription, deduplication, cursor replay, bounded reconnect delay |
| `ui.py` | Native GTK4/libadwaita layout, setup flow, topic navigation, text compose and message cards |
| `__main__.py` | Application launch |

## Data flow

1. User supplies ntfy server URL and optional bearer token.
2. Non-secret server and topics are stored in XDG config. Token is stored only in OS credential provider when supplied.
3. Each selected topic opens an authenticated `GET /<topic>/json?since=10m` streaming subscription.
4. Later reconnects use the most recent message ID in `since=` so the server can replay missed events.
5. Received `event=message` objects update GTK on the main loop; only the last 200 per topic are kept in process memory.
6. Publishing sends an HTTP POST to the selected topic with optional title, tags and priority.

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
