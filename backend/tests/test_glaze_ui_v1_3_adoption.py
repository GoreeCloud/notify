from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LEDGER = ROOT / "docs" / "glaze-ui-v1.3-adoption.json"


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _ledger() -> dict:
    return json.loads(LEDGER.read_text(encoding="utf-8"))


def test_notify_preserves_v1_3_source_mapping_as_historical_evidence() -> None:
    ledger = _ledger()
    assert ledger["application"] == "goreecloud-notify"
    assert ledger["target_release"] == "1.3.0"
    assert ledger["baseline_release"] == "1.2.0"
    assert ledger["canonical_repository"] == "GoreeCloud/goreecloud-glaze-ui"
    assert ledger["canonical_revision"] == "fc7cc91d2eace8da2371371c2855c24cbcb326a1"
    assert ledger["adoption_status"] == "historical-source-mapping-superseded"
    assert ledger["superseded_by"] == "docs/glaze-ui-v1.6.0-adoption.json"
    assert ledger["conformance_claim"] is False
    assert ledger["stable_eligible"] is False


def test_v1_3_current_source_mapping_is_superseded_by_v1_6_0() -> None:
    css = _read("frontend/src/glaze-contract.css")
    main = _read("frontend/src/main.tsx")
    index = _read("frontend/index.html")
    dart = _read("client/lib/glaze_theme.dart")

    assert '--glaze-ui-version: "1.6.0"' in css
    assert '--glaze-ui-version: "1.3.0"' not in css
    assert "dataset.glazeUi = '1.6.0'" in main
    assert "dataset.glazeUiTarget = '1.6.0'" in main
    assert "dataset.glazeUiStatus = 'source-adoption-candidate'" in main
    assert 'data-glaze-ui="1.6.0"' in index
    assert "stableVersion = '1.6.0'" in dart
    assert "stableVersion = '1.3.0'" not in dart


def test_v1_3_ergonomic_and_resilience_foundation_is_preserved_in_v1_6_0_source() -> None:
    css = _read("frontend/src/glaze-contract.css")
    dart = _read("client/lib/glaze_theme.dart")
    for token in (
        "--glaze-target-min: 48px",
        "--glaze-target-touch-assistance: 56px",
        "--glaze-target-far-view: 56px",
        "--glaze-material-clarity: balanced",
        "--glaze-density-effective: standard",
        'data-glaze-large-text="true"',
        'data-glaze-touch-assistance="true"',
        'data-glaze-far-view="true"',
        "prefers-reduced-transparency: reduce",
        "prefers-reduced-motion: reduce",
        "prefers-contrast: more",
        "forced-colors: active",
    ):
        assert token in css

    assert "targetMin = 48" in dart
    assert "targetTouchAssistance = 56" in dart
    assert "targetFarView = 56" in dart
    for role in ("softGlaze", "glaze", "deepGlaze", "liveGlaze"):
        assert role in dart

def test_glaze_does_not_replace_platform_authorities() -> None:
    assert _ledger()["platform_authority"] == {
        "security": "Wardveil Security",
        "privacy": "Privacy Shield",
        "continuity": "Everkeep",
        "identity": "GoreeCloud Identity",
        "coordination": "GoreeCloud Mesh",
    }


def test_v1_3_historical_evidence_remains_fail_closed() -> None:
    ledger = _ledger()
    platform = json.loads(_read("docs/platform-conformance.json"))
    assert platform["stable_eligible"] is False
    for gate in (
        "11_browser_os_accessibility",
        "12_flutter_native_accessibility",
        "13_physical_device_acceptance",
        "14_application_performance",
        "15_visual_excellence",
        "16_authoritative_platform_state",
        "17_rollback_and_production_approval",
        "18_central_consumer_registry",
    ):
        assert gate in ledger["blocking_gates"]


def test_v1_3_gate_evidence_paths_exist() -> None:
    for gate in _ledger()["gates"].values():
        for relative_path in gate.get("evidence", []):
            assert (ROOT / relative_path).exists(), relative_path
