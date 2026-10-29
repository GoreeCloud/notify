"""CLI behavior tests. No network, GUI, production keys, or real notifications."""
from __future__ import annotations

import io
import json
from types import SimpleNamespace
from dataclasses import dataclass

import pytest
from goreecloud_notify import cli


@dataclass(frozen=True)
class Note:
    id: str
    topic: str
    message: str
    title: str = ""
    priority: int = 3
    time: int = 0
    tags: tuple[str, ...] = ()


@pytest.fixture
def setup(monkeypatch):
    state = {"server": "https://notify.example.test", "topics": ["alerts"]}
    keys = {state["server"]: "local-test-token"}
    observed = []

    class FakeClient:
        def __init__(self, server, token):
            self.server, self.token = server, token
            observed.append(("client", server, token))

        def publish(self, topic, text, **kwargs):
            observed.append(("publish", topic, text, kwargs))

        def stream(self, topic, since, stop):
            observed.append(("stream", topic, since))
            yield Note("n1", topic, "hello")
            yield Note("n2", topic, "another")
            yield Note("n3", topic, "third")

    monkeypatch.setattr(cli, "load_settings", lambda: {"server": state["server"], "topics": list(state["topics"])})
    def save(settings):
        state.update(settings)
        observed.append(("save", dict(settings)))
    monkeypatch.setattr(cli, "save_settings", save)
    monkeypatch.setattr(cli, "load_token", lambda server: keys.get(server, ""))
    monkeypatch.setattr(cli, "save_token", lambda server, token: keys.__setitem__(server, token))
    monkeypatch.setattr(cli, "NtfyClient", FakeClient)
    monkeypatch.setattr(cli, "probe_health", lambda client: SimpleNamespace(healthy=True, latency_ms=12))
    return state, keys, observed


def invoke(*argv, stdin=None):
    output, errors = io.StringIO(), io.StringIO()
    code = cli.main(list(argv), stdin=stdin or io.StringIO(""), stdout=output, stderr=errors)
    return code, output.getvalue(), errors.getvalue()


def test_config_show_never_exposes_token(setup):
    state, keys, observed = setup
    code, out, err = invoke("config", "show")
    assert code == 0 and json.loads(out) == state
    assert "local-test-token" not in out and not err


def test_setting_new_server_clears_previous_topics_without_copying_token(setup):
    state, keys, observed = setup
    code, _, _ = invoke("config", "set-server", "https://another.example.test")
    assert code == 0
    assert state == {"server": "https://another.example.test", "topics": []}
    assert keys.get("https://another.example.test") is None


def test_topic_local_list_add_dedupe_and_remove(setup):
    state, keys, observed = setup
    assert invoke("topics", "add", "alerts")[0] == 0
    assert invoke("topics", "add", "builds")[0] == 0
    assert state["topics"] == ["alerts", "builds"]
    assert invoke("topics", "list")[1] == "alerts\nbuilds\n"
    assert invoke("topics", "remove", "alerts")[0] == 0
    assert state["topics"] == ["builds"]


def test_invalid_topics_fail_without_state_mutation(setup):
    state, keys, observed = setup
    code, output, error = invoke("topics", "add", "../../escape")
    assert code == 2
    assert state["topics"] == ["alerts"]
    assert output == ""
    assert "token" not in error.lower()


def test_health_json_and_unhealthy_exit(setup, monkeypatch):
    state, keys, observed = setup
    code, output, error = invoke("health", "--json")
    assert code == 0 and json.loads(output) == {"healthy": True, "latency_ms": 12}
    assert observed[0] == ("client", state["server"], "local-test-token")
    monkeypatch.setattr(cli, "probe_health", lambda _: SimpleNamespace(healthy=False, latency_ms=9))
    assert invoke("health", "--json")[0] == 1


def test_anonymous_does_not_forward_secret(setup):
    state, keys, observed = setup
    assert invoke("--anonymous", "health")[0] == 0
    assert observed[-1] == ("client", state["server"], "")


def test_explicit_server_uses_only_its_keyring_identity(setup):
    state, keys, observed = setup
    code, output, error = invoke("--server", "https://other.example.test", "health")
    assert code == 0
    assert observed[-1] == ("client", "https://other.example.test", "")


def test_publish_piped_stdin_and_priority(setup):
    state, keys, observed = setup
    code, output, error = invoke("publish", "alerts", "--priority", "5", stdin=io.StringIO("hello\n"))
    assert code == 0
    assert observed[-1] == ("publish", "alerts", "hello\n", {"title": "", "priority": 5, "tags": ""})
    assert output == "Published to #alerts\n"


