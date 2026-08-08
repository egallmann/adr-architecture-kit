"""Build-once release, installed-wheel, and workflow contracts."""

from __future__ import annotations

import gzip
import io
import json
import subprocess
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _release_utility(*arguments: str) -> subprocess.CompletedProcess[str]:
    script = ROOT / "scripts" / "release_manifest.py"
    assert script.is_file(), "missing release-manifest utility"
    return subprocess.run(
        [sys.executable, str(script), *arguments],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def _write_sdist(path: Path, timestamp: int) -> None:
    payload = b"deterministic content\n"
    with (
        path.open("wb") as raw,
        gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=timestamp) as compressed,
        tarfile.open(fileobj=compressed, mode="w", format=tarfile.PAX_FORMAT) as archive,
    ):
        member = tarfile.TarInfo("package/file.txt")
        member.size = len(payload)
        member.mtime = timestamp
        member.uid = timestamp
        member.gid = timestamp
        member.uname = "builder"
        member.gname = "builder"
        archive.addfile(member, io.BytesIO(payload))


def test_release_manifest_rejects_missing_extra_hash_tag_and_version_mismatches(
    tmp_path: Path,
) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    wheel = dist / "adr_architecture_kit-0.1.0-py3-none-any.whl"
    sdist = dist / "adr_architecture_kit-0.1.0.tar.gz"
    wheel.write_bytes(b"wheel")
    sdist.write_bytes(b"sdist")
    manifest = tmp_path / "release-manifest.json"

    created = _release_utility(
        "create",
        "--dist-dir",
        str(dist),
        "--output",
        str(manifest),
        "--source-commit",
        "a" * 40,
        "--version",
        "0.1.0",
    )
    assert created.returncode == 0, created.stdout + created.stderr

    verified = _release_utility(
        "verify",
        "--dist-dir",
        str(dist),
        "--manifest",
        str(manifest),
        "--expected-source-commit",
        "a" * 40,
        "--expected-version",
        "0.1.0",
        "--expected-tag",
        "v0.1.0",
    )
    assert verified.returncode == 0, verified.stdout + verified.stderr

    wheel.write_bytes(b"corrupt")
    assert (
        _release_utility("verify", "--dist-dir", str(dist), "--manifest", str(manifest)).returncode
        != 0
    )
    wheel.write_bytes(b"wheel")
    assert (
        _release_utility(
            "verify",
            "--dist-dir",
            str(dist),
            "--manifest",
            str(manifest),
            "--expected-tag",
            "v0.1.1",
        ).returncode
        != 0
    )

    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["package_version"] = "0.1.1"
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    assert (
        _release_utility(
            "verify",
            "--dist-dir",
            str(dist),
            "--manifest",
            str(manifest),
            "--expected-version",
            "0.1.0",
        ).returncode
        != 0
    )

    manifest.unlink()
    sdist.unlink()
    assert (
        _release_utility(
            "create",
            "--dist-dir",
            str(dist),
            "--output",
            str(manifest),
            "--source-commit",
            "a" * 40,
            "--version",
            "0.1.0",
        ).returncode
        != 0
    )

    sdist.write_bytes(b"sdist")
    (dist / "extra-0.1.0.tar.gz").write_bytes(b"extra")
    assert (
        _release_utility(
            "create",
            "--dist-dir",
            str(dist),
            "--output",
            str(manifest),
            "--source-commit",
            "a" * 40,
            "--version",
            "0.1.0",
        ).returncode
        != 0
    )


def test_sdist_normalization_removes_build_time_and_owner_variation(tmp_path: Path) -> None:
    first = tmp_path / "first.tar.gz"
    second = tmp_path / "second.tar.gz"
    epoch = 1_767_225_600
    _write_sdist(first, epoch + 10)
    _write_sdist(second, epoch + 20)
    assert first.read_bytes() != second.read_bytes()

    for path in (first, second):
        result = _release_utility(
            "normalize-sdist",
            "--sdist",
            str(path),
            "--source-date-epoch",
            str(epoch),
        )
        assert result.returncode == 0, result.stdout + result.stderr

    assert first.read_bytes() == second.read_bytes()
    with tarfile.open(first, "r:gz") as archive:
        members = archive.getmembers()
    assert members
    assert all(member.mtime == epoch for member in members)
    assert all(member.uid == member.gid == 0 for member in members)
    assert all(member.uname == member.gname == "" for member in members)


def test_installed_wheel_harness_declares_all_consumer_probes() -> None:
    script = ROOT / "scripts" / "test_installed_wheel.py"
    assert script.is_file(), "missing installed-wheel consumer harness"
    result = subprocess.run(
        [sys.executable, str(script), "--describe"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    for probe in (
        "imports",
        "cli",
        "external-fixture",
        "schemas",
        "templates",
        "source-isolation",
        "sdk-consumer",
        "sdk-version-parity",
        "sdk-operations",
        "compiler-containment",
        "v1.2-schemas",
        "v1.2-compilation",
        "promoted-entity-queries",
        "external-bindings",
        "topology-migration-entrypoint",
    ):
        assert probe in result.stdout


def test_publish_workflow_promotes_without_rebuilding_and_scopes_privilege() -> None:
    workflow = (ROOT / ".github" / "workflows" / "publish-pypi.yml").read_text(encoding="utf-8")
    assert "tags:" in workflow and '"v*"' in workflow
    assert "download-artifact" in workflow
    publish_section = workflow[workflow.index("  publish:") :]
    assert "python -m build" not in publish_section
    assert "id-token: write" in publish_section
    assert "environment:" in publish_section and "name: pypi" in publish_section
    pre_publish = workflow[: workflow.index("  publish:")]
    assert "id-token: write" not in pre_publish
    assert "normalize-sdist" in pre_publish


def test_pr_workflow_has_source_wheel_quality_security_and_reproducibility_gates() -> None:
    workflow = (ROOT / ".github" / "workflows" / "adr-governance.yml").read_text(encoding="utf-8")
    for version in ('"3.11"', '"3.12"', '"3.13"', '"3.14"'):
        assert version in workflow
    for contract in (
        "source-tests",
        "governance",
        "coverage",
        "quality-ratchets",
        "dependency-audit",
        "release-artifacts",
        "wheel-smoke",
        "reproducibility",
        "benchmark-smoke",
    ):
        assert f"  {contract}:" in workflow
    assert workflow.count("normalize-sdist") >= 3
    source_section = workflow[workflow.index("  source-tests:") : workflow.index("  governance:")]
    assert "scripts/test_sdk_consumer.py" in source_section
    assert "python -m pip install -e ." in source_section
    assert source_section.count("scripts/test_sdk_consumer.py") >= 2
    wheel_section = workflow[
        workflow.index("  wheel-smoke:") : workflow.index("  reproducibility:")
    ]
    assert "scripts/test_installed_wheel.py" in wheel_section
    assert "sdk-consumer" in workflow
