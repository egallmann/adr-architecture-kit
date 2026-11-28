"""Build-once release, installed-wheel, and workflow contracts."""

from __future__ import annotations

import gzip
import io
import json
import re
import shlex
import subprocess
import sys
import tomllib
import tarfile
from pathlib import Path

from typing import Any, cast

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_python_package_data_excludes_every_unreleased_contract_identity() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    excluded = project["tool"]["setuptools"]["exclude-package-data"]
    lifecycle = json.loads(
        (ROOT / "adrs/migrations/semantic-contract-lifecycle-classification.json").read_text(
            encoding="utf-8"
        )
    )
    released = {(entry["family"], entry["version"]) for entry in lifecycle["released_contracts"]}
    definitions = ROOT / "contracts/semantic-contract/v1.0/definitions"
    candidate_ids = {
        (value["semanticContractFamily"], value["semanticContractVersion"])
        for path in definitions.glob("*.json")
        if (value := json.loads(path.read_text(encoding="utf-8")))
        and (value["semanticContractFamily"], value["semanticContractVersion"]) not in released
    }
    semantic_exclusions = set(excluded["adr_kit.semantic_contract.v1_0"])
    resource_exclusions = set(excluded["adr_kit.semantic_contract.v1_0.resources"])
    manifest_lines = set((ROOT / "MANIFEST.in").read_text(encoding="utf-8").splitlines())
    for family, version in candidate_ids:
        stem = f"{family}-{version}"
        assert f"{stem}.json" in semantic_exclusions
        assert f"definitions/{stem}.json" in semantic_exclusions
        assert f"{stem}-*.json" in resource_exclusions
        assert f"exclude src/adr_kit/semantic_contract/v1_0/{stem}.json" in manifest_lines
        assert (
            f"exclude src/adr_kit/semantic_contract/v1_0/definitions/{stem}.json" in manifest_lines
        )
        assert (
            f"recursive-exclude src/adr_kit/semantic_contract/v1_0/resources {stem}-*.json"
            in manifest_lines
        )
    assert "custom-entity-1.0-*.json" in resource_exclusions
    assert (
        "recursive-exclude src/adr_kit/semantic_contract/v1_0/resources custom-entity-1.0-*.json"
        in manifest_lines
    )
    assert "*.json" in excluded["adr_kit.schema.v2_5"]
    assert "prune src/adr_kit/schema/v2_5" in manifest_lines


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


def _workflow_trigger(workflow: dict[str, Any]) -> dict[str, Any]:
    trigger = workflow.get("on", workflow.get(cast(Any, True)))
    assert isinstance(trigger, dict)
    return trigger


def _required(item: dict[str, Any]) -> None:
    assert item.get("if") in (None, "success()", "${{ success() }}")
    assert item.get("continue-on-error", False) is False


def _commands(job: dict[str, Any]) -> str:
    return "\n".join(" ".join(step["run"].split()) for step in job["steps"] if "run" in step)


def _command_step(job: dict[str, Any], command: str) -> dict[str, Any]:
    matches: list[dict[str, Any]] = [
        step for step in job["steps"] if command in " ".join(step.get("run", "").split())
    ]
    assert len(matches) == 1, f"expected one step running {command}"
    _required(matches[0])
    return matches[0]


def _actions(job: dict[str, Any], action: str) -> list[dict[str, Any]]:
    return [
        step for step in job.get("steps", []) if step.get("uses", "").split("@", 1)[0] == action
    ]


def _needs(job: dict[str, Any]) -> set[str]:
    dependencies = job.get("needs", [])
    return {dependencies} if isinstance(dependencies, str) else set(dependencies)


def _publisher_steps(job: dict[str, Any]) -> list[dict[str, Any]]:
    return _actions(job, "pypa/gh-action-pypi-publish") + [
        step
        for step in job.get("steps", [])
        if "npm publish " in " ".join(step.get("run", "").split())
    ]


