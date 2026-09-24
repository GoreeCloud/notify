from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

MANDATORY_ROOT_CONTROLS = [
    "README.md",
    "SPECIFICATIONS.md",
    "FEATURES.md",
    "IMPLEMENTED-FEATURES.md",
    "PLANNED-FEATURES.md",
    "CHANGELOGS.md",
    "BENEFITS.md",
    "COMPETITIVE-OBJECTIVES.md",
    "BRANDING.md",
    "USER-MANUAL.md",
    "PRIVACY POLICY.md",
    "NOTES.md",
    "SECURITY.md",
    ".gitignore",
    ".editorconfig",
    "goreecloud.platform.yaml",
]


def test_mandatory_repository_controls_exist() -> None:
    missing = [name for name in MANDATORY_ROOT_CONTROLS if not (ROOT / name).is_file()]
    assert missing == []


def test_retired_feature_and_changelog_controls_are_absent() -> None:
    retired = ["FEATURE-ROADMAP.md", "CHANGELOG.md"]
    present = [name for name in retired if (ROOT / name).exists()]
    assert present == []


def test_repository_controls_keep_release_candidate_boundary() -> None:
    specs = (ROOT / "SPECIFICATIONS.md").read_text(encoding="utf-8")
    features = (ROOT / "FEATURES.md").read_text(encoding="utf-8")
    notes = (ROOT / "NOTES.md").read_text(encoding="utf-8")
    assert "release candidate" in specs.lower()
    assert "not automatically production-accepted" in features.lower()
    assert "production acceptance remains false" in notes.lower()


def test_repository_identity_metadata_uses_current_canonical_repository() -> None:
    canonical_repository = "GoreeCloud/notify"
    canonical_source = "https://github.com/GoreeCloud/notify"
    legacy_repository = "GoreeCloud/goreecloud-notify"

    manifest = (ROOT / "goreecloud.platform.yaml").read_text(encoding="utf-8")
    dockerfile = (ROOT / "Dockerfile.production").read_text(encoding="utf-8")
    release_deployment = (ROOT / "docs" / "release-deployment.md").read_text(
        encoding="utf-8"
    )

    assert f"repository: {canonical_repository}" in manifest
    assert f'org.opencontainers.image.source="{canonical_source}"' in dockerfile
    assert f"org.opencontainers.image.source={canonical_source}" in release_deployment

    for content in (manifest, dockerfile, release_deployment):
        assert legacy_repository not in content
