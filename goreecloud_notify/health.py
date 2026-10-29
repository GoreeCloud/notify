"""Bounded, read-only health probe for the configured ntfy server."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass

from .core import NtfyClient, NotifyError

MAX_HEALTH_BODY = 4096


@dataclass(frozen=True)
class HealthResult:
    healthy: bool
    latency_ms: int


def probe_health(client: NtfyClient) -> HealthResult:
    """Check ntfy's /v1/health without sending or receiving topic content.

    A healthy response requires HTTP 200 plus the literal JSON boolean true.
    A response of {"healthy": false} is a reachable but unhealthy service.
    Network/auth/proxy errors remain explicit failures, not "healthy".
    """
    start = time.monotonic()
    request = client._request(client.server + "/v1/health")
    with client._open(request, timeout=8) as response:
        body = response.read(MAX_HEALTH_BODY + 1)
    if len(body) > MAX_HEALTH_BODY:
        raise NotifyError("Health endpoint response is too large")
    try:
        data = json.loads(body)
    except (ValueError, UnicodeError, TypeError) as exc:
        raise NotifyError("Health endpoint returned invalid JSON") from exc
    if not isinstance(data, dict) or type(data.get("healthy")) is not bool:
        raise NotifyError("Health endpoint has an unexpected format")
    return HealthResult(data["healthy"], round((time.monotonic() - start) * 1000))
