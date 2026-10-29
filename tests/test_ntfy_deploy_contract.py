"""Static security contract for the upstream ntfy Docker deployment template.

The runtime readiness, secret handling and network-reachability checks are
separate acceptance gates: source assertions cannot prove live deployment.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "deploy" / "ntfy" / "compose.yaml"


def test_ntfy_deployment_is_isolated_and_pinned():
    content = COMPOSE.read_text(encoding="utf-8")
    assert "name: goreecloud-ntfy" in content
    assert re.search(r"binwiederhier/ntfy:v\d+\.\d+\.\d+@sha256:[0-9a-f]{64}", content)
    assert '"127.0.0.1:8792:8080"' in content
    assert "0.0.0.0:8792" not in content
    assert '"[::]:8792' not in content
    assert "NTFY_AUTH_DEFAULT_ACCESS: deny-all" in content
    assert "NTFY_AUTH_FILE: /var/lib/ntfy/auth.db" in content
    assert "NTFY_CACHE_FILE: /var/lib/ntfy/cache.db" in content
    assert "read_only: true" in content
    assert "no-new-privileges:true" in content
    assert "cap_drop:" in content and "- ALL" in content
    assert '"1001:1001"' in content
    assert "restart: unless-stopped" in content
    assert "/v1/ready" in content
    assert "NTFY_BEHIND_PROXY: \"false\"" in content


def test_ntfy_template_has_no_embedded_credentials_or_network_expansion():
    content = COMPOSE.read_text(encoding="utf-8")
    for forbidden in (
        "privileged: true", "network_mode: host", "NTFY_AUTH_USERS:",
        "NTFY_AUTH_TOKENS:", "NTFY_PASSWORD:", "PORKBUN_", "API_KEY",
        "secrets:", "NTFY_BASE_URL: https://",
    ):
        assert forbidden not in content, forbidden
    ignored = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "deploy/ntfy/data/" in ignored
    assert not (ROOT / "deploy" / "ntfy" / "data" / "auth.db").exists()
    assert not (ROOT / "deploy" / "ntfy" / "data" / "cache.db").exists()
