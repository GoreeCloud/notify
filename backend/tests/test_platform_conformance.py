from __future__ import annotations

import json
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = REPOSITORY_ROOT / "docs" / "platform-conformance.json"
MANIFEST_PATH = REPOSITORY_ROOT / "goreecloud.platform.yaml"


def _contract() -> dict:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def test_platform_conformance_contract_is_fail_closed() -> None:
    contract = _contract()
    assert contract["application"] == "goreecloud-notify"
    assert contract["stable_eligible"] is False
    assert set(contract["platform_systems"]) == {
        "manager",
        "privacy_shield",
        "wardveil_security",
        "everkeep",
        "glaze_ui",
        "goreecloud_mesh",
        "goreecloud_identity",
        "goreecloud_policy",
        "goreecloud_observability",
    }
    glaze = contract["platform_systems"]["glaze_ui"]
    assert glaze["required_version"] == "1.6"
    assert glaze["required_release"] == "1.6.0"
    assert glaze["canonical_repository"] == "GoreeCloud/glaze-ui"
    assert glaze["canonical_revision"] == "a7180679ea851389e0f3004515f9a25f420e716d"
    assert glaze["source_status"] == "v1.6.0-source-adoption-candidate-acceptance-required"


def test_root_platform_manifest_tracks_current_contract() -> None:
    manifest = MANIFEST_PATH.read_text(encoding="utf-8")
    for expected in (
        'schema_version: "0.4"',
        "type: application",
        "id: goreecloud-notify",
        "lifecycle: release-candidate",
        'platform_contract: "0.4"',
        'glaze_ui_required: "1.6.0"',
        'version: "1.6.0"',
        "status: nonconformant",
    ):
        assert expected in manifest


def test_platform_conformance_uses_canonical_identities() -> None:
    systems = _contract()["platform_systems"]
    assert systems["glaze_ui"]["identity"] == "Glaze UI"
    assert systems["wardveil_security"]["identity"] == "Wardveil Security by GoreeCloud"
    assert systems["privacy_shield"]["identity"] == "GoreeCloud Privacy Shield"
    assert systems["everkeep"]["identity"] == "Everkeep"
    assert systems["manager"]["identity"] == "GoreeCloud Manager"
    assert systems["goreecloud_mesh"]["identity"] == "GoreeCloud Mesh"
    assert systems["goreecloud_identity"]["identity"] == "GoreeCloud Identity"
    assert systems["goreecloud_policy"]["identity"] == "GoreeCloud Policy"
    assert systems["goreecloud_observability"]["identity"] == "GoreeCloud Observability"


def test_platform_conformance_evidence_paths_exist() -> None:
    for system in _contract()["platform_systems"].values():
        for relative_path in system.get("evidence", []):
            assert (REPOSITORY_ROOT / relative_path).exists(), relative_path


def test_incomplete_platform_contracts_cannot_be_represented_as_complete() -> None:
    contract = _contract()
    systems = contract["platform_systems"]
    assert systems["wardveil_security"]["source_status"] == "draft-application-adoption-candidate"
    wardveil_acceptance = json.loads(
        (REPOSITORY_ROOT / "docs" / "wardveil.adoption.json").read_text(encoding="utf-8")
    )["acceptance"]
    assert wardveil_acceptance["target_runtime_acceptance_required"] is True
    assert wardveil_acceptance["production_approved"] is False
    assert systems["privacy_shield"]["source_status"] == "draft-adapter-source-candidate"
    privacy_acceptance = json.loads(
        (REPOSITORY_ROOT / "docs" / "privacy-shield.adapter.json").read_text(encoding="utf-8")
    )["acceptance"]
    assert privacy_acceptance["runtime_acceptance_required"] is True
    assert privacy_acceptance["production_approved"] is False
    assert systems["everkeep"]["source_status"] == "draft-acceptance-policy-candidate"
    everkeep_adoption = json.loads(
        (REPOSITORY_ROOT / "docs" / "everkeep.adoption.json").read_text(encoding="utf-8")
    )
    assert everkeep_adoption["fail_closed"] is True
    assert everkeep_adoption["read_only"] is True
    everkeep_acceptance = json.loads(
        (REPOSITORY_ROOT / "docs" / "everkeep.acceptance.json").read_text(encoding="utf-8")
    )["acceptance"]
    assert everkeep_acceptance["everkeep_integrated"] is False
    assert everkeep_acceptance["everkeep_ready"] is False
    assert everkeep_acceptance["target_runtime_acceptance_required"] is True
    assert everkeep_acceptance["exact_revision_acceptance_required"] is True
    assert systems["goreecloud_policy"]["source_status"].startswith("applicable-blocked")
    assert systems["goreecloud_observability"]["source_status"].startswith("applicable-blocked")
    assert contract["stable_eligible"] is False
    assert contract["production_blockers"]
