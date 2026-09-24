from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LEDGER = ROOT / "docs" / "glaze-ui-v1.6.0-adoption.json"


def _ledger() -> dict:
    return json.loads(LEDGER.read_text(encoding="utf-8"))


def test_notify_requires_current_glaze_v1_6_0_without_claiming_adoption() -> None:
    ledger = _ledger()
    assert ledger["application"] == "goreecloud-notify"
    assert ledger["required_target_release"] == "1.6.0"
    assert ledger["current_source_mapping_release"] == "1.6.0"
    assert ledger["canonical_repository"] == "GoreeCloud/glaze-ui"
    assert ledger["accepted_release_source"] == "a7180679ea851389e0f3004515f9a25f420e716d"
    assert ledger["source_qualification_anchor"] == "c7509c79256b04b0aa67cb9dd0737d7588e0ae4a"
    assert ledger["adoption_status"] == "source-adoption-candidate"
    assert ledger["conformance_claim"] is False
    assert ledger["production_eligible"] is False


def test_current_glaze_ledger_preserves_required_supported_surfaces() -> None:
    ledger = _ledger()
    assert set(ledger["supported_surfaces"]) == {"web", "flutter-linux", "flutter-android"}
    assert ledger["source_implementation"]["web"]["status"].startswith("source-evidence-present")
    assert ledger["source_implementation"]["flutter_linux"]["status"].startswith("source-evidence-present")
    assert ledger["source_implementation"]["flutter_android"]["status"].startswith("source-evidence-present")


def test_current_glaze_ledger_is_fail_closed_on_missing_acceptance() -> None:
    ledger = _ledger()
    assert ledger["conformance_claim"] is False
    assert ledger["production_eligible"] is False
    assert "representative-application-performance-budget" in ledger["required_acceptance"]
    assert "governed-consumer-registry-acceptance" in ledger["required_acceptance"]
    assert "exact-revision-production-approval" in ledger["required_acceptance"]
    assert ledger["blockers"]


def test_historical_v1_3_ledger_is_explicitly_superseded() -> None:
    historical = json.loads(
        (ROOT / "docs" / "glaze-ui-v1.3-adoption.json").read_text(encoding="utf-8")
    )
    assert historical["adoption_status"] == "historical-source-mapping-superseded"
    assert historical["superseded_by"] == "docs/glaze-ui-v1.6.0-adoption.json"
    assert historical["stable_eligible"] is False


def test_v1_5_1_remains_explicit_historical_rollback_provenance() -> None:
    historical = json.loads(
        (ROOT / "docs" / "glaze-ui-v1.5.1-adoption.json").read_text(encoding="utf-8")
    )
    assert historical["application"] == "goreecloud-notify"
    assert historical["required_target_release"] == "1.5.1"
    assert historical["current_source_mapping_release"] == "1.5.1"
    assert historical["runtime_entrypoint"] == "js/glaze-v1.5.1.mjs"
    assert historical["adoption_status"] == "historical-source-mapping-superseded"
    assert historical["superseded_by"] == "docs/glaze-ui-v1.6.0-adoption.json"
    assert "rollback and audit" in historical["acceptance_boundary"]
    assert historical["conformance_claim"] is False
    assert historical["production_eligible"] is False
