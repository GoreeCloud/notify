#!/usr/bin/env python3
"""Read-only target evidence collector for GoreeCloud Notify production readiness."""
from __future__ import annotations

import argparse
import ipaddress
import json
import re
import socket
import stat
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

CSP = "; ".join((
    "default-src 'self'",
    "base-uri 'none'",
    "object-src 'none'",
    "frame-ancestors 'none'",
    "frame-src 'none'",
    "form-action 'self'",
    "script-src 'self'",
    "style-src 'self'",
    "img-src 'self' data:",
    "font-src 'self'",
    "connect-src 'self'",
    "media-src 'none'",
    "worker-src 'none'",
    "manifest-src 'self'",
))
PERMISSIONS_POLICY = "camera=(), microphone=(), geolocation=(), payment=(), usb=()"
STRICT_TRANSPORT_SECURITY = "max-age=31536000"
WARDVEIL_HEADER = "X-Wardveil-Security"
WARDVEIL_STATUS = "Protected by Wardveil"
REQUEST_ID_HEADER = "X-Request-ID"
REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9._:-]{0,62}[A-Za-z0-9])?$")
APP_ICON_PATH = "/brand/goreecloud-notify-icon.svg"
MANIFEST_PATH = "/manifest.webmanifest"
APP_ICON_CACHE_CONTROL = "public, max-age=86400, must-revalidate"
MANIFEST_CACHE_CONTROL = "public, max-age=3600, must-revalidate"
CURRENT_RELEASE_STAGE = "release_candidate"
CURRENT_ACCEPTANCE_STATUS = "pending"
CURRENT_ACCEPTANCE_GATES = {
    "backup_restore": "pending",
    "independent_monitoring": "pending",
    "target_runtime_publication": "pending",
    "manual_browser_os": "pending",
}
NETBIRD = ipaddress.ip_network("100.64.0.0/10")
REVISION_RE = re.compile(r"^[0-9a-f]{40}$")
OCI_IMAGE_TITLE = "GoreeCloud Notify"
OCI_IMAGE_SOURCE = "https://github.com/GoreeCloud/notify"
OCI_IMAGE_LICENSE = "AGPL-3.0-only"
LOG_MARKERS = {
    "authorization_header": re.compile(r"\bauthorization\s*:", re.I),
    "bearer_token": re.compile(r"\bbearer\s+[A-Za-z0-9._~+/=-]{8,}", re.I),
    "cookie_header": re.compile(r"\b(?:set-)?cookie\s*:", re.I),
    "admin_token_assignment": re.compile(r"\bGOREECLOUD_NOTIFY_ADMIN_TOKEN\s*=", re.I),
    "password_assignment": re.compile(r"\bpassword\s*=", re.I),
}


def command(*parts: str) -> str:
    result = subprocess.run(parts, check=True, text=True, capture_output=True)
    return result.stdout.strip()


def dinspect(container: str, template: str) -> str:
    return command("docker", "inspect", "--format", template, container)


def decoded(value: str, default):
    return default if not value or value == "<no value>" else json.loads(value)


def add(checks: list[dict[str, str]], name: str, ok: bool, good: str, bad: str) -> None:
    checks.append(
        {
            "name": name,
            "status": "pass" if ok else "fail",
            "detail": good if ok else bad,
        }
    )


def response_security_headers(headers) -> None:
    expected = {
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "no-referrer",
        "Content-Security-Policy": CSP,
        "X-Frame-Options": "DENY",
        "Permissions-Policy": PERMISSIONS_POLICY,
        "Strict-Transport-Security": STRICT_TRANSPORT_SECURITY,
        "Cross-Origin-Opener-Policy": "same-origin",
        "Cross-Origin-Resource-Policy": "same-origin",
        "Origin-Agent-Cluster": "?1",
        "X-Permitted-Cross-Domain-Policies": "none",
        WARDVEIL_HEADER: WARDVEIL_STATUS,
    }
    for name, value in expected.items():
        if headers.get(name) != value:
            raise AssertionError(f"unexpected {name}")

    request_id = headers.get(REQUEST_ID_HEADER)
    if not request_id or not REQUEST_ID_RE.fullmatch(request_id):
        raise AssertionError(f"invalid or missing {REQUEST_ID_HEADER}")


def private_headers(headers) -> None:
    if headers.get("Cache-Control") != "no-store" or headers.get("Pragma") != "no-cache":
        raise AssertionError("private cache policy is missing")
    response_security_headers(headers)


