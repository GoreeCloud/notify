"""ntfy protocol primitives; no GUI or credential persistence dependencies."""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Callable, Iterator

TOPIC_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
MAX_LINE = 65536
MAX_MESSAGE = 8192


class NotifyError(Exception):
    """A deliberately non-sensitive client-facing error."""


@dataclass(frozen=True)
class Notification:
    id: str
    topic: str
    message: str
    title: str
    priority: int
    time: int
    tags: tuple[str, ...] = ()


def normalize_server(value: str) -> str:
    """Require TLS except when the destination is an explicit loopback host."""
    raw = value.strip().rstrip("/")
    try:
        p = urllib.parse.urlsplit(raw)
        port = p.port  # Trigger validation of malformed ports.
    except ValueError as exc:
        raise NotifyError("Invalid server address") from exc
    if p.scheme not in ("http", "https") or not p.hostname:
        raise NotifyError("Enter an absolute https:// server URL")
    if p.username or p.password or p.query or p.fragment:
        raise NotifyError("Server URL cannot contain credentials, query, or fragment")
    if p.scheme == "http" and p.hostname.lower() not in ("localhost", "127.0.0.1", "::1"):
        raise NotifyError("HTTPS is required except for local loopback servers")
    if any(ord(c) < 32 for c in raw) or "\\" in p.path:
        raise NotifyError("Invalid server URL")
    if port is not None and not 1 <= port <= 65535:
        raise NotifyError("Invalid server port")
    return urllib.parse.urlunsplit((p.scheme, p.netloc, p.path.rstrip("/"), "", ""))


def validate_topic(value: str) -> str:
    topic = value.strip()
    if not TOPIC_RE.fullmatch(topic):
        raise NotifyError("Topics must be 1–64 letters, numbers, hyphens, or underscores")
    return topic


def topic_url(server: str, topic: str, mode: str = "") -> str:
    base = normalize_server(server)
    name = validate_topic(topic)
    if mode not in ("", "json"):
        raise NotifyError("Unsupported endpoint")
    return base + "/" + name + ("/json" if mode == "json" else "")


def _header(value: str, field: str, limit: int = 160) -> str:
    if not isinstance(value, str) or "\r" in value or "\n" in value or len(value) > limit:
        raise NotifyError("Invalid " + field)
    return value


def parse_notification(payload: bytes | str | dict) -> Notification | None:
    try:
        obj = json.loads(payload) if not isinstance(payload, dict) else payload
    except (ValueError, UnicodeError, TypeError):
        return None
    if not isinstance(obj, dict) or obj.get("event") != "message":
        return None
    ident, topic, body = obj.get("id"), obj.get("topic"), obj.get("message")
    if not isinstance(ident, str) or not isinstance(topic, str) or not isinstance(body, str):
        return None
    if len(ident) > 128 or len(body) > 65536:
        return None
    try:
        priority = int(obj.get("priority", 3))
        timestamp = int(obj.get("time", 0))
    except (TypeError, ValueError, OverflowError):
        return None
    if priority not in range(1, 6) or timestamp < 0:
        return None
    raw_tags = obj.get("tags", [])
    tags = tuple(t[:40] for t in raw_tags[:12] if isinstance(t, str)) if isinstance(raw_tags, list) else ()
    title = obj.get("title")
    if not isinstance(title, str):
        title = ""
    return Notification(ident, topic, body, title[:240], priority, timestamp, tags)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """Avoid leaking Authorization to another origin through a redirect."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class NtfyClient:
    def __init__(self, server: str, token: str = "", opener=None):
        self.server = normalize_server(server)
        self.token = token
        self.opener = opener if opener is not None else urllib.request.build_opener(NoRedirect)

    def _open(self, request: urllib.request.Request, timeout: int = 35):
        try:
            return self.opener.open(request, timeout=timeout)
        except urllib.error.HTTPError as exc:
            if exc.code in (401, 403):
                raise NotifyError("Access denied. Check topic permissions and token") from exc
            if exc.code in (301, 302, 303, 307, 308):
                raise NotifyError("Server redirects are disabled to protect credentials") from exc
            if exc.code == 429:
                raise NotifyError("Server rate limit reached") from exc
            raise NotifyError("Server returned HTTP " + str(exc.code)) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise NotifyError("Unable to connect to ntfy server") from exc

    def _request(self, url: str, *, data: bytes | None = None, headers: dict | None = None):
        h = {"User-Agent": "GoreeCloud-Notify/0.1", "Accept": "application/x-ndjson"}
        if self.token:
            if "\r" in self.token or "\n" in self.token:
                raise NotifyError("Invalid access token")
            h["Authorization"] = "Bearer " + self.token
        if headers:
            h.update(headers)
        return urllib.request.Request(url, data=data, headers=h, method="POST" if data is not None else "GET")

    def publish(self, topic: str, message: str, *, title: str = "", priority: int = 3, tags: str = "") -> None:
        if not message.strip() or len(message) > MAX_MESSAGE:
            raise NotifyError("Message must contain 1–8192 characters")
        if priority not in range(1, 6):
            raise NotifyError("Priority must be between 1 and 5")
        headers = {"Content-Type": "text/plain; charset=utf-8", "Priority": str(priority)}
        if title:
            headers["Title"] = _header(title.strip(), "title", 160)
        if tags:
            headers["Tags"] = _header(tags.strip(), "tags", 120)
        request = self._request(topic_url(self.server, topic), data=message.encode("utf-8"), headers=headers)
        with self._open(request, timeout=15) as response:
            response.read(4096)

    def stream(self, topic: str, since: str, stop: Callable[[], bool], on_open: Callable[[], None] | None = None) -> Iterator[Notification]:
        """Consume newline-delimited JSON, reconnecting at the worker layer."""
        url = topic_url(self.server, topic, "json") + "?" + urllib.parse.urlencode({"since": since})
        req = self._request(url)
        with self._open(req) as response:
            if on_open is not None:
                on_open()
            while not stop():
                try:
                    line = response.readline(MAX_LINE + 1)
                except (TimeoutError, OSError) as exc:
                    raise NotifyError("Subscription connection interrupted") from exc
                if not line:
                    break
                if len(line) > MAX_LINE:
                    raise NotifyError("Oversized event from server")
                note = parse_notification(line)
                if note is not None and note.topic == topic:
                    yield note
