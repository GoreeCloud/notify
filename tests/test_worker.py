import threading

from goreecloud_notify.core import Notification
from goreecloud_notify.worker import SubscriptionManager


def test_stop_is_safe_before_start():
    manager = SubscriptionManager(lambda n: None, lambda a, b: None)
    manager.stop()
    assert manager._stop.is_set()


def test_worker_deduplicates_stream_events(monkeypatch):
    got = []
    topic = "alerts"
    class Client:
        def __init__(self, server, token):
            pass
        def stream(self, value, since, stop, on_open=None):
            assert value == topic
            if on_open:
                on_open()
            for id in ("same", "same", "other"):
                yield Notification(id, topic, "body", "", 3, 1)
            manager._stop.set()
    monkeypatch.setattr("goreecloud_notify.worker.NtfyClient", Client)
    manager = SubscriptionManager(got.append, lambda *args: None)
    manager._listen("https://ntfy.example.org", topic, "", manager._stop)
    assert [n.id for n in got] == ["same", "other"]
