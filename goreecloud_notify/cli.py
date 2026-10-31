"""Command-line interface for GoreeCloud Notify (GTK-free).

Shares the native application's validated ntfy client and OS credential store.
No token CLI arguments, token environment variables, or plaintext token files.
"""
from __future__ import annotations

import argparse
import getpass
import json
import re
import sys
from contextlib import closing
from dataclasses import asdict
from typing import Sequence, TextIO

from .core import MAX_MESSAGE, NtfyClient, NotifyError, normalize_server, validate_topic
from .health import probe_health
from .storage import load_settings, load_token, save_settings, save_token

MAX_TOPICS = 50
CURSOR = re.compile(r"^(?:[A-Za-z0-9_-]{1,128}|[0-9]+[smhd])$")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="goreecloud-notify-cli",
        description="GoreeCloud Notify terminal client (native Python, no GTK required)",
    )
    parser.add_argument("--server", help="Use another HTTPS or loopback ntfy server for this command")
    parser.add_argument("--anonymous", action="store_true", help="Do not retrieve a keyring token")
    parser.add_argument("--version", action="version", version="GoreeCloud Notify CLI 0.1.0.dev0")
    commands = parser.add_subparsers(dest="command", required=True)

    config = commands.add_parser("config", help="Manage nonsecret connection settings")
    config_actions = config.add_subparsers(dest="operation", required=True)
    config_actions.add_parser("show", help="Print only saved server and topic metadata")
    server = config_actions.add_parser("set-server", help="Set default server")
    server.add_argument("url")

    topics = commands.add_parser("topics", help="Manage local topic subscriptions")
    topic_actions = topics.add_subparsers(dest="operation", required=True)
    topic_actions.add_parser("list")
    for name in ("add", "remove"):
        action = topic_actions.add_parser(name)
        action.add_argument("topic")

    auth = commands.add_parser("auth", help="Manage the OS-keyring bearer token")
    auth_actions = auth.add_subparsers(dest="operation", required=True)
    auth_actions.add_parser("status", help="Print whether a token exists; never the value")
    auth_actions.add_parser("set", help="Prompt for a token without terminal echo")
    auth_actions.add_parser("clear", help="Remove stored token for this server")

    health = commands.add_parser("health", help="Read ntfy server health")
    health.add_argument("--json", action="store_true", help="Emit a stable JSON result")

    publish = commands.add_parser("publish", help="Publish one notification")
    publish.add_argument("topic")
    publish.add_argument("message", nargs="?", help="Text (omit to read stdin; preferred for sensitive data)")
    publish.add_argument("--title", default="")
    publish.add_argument("--priority", type=int, choices=range(1, 6), metavar="1..5", default=3)
    publish.add_argument("--tags", default="")

    subscribe = commands.add_parser("subscribe", aliases=["listen"], help="Stream notifications as JSON Lines")
    subscribe.add_argument("topic")
    subscribe.add_argument("--since", default="10m", help="Replay cursor ID or duration, e.g. 10m")
    subscribe.add_argument("--count", type=int, help="Stop after this many notifications")
    return parser


def _server(args: argparse.Namespace, settings: dict) -> str:
    chosen = args.server or settings.get("server", "")
    if not chosen:
        raise NotifyError("No server configured. Run config set-server URL or pass --server")
    return normalize_server(chosen)


def _message_text(text: str | None, stream: TextIO) -> str:
    if text is None:
        if stream.isatty():
            raise NotifyError("Enter message text or pipe it through stdin")
        # A byte cap applies even when stdin is an unbounded pipe.
        if hasattr(stream, "buffer"):
            raw = stream.buffer.read(MAX_MESSAGE + 1)
            try:
                text = raw.decode("utf-8")
            except UnicodeError as exc:
                raise NotifyError("Message must be UTF-8") from exc
        else:
            text = stream.read(MAX_MESSAGE + 1)
    if not isinstance(text, str) or not text.strip() or len(text.encode("utf-8")) > MAX_MESSAGE:
        raise NotifyError("Message must contain 1–8192 UTF-8 bytes")
    return text