@pytest.mark.parametrize(
    ("filename", "registry"), [("publish-pypi.yml", "pypi"), ("publish-npm.yml", "npm")]
)
def test_publishers_promote_only_independently_verified_bundles(
    filename: str, registry: str
) -> None:
    workflow = _load_workflow(filename)
    trigger = _workflow_trigger(workflow)
    assert trigger["push"] == {"tags": ["v*"]}
    assert set(trigger) == ({"push"} if registry == "pypi" else {"push", "workflow_dispatch"})
    if registry == "npm":
        assert trigger["workflow_dispatch"]["inputs"]["tag"]["required"] is True

    jobs = workflow["jobs"]
    resolve = jobs["resolve-bundle"]
    publish = jobs["publish"]
    assert "write" not in workflow.get("permissions", {}).values()
    for role in (resolve, publish):
        assert role["permissions"].get("contents") == "read"
        assert role["permissions"].get("actions") == "read"
    assert all(
        value != "write" or (name == "publish" and scope == "id-token")
        for name, job in jobs.items()
        for scope, value in job.get("permissions", {}).items()
    )
    assert {
        name for name, job in jobs.items() if job.get("permissions", {}).get("id-token") == "write"
    } == {"publish"}
    assert {name for name, job in jobs.items() if _publisher_steps(job)} == {"publish"}
    assert {"resolve-bundle"} <= _needs(publish)
    assert publish["environment"]["name"] == registry
    _required(resolve)
    _required(publish)

    resolution = _command_step(resolve, "resolve_qualified_release_bundle.py resolve")
    assert "git rev-parse HEAD" in resolution["run"]
    for option, value in (
        ("--sha", "$source"),
        ("--workflow", "release-certification.yml"),
        ("--branch", "main"),
        ("--event", "push"),
        ("--artifact-name", "release-bundle"),
    ):
        assert re.search(rf"{option}\s+['\"]?{re.escape(value)}['\"]?(?=\s|$)", resolution["run"])
    verify_steps = []
    for job, source, certification in (
        (resolve, "${{ steps.resolve.outputs.source }}", "${{ steps.resolve.outputs.run_id }}"),
        (
            publish,
            "${{ needs.resolve-bundle.outputs.source }}",
            "${{ needs.resolve-bundle.outputs.run_id }}",
        ),
    ):
        download = _command_step(job, "release_authority_promotion.py download")
        verify = _command_step(job, "release_authority_promotion.py verify")
        for verb, step in (("download", download), ("verify", verify)):
            assert step["env"]["SOURCE"] == source
            assert step["env"]["CERTIFICATION"] == certification
            line = next(
                line
                for line in step["run"].splitlines()
                if f"release_authority_promotion.py {verb}" in " ".join(line.split())
            )
            args = shlex.split(line)
            for option, value in (
                ("--source", "$SOURCE"),
                ("--certification-run", "$CERTIFICATION"),
                ("--bundle", "release-bundle"),
            ):
                assert args[args.index(option) + 1] == value
        assert job["steps"].index(download) <= job["steps"].index(verify)
        script = _commands(job)
        assert not re.search(r"python\s+-m\s+build\b|npm\s+(?:ci|pack|run\s+build)\b", script)
        assert '"-m", "build"' not in script and '("-m", "build")' not in script
        verify_steps.append(verify)
    resolved, independent = verify_steps
    assert "attestation_digest" in resolved["run"]
    assert independent["env"]["ATTESTATION"] == "${{ needs.resolve-bundle.outputs.attestation }}"
    assert re.search(r"--expected-attestation-digest\s+[\"']?\$ATTESTATION\b", independent["run"])
    assert any(
        step["with"].get("ref") == independent["env"]["SOURCE"]
        for step in _actions(publish, "actions/checkout")
    )
    (publication,) = _publisher_steps(publish)
    _required(publication)
    assert publish["steps"].index(independent) < publish["steps"].index(publication)
    if registry == "pypi":
        assert publication["with"]["packages-dir"] == "release-bundle/python-dist"
        assert "password" not in publication["with"]
    else:
        assert "release-bundle/node-dist" in publication["run"]
        assert "check_npm_publication.py" in publication["run"]
        assert re.search(r"npm\s+publish\b[^\n]*\s--provenance\b", publication["run"])


