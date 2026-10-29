"""Minimal local settings storage; tokens are never written to JSON."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from .core import NotifyError, normalize_server, validate_topic


def config_path() -> Path:
    root = Path(os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config"))
    return root / "goreecloud" / "notify.json"


def load_settings(path: Path | None = None) -> dict:
    filename = path or config_path()
    if not filename.exists():
        return {"server": "", "topics": []}
    try:
        data = json.loads(filename.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("Expected object")
        server = normalize_server(data["server"]) if data.get("server") else ""
        topics = list(dict.fromkeys(validate_topic(t) for t in data.get("topics", [])))
        return {"server": server, "topics": topics[:50]}
    except (OSError, ValueError, TypeError, KeyError, NotifyError) as exc:
        raise NotifyError("Settings are invalid; repair ~/.config/goreecloud/notify.json") from exc


def save_settings(settings: dict, path: Path | None = None) -> None:
    filename = path or config_path()
    server = normalize_server(settings["server"]) if settings.get("server") else ""
    topics = list(dict.fromkeys(validate_topic(t) for t in settings.get("topics", [])))[:50]
    filename.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    # Atomic replacement prevents partial writes; config intentionally contains no token.
    fd, temporary = tempfile.mkstemp(prefix=".notify-", dir=filename.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump({"server": server, "topics": topics}, handle, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, filename)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _key(server: str) -> str:
    return normalize_server(server)


def load_token(server: str) -> str:
    if not server:
        return ""
    try:
        import keyring
        return keyring.get_password("GoreeCloud Notify", _key(server)) or ""
    except Exception as exc:
        raise NotifyError("OS credential store unavailable") from exc


def save_token(server: str, token: str) -> None:
    try:
        import keyring
        if token:
            if "\n" in token or "\r" in token:
                raise NotifyError("Invalid token")
            keyring.set_password("GoreeCloud Notify", _key(server), token)
        else:
            try:
                keyring.delete_password("GoreeCloud Notify", _key(server))
            except keyring.errors.PasswordDeleteError:
                pass
    except NotifyError:
        raise
    except Exception as exc:
        raise NotifyError("Cannot save token in OS credential store") from exc
