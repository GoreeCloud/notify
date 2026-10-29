"""Isolated HTTP integration tests: web preview + fixed ntfy mock server."""
from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from web.dev_server import Handler, validate_upstream


@pytest.fixture
def local_servers(monkeypatch):
    received = []

    class MockNtfy(BaseHTTPRequestHandler):
        def log_message(self, *_): pass

        def do_GET(self):
            if self.path == "/v1/health":
                body = b'{"healthy":true}'
            elif self.path == "/alerts/json?since=10m":
                body = (
                    b'{"event":"open"}\n' +
                    b'{"event":"message","id":"test1","topic":"alerts","message":"Complete","time":10}\n'
                )
            elif self.path == "/redirect/json?since=10m":
                self.send_response(302)
                self.send_header("Location", "https://example.invalid/secret")
                self.end_headers()
                return
            else:
                self.send_error(404)
                return
            received.append(("GET", self.path, self.headers.get("Authorization", "")))
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            body = self.rfile.read(int(self.headers["Content-Length"]))
            received.append(("POST", self.path, self.headers.get("Authorization", ""), body,
                             self.headers.get("Title"), self.headers.get("Priority")))
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")

    upstream = ThreadingHTTPServer(("127.0.0.1", 0), MockNtfy)
    thread_upstream = threading.Thread(target=upstream.serve_forever, daemon=True)
    thread_upstream.start()

    class Preview(Handler):
        pass

    Preview.upstream = f"http://127.0.0.1:{upstream.server_port}"
    preview = ThreadingHTTPServer(("127.0.0.1", 0), Preview)
    thread_preview = threading.Thread(target=preview.serve_forever, daemon=True)
    thread_preview.start()
    try:
        yield (f"http://127.0.0.1:{preview.server_port}", received)
    finally:
        preview.shutdown()
        preview.server_close()
        upstream.shutdown()
        upstream.server_close()
        thread_preview.join(timeout=2)
        thread_upstream.join(timeout=2)


def request(url, method="GET", data=None, token=""):
    headers = {"Authorization": "Bearer " + token} if token else {}
    return urllib.request.urlopen(urllib.request.Request(url, method=method, data=data, headers=headers), timeout=3)


def test_upstream_safety_validation():
    assert validate_upstream("http://127.0.0.1:8080") == "http://127.0.0.1:8080"
    assert validate_upstream("https://ntfy.example.test/") == "https://ntfy.example.test"
    for bad in ("http://192.168.1.1", "ftp://example.test", "https://u:p@example.test",
                "https://example.test?secret=x", "https://example.test#hash"):
        with pytest.raises(ValueError):
            validate_upstream(bad)


def test_web_static_and_content_security_policy(local_servers):
    base, _ = local_servers
    with request(base + "/") as response:
        content = response.read().decode()
        assert "GoreeCloud Notify" in content
        assert response.headers["Content-Security-Policy"].startswith("default-src 'self'")
        assert response.headers["X-Content-Type-Options"] == "nosniff"
    with request(base + "/app.js") as response:
        assert b"startStreams" in response.read()
    with pytest.raises(urllib.error.HTTPError) as error:
        request(base + "/api/ntfy/bad/path/more")
    assert error.value.code == 400


def test_same_origin_health_subscribe_publish_and_bearer(local_servers):
    base, calls = local_servers
    with request(base + "/api/ntfy/v1/health", token="demo") as response:
        assert json.loads(response.read()) == {"healthy": True}
    with request(base + "/api/ntfy/alerts/json?since=10m", token="demo") as response:
        lines = response.read().decode().splitlines()
        assert json.loads(lines[1])["message"] == "Complete"
    with request(base + "/api/ntfy/alerts", method="POST", data=b"hello", token="demo") as response:
        assert response.status == 200
    assert calls[0] == ("GET", "/v1/health", "Bearer demo")
    assert calls[1] == ("GET", "/alerts/json?since=10m", "Bearer demo")
    assert calls[2][:4] == ("POST", "/alerts", "Bearer demo", b"hello")


def test_disallows_unbounded_endpoints_and_redirects(local_servers):
    base, _ = local_servers
    for path in ("/api/ntfy/alerts/json?since=bad%20value", "/api/ntfy/alerts/json?since=10m&secret=x",
                 "/api/ntfy/../../admin", "/api/ntfy/alerts?auth=secret"):
        with pytest.raises(urllib.error.HTTPError):
            request(base + path)
    with pytest.raises(urllib.error.HTTPError) as error:
        request(base + "/api/ntfy/redirect/json?since=10m", token="demo")
    assert error.value.code == 502
    with pytest.raises(urllib.error.HTTPError) as error:
        request(base + "/api/ntfy/alerts", method="POST", data=b"x" * 8200)
    assert error.value.code == 413