def test_authority_promotion_requires_the_owner_environment_and_cannot_publish() -> None:
    workflow = _load_workflow("authority-promotion.yml")
    assert set(_workflow_trigger(workflow)) == {"workflow_dispatch"}
    subject = workflow["jobs"]["subject"]
    attest = workflow["jobs"]["attest"]
    assert subject["if"] == "github.ref == 'refs/heads/main'"
    assert "subject" in _needs(attest)
    assert attest["environment"]["name"] == "semantic-authority-promotion"
    _required(attest)
    _command_step(attest, "release_authority_promotion.py attest")
    assert not any(_publisher_steps(job) for job in workflow["jobs"].values())
    assert "write" not in workflow["permissions"].values()
    assert all(
        "write" not in job.get("permissions", {}).values() for job in workflow["jobs"].values()
    )


def test_codeql_analyzes_python_and_typescript_on_main_and_develop() -> None:
    workflow = _load_workflow("codeql.yml")
    trigger = _workflow_trigger(workflow)
    for event in ("push", "pull_request"):
        assert set(trigger[event]["branches"]) == {"main", "develop"}
    assert trigger["schedule"]
    analyze = workflow["jobs"]["analyze"]
    _required(analyze)
    assert set(analyze["strategy"]["matrix"]["language"]) == {"python", "javascript-typescript"}
    (init,) = _actions(analyze, "github/codeql-action/init")
    (scan,) = _actions(analyze, "github/codeql-action/analyze")
    for step in (init, scan):
        _required(step)
    assert init["with"]["languages"] == "${{ matrix.language }}"
    assert init["with"]["queries"] == "security-extended"


NATIVE_WORKFLOW = "./.github/workflows/semantic-core-native.yml"
WASM_WORKFLOW = "./.github/workflows/semantic-core-wasm.yml"
INTEGRATION_WORKFLOW = "./.github/workflows/integration-assurance.yml"
PORTABILITY_OS = {"windows-latest", "macos-latest"}
EVENT_SHA = "${{ github.sha }}"
GOVERNANCE_COMMANDS = (
    "adr repair-canonical-ids --check",
    "adr governance-checks",
    "adr validate-generated-docs",
    "adr validate-system-overview",
)


def _artifact_consumer(job: dict[str, Any], source: str) -> None:
    (checkout,) = _actions(job, "actions/checkout")
    _required(checkout)
    assert checkout.get("with", {}).get("ref", EVENT_SHA) == source
    (download,) = _actions(job, "actions/download-artifact")
    _required(download)
    assert download["with"]["name"] == f"semantic-core-{source}"
    assert (
        not {"run-id", "repository", "github-token", "pattern", "artifact-ids"}
        & download["with"].keys()
    )
    consume = _command_step(job, "semantic_core_artifact_bundle.py consume")
    args = shlex.split(consume["run"])
    assert args[args.index("--source-commit") + 1] == source
    assert args[args.index("--bundle-dir") + 1] == download["with"]["path"]
    verify = _command_step(job, "scripts/verify_semantic_core_artifact.py")
    steps = job["steps"]
    assert (
        steps.index(checkout) < steps.index(download) < steps.index(consume) < steps.index(verify)
    )


def _core_calls(
    jobs: dict[str, Any], source: str, *, prerequisites: frozenset[str] = frozenset()
) -> None:
    for name, workflow in (("native-rust", NATIVE_WORKFLOW), ("semantic-core-wasm", WASM_WORKFLOW)):
        job = jobs[name]
        _required(job)
        assert job["uses"] == workflow
        assert _needs(job) == prerequisites
        assert job["with"]["source_ref"] == source


def _and_terms(expression: str) -> set[str]:
    assert expression.startswith("${{") and expression.endswith("}}")
    return {term.strip() for term in expression[3:-2].split("&&")}


def _assurance_gate(
    job: dict[str, Any], required: set[str], source: str, *, optional_os: bool = False
) -> None:
    assert job["if"] == "${{ always() }}"
    assert job.get("continue-on-error", False) is False
    optional = {"os-portability"} if optional_os else set()
    assert _needs(job) == required | optional
    check = _command_step(job, 'test "$REQUIRED_SUCCEEDED" = true')
    assert check["shell"] == "bash"
    env = check["env"]
    assert _and_terms(env["REQUIRED_SUCCEEDED"]) == {
        f"needs.{name}.result == 'success'" for name in required
    }
    assert _and_terms(env["SOURCE_MATCH"]) == {
        f"needs.{name}.outputs.source_commit == {source}"
        for name in ("native-rust", "semantic-core-wasm")
    }
    _command_step(job, 'test "$SOURCE_MATCH" = true')
    if optional_os:
        assert env["PORTABILITY_SUCCEEDED"] == (
            "${{ needs.os-portability.result == "
            "(inputs.full_os_portability && 'success' || 'skipped') }}"
        )
        _command_step(job, 'test "$PORTABILITY_SUCCEEDED" = true')


