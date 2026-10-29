from __future__ import annotations

import json
import urllib.error

import pytest

from goreecloud_notify.core import (
    NtfyClient, NoRedirect, NotifyError, normalize_server,
    parse_notification, topic_url, validate_topic,
)


@pytest.mark.parametrize("address,expected", [
    ("https://ntfy.example.org/", "https://ntfy.example.org"),
    ("https://ntfy.example.org/prefix/", "https://ntfy.example.org/prefix"),
    ("http://localhost:2586", "http://localhost:2586"),
    ("http://127.0.0.1:2586", "http://127.0.0.1:2586"),
])
def test_server_valid(address, expected):
    assert normalize_server(address) == expected


@pytest.mark.parametrize("address", [
    "http://ntfy.example.org", "ftp://example.org", "not-a-url", "https://",
    "https://user:pass@example.org", "https://example.org/?token=123",
    "https://example.org/#fragment", "https://example.org:99999",
    "http://192.168.1.2", "https://example.org/\\trick",
])
def test_server_invalid(address):
    with pytest.raises(NotifyError):
        normalize_server(address)


@pytest.mark.parametrize("topic", ["../escape", "with/slash", "a,b", "", "hello world"])
def test_topic_invalid(topic):
    with pytest.raises(NotifyError):
        validate_topic(topic)


def test_url_has_prefix():
    assert topic_url("https://host.example/ntfy", "alerts", "json") == "https://host.example/ntfy/alerts/json"


def test_parses_message_and_ignores_control_events():
    payload = {"event": "message", "id": "AB12", "topic": "alerts", "message": "<b>plain text</b>", "priority": 5,
               "time": 123, "tags": ["backup", "success"]}
    note = parse_notification(json.dumps(payload).encode())
    assert note.message == "<b>plain text</b>"
    assert note.priority == 5
    assert note.tags == ("backup", "success")
    assert parse_notification({"event": "keepalive"}) is None
    assert parse_notification("{invalid") is None
    assert parse_notification({"event": "message", "topic": "x"}) is None
    assert parse_notification({**payload, "priority": 99}) is None


class FakeResponse:
    def __init__(self, lines=None):
        self.lines = iter(lines or [])
        self.read_size = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def readline(self, limit):
        try:
            return next(self.lines)
        except StopIteration:
            return b""

    def read(self, size):
        self.read_size = size
        return b'{"id":"ok"}'


class FakeOpener:
    def __init__(self, response=None, error=None):
        self.requests = []
        self.response = response or FakeResponse()
        self.error = error

    def open(self, request, timeout=None):
        self.requests.append(request)
        if self.error:
            raise self.error
        return self.response


def test_publish_headers_and_token():
    opener = FakeOpener()
    client = NtfyClient("https://ntfy.example.org", "token-example", opener=opener)
    client.publish("alarms", "Hello", title="Backup complete", priority=4, tags="backup,success")
    request = opener.requests[0]
    assert request.full_url == "https://ntfy.example.org/alarms"
    assert request.get_method() == "POST"
    assert request.get_header("Authorization") == "Bearer token-example"
    assert request.get_header("Priority") == "4"
    assert request.data == b"Hello"


def test_publish_rejects_injected_header_and_missing_message():
    client = NtfyClient("https://ntfy.example.org", opener=FakeOpener())
    with pytest.raises(NotifyError):
        client.publish("alerts", "body", title="okay\r\nInjected: true")
    with pytest.raises(NotifyError):
        client.publish("alerts", "  ")


def test_subscribe_skips_open_and_keepalive_and_wrong_topics():
    lines = [json.dumps(v).encode() + b"\n" for v in (
        {"event": "open"},
        {"event": "keepalive"},
        {"event": "message", "id": "a", "topic": "alerts", "message": "hello", "time": 1},
        {"event": "message", "id": "b", "topic": "other", "message": "wrong", "time": 2},
    )]
    opener = FakeOpener(FakeResponse(lines))
    messages = list(NtfyClient("https://ntfy.example.org", opener=opener).stream("alerts", "10m", lambda: False))
    assert [n.id for n in messages] == ["a"]
    assert "since=10m" in opener.requests[0].full_url


def test_oversized_stream_event_is_rejected():
    opener = FakeOpener(FakeResponse([b"x" * 65537]))
    with pytest.raises(NotifyError, match="Oversized"):
        list(NtfyClient("https://ntfy.example.org", opener=opener).stream("alerts", "10m", lambda: False))


def test_http_auth_error_is_redacted():
    req = "https://ntfy.example.org/alerts"
    exc = urllib.error.HTTPError(req, 401, "Unauthorized", {}, None)
    with pytest.raises(NotifyError, match="Access denied"):
        NtfyClient("https://ntfy.example.org", opener=FakeOpener(error=exc)).publish("alerts", "hello")


def test_redirect_disabled():
    assert NoRedirect().redirect_request(None, None, 302, "Found", {}, "https://evil.test") is None
