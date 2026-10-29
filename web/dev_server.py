#!/usr/bin/env python3
"""Loopback-only GoreeCloud Notify web development server.

Serve the static browser client and proxy a fixed, explicitly configured ntfy
upstream at /api/ntfy. Not intended for public deployment or authentication.
"""
from __future__ import annotations

import argparse
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

WEB_DIR = Path(__file__).resolve().parent
TOPIC_RE = re.compile(r"^/([A-Za-z0-9_-]{1,64})(/json)?$")
HEALTH_PATH = "/v1/health"
MAX_POST = 8192
MAX_STREAM_LINE = 65536
CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
    "connect-src 'self'; object-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
)


def validate_upstream(raw: str) -> str:
    try:
        url = urllib.parse.urlsplit(raw.strip().rstrip("/"))
        _ = url.port
    except ValueError as exc:
        raise ValueError("Invalid NTFY_UPSTREAM address") from exc
    if not url.hostname or url.scheme not in ("https", "http") or url.username or url.password or url.query or url.fragment:
        raise ValueError("NTFY_UPSTREAM must be an absolute URL without credentials or query")
    if url.scheme == "http" and url.hostname not in ("localhost", "127.0.0.1", "::1"):
        raise ValueError("NTFY_UPSTREAM requires HTTPS except for loopback")
    return urllib.parse.urlunsplit((url.scheme, url.netloc, url.path.rstrip("/"), "", ""))


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Handler(SimpleHTTPRequestHandler):
    upstream = ""
    opener = urllib.request.build_opener(NoRedirect)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    def log_message(self, *args):
        # No request-path or credential logs in development.
        return

    def end_headers(self):
        self.send_header("Content-Security-Policy", CSP)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def list_directory(self, path):
        self.send_error(403)
        return None

    def do_GET(self):
        if self.path.startswith("/api/ntfy"):
            return self.proxy("GET")
        return super().do_GET()

    def do_POST(self):
        if not self.path.startswith("/api/ntfy"):
            return self.send_error(405)
        return self.proxy("POST")

    def proxy(self, method: str):
        headers_sent = False
        if not self.upstream:
            return self.send_error(503, "NTFY_UPSTREAM not configured")
        try:
            url = urllib.parse.urlsplit(self.path)
            if url.fragment or not url.path.startswith("/api/ntfy/"):
                return self.send_error(404)
            path = url.path[len("/api/ntfy"):]
            match = TOPIC_RE.fullmatch(path)
            if path == HEALTH_PATH and method == "GET" and not url.query:
                allowed = True
            elif match and match.group(2) == "/json" and method == "GET":
                try:
                    query = urllib.parse.parse_qs(url.query, strict_parsing=True)
                except ValueError:
                    return self.send_error(400, "Invalid subscription query")
                since = query.get("since", [])
                allowed = len(query) == 1 and len(since) == 1 and bool(re.fullmatch(r"[A-Za-z0-9_-]{1,128}", since[0]))
            elif match and not match.group(2) and method == "POST" and not url.query:
                allowed = True
            else:
                allowed = False
            if not allowed:
                return self.send_error(400, "Unsupported ntfy proxy endpoint")
            headers = {"Accept": "application/x-ndjson"}
            authorization = self.headers.get("Authorization", "")
            if authorization:
                if not authorization.startswith("Bearer ") or len(authorization) > 2048 or any(ord(c) < 32 for c in authorization):
                    return self.send_error(400, "Invalid Authorization")
                headers["Authorization"] = authorization
            data = None
            if method == "POST":
                try:
                    length = int(self.headers.get("Content-Length", "-1"))
                except ValueError:
                    return self.send_error(400, "Invalid body length")
                if length < 1 or length > MAX_POST:
                    return self.send_error(413, "Invalid body size")
                data = self.rfile.read(length)
                headers["Content-Type"] = "text/plain; charset=utf-8"
                for key, limit in (("Priority", 1), ("Title", 160), ("Tags", 120)):
                    value = self.headers.get(key, "")
                    if value:
                        if len(value) > limit or any(ord(c) < 32 for c in value):
                            return self.send_error(400, "Invalid publish metadata")
                        headers[key] = value
            target = self.upstream + path + ("?" + url.query if url.query else "")
            request = urllib.request.Request(target, data=data, method=method, headers=headers)
            with self.opener.open(request, timeout=40) as response:
                self.send_response(response.status)
                headers_sent = True
                is_stream = bool(match and match.group(2))
                self.send_header("Content-Type", "application/x-ndjson" if is_stream else
                                 ("application/json" if method == "GET" else "text/plain; charset=utf-8"))
                self.end_headers()
                self.close_connection = True
                if is_stream:
                    while True:
                        line = response.readline(MAX_STREAM_LINE + 1)
                        if not line: break
                        if len(line) > MAX_STREAM_LINE: break
                        self.wfile.write(line)
                        self.wfile.flush()
                else:
                    self.wfile.write(response.read(4097))
        except urllib.error.HTTPError as exc:
            self.send_error(exc.code if exc.code in (400, 401, 403, 404, 429) else 502, "Upstream rejected request")
        except (urllib.error.URLError, TimeoutError, OSError):
            # A streaming connection may already have sent response headers.
            if not headers_sent:
                self.send_error(502, "ntfy upstream unavailable")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    Handler.upstream = validate_upstream(os.environ.get("NTFY_UPSTREAM", "")) if os.environ.get("NTFY_UPSTREAM") else ""
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"GoreeCloud Notify web preview: http://127.0.0.1:{server.server_port}/", flush=True)
    if not Handler.upstream:
        print("NTFY_UPSTREAM unset: UI preview only; API returns 503", flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()


if __name__ == "__main__":
    main()