def validate_release_meta(meta: dict[str, object], expected_revision: str) -> None:
    if meta.get("runtime_environment") != "production":
        raise AssertionError("runtime environment is not production")
    if meta.get("production") is not True or meta.get("production_configuration") is not True:
        raise AssertionError("production configuration metadata is not active")
    if meta.get("build_revision") != expected_revision:
        raise AssertionError("production metadata revision mismatch")
    if meta.get("release_stage") != CURRENT_RELEASE_STAGE:
        raise AssertionError("unexpected release stage")
    if meta.get("production_accepted") is not False:
        raise AssertionError("target candidate unexpectedly reports production acceptance")
    if meta.get("acceptance_status") != CURRENT_ACCEPTANCE_STATUS:
        raise AssertionError("unexpected production acceptance status")
    if meta.get("acceptance_gates") != CURRENT_ACCEPTANCE_GATES:
        raise AssertionError("production acceptance gates do not match the current source contract")

    security = meta.get("security_identity")
    if not isinstance(security, dict):
        raise AssertionError("Wardveil security identity metadata is missing")
    if (
        security.get("name") != "Wardveil Security"
        or security.get("full_presentation") != "Wardveil Security by GoreeCloud"
        or security.get("protection_status") != WARDVEIL_STATUS
    ):
        raise AssertionError("Wardveil security identity metadata is inconsistent")
    authority = security.get("authority")
    if not isinstance(authority, str) or not authority.strip():
        raise AssertionError("application security authority metadata is missing")

    observability = meta.get("observability")
    if not isinstance(observability, dict):
        raise AssertionError("observability metadata is missing")
    if (
        observability.get("request_correlation_header") != REQUEST_ID_HEADER
        or observability.get("structured_http_events") is not True
        or observability.get("sensitive_request_data_logged") is not False
    ):
        raise AssertionError("observability metadata is inconsistent")


def validate_image_identity(labels: dict[str, object], expected_revision: str) -> None:
    expected = {
        "org.opencontainers.image.title": OCI_IMAGE_TITLE,
        "org.opencontainers.image.source": OCI_IMAGE_SOURCE,
        "org.opencontainers.image.licenses": OCI_IMAGE_LICENSE,
        "org.opencontainers.image.revision": expected_revision,
    }
    for name, value in expected.items():
        if labels.get(name) != value:
            raise AssertionError(f"OCI image identity mismatch for {name}")


def request(
    base: str,
    path: str,
    *,
    method: str = "GET",
    headers=None,
    expected: int = 200,
):
    req = urllib.request.Request(
        urllib.parse.urljoin(base.rstrip("/") + "/", path.lstrip("/")),
        headers={"User-Agent": "goreecloud-notify-target-preflight/2", **(headers or {})},
        method=method,
    )
    try:
        response = urllib.request.urlopen(req, timeout=8)
    except urllib.error.HTTPError as exc:
        if exc.code != expected:
            raise AssertionError(f"{method} {path} returned {exc.code}, expected {expected}") from exc
        return exc.read(), exc.headers
    with response:
        if response.status != expected:
            raise AssertionError(f"{method} {path} returned {response.status}, expected {expected}")
        return response.read(), response.headers


