from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
V020_COMMIT = "dd22a7ad0765c8ca62b401749265594bb0a06e23"


def _read(path: str) -> str:
    return (REPOSITORY_ROOT / path).read_text(encoding="utf-8")


def test_current_source_license_metadata_is_synchronized() -> None:
    license_text = _read("LICENSE")
    notice = _read("LICENSE-NOTICE.md")
    readme = _read("README.md")
    dockerfile = _read("Dockerfile.production")
    dependency_review = _read("docs/dependency-license-review.md")
    debian_packaging = _read("client/package-deb.sh")

    assert "SPDX-License-Identifier: AGPL-3.0-only" in license_text
    assert "version 3 only" in license_text

    assert V020_COMMIT in notice
    assert "MIT License" in notice
    assert "does not revoke" in notice

    assert "AGPL-3.0-only" in readme
    assert "published `v0.2.0` source release remains available under the MIT License" in readme
    assert "LICENSE-NOTICE.md" in readme

    assert 'org.opencontainers.image.licenses="AGPL-3.0-only"' in dockerfile
    assert "COPY LICENSE ./LICENSE" in dockerfile
    assert "COPY LICENSE-NOTICE.md ./LICENSE-NOTICE.md" in dockerfile

    assert "AGPL-3.0-only" in dependency_review
    assert V020_COMMIT in dependency_review
    assert "retain their MIT permissions" in dependency_review

    assert '"$ROOT/usr/share/doc/goreecloud-notify/LICENSE"' in debian_packaging
    assert '"$ROOT/usr/share/doc/goreecloud-notify/LICENSE-NOTICE.md"' in debian_packaging



def test_release_controls_distinguish_current_agpl_from_historical_mit() -> None:
    release_deployment = _read("docs/release-deployment.md")
    release_checklist = _read("docs/release-checklist.md")
    changelog = _read("CHANGELOG.md")

    assert "org.opencontainers.image.licenses=AGPL-3.0-only" in release_deployment
    assert "org.opencontainers.image.licenses=MIT" not in release_deployment

    assert "Current repository source license is `AGPL-3.0-only`" in release_checklist
    assert V020_COMMIT in release_checklist
    assert "historical MIT grant" in release_checklist

    # Historical v0.2.0 release metadata remains intentionally MIT.
    assert "MIT application license and OCI source/version/license metadata." in changelog
