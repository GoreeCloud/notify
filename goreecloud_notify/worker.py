"""Background ntfy subscriptions with stale-worker cancellation fences."""
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

    def _is_current(self, stop: threading.Event) -> bool:
        return not stop.is_set() and stop is self._stop

    def _report(self, topic: str, state: str, stop: threading.Event, on_status) -> None:
        if self._is_current(stop):
            on_status(topic, state)

    def _listen(self, server: str, topic: str, token: str, stop: threading.Event):
        # Freeze callbacks for this worker so a previous connection cannot use
        # the next connection's newly installed GTK callback generation.
        on_message, on_status = self.on_message, self.on_status
        client = NtfyClient(server, token)
        since = "10m"  # Bounded initial history, not full-cache replay.
        backoff = 1
        seen = self._seen.setdefault(topic, deque(maxlen=500))
        while self._is_current(stop):
            self._report(topic, "Connecting", stop, on_status)
            try:
                for note in client.stream(
                    topic, since, lambda: not self._is_current(stop),
                    on_open=lambda: self._report(topic, "Connected", stop, on_status),
                ):
                    if not self._is_current(stop):
                        return
                    since = note.id
                    if note.id in seen:
                        continue
                    seen.append(note.id)
                    on_message(note)
                backoff = 1
            except NotifyError as exc:
                self._report(topic, str(exc), stop, on_status)
            except Exception:
                self._report(topic, "Subscription failed; retrying", stop, on_status)
            if not self._is_current(stop) or stop.wait(backoff):
                break
            backoff = min(backoff * 2, 30)
        self._report(topic, "Disconnected", stop, on_status)
