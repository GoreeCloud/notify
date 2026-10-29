from __future__ import annotations

from io import BytesIO

import pytest

from goreecloud_notify.core import NtfyClient, NotifyError
from goreecloud_notify.health import probe_health


class Response:
    def __init__(self, data):
        self.payload = BytesIO(data)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self, n):
        return self.payload.read(n)


class Opener:
    def __init__(self, body):
        self.body = body
        self.urls = []
        self.headers = []

    def open(self, request, timeout=None):
        self.urls.append(request.full_url)
        self.headers.append(dict(request.headers))
        assert timeout == 8
        return Response(self.body)


@pytest.mark.parametrize("payload,healthy", [
    (b'{"healthy":true}', True),
    (b'{"healthy":false}', False),
])
def test_health_probe(payload, healthy):
    opener = Opener(payload)
    result = probe_health(NtfyClient("https://ntfy.example.test/ntfy", "secret-test", opener=opener))
    assert result.healthy is healthy
    assert result.latency_ms >= 0
    assert opener.urls == ["https://ntfy.example.test/ntfy/v1/health"]
    assert opener.headers[0]["Authorization"] == "Bearer secret-test"


@pytest.mark.parametrize("payload", [
    b'not JSON', b'{"healthy":"true"}', b'{"healthy":1}', b'{}',
    b'[]', b'{"healthy":true}' + b"x" * 4100,
])
def test_health_probe_invalid(payload):
    with pytest.raises(NotifyError):
        probe_health(NtfyClient("https://ntfy.example.test", opener=Opener(payload)))