def test_pr_and_integration_require_native_rust_and_source_built_wasm() -> None:
    for filename, consumers in (
        ("pr-feedback.yml", ("python-semantic", "typescript-consumer", "governance")),
        (
            "integration-assurance.yml",
            ("source-compatibility", "typescript-consumer", "governance", "full-python-coverage"),
        ),
    ):
        jobs = _load_workflow(filename)["jobs"]
        _core_calls(jobs, EVENT_SHA)
        for name in consumers:
            job = jobs[name]
            _required(job)
            assert _needs(job) == {"semantic-core-wasm"}
            _artifact_consumer(job, EVENT_SHA)
        _required(jobs["quality-ratchets"])
        _command_step(jobs["quality-ratchets"], "scripts/check_quality_ratchets.py")
        for command in ("npm run build", "npm run typecheck", "npm test", "npm run browser:check"):
            _command_step(jobs["typescript-consumer"], command)
        assert not any(
            step.get("with", {}).get("name") == "release-bundle"
            for job in jobs.values()
            if "steps" in job
            for step in _actions(job, "actions/upload-artifact")
        )
        required = {*consumers, "native-rust", "semantic-core-wasm", "quality-ratchets"}
        optional_os = filename == "integration-assurance.yml"
        if optional_os:
            required.add("dependency-audit")
            assert _needs(jobs["os-portability"]) == {"semantic-core-wasm"}
        _assurance_gate(jobs["assurance"], required, "github.sha", optional_os=optional_os)


def test_core_reusables_validate_exact_source_and_preserve_native_and_wasm_guards() -> None:
    for filename, name, output in (
        ("semantic-core-native.yml", "native-rust", "steps.tests.outputs.source_commit"),
        ("semantic-core-wasm.yml", "semantic-core-wasm", "steps.source.outputs.commit"),
    ):
        workflow = _load_workflow(filename)
        call = _workflow_trigger(workflow)["workflow_call"]
        assert call["inputs"]["source_ref"]["required"] is True
        assert call["outputs"]["source_commit"]["value"] == (
            f"${{{{ jobs.{name}.outputs.source_commit }}}}"
        )
        assert set(workflow["jobs"]) == {name}
        job = workflow["jobs"][name]
        _required(job)
        assert not _needs(job)
        assert job["outputs"]["source_commit"] == f"${{{{ {output} }}}}"
        (checkout,) = _actions(job, "actions/checkout")
        _required(checkout)
        assert checkout["with"]["ref"] == "${{ inputs.source_ref }}"
        source = _command_step(job, "git rev-parse HEAD")
        assert source["env"]["EXPECTED_SOURCE"] == "${{ inputs.source_ref }}"
        assert '[[ "$commit" == "$EXPECTED_SOURCE" ]]' in source["run"]
        assert "commit=$commit" in source["run"]
        toolchain = _command_step(job, "rust-toolchain.toml")
        (install,) = _actions(job, "dtolnay/rust-toolchain")
        _required(install)
        assert re.fullmatch(r"dtolnay/rust-toolchain@[0-9a-f]{40}", install["uses"])
        assert install["with"]["toolchain"] == "${{ steps.rust-toolchain.outputs.channel }}"
        if name == "native-rust":
            test = _command_step(job, "cargo test")
            cargo = next(line for line in test["run"].splitlines() if "cargo test" in line)
            assert shlex.split(cargo) == ["cargo", "test", "--manifest-path", "core/Cargo.toml"]
            assert test["shell"] == "bash"
            assert test["env"]["TESTED_SOURCE"] == "${{ steps.source.outputs.commit }}"
            assert '"source_commit=$TESTED_SOURCE" >> "$GITHUB_OUTPUT"' in test["run"]
            assert job["steps"].index(source) < job["steps"].index(toolchain)
            assert job["steps"].index(install) < job["steps"].index(test)

    producer = _load_workflow("semantic-core-wasm.yml")["jobs"]["semantic-core-wasm"]
    assert "cargo test" not in _commands(producer)
    build = _command_step(producer, "scripts/build_semantic_core.mjs")
    verify = _command_step(producer, "scripts/verify_semantic_core_artifact.py")
    guard = _command_step(producer, "scripts/check_semantic_core_artifact_change.py")
    bundle = _command_step(producer, "semantic_core_artifact_bundle.py create ")
    bootstrap = _command_step(producer, "semantic_core_artifact_bundle.py create-bootstrap")
    source_ref = "${{ steps.source.outputs.commit }}"
    (upload,) = [
        step
        for step in _actions(producer, "actions/upload-artifact")
        if step["with"]["name"] == f"semantic-core-{source_ref}"
    ]
    (bootstrap_upload,) = [
        step
        for step in _actions(producer, "actions/upload-artifact")
        if step["with"]["name"] == f"semantic-core-bootstrap-{source_ref}"
    ]
    for step in (upload, bootstrap_upload):
        _required(step)
        assert step["with"]["if-no-files-found"] == "error"
    steps = producer["steps"]
    assert steps.index(build) < steps.index(bootstrap) < steps.index(bootstrap_upload)
    assert steps.index(bootstrap_upload) < min(steps.index(verify), steps.index(guard))
    assert max(steps.index(verify), steps.index(guard)) < steps.index(bundle) < steps.index(upload)
    args = shlex.split(bundle["run"])
    assert args[args.index("--source-commit") + 1] == source_ref
    assert args[args.index("--output-dir") + 1] == upload["with"]["path"].rstrip("/")
    assert "--artifact-only" in build["run"]
    assert "--built-artifact" in guard["run"]