def test_publish_rejects_unicode_over_byte_limit(setup):
    state, keys, observed = setup
    code, output, error = invoke("publish", "alerts", "🙂" * 2100)
    assert code == 2 and "UTF-8 bytes" in error
    assert not any(o[0] == "publish" for o in observed)


def test_subscribe_count_outputs_machine_readable_jsonl(setup):
    state, keys, observed = setup
    code, output, error = invoke("subscribe", "alerts", "--count", "2", "--since", "10m")
    assert code == 0
    lines = output.splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["id"] == "n1"
    assert json.loads(lines[1])["id"] == "n2"
    assert observed[-1] == ("stream", "alerts", "10m")


def test_invalid_resume_cursor_and_count_rejected(setup):
    state, keys, observed = setup
    assert invoke("subscribe", "alerts", "--since", "../../secret")[0] == 2
    assert invoke("subscribe", "alerts", "--count", "0")[0] == 2
    assert not any(o[0] == "stream" for o in observed)


def test_auth_status_and_clear_never_expose_token(setup):
    state, keys, observed = setup
    assert invoke("auth", "status")[1] == "Token configured\n"
    assert invoke("auth", "clear")[0] == 0
    assert keys[state["server"]] == ""
    assert invoke("auth", "status")[1] == "No token configured\n"


def test_noninteractive_keyring_write_is_rejected(setup, monkeypatch):
    state, keys, observed = setup
    monkeypatch.setattr(cli.sys, "stdin", io.StringIO("secret"))
    code, output, error = invoke("auth", "set")
    assert code == 2 and "interactive terminal" in error
    assert keys[state["server"]] == "local-test-token"


def test_parser_has_no_token_or_password_flag():
    parser = cli.build_parser()
    assert "--token" not in parser.format_help()
    assert "--password" not in parser.format_help()


def test_auth_set_prompts_without_echo_or_command_arguments(setup, monkeypatch):
    state, keys, observed = setup

    class Interactive(io.StringIO):
        def isatty(self):
            return True

    monkeypatch.setattr(cli.sys, "stdin", Interactive())
    monkeypatch.setattr(cli.getpass, "getpass", lambda prompt: "synthetic-token-123")
    code, output, error = invoke("auth", "set")
    assert code == 0
    assert keys[state["server"]] == "synthetic-token-123"
    assert "synthetic-token-123" not in output + error


def test_stream_is_closed_after_count_limit(setup, monkeypatch):
    state, keys, observed = setup
    finished = []

    class ClosingClient:
        def __init__(self, server, token):
            pass

        def stream(self, topic, since, stop):
            try:
                yield Note("first", topic, "A")
                yield Note("second", topic, "B")
            finally:
                finished.append(True)

    monkeypatch.setattr(cli, "NtfyClient", ClosingClient)
    assert invoke("subscribe", "alerts", "--count", "1")[0] == 0
    assert finished == [True]


def test_binary_stdin_has_strict_byte_limit(setup):
    state, keys, observed = setup
    huge = io.TextIOWrapper(io.BytesIO(b"x" * 8193), encoding="utf-8")
    code, output, error = invoke("publish", "alerts", stdin=huge)
    assert code == 2
    assert "UTF-8 bytes" in error
    assert not any(o[0] == "publish" for o in observed)


def test_invalid_binary_utf8_is_rejected_without_publishing(setup):
    state, keys, observed = setup
    invalid = io.TextIOWrapper(io.BytesIO(b"\xff\xfe"), encoding="utf-8")
    code, output, error = invoke("publish", "alerts", stdin=invalid)
    assert code == 2
    assert "UTF-8" in error
    assert not any(o[0] == "publish" for o in observed)


def test_remote_http_is_not_accepted_as_server(setup):
    state, keys, observed = setup
    code, output, error = invoke("config", "set-server", "http://remote.example.test")
    assert code == 2
    assert state["server"] == "https://notify.example.test"


def test_cli_import_does_not_load_gtk():
    import subprocess
    import sys
    from pathlib import Path
    root = str(Path(__file__).resolve().parents[1])
    result = subprocess.run(
        [sys.executable, "-c", "import goreecloud_notify.cli,sys; "
         "assert 'gi' not in sys.modules; print('no Gtk dependency')"],
        cwd=root, capture_output=True, text=True, timeout=5, check=True,
    )
    assert "no Gtk dependency" in result.stdout
