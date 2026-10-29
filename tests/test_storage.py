import json
import os
from pathlib import Path

import pytest

from goreecloud_notify.core import NotifyError
from goreecloud_notify.storage import load_settings, save_settings


def test_settings_roundtrip_and_permissions(tmp_path):
    path = tmp_path / "settings" / "notify.json"
    save_settings({"server": "https://ntfy.example.org", "topics": ["alerts", "alerts", "monitor"]}, path)
    assert load_settings(path) == {"server": "https://ntfy.example.org", "topics": ["alerts", "monitor"]}
    assert "token" not in path.read_text()
    assert os.stat(path).st_mode & 0o777 == 0o600


def test_corrupted_config_fails_closed(tmp_path):
    path = tmp_path / "notify.json"
    path.write_text('{"server": "http://public.example", "topics": []}')
    with pytest.raises(NotifyError):
        load_settings(path)


def test_default_missing_config(tmp_path):
    assert load_settings(tmp_path / "missing.json") == {"server": "", "topics": []}


def test_reject_unsafe_topic_and_preserve_old_config(tmp_path):
    path = tmp_path / "notify.json"
    save_settings({"server": "https://ntfy.example.org", "topics": ["good"]}, path)
    before = path.read_bytes()
    with pytest.raises(NotifyError):
        save_settings({"server": "https://ntfy.example.org", "topics": ["../../"]}, path)
    assert path.read_bytes() == before