def test_pr_feedback_exercises_fast_semantic_and_source_contracts() -> None:
    workflow = _load_workflow("pr-feedback.yml")
    assert set(_workflow_trigger(workflow)["pull_request"]["branches"]) == {"main", "develop"}
    python = workflow["jobs"]["python-semantic"]
    fast = _command_step(python, "pytest")
    args = shlex.split(fast["run"])
    args = args[args.index("pytest") + 1 :]
    assert "-m" in args and args[args.index("-m") + 1] == "fast"
    for command in ("scripts/run_pr_feedback.py", "scripts/run_source_compat.py"):
        _command_step(python, command)
    for command in GOVERNANCE_COMMANDS:
        _command_step(workflow["jobs"]["governance"], command)


def test_develop_assurance_requires_integration_and_branch_synchronization() -> None:
    workflow = _load_workflow("develop-assurance.yml")
    assert _workflow_trigger(workflow)["push"]["branches"] == ["develop"]
    jobs = workflow["jobs"]
    _required(jobs["integration"])
    assert jobs["integration"]["uses"] == INTEGRATION_WORKFLOW
    _required(jobs["release-branch-sync"])
    sync = _command_step(jobs["release-branch-sync"], "scripts/verify_release_branch_sync.py")
    assert "--main-ref origin/main" in " ".join(sync["run"].split())
    assert f"--develop-ref {EVENT_SHA}" in " ".join(sync["run"].split())

    integration = _load_workflow("integration-assurance.yml")["jobs"]
    coverage = _command_step(integration["full-python-coverage"], "pytest")
    args = shlex.split(coverage["run"])
    args = args[args.index("pytest") + 1 :]
    assert {"--cov=adr_kit", "--cov-fail-under=80"} <= set(args)
    assert "-m" not in args or args[args.index("-m") + 1] == "not governance"
    _command_step(integration["source-compatibility"], "scripts/run_source_compat.py")
    _command_step(integration["governance"], "pytest -m governance")
    for command in GOVERNANCE_COMMANDS:
        _command_step(integration["governance"], command)
    _required(integration["dependency-audit"])
    _command_step(integration["dependency-audit"], "pip_audit")
    portability = integration["os-portability"]
    assert portability["if"] == "inputs.full_os_portability"
    assert portability.get("continue-on-error", False) is False
    assert set(portability["strategy"]["matrix"]["os"]) == PORTABILITY_OS
    _artifact_consumer(portability, EVENT_SHA)
    _command_step(portability, "pytest")


