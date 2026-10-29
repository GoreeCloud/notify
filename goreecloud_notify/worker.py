"""Background ntfy subscriptions. GTK updates are marshalled to the main loop."""
from __future__ import annotations

import threading
from collections import deque
from typing import Callable

from .core import Notification, NotifyError, NtfyClient


class SubscriptionManager:
    def __init__(self, on_message: Callable[[Notification], None], on_status: Callable[[str, str], None]):
        self.on_message = on_message
        self.on_status = on_status
        self._stop = threading.Event()
        self._threads: list[threading.Thread] = []
        self._seen: dict[str, deque[str]] = {}

    def start(self, server: str, topics: list[str], token: str = ""):
        self.stop()
        self._stop = threading.Event()
        self._threads = []
        self._seen = {}
        for topic in topics:
            t = threading.Thread(target=self._listen, args=(server, topic, token, self._stop),
                                 daemon=True, name="ntfy-" + topic)
            self._threads.append(t)
            t.start()

    def stop(self):
        self._stop.set()
        # Streams have a read timeout; don't block GTK main thread waiting for them.
        self._threads = []

    def _listen(self, server: str, topic: str, token: str, stop: threading.Event):
        client = NtfyClient(server, token)
        since = "10m"  # Bounded initial history, not full-cache replay.
        backoff = 1
        seen = self._seen.setdefault(topic, deque(maxlen=500))
        while not stop.is_set():
            self.on_status(topic, "Connecting")
            try:
                for note in client.stream(topic, since, stop.is_set, on_open=lambda: self.on_status(topic, "Connected")):
                    if stop.is_set():
                        return
                    since = note.id
                    if note.id in seen:
                        continue
                    seen.append(note.id)
                    self.on_message(note)
                backoff = 1
            except NotifyError as exc:
                if not stop.is_set():
                    self.on_status(topic, str(exc))
            except Exception:
                if not stop.is_set():
                    self.on_status(topic, "Subscription failed; retrying")
            if stop.wait(backoff):
                break
            backoff = min(backoff * 2, 30)
        self.on_status(topic, "Disconnected")