def run(args: argparse.Namespace, *, stdin: TextIO, stdout: TextIO) -> int:
    settings = load_settings()
    if args.command == "config":
        if args.operation == "show":
            print(json.dumps({"server": settings["server"], "topics": settings["topics"]},
                             sort_keys=True), file=stdout)
            return 0
        new_server = normalize_server(args.url)
        changed = new_server != settings["server"]
        save_settings({"server": new_server, "topics": [] if changed else settings["topics"]})
        print("Server configured" + ("; local topics cleared" if changed else ""), file=stdout)
        return 0

    if args.command == "topics":
        if args.operation == "list":
            for topic in settings["topics"]:
                print(topic, file=stdout)
            return 0
        topic = validate_topic(args.topic)
        topics = list(settings["topics"])
        if args.operation == "add":
            if topic not in topics:
                if len(topics) >= MAX_TOPICS:
                    raise NotifyError("At most 50 saved topics are supported")
                topics.append(topic)
        else:
            topics = [value for value in topics if value != topic]
        save_settings({"server": settings["server"], "topics": topics})
        print("Saved local topics; server ACLs unchanged", file=stdout)
        return 0

    server = _server(args, settings)
    if args.command == "auth":
        if args.operation == "status":
            present = bool(load_token(server))
            print("Token configured" if present else "No token configured", file=stdout)
        elif args.operation == "clear":
            save_token(server, "")
            print("OS keyring token cleared", file=stdout)
        else:
            if not sys.stdin.isatty():
                raise NotifyError("An interactive terminal is required to enter credentials")
            token = getpass.getpass("ntfy access token: ")
            if not token.strip() or "\n" in token or "\r" in token:
                raise NotifyError("Token must not be empty or contain newlines")
            save_token(server, token)
            print("Token saved in OS keyring", file=stdout)
        return 0

    token = "" if args.anonymous else load_token(server)
    client = NtfyClient(server, token)
    if args.command == "health":
        health = probe_health(client)
        if args.json:
            print(json.dumps({"healthy": health.healthy, "latency_ms": health.latency_ms},
                             sort_keys=True), file=stdout)
        else:
            print(("healthy" if health.healthy else "unhealthy") +
                  f" ({health.latency_ms} ms)", file=stdout)
        return 0 if health.healthy else 1
    if args.command == "publish":
        topic = validate_topic(args.topic)
        text = _message_text(args.message, stdin)
        client.publish(topic, text, title=args.title, priority=args.priority, tags=args.tags)
        print("Published to #" + topic, file=stdout)
        return 0
    if args.command in ("subscribe", "listen"):
        topic = validate_topic(args.topic)
        if not CURSOR.fullmatch(args.since):
            raise NotifyError("Invalid resume cursor")
        if args.count is not None and not 1 <= args.count <= 100000:
            raise NotifyError("Count must be between 1 and 100000")
        seen = 0
        # Explicit generator closure releases the underlying network response
        # when --count is reached (not just on interpreter garbage collection).
        with closing(client.stream(topic, args.since, lambda: False)) as events:
            for notification in events:
                print(json.dumps(asdict(notification), ensure_ascii=True, separators=(",", ":")),
                      file=stdout, flush=True)
                seen += 1
                if args.count is not None and seen >= args.count:
                    break
        return 0
    raise NotifyError("Unknown CLI operation")


def main(argv: Sequence[str] | None = None, *, stdin=None, stdout=None, stderr=None) -> int:
    stdin = sys.stdin if stdin is None else stdin
    stdout = sys.stdout if stdout is None else stdout
    stderr = sys.stderr if stderr is None else stderr
    args = build_parser().parse_args(argv)
    try:
        return run(args, stdin=stdin, stdout=stdout)
    except NotifyError as exc:
        print("GoreeCloud Notify: " + str(exc), file=stderr)
        return 2
    except KeyboardInterrupt:
        return 130
    except BrokenPipeError:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