def host_checks(args, checks: list[dict[str, str]]) -> None:
    try:
        user = dinspect(args.container, "{{.Config.User}}")
        add(
            checks,
            "container_user",
            user == "10001:10001",
            "runtime user is 10001:10001",
            f"runtime user is {user!r}",
        )
        ro = dinspect(args.container, "{{.HostConfig.ReadonlyRootfs}}").lower()
        add(
            checks,
            "read_only_rootfs",
            ro == "true",
            "root filesystem is read-only",
            "root filesystem is writable",
        )
        pids = int(dinspect(args.container, "{{.HostConfig.PidsLimit}}"))
        add(checks, "pids_limit", pids == 256, "PID limit is 256", f"PID limit is {pids}")
        sec = decoded(dinspect(args.container, "{{json .HostConfig.SecurityOpt}}"), [])
        add(
            checks,
            "no_new_privileges",
            any(str(x).startswith("no-new-privileges") for x in sec),
            "no-new-privileges is enabled",
            "no-new-privileges is absent",
        )
        caps = decoded(dinspect(args.container, "{{json .HostConfig.CapDrop}}"), [])
        add(
            checks,
            "capabilities",
            "ALL" in caps,
            "all Linux capabilities are dropped",
            f"capability drop set is {caps!r}",
        )
        ports = decoded(dinspect(args.container, "{{json .HostConfig.PortBindings}}"), {})
        add(
            checks,
            "host_ports",
            not ports,
            "no host ports are published",
            f"host port bindings are present: {sorted(ports)}",
        )
        mode = dinspect(args.container, "{{.HostConfig.NetworkMode}}")
        networks = sorted(decoded(dinspect(args.container, "{{json .NetworkSettings.Networks}}"), {}))
        add(
            checks,
            "docker_networks",
            mode == "proxy" and networks == ["proxy"],
            "container is attached only to proxy",
            f"network mode={mode!r}, attached={networks!r}",
        )
        tmpfs = decoded(dinspect(args.container, "{{json .HostConfig.Tmpfs}}"), {})
        tmp = str(tmpfs.get("/tmp", ""))
        add(
            checks,
            "tmpfs",
            "/tmp" in tmpfs and "noexec" in tmp and "nosuid" in tmp,
            "/tmp uses noexec,nosuid tmpfs",
            f"unexpected /tmp tmpfs: {tmpfs!r}",
        )
        health = dinspect(args.container, "{{.State.Health.Status}}")
        add(
            checks,
            "container_health",
            health == "healthy",
            "container is healthy",
            f"container health is {health!r}",
        )
        mounts = decoded(dinspect(args.container, "{{json .Mounts}}"), [])
        data = [
            mount
            for mount in mounts
            if mount.get("Destination") == "/data" and mount.get("Type") == "bind"
        ]
        mount_ok = len(data) == 1 and Path(data[0].get("Source", "")).resolve() == args.data_dir
        add(
            checks,
            "data_mount",
            mount_ok,
            f"/data is bound from {args.data_dir}",
            "/data bind does not match approved data directory",
        )
        image_ref = dinspect(args.container, "{{.Config.Image}}")
        image_id = dinspect(args.container, "{{.Image}}")
        checks += [
            {"name": "container_image_ref", "status": "pass", "detail": image_ref},
            {"name": "container_image_id", "status": "pass", "detail": image_id},
        ]
        revision = command(
            "docker",
            "image",
            "inspect",
            "--format",
            '{{ index .Config.Labels "org.opencontainers.image.revision" }}',
            image_id,
        )
        add(
            checks,
            "image_revision",
            revision == args.expected_revision,
            f"OCI image revision matches {args.expected_revision}",
            f"OCI image revision is {revision!r}",
        )
        labels = decoded(
            command(
                "docker",
                "image",
                "inspect",
                "--format",
                "{{json .Config.Labels}}",
                image_id,
            ),
            {},
        )
        try:
            validate_image_identity(labels, args.expected_revision)
        except AssertionError as exc:
            add(checks, "image_identity", False, "", str(exc))
        else:
            add(
                checks,
                "image_identity",
                True,
                "OCI title, source, license, and exact revision identify GoreeCloud Notify",
                "",
            )
        repo_digests = decoded(
            command(
                "docker",
                "image",
                "inspect",
                "--format",
                "{{json .RepoDigests}}",
                image_id,
            ),
            [],
        )
        checks.append(
            {
                "name": "container_image_repo_digests",
                "status": "pass",
                "detail": ", ".join(sorted(str(item) for item in repo_digests)) or "unavailable",
            }
        )
    except (OSError, subprocess.CalledProcessError, ValueError, json.JSONDecodeError) as exc:
        add(
            checks,
            "docker_runtime_inspection",
            False,
            "",
            f"runtime inspection failed: {type(exc).__name__}",
        )

    for path, kind in (
        (args.env_file, "env"),
        (args.data_dir, "data"),
        (args.data_dir / "goreecloud_notify.db", "database"),
    ):
        try:
            info = path.stat()
            mode_bits = stat.S_IMODE(info.st_mode)
            owner = f"{info.st_uid}:{info.st_gid}"
            if kind == "env":
                add(
                    checks,
                    "env_file_mode",
                    mode_bits in {0o600, 0o640},
                    f"protected environment file mode is {mode_bits:04o}",
                    f"protected environment file mode is {mode_bits:04o}; expected 0600 or 0640",
                )
                checks.append({"name": "env_file_owner", "status": "pass", "detail": owner})
            else:
                add(
                    checks,
                    f"{kind}_owner",
                    owner == "10001:10001",
                    f"{kind} owner/group is 10001:10001",
                    f"{kind} owner/group is {owner}",
                )
                perms_ok = (
                    (mode_bits & 0o007) == 0
                    and bool(mode_bits & 0o200)
                    and (kind != "data" or bool(mode_bits & 0o100))
                )
                add(
                    checks,
                    f"{kind}_mode",
                    perms_ok,
                    f"{kind} mode {mode_bits:04o} is restrictive",
                    f"{kind} mode {mode_bits:04o} is too broad or not owner-writable",
                )
        except OSError as exc:
            add(
                checks,
                f"{kind}_path",
                False,
                "",
                f"cannot stat {kind} path: {exc.strerror}",
            )

    try:
        log_text = command("docker", "logs", "--tail", str(args.log_lines), args.container)
        found = {
            name: len(pattern.findall(log_text))
            for name, pattern in LOG_MARKERS.items()
            if pattern.search(log_text)
        }
        add(
            checks,
            "runtime_log_scan",
            not found,
            f"last {args.log_lines} log lines contain no protected-value marker patterns",
            f"protected-value marker counts detected without printing matched content: {found}",
        )
    except (OSError, subprocess.CalledProcessError):
        add(checks, "runtime_log_scan", False, "", "could not read bounded container logs")


