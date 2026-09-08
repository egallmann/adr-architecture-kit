"""Build-once release, installed-wheel, and workflow contracts."""

from __future__ import annotations

import gzip
import io
import json
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


def _workflow_trigger(workflow: dict[str, Any]) -> dict[str, Any]:
    trigger = workflow.get("on")
    if trigger is None:
        trigger = workflow.get(cast(Any, True))
    assert isinstance(trigger, dict)
    return trigger


def test_pr_feedback_is_fast_and_semantically_explicit() -> None:
    workflow = _load_workflow("pr-feedback.yml")
    assert _workflow_trigger(workflow)["pull_request"]["branches"] == ["main", "develop"]
    assert workflow["concurrency"]["cancel-in-progress"] is True
    jobs = workflow["jobs"]
    assert set(jobs) == {
        "python-semantic",
        "rust-semantic-core",
        "typescript-consumer",
        "governance",
        "quality-ratchets",
    }

    python_text = _job_steps_text(jobs["python-semantic"])
    assert "run_pr_feedback.py" in python_text
    assert "run_source_compat.py" in python_text
    assert "--durations=30" not in python_text
    assert "python -m pytest" not in python_text

    node_text = _job_steps_text(jobs["typescript-consumer"])
    for command in ("npm run build", "npm run typecheck", "npm test", "browser:check"):
        assert command in node_text
    assert "npm audit" not in node_text
    assert "npm run pack:check" not in node_text

    for job in jobs.values():
        text = _job_steps_text(job)
        assert "release_manifest.py" not in text
        assert "python -m build" not in text
        assert "upload-artifact" not in text


def test_integration_assurance_owns_full_suite_and_develop_runs_it() -> None:
    workflow = _load_workflow("develop-assurance.yml")
    trigger = _workflow_trigger(workflow)
    assert trigger["push"]["branches"] == ["develop"]
    assert (
        workflow["jobs"]["integration"]["uses"] == "./.github/workflows/integration-assurance.yml"
    )

    assurance = _load_workflow("integration-assurance.yml")
    jobs = assurance["jobs"]
    assert {
        "full-python-coverage",
        "os-portability",
        "dependency-audit",
        "typescript-consumer",
    } <= set(jobs)
    coverage_text = _job_steps_text(jobs["full-python-coverage"])
    assert "--cov=adr_kit" in coverage_text
    assert "--cov-fail-under=80" in coverage_text
    assert "--durations=30" in coverage_text
    os_port = jobs["os-portability"]
    assert set(os_port["strategy"]["matrix"]["os"]) == {"windows-latest", "macos-latest"}
    assert "--durations=30" in _job_steps_text(os_port)
    assert "release-artifacts" not in jobs


def test_release_certification_owns_retained_artifacts_and_release_only_checks() -> None:
    workflow = _load_workflow("release-certification.yml")
    trigger = _workflow_trigger(workflow)
    assert trigger["push"]["branches"] == ["main"]
    assert "workflow_dispatch" not in trigger
    jobs = workflow["jobs"]
    assert jobs["integration"]["uses"] == "./.github/workflows/integration-assurance.yml"
    assert jobs["release-artifacts"]["needs"] == ["integration", "semantic-core-qualification"]
    semantic_core = jobs["semantic-core-qualification"]
    semantic_core_text = _job_steps_text(semantic_core)
    assert "cargo test --manifest-path core/Cargo.toml" in semantic_core_text
    assert "scripts/build_semantic_core.mjs" in semantic_core_text
    assert "scripts/verify_semantic_core_artifact.py" in semantic_core_text
    assert "tests/test_semantic_core_conformance.py" in semantic_core_text
    assert "npm test" in semantic_core_text
    assert semantic_core_text.index("scripts/build_semantic_core.mjs") < semantic_core_text.index(
        "pip install .[dev]"
    )
    assert jobs["wheel-smoke"]["needs"] == "release-artifacts"
    assert jobs["os-wheel-smoke"]["needs"] == "release-artifacts"
    for name in ("release-artifacts", "reproducibility", "benchmark-smoke"):
        text = _job_steps_text(jobs[name])
        assert "Record interpreter" in text or name == "benchmark-smoke"
    release_text = _job_steps_text(jobs["release-artifacts"])
    assert "normalize-sdist" in release_text
    assert "release-manifest.json" in release_text
    assert "upload-artifact" in release_text
    assert "semantic-core.wasm" in release_text
    assert "scripts/verify_semantic_core_artifact.py" in release_text

    wheel_text = _job_steps_text(jobs["wheel-smoke"])
    assert "scripts/test_installed_wheel.py" in wheel_text
    os_wheel = jobs["os-wheel-smoke"]
    assert set(os_wheel["strategy"]["matrix"]["os"]) == {"windows-latest", "macos-latest"}
    assert "download-artifact" in _job_steps_text(os_wheel)


def test_publishing_workflows_resolve_main_release_certification() -> None:
    for filename in ("publish-pypi.yml", "publish-npm.yml"):
        workflow_text = (ROOT / ".github" / "workflows" / filename).read_text(encoding="utf-8")
        assert "release-certification.yml" in workflow_text
        assert "adr-governance.yml" not in workflow_text


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
