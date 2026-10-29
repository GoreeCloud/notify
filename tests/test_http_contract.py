"""Network contract tests against an isolated, loopback HTTP fixture."""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from goreecloud_notify.core import NtfyClient


def test_publish_and_json_stream_over_loopback():
    received = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            assert self.path == "/ntfy/alerts/json?since=10m"
            body = (
                json.dumps({"event": "open", "topic": "alerts"}) + "\n" +
                json.dumps({"event": "message", "id": "new1", "topic": "alerts",
                            "message": "Backups complete", "priority": 4, "time": 1740000000}) + "\n"
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/x-ndjson")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            assert self.path == "/ntfy/alerts"
            received.append({
                "body": self.rfile.read(int(self.headers["Content-Length"])),
                "title": self.headers["Title"],
                "priority": self.headers["Priority"],
                "authorization": self.headers.get("Authorization"),
            })
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        client = NtfyClient(f"http://127.0.0.1:{server.server_port}/ntfy", "sample-token")
        notes = list(client.stream("alerts", "10m", lambda: False))
        assert len(notes) == 1
        assert notes[0].message == "Backups complete"
        client.publish("alerts", "sent", title="Test", priority=5)
        assert received == [{
            "body": b"sent", "title": "Test", "priority": "5",
            "authorization": "Bearer sample-token",
        }]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