def network_checks(args, checks: list[dict[str, str]]) -> None:
    parsed = urllib.parse.urlparse(args.base_url)
    add(
        checks,
        "https_scheme",
        parsed.scheme == "https",
        "target origin uses HTTPS",
        "target origin is not HTTPS",
    )
    if parsed.scheme != "https" or not parsed.hostname:
        return

    try:
        addresses = sorted(
            {
                item[4][0]
                for item in socket.getaddrinfo(
                    parsed.hostname,
                    443,
                    socket.AF_INET,
                    socket.SOCK_STREAM,
                )
            }
        )
        private = bool(addresses) and all(
            ipaddress.ip_address(address) in NETBIRD for address in addresses
        )
        add(
            checks,
            "private_dns",
            private,
            f"{parsed.hostname} resolves only inside NetBird IPv4 space: {', '.join(addresses)}",
            (
                f"{parsed.hostname} resolved outside NetBird IPv4 space: "
                f"{', '.join(addresses) or 'no IPv4 answer'}"
            ),
        )
    except (OSError, ValueError) as exc:
        add(checks, "private_dns", False, "", f"DNS resolution failed: {type(exc).__name__}")

    try:
        body, headers = request(args.base_url, "/healthz")
        private_headers(headers)
        health = json.loads(body)
        if health.get("status") != "ok" or "build_revision" in health:
            raise AssertionError("unexpected health payload")
        add(
            checks,
            "https_health",
            True,
            "verified-TLS /healthz, Wardveil/correlation, HSTS, isolation, and private headers passed",
            "",
        )

        body, headers = request(args.base_url, "/api/v1/meta")
        private_headers(headers)
        meta = json.loads(body)
        if not isinstance(meta, dict):
            raise AssertionError("production metadata is not an object")
        validate_release_meta(meta, args.expected_revision)
        add(
            checks,
            "https_meta",
            True,
            "production configuration, exact revision, Wardveil observability, and release-candidate acceptance metadata passed",
            "",
        )

        for path, name in (
            ("/api/v1/me", "unauthenticated_session"),
            ("/api/v1/inbox/stream", "unauthenticated_sse"),
        ):
            _, headers = request(args.base_url, path, expected=401)
            private_headers(headers)
            add(
                checks,
                name,
                True,
                f"unauthenticated {path} is denied with current private/security headers",
                "",
            )

        index, headers = request(args.base_url, "/")
        private_headers(headers)
        index_text = index.decode()
        match = re.search(r'(?:src|href)="(/assets/[^"]+)"', index_text)
        if not match:
            raise AssertionError("production index has no built asset")
        if f'href="{MANIFEST_PATH}"' not in index_text:
            raise AssertionError("production index does not reference the canonical manifest")
        if f'href="{APP_ICON_PATH}"' not in index_text:
            raise AssertionError("production index does not reference the canonical application icon")

        _, headers = request(args.base_url, match.group(1))
        response_security_headers(headers)
        cache = headers.get("Cache-Control", "")
        if (
            "immutable" not in cache
            or "max-age=31536000" not in cache
            or headers.get("Pragma") is not None
        ):
            raise AssertionError("asset cache policy mismatch")
        add(
            checks,
            "frontend_cache_policy",
            True,
            "HTML is no-store and built assets are immutable under the current security header contract",
            "",
        )

        manifest_body, manifest_headers = request(args.base_url, MANIFEST_PATH)
        response_security_headers(manifest_headers)
        if manifest_headers.get("Cache-Control") != MANIFEST_CACHE_CONTROL:
            raise AssertionError("manifest cache policy mismatch")
        if not manifest_headers.get("Content-Type", "").startswith("application/manifest+json"):
            raise AssertionError("manifest media type mismatch")
        manifest = json.loads(manifest_body)
        if (
            manifest.get("id") != "/"
            or manifest.get("name") != "GoreeCloud Notify"
            or not isinstance(manifest.get("icons"), list)
            or not manifest["icons"]
            or manifest["icons"][0].get("src") != APP_ICON_PATH
        ):
            raise AssertionError("manifest application identity mismatch")

        icon_body, icon_headers = request(args.base_url, APP_ICON_PATH)
        response_security_headers(icon_headers)
        if icon_headers.get("Cache-Control") != APP_ICON_CACHE_CONTROL:
            raise AssertionError("application icon cache policy mismatch")
        if not icon_headers.get("Content-Type", "").startswith("image/svg+xml"):
            raise AssertionError("application icon media type mismatch")
        if not icon_body.lstrip().startswith(b"<svg"):
            raise AssertionError("application icon payload is not SVG")
        add(
            checks,
            "application_identity",
            True,
            "canonical manifest and application icon resolve through final HTTPS with current identity/cache/security contract",
            "",
        )

        _, headers = request(
            args.base_url,
            "/api/v1/meta",
            method="OPTIONS",
            headers={
                "Origin": args.base_url.rstrip("/"),
                "Access-Control-Request-Method": "GET",
            },
        )
        private_headers(headers)
        if (
            headers.get("Access-Control-Allow-Origin") != args.base_url.rstrip("/")
            or headers.get("Access-Control-Allow-Credentials") != "true"
        ):
            raise AssertionError("CORS mismatch")
        add(
            checks,
            "same_origin_cors",
            True,
            "same-origin credentialed CORS preflight passed with current security headers",
            "",
        )
    except (
        AssertionError,
        urllib.error.URLError,
        json.JSONDecodeError,
        TimeoutError,
        UnicodeDecodeError,
    ) as exc:
        add(checks, "https_private_path", False, "", f"HTTPS validation failed: {exc}")


