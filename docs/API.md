# GoreeCloud Notify API v1 (alpha)

Base URL: `http://127.0.0.1:8080` by default. All `/api/v1/*` requests require `Authorization: Bearer TOKEN`. There are no anonymous publish or subscription permissions. No credentials are accepted in query strings. Exactly one `Authorization` header is required; duplicated or malformed bearer headers receive `401`.

| Method | Endpoint | Role | Description |
| --- | --- | --- | --- |
| GET | `/healthz` | Public | Process health |
| GET | `/readyz` | Public | Process readiness |
| GET | `/api/v1/me` | Any authenticated | Principal name, role, topic patterns |
| GET | `/api/v1/topics` | Any authenticated | Topics visible to principal's read ACL |
| POST | `/api/v1/topics/{topic}/messages` | Admin or publisher | Create a notification |
| GET | `/api/v1/topics/{topic}/messages?limit=50` | Admin or subscriber | Most recent messages; newest first, limit 1–100 |
| GET | `/api/v1/topics/{topic}/events?after={id}` | Admin or subscriber | Server-Sent Events, retained replay + live delivery |
| GET | `/metrics` | Admin | Prometheus counters and gauges |

## Publish

`Content-Type: application/json` required. Payload:

```json
{
  "title": "Backup complete",
  "body": "Verification passed.",
  "priority": 4,
  "tags": ["backup", "success"],
  "click": "https://example.org/status"
}
```

- `body` required, maximum 4096 bytes; `title` optional, maximum 120 bytes.
- `priority`: 1 minimum, 2 low, 3 normal (default), 4 high, 5 critical.
- `tags`: maximum 12, alphanumeric, underscore or hyphen, up to 32 characters each.
- `click`: optional absolute HTTP(S) URL, no embedded userinfo.
- Topic segments: 1–64 ASCII letters, digits, underscore, hyphen. Topic name is case sensitive.
- JSON body maximum 16 KiB; unknown fields and trailing JSON rejected.
- Optional `Idempotency-Key`: 1–100 ASCII letters, digits, period, underscore, colon or hyphen. Same token/topic/key and same canonical payload returns `200` and `Idempotent-Replay: true`; conflicting payload returns `409`. New message returns `201`.
- Valid JSON response includes `id`, `topic`, `body`, `title`, `priority`, `tags`, `click`, and `created_at`. Event IDs are random hexadecimal identifiers.

## Subscribe

`GET /api/v1/topics/{topic}/events` emits `text/event-stream` events:

```
retry: 3000

id: 0123456789abcdef0123456789abcdef
event: notification
data: {"id":"...","topic":"backup","body":"Verification passed.","priority":4,"created_at":"..."}

```

On connect, replay at most 100 retained events from the topic (oldest to newest). When `Last-Event-ID` or `after` identifies an event in this window, only subsequent retained events are replayed. Unknown/expired cursors replay the available window. A slow subscriber with a full 128-event queue is disconnected and should reconnect. At most **4 simultaneous SSE connections per bearer credential** and **64 total active SSE connections per server process** are accepted; additional connections receive `429` with `Retry-After: 5`. The limits are in-memory, per instance; a fronting proxy must also enforce network-level protections. There is no exactly-once delivery guarantee, no cross-topic atomic transaction, and no mobile OS push gateway in this alpha.

## Errors

Errors are JSON `{"error":"..."}` with relevant HTTP status codes: `400` malformed request, `401` missing or invalid bearer, `403` insufficient topic privileges, `409` idempotency conflict, `415` unsupported content type, `429` publish quota or SSE stream budget exceeded, `500` storage failure. The alpha applies a 120-attempts/minute per-token publishing limit, plus **240 requests/minute per direct socket peer** and **30 failed authentication attempts/minute per direct peer**; additional requests get `429` and `Retry-After: 60`. The peer limiter tracks socket addresses, groups IPv6 addresses by `/64`, ignores forwarded headers, and has a 10,000-peer memory cap; reverse-proxy clients share a budget and require independent ingress controls. Liveness/readiness checks are exempt. Clients should not assume a `201` response guarantees delivery to an offline mobile device.
