"""Build-once release, installed-wheel, and workflow contracts."""

from __future__ import annotations

import gzip
import io
import json
import re
import subprocess
import sys
import tarfile
from pathlib import Path

from typing import Any, cast

import yaml

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


def _load_workflow(name: str) -> dict[str, Any]:
    path = ROOT / ".github" / "workflows" / name
    assert path.is_file(), f"missing workflow {name}"
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _job_steps_text(job: dict[str, Any]) -> str:
    chunks: list[str] = []
    for step in job.get("steps") or []:
        if not isinstance(step, dict):
            continue
        for key in ("run", "uses", "name"):
            value = step.get(key)
            if isinstance(value, str):
                chunks.append(value)
        with_block = step.get("with")
        if isinstance(with_block, dict):
            chunks.extend(str(value) for value in with_block.values())
    return "\n".join(chunks)


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
        "public-api",
        "coverage-registry",
        "projection-generation",
        "governance-cli",
        "system-overview",
    ):
        assert probe in result.stdout


def test_installed_wheel_harness_starts_without_site_packages() -> None:
    script = ROOT / "scripts" / "test_installed_wheel.py"
    result = subprocess.run(
        [sys.executable, "-I", "-S", str(script), "--describe"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_publish_workflow_is_promotion_only_and_scopes_oidc() -> None:
    workflow = _load_workflow("publish-pypi.yml")
    jobs = workflow["jobs"]
    assert set(jobs) == {"resolve-bundle", "publish"}

    resolve = jobs["resolve-bundle"]
    publish = jobs["publish"]
    assert resolve["permissions"]["contents"] == "read"
    assert resolve["permissions"]["actions"] == "read"
    assert "id-token" not in resolve.get("permissions", {})
    assert publish["permissions"]["contents"] == "read"
    assert publish["permissions"]["id-token"] == "write"
    assert publish["environment"]["name"] == "pypi"
    assert publish["needs"] == ["resolve-bundle"]
    assert "concurrency" not in workflow

    resolve_text = _job_steps_text(resolve)
    publish_text = _job_steps_text(publish)
    for text in (resolve_text, publish_text):
        assert "actions/checkout@" in text
        assert "actions/setup-python@" in text
        assert "3.14" in text
        assert "Record interpreter" in text
        assert "python --version" in text
        assert "release_manifest.py" in text
        assert "verify" in text
        assert "expected-source-commit" in text
        assert "expected-version" in text
        assert "expected-tag" in text
        assert "pip install .[dev]" not in text
        assert "python -m build" not in text
        assert '-m", "build"' not in text and '("-m", "build")' not in text
        assert "pytest" not in text
        assert "governance-checks" not in text
        assert "pip_audit" not in text
    assert "resolve_qualified_release_bundle.py" in resolve_text
    assert "download-artifact" in resolve_text
    assert "download-artifact" in publish_text
    assert "gh-action-pypi-publish" in publish_text
    assert "os-portability" not in yaml.dump(workflow)
    assert "os-wheel-smoke" not in yaml.dump(workflow)


def test_npm_publish_workflow_is_promotion_only_and_uses_trusted_publishing_runtime() -> None:
    workflow = _load_workflow("publish-npm.yml")
    jobs = workflow["jobs"]
    resolve = jobs["resolve-bundle"]
    publish = jobs["publish"]

    trigger = workflow.get("on")
    if trigger is None:
        trigger = workflow.get(cast(Any, True))
    assert isinstance(trigger, dict)
    assert trigger["push"]["tags"] == ["v*"]
    assert resolve["permissions"] == {"contents": "read", "actions": "read"}
    assert publish["permissions"] == {"contents": "read", "id-token": "write"}
    assert publish["environment"]["name"] == "npm"
    assert publish["needs"] == ["resolve-bundle"]

    publish_text = _job_steps_text(publish)
    assert "22.14.0" in publish_text
    assert "npm@11.15.0" in publish_text
    assert "npm publish" in publish_text
    assert "--provenance" in publish_text
    assert "download-artifact" in publish_text
    assert "check_npm_publication.py" in publish_text
    assert "publication_status" in publish_text
    assert "noop" in publish_text
    assert "npm run build" not in publish_text
    assert "npm ci" not in publish_text
    assert "python -m build" not in publish_text


def test_codeql_analyzes_python_and_typescript_consumer_binding_separately() -> None:
    workflow = _load_workflow("codeql.yml")
    jobs = workflow["jobs"]
    analyze = jobs["analyze"]
    matrix = analyze["strategy"]["matrix"]["language"]
    assert matrix == ["python", "javascript-typescript"]
    assert analyze["name"] == "Analyze (${{ matrix.language }})"

    steps_text = _job_steps_text(analyze)
    assert "github/codeql-action/init@v3" in steps_text
    assert "${{ matrix.language }}" in steps_text
    assert "security-extended" in steps_text
    assert "github/codeql-action/autobuild@v3" in steps_text
    assert "github/codeql-action/analyze@v3" in steps_text
    assert "/language:${{ matrix.language }}" in steps_text

    trigger = workflow.get("on")
    if trigger is None:
        trigger = workflow.get(cast(Any, True))
    assert isinstance(trigger, dict)
    assert trigger["push"]["branches"] == ["main", "develop"]
    assert trigger["pull_request"]["branches"] == ["main", "develop"]
    assert trigger["schedule"] == [{"cron": "17 7 * * 1"}]


def test_pr_workflow_has_orthogonal_qualification_owners() -> None:
    workflow = _load_workflow("adr-governance.yml")
    jobs = workflow["jobs"]
    for name in (
        "source-tests",
        "governance",
        "coverage",
        "os-portability",
        "os-wheel-smoke",
        "quality-ratchets",
        "dependency-audit",
        "release-artifacts",
        "wheel-smoke",
        "reproducibility",
        "benchmark-smoke",
    ):
        assert name in jobs

    concurrency = workflow["concurrency"]
    assert concurrency["group"] == "${{ github.workflow }}-${{ github.ref }}"
    cancel = concurrency["cancel-in-progress"]
    assert "pull_request" in cancel
    assert "refs/heads/develop" in cancel
    assert "refs/heads/main" not in cancel or "||" in cancel
    # Main must not cancel: expression is true only for PR or develop.
    assert cancel == (
        "${{ github.event_name == 'pull_request' || github.ref == 'refs/heads/develop' }}"
    )

    coverage = jobs["coverage"]
    coverage_text = _job_steps_text(coverage)
    assert coverage.get("runs-on") == "ubuntu-latest"
    assert "3.14" in coverage_text
    assert "--cov=adr_kit" in coverage_text
    assert "--cov-fail-under=80" in coverage_text
    assert "Record interpreter" in coverage_text
    assert "python --version" in coverage_text

    source = jobs["source-tests"]
    source_matrix = source["strategy"]["matrix"]["python-version"]
    assert source_matrix == ["3.14"]
    source_text = _job_steps_text(source)
    assert "run_source_compat.py" in source_text
    assert "Record interpreter" in source_text
    assert "python --version" in source_text
    assert re.search(r"(?m)^\s*python -m pytest\s*$", source_text) is None
    assert "mkdir -p" not in source_text
    assert "env -u PYTHONPATH" not in source_text

    governance_text = _job_steps_text(jobs["governance"])
    assert "governance-checks --skip-tests" in governance_text
    assert "Record interpreter" in governance_text
    assert "python --version" in governance_text
    assert "run_local_pre_push_checks.py" not in governance_text
    assert "adr validate --cross-references" not in governance_text

    os_port = jobs["os-portability"]
    assert "needs" not in os_port
    assert set(os_port["strategy"]["matrix"]["os"]) == {"windows-latest", "macos-latest"}
    os_port_text = _job_steps_text(os_port)
    assert "3.14" in os_port_text
    assert "Record interpreter" in os_port_text
    assert "python --version" in os_port_text
    assert "python -m pytest" in os_port_text
    assert "--cov=" not in os_port_text
    assert "python -m build" not in os_port_text

    release = jobs["release-artifacts"]
    release_text = _job_steps_text(release)
    assert "build" in release_text and "normalize-sdist" in release_text
    assert "--output" in release_text and "release-manifest.json" in release_text
    assert "python-dist/release-manifest.json" not in release_text
    assert "Record interpreter" in release_text
    assert "python --version" in release_text

    wheel = jobs["wheel-smoke"]
    assert wheel["needs"] in ("release-artifacts", ["release-artifacts"])
    assert wheel["strategy"]["matrix"]["python-version"] == ["3.14"]
    wheel_text = _job_steps_text(wheel)
    assert "scripts/test_installed_wheel.py" in wheel_text
    assert "Record interpreter" in wheel_text
    assert "python --version" in wheel_text

    for job_name in (
        "quality-ratchets",
        "dependency-audit",
        "reproducibility",
        "benchmark-smoke",
        "typescript-consumer-binding",
    ):
        job_text = _job_steps_text(jobs[job_name])
        assert "Record interpreter" in job_text
        assert "python --version" in job_text
        assert "3.14" in job_text

    os_wheel = jobs["os-wheel-smoke"]
    assert os_wheel["needs"] in ("release-artifacts", ["release-artifacts"])
    assert set(os_wheel["strategy"]["matrix"]["os"]) == {"windows-latest", "macos-latest"}
    os_wheel_text = _job_steps_text(os_wheel)
    assert "3.14" in os_wheel_text
    assert "Record interpreter" in os_wheel_text
    assert "python --version" in os_wheel_text
    assert "download-artifact" in os_wheel_text
    assert "release-bundle" in os_wheel_text
    assert "scripts/test_installed_wheel.py" in os_wheel_text
    assert "python -m build" not in os_wheel_text
    assert "python -m pytest" not in os_wheel_text
    assert "pip install .[dev]" not in os_wheel_text

    # No Python×OS Cartesian retained-wheel matrix.
    assert "os" not in wheel["strategy"]["matrix"]
    assert "python-version" not in os_wheel["strategy"]["matrix"]


def test_local_pre_push_checks_include_readme_pypi_portability() -> None:
    script = (ROOT / "scripts" / "run_local_pre_push_checks.py").read_text(encoding="utf-8")
    assert "tests/test_readme_pypi_portability.py" in script


def test_local_pre_push_checks_include_v15_attribution_invariants() -> None:
    script = (ROOT / "scripts" / "run_local_pre_push_checks.py").read_text(encoding="utf-8")
    for path in (
        "tests/test_readme_attribution_docs.py",
        "tests/test_semantic_attribution_matrix.py",
        "tests/test_semantic_attribution_vocabulary_parity.py",
        "tests/test_attribution_shim_parity.py",
        "tests/test_legacy_attribution_normalization.py",
        "tests/test_attribution_resolution.py",
        "tests/test_decorators.py",
        "tests/test_attribution_dual_encode_guard.py",
        "tests/test_next_id_v13_alias_allocation.py",
        "tests/test_package_schema_parity.py",
        "tests/test_implementation_attribution_validation.py",
        "tests/test_attribution_cli.py",
    ):
        assert path in script