def self_test() -> None:
    checks: list[dict[str, str]] = []
    add(checks, "yes", True, "ok", "bad")
    add(checks, "no", False, "ok", "expected")
    assert REVISION_RE.fullmatch("a" * 40)
    assert not REVISION_RE.fullmatch("development")
    validate_image_identity(
        {
            "org.opencontainers.image.title": OCI_IMAGE_TITLE,
            "org.opencontainers.image.source": OCI_IMAGE_SOURCE,
            "org.opencontainers.image.licenses": OCI_IMAGE_LICENSE,
            "org.opencontainers.image.revision": "a" * 40,
        },
        "a" * 40,
    )
    try:
        validate_image_identity(
            {
                "org.opencontainers.image.title": OCI_IMAGE_TITLE,
                "org.opencontainers.image.source": "https://example.invalid/not-notify",
                "org.opencontainers.image.licenses": OCI_IMAGE_LICENSE,
                "org.opencontainers.image.revision": "a" * 40,
            },
            "a" * 40,
        )
    except AssertionError:
        pass
    else:
        raise AssertionError("image identity validator accepted the wrong OCI source")
    assert ipaddress.ip_address("100.71.27.119") in NETBIRD
    assert ipaddress.ip_address("135.148.45.22") not in NETBIRD

    response_headers = {
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "no-referrer",
        "Content-Security-Policy": CSP,
        "X-Frame-Options": "DENY",
        "Permissions-Policy": PERMISSIONS_POLICY,
        "Strict-Transport-Security": STRICT_TRANSPORT_SECURITY,
        "Cross-Origin-Opener-Policy": "same-origin",
        "Cross-Origin-Resource-Policy": "same-origin",
        "Origin-Agent-Cluster": "?1",
        "X-Permitted-Cross-Domain-Policies": "none",
        WARDVEIL_HEADER: WARDVEIL_STATUS,
        REQUEST_ID_HEADER: "a" * 32,
    }
    private_headers(
        {
            **response_headers,
            "Cache-Control": "no-store",
            "Pragma": "no-cache",
        }
    )
    validate_release_meta(
        {
            "runtime_environment": "production",
            "production": True,
            "production_configuration": True,
            "build_revision": "a" * 40,
            "release_stage": CURRENT_RELEASE_STAGE,
            "production_accepted": False,
            "acceptance_status": CURRENT_ACCEPTANCE_STATUS,
            "acceptance_gates": dict(CURRENT_ACCEPTANCE_GATES),
            "security_identity": {
                "name": "Wardveil Security",
                "full_presentation": "Wardveil Security by GoreeCloud",
                "protection_status": WARDVEIL_STATUS,
                "authority": "GoreeCloud Notify application security controls remain authoritative",
            },
            "observability": {
                "request_correlation_header": REQUEST_ID_HEADER,
                "structured_http_events": True,
                "sensitive_request_data_logged": False,
            },
        },
        "a" * 40,
    )
    assert not any(pattern.search("INFO startup complete") for pattern in LOG_MARKERS.values())
    assert LOG_MARKERS["bearer_token"].search("Authorization: Bearer synthetic-secret-value")
    print("target preflight self-test passed")