def test_release_certification_requires_retained_packages_and_portability() -> None:
    workflow = _load_workflow("release-certification.yml")
    assert _workflow_trigger(workflow) == {"push": {"branches": ["main"]}}
    jobs = workflow["jobs"]
    required = (
        "integration",
        "release-artifacts",
        "wheel-smoke",
        "os-wheel-smoke",
        "reproducibility",
        "benchmark-smoke",
    )
    for name in required:
        _required(jobs[name])
    assert jobs["integration"]["uses"] == INTEGRATION_WORKFLOW
    assert jobs["integration"]["with"]["full_os_portability"] is True

    artifacts = jobs["release-artifacts"]
    assert "integration" in _needs(artifacts)
    _artifact_consumer(artifacts, EVENT_SHA)
    inventory = _command_step(artifacts, "release_manifest.py inventory")
    assert shlex.split(inventory["run"])[-2:] == ["--source-commit", "$GITHUB_SHA"]
    (upload,) = _actions(artifacts, "actions/upload-artifact")
    _required(upload)
    assert artifacts["steps"].index(inventory) < artifacts["steps"].index(upload)
    assert upload["with"]["name"] == "release-bundle"
    assert upload["with"]["if-no-files-found"] == "error"
    assert {
        "python-dist/",
        "node-dist/",
        "release-manifest.json",
        "authority-inventory.json",
        "authority-manifest.json",
    } <= set(upload["with"]["path"].split())
    assert "normalize-sdist" in _commands(artifacts)
    _command_step(artifacts, "scripts/verify_npm_tarball.py")
    _command_step(artifacts, "adr_kit/core/semantic-core.wasm")
    _command_step(artifacts, "package/dist/generated/semantic-core.wasm")
    for name in ("wheel-smoke", "os-wheel-smoke"):
        job = jobs[name]
        assert "release-artifacts" in _needs(job)
        (download,) = _actions(job, "actions/download-artifact")
        _required(download)
        assert download["with"]["name"] == "release-bundle"
        assert job["steps"].index(download) < job["steps"].index(
            _command_step(job, "scripts/test_installed_wheel.py")
        )
    assert set(jobs["os-wheel-smoke"]["strategy"]["matrix"]["os"]) == PORTABILITY_OS
    assert jobs["reproducibility"]["env"]["SOURCE_DATE_EPOCH"]
    _command_step(jobs["reproducibility"], "hashlib.sha256")
    _command_step(jobs["benchmark-smoke"], "benchmarks/architecture-workflow.py")


def test_scheduled_portability_qualifies_and_consumes_the_resolved_commit() -> None:
    workflow = _load_workflow("portability-assurance.yml")
    assert {"schedule", "workflow_dispatch"} <= _workflow_trigger(workflow).keys()
    jobs = workflow["jobs"]
    resolver = jobs["resolve-source"]
    _required(resolver)
    (checkout,) = _actions(resolver, "actions/checkout")
    assert (
        checkout["with"]["ref"]
        == "${{ github.event_name == 'schedule' && 'refs/heads/develop' || github.sha }}"
    )
    _command_step(resolver, "git rev-parse HEAD")
    assert resolver["outputs"]["source_commit"] == "${{ steps.source.outputs.commit }}"

    source = "needs.resolve-source.outputs.source_commit"
    _core_calls(jobs, f"${{{{ {source} }}}}", prerequisites=frozenset({"resolve-source"}))
    suite = jobs["full-os-suite"]
    _required(suite)
    assert _needs(suite) == {"semantic-core-wasm"}
    _artifact_consumer(suite, "${{ needs.semantic-core-wasm.outputs.source_commit }}")
    assert set(suite["strategy"]["matrix"]["os"]) == PORTABILITY_OS
    _command_step(suite, "pytest")
    _assurance_gate(
        jobs["assurance"],
        {"resolve-source", "native-rust", "semantic-core-wasm", "full-os-suite"},
        source,
    )


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


def test_pr_feedback_runner_includes_exact_current_output_byte_golden() -> None:
    from scripts.run_pr_feedback import SEMANTIC_TESTS

    assert "tests/test_authoring_construction_v11_contract.py" in SEMANTIC_TESTS
    assert (
        "tests/golden/test_current_outputs.py::test_current_outputs_match_expected_bytes"
        in SEMANTIC_TESTS
    )