def arguments():
    parser = argparse.ArgumentParser(
        description="Read-only GoreeCloud Notify target production preflight"
    )
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--scope", choices=("host", "network", "all"), default="all")
    parser.add_argument("--base-url")
    parser.add_argument("--expected-revision")
    parser.add_argument("--container", default="goreecloud-notify")
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--log-lines", type=int, default=500)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("goreecloud-notify-target-preflight.json"),
    )
    args = parser.parse_args()
    if args.self_test:
        return args

    required = {"--expected-revision": args.expected_revision}
    if args.scope in {"network", "all"}:
        required["--base-url"] = args.base_url
    if args.scope in {"host", "all"}:
        required.update({"--data-dir": args.data_dir, "--env-file": args.env_file})
    missing = [key for key, value in required.items() if value is None or value == ""]
    if missing:
        parser.error("missing required arguments: " + ", ".join(missing))
    if not REVISION_RE.fullmatch(args.expected_revision):
        parser.error("--expected-revision must be an exact 40-character lowercase Git SHA")
    if not 1 <= args.log_lines <= 5000:
        parser.error("--log-lines must be between 1 and 5000")
    if args.data_dir is not None:
        args.data_dir = args.data_dir.resolve()
    if args.env_file is not None:
        args.env_file = args.env_file.resolve()
    args.output = args.output.resolve()
    return args


def main() -> int:
    args = arguments()
    if args.self_test:
        self_test()
        return 0

    checks: list[dict[str, str]] = []
    if args.scope in {"host", "all"}:
        host_checks(args, checks)
    if args.scope in {"network", "all"}:
        network_checks(args, checks)
    ok = bool(checks) and all(item["status"] == "pass" for item in checks)
    report = {
        "schema": "goreecloud-notify-target-preflight-v2",
        "generated_at": datetime.now(ZoneInfo("America/Chicago")).isoformat(),
        "scope": args.scope,
        "base_url": args.base_url,
        "expected_revision": args.expected_revision,
        "container": args.container if args.scope in {"host", "all"} else None,
        "data_dir": str(args.data_dir) if args.data_dir else None,
        "env_file": str(args.env_file) if args.env_file else None,
        "result": "pass" if ok else "fail",
        "checks": checks,
        "limitations": [
            "No authenticated browser/session acceptance is proven.",
            "Approved-versus-denied NetBird access from two real source locations is not proven.",
            "Long-lived authenticated SSE, revocation/expiry, and prolonged network interruption recovery are not proven.",
            "Backup/restore, Uptime Kuma/out-of-band alerting, producer migration, and ntfy rollback are not proven.",
            "The bounded log marker scan is a regression aid, not exhaustive secret-leak proof.",
            "A passing candidate preflight does not advance release_stage or production_accepted.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    for item in checks:
        print(f"[{item['status'].upper()}] {item['name']}: {item['detail']}")
    print(f"Evidence written to {args.output}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
