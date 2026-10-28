"""Adversarial package/publisher admission, with only GitHub transport replaced.

Fixtures are ordinary wheel/tar/ZIP payloads containing the actual authority and
source WASM. No production trust flag or synthetic approval mode exists.
"""

from __future__ import annotations

import base64
import copy
import hashlib
import io
import json
import os
import shutil
import subprocess
import tarfile
import tomllib
import zipfile
from urllib.error import HTTPError
from email.message import Message
from pathlib import Path
from typing import Any

import pytest
import yaml

from scripts import release_authority_inventory as scanner
from scripts import release_authority_promotion as promotion
from scripts.check_semantic_contract_lifecycle_design import canonical_bytes, digest
from scripts.release_manifest import create_manifest

ROOT = Path(__file__).resolve().parents[1]


def zip_payload(files: dict[str, bytes]) -> bytes:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, value in sorted(files.items()):
            entry = zipfile.ZipInfo("placeholder")
            entry.filename = entry.orig_filename = name
            entry.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(entry, value)
    return stream.getvalue()


def tar_payload(files: dict[str, bytes]) -> bytes:
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w:gz") as archive:
        for name, value in sorted(files.items()):
            entry = tarfile.TarInfo(name)
            entry.size = len(value)
            archive.addfile(entry, io.BytesIO(value))
    return stream.getvalue()


@pytest.fixture(scope="module")
def qualified_index() -> scanner.AuthorityIndex:
    return scanner.AuthorityIndex(ROOT)


@pytest.fixture(scope="module")
def cohort_template(
    tmp_path_factory: pytest.TempPathFactory, qualified_index: scanner.AuthorityIndex
) -> Path:
    bundle = tmp_path_factory.mktemp("cohort")
    (bundle / "python-dist").mkdir()
    (bundle / "node-dist").mkdir()
    version = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"][
        "version"
    ]
    files = {
        p.relative_to(ROOT / "src").as_posix(): p.read_bytes()
        for p in (ROOT / "src/adr_kit").rglob("*.json")
    }
    files["adr_kit/core/semantic-core.wasm"] = (
        ROOT / "src/adr_kit/core/semantic-core.wasm"
    ).read_bytes()
    (bundle / f"python-dist/adr_architecture_kit-{version}-py3-none-any.whl").write_bytes(
        zip_payload(files)
    )
    (bundle / f"python-dist/adr_architecture_kit-{version}.tar.gz").write_bytes(
        tar_payload({f"adr-kit-{version}/src/{k}": v for k, v in files.items()})
    )
    node = {"package/dist/generated/" + k: v for k, v in files.items()}
    node["package/package.json"] = (ROOT / "packages/node/package.json").read_bytes()
    # Exercise generated JS authority discovery, not only JSON file mirrors.
    definition = next(iter(qualified_index.definitions.values()))
    node["package/dist/generated/authority.js"] = (
        "export const authority = " + json.dumps(definition) + ";\n"
    ).encode()
    (bundle / f"node-dist/adr-kit-{version}.tgz").write_bytes(tar_payload(node))
    source = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    create_manifest(bundle / "python-dist", bundle / "release-manifest.json", source, version)
    patch = pytest.MonkeyPatch()
    patch.setattr(scanner, "AuthorityIndex", lambda root: qualified_index)
    patch.setattr(promotion, "recorded_promotion_sources", lambda *args, **kwargs: [])
    try:
        scanner.create_cohort(bundle, source)
    finally:
        patch.undo()
    bundle.with_suffix(".zip").write_bytes(
        zip_payload(
            {
                p.relative_to(bundle).as_posix(): p.read_bytes()
                for p in bundle.rglob("*")
                if p.is_file()
            }
        )
    )
    return bundle


@pytest.fixture
def admitted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    cohort_template: Path,
    qualified_index: scanner.AuthorityIndex,
) -> dict[str, Any]:
    bundle = tmp_path / "release-bundle"
    shutil.copytree(cohort_template, bundle)
    raw_zip = cohort_template.with_suffix(".zip").read_bytes()
    bundle.with_suffix(".zip").write_bytes(raw_zip)
    source = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    monkeypatch.setattr(scanner, "AuthorityIndex", lambda root: qualified_index)
    monkeypatch.setattr(promotion, "recorded_promotion_sources", lambda *args, **kwargs: [])
    user = {"id": 13423582, "login": "egallmann", "type": "User"}
    cert = {
        "path": ".github/workflows/release-certification.yml",
        "head_sha": source,
        "head_branch": "main",
        "event": "push",
        "status": "completed",
        "conclusion": "success",
        "repository": {"full_name": promotion.REPOSITORY},
        "head_repository": {"full_name": promotion.REPOSITORY},
    }
    run = {**copy.deepcopy(cert), "path": promotion.WORKFLOW, "event": "workflow_dispatch"}
    artifact = {
        "id": 55,
        "name": "release-bundle",
        "expired": False,
        "digest": digest(raw_zip),
        "workflow_run": {"id": 88, "head_sha": source},
    }
    environment = {
        "id": 4,
        "name": promotion.ENVIRONMENT,
        "can_admins_bypass": False,
        "protection_rules": [
            {
                "type": "required_reviewers",
                "prevent_self_review": False,
                "reviewers": [{"type": "User", "reviewer": user}],
            }
        ],
    }
    review = {
        "user": copy.deepcopy(user),
        "state": "approved",
        "comment": "",
        "environments": [{"id": 4, "name": promotion.ENVIRONMENT}],
    }
    responses: dict[str, Any] = {
        "actions/runs/88": cert,
        "actions/runs/99": run,
        f"environments/{promotion.ENVIRONMENT}": environment,
        "actions/runs/99/approvals": [review],
    }
    monkeypatch.setattr(promotion, "api", lambda path: responses[path])
    monkeypatch.setattr(promotion.github, "_token", lambda: "test-transport-token")
    monkeypatch.setattr(promotion.github, "_paginate", lambda *args: [artifact])
    witness = cohort_template.parent / "qualified-subject.json"
    if not witness.exists():
        witness.write_bytes(canonical_bytes(promotion.bundle_evidence(bundle, source, 88)))
    evidence = json.loads(witness.read_bytes())
    review["comment"] = promotion.approval_statement(evidence)
    attestation = {**evidence, "human_approval": promotion.authorized_approval(evidence, 99)}
    # Transport payload follows the actual durable Git contents API shape.
    responses[f"contents/.github/authority-promotions/{source}.json?ref=main"] = {
        "type": "file",
        "encoding": "base64",
        "sha": "b" * 40,
        "content": base64.b64encode(canonical_bytes(attestation)).decode(),
    }
    responses[f"commits?path=.github/authority-promotions/{source}.json&sha=main&per_page=100"] = [
        {"sha": "c" * 40}
    ]
    responses[f"compare/{source}...{'c' * 40}"] = {
        "status": "ahead",
        "merge_base_commit": {"sha": source},
    }
    responses[f"contents/.github/authority-promotions/{source}.json?ref={'c' * 40}"] = responses[
        f"contents/.github/authority-promotions/{source}.json?ref=main"
    ]
    return {
        "bundle": bundle,
        "source": source,
        "artifact": artifact,
        "responses": responses,
        "review": review,
        "environment": environment,
        "run": run,
        "cert": cert,
        "attestation": attestation,
        "evidence": evidence,
    }


def test_actual_authority_cohort_and_owner_environment_path(admitted: dict[str, Any]) -> None:
    result = promotion.verify_promotion(admitted["bundle"], admitted["source"], 88)
    assert result["promotion_authorized"] is True
    assert result["approval"]["provider"] == "protected-human-environment"
    assert result["approval"]["actor"] == "egallmann"
    inventory = scanner.verify_cohort(admitted["bundle"], admitted["source"])
    assert any(
        p["encoding"] == "embedded-wasm" for a in inventory["authorities"] for p in a["placements"]
    )
    assert any(
        "authority.js" in p["locator"] for a in inventory["authorities"] for p in a["placements"]
    )
    assert {a["name"].split("/")[0] for a in inventory["artifacts"]} == {"python-dist", "node-dist"}


@pytest.mark.parametrize(
    "mutation",
    [
        "actor",
        "bot",
        "state",
        "comment",
        "environment",
        "ambiguous",
        "self-review",
        "bypass",
        "no-protection",
        "source",
        "workflow",
        "event",
        "foreign-repo",
        "run-incomplete",
        "expired",
        "artifact-source",
        "archive-digest",
        "cert-branch",
        "cert-event",
        "cert-failed",
    ],
)
def test_live_promotion_evidence_fails_closed(admitted: dict[str, Any], mutation: str) -> None:
    a = admitted
    if mutation == "actor":
        a["review"]["user"]["login"] = "someone-else"
    elif mutation == "bot":
        a["review"]["user"]["type"] = "Bot"
    elif mutation == "state":
        a["review"]["state"] = "rejected"
    elif mutation == "comment":
        a["review"]["comment"] += " altered"
    elif mutation == "environment":
        a["review"]["environments"][0]["id"] = 5
    elif mutation == "ambiguous":
        a["responses"]["actions/runs/99/approvals"].append(copy.deepcopy(a["review"]))
    elif mutation == "self-review":
        a["environment"]["protection_rules"][0]["prevent_self_review"] = True
    elif mutation == "bypass":
        a["environment"]["can_admins_bypass"] = True
    elif mutation == "no-protection":
        a["environment"]["protection_rules"] = []
    elif mutation == "source":
        a["run"]["head_sha"] = "f" * 40
    elif mutation == "workflow":
        a["run"]["path"] = ".github/workflows/not-promotion.yml"
    elif mutation == "event":
        a["run"]["event"] = "pull_request"
    elif mutation == "foreign-repo":
        a["run"]["head_repository"]["full_name"] = "other/repo"
    elif mutation == "run-incomplete":
        a["run"]["status"] = "in_progress"
    elif mutation == "expired":
        a["artifact"]["expired"] = True
    elif mutation == "artifact-source":
        a["artifact"]["workflow_run"]["head_sha"] = "f" * 40
    elif mutation == "archive-digest":
        a["artifact"]["digest"] = "sha256:" + "0" * 64
    elif mutation == "cert-branch":
        a["cert"]["head_branch"] = "develop"
    elif mutation == "cert-event":
        a["cert"]["event"] = "pull_request"
    elif mutation == "cert-failed":
        a["cert"]["conclusion"] = "failure"
    with pytest.raises((ValueError, RuntimeError)):
        if mutation == "archive-digest":
            promotion.bundle_evidence(a["bundle"], a["source"], 88)
        elif mutation in {"expired", "artifact-source", "cert-branch", "cert-event", "cert-failed"}:
            promotion.qualified_bundle(88, a["source"])
        else:
            promotion.authorized_approval(a["evidence"], 99)


@pytest.mark.parametrize(
    "field",
    ["source_commit", "retained_bundle", "approved_authorities", "artifacts", "human_approval"],
)
def test_forged_durable_attestation_rejected(admitted: dict[str, Any], field: str) -> None:
    attestation = copy.deepcopy(admitted["attestation"])
    if field == "source_commit":
        attestation[field] = "f" * 40
    elif field == "retained_bundle":
        attestation[field]["artifact_id"] = "999"
    elif field in {"approved_authorities", "artifacts"}:
        attestation[field].pop()
    else:
        attestation[field]["actor"] = "unapproved"
    admitted["responses"][
        f"contents/.github/authority-promotions/{admitted['source']}.json?ref=main"
    ]["content"] = base64.b64encode(canonical_bytes(attestation)).decode()
    with pytest.raises((ValueError, RuntimeError)):
        promotion.verify_promotion(admitted["bundle"], admitted["source"], 88)


@pytest.mark.parametrize(
    "mutation", ["payload", "inventory", "manifest", "extra", "missing", "zip"]
)
def test_retained_bundle_is_never_repaired_or_rehashed(
    admitted: dict[str, Any], mutation: str
) -> None:
    bundle = admitted["bundle"]
    if mutation == "payload":
        path = next((bundle / "node-dist").glob("*.tgz"))
        path.write_bytes(path.read_bytes() + b"changed")
    elif mutation == "inventory":
        (bundle / "authority-inventory.json").write_bytes(b"{}")
    elif mutation == "manifest":
        (bundle / "authority-manifest.json").write_bytes(b"{}")
    elif mutation == "extra":
        (bundle / "surprise.json").write_bytes(b"{}")
    elif mutation == "missing":
        (bundle / "release-manifest.json").unlink()
    else:
        bundle.with_suffix(".zip").write_bytes(b"forged")
    with pytest.raises((ValueError, RuntimeError)):
        promotion.verify_promotion(bundle, admitted["source"], 88)


def test_changed_resource_with_recalculated_package_digests_is_not_authority(
    admitted: dict[str, Any],
) -> None:
    bundle = admitted["bundle"]
    wheel = next((bundle / "python-dist").glob("*.whl"))
    files = scanner.archive_members(wheel.read_bytes(), True)
    name = next(
        n
        for n in files
        if n.endswith("architecture-interpretation-1.5-identity-representation-recipes.json")
    )
    value = json.loads(files[name])
    value["forged_rule"] = "unauthorized but rehashed"
    files[name] = json.dumps(value).encode()
    wheel.write_bytes(zip_payload(files))
    with pytest.raises((ValueError, RuntimeError), match="unknown or changed"):
        scanner.create_cohort(bundle, admitted["source"])


@pytest.mark.parametrize("kind", ["wheel", "sdist", "npm"])
def test_entire_released_authority_cannot_disappear_from_a_distribution(
    admitted: dict[str, Any],
    qualified_index: scanner.AuthorityIndex,
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
) -> None:
    bundle = admitted["bundle"]
    pattern = {
        "wheel": "python-dist/*.whl",
        "sdist": "python-dist/*.tar.gz",
        "npm": "node-dist/*.tgz",
    }[kind]
    artifact = next(bundle.glob(pattern))
    files = scanner.archive_members(artifact.read_bytes(), kind == "wheel")
    wasm = (ROOT / "src/adr_kit/core/semantic-core.wasm").read_bytes()
    embedded = {
        value for _, value in qualified_index.observations["wasm", hashlib.sha256(wasm).hexdigest()]
    }
    manifest_keys = {e["key"] for entries in qualified_index.required.values() for e in entries}
    baseline = qualified_index.released_values["npm" if kind == "npm" else "wheel"]
    candidates = {}
    for name, data in files.items():
        if not name.endswith(".json"):
            continue
        value = scanner.json_identity(json.loads(data))
        if (
            value in baseline
            and value not in embedded
            and not any(entry[2] in manifest_keys for entry in qualified_index.values[value])
            and not any(
                value in targets
                for owner, targets in qualified_index.schema_dependencies.items()
                if owner != value
            )
        ):
            candidates.setdefault(value, []).append(name)
    if not candidates:
        pytest.skip(
            "No released JSON-only leaf; released meaning is retained by other representations"
        )
    selected = sorted(candidates)[0]
    for name in candidates[selected]:
        del files[name]
    artifact.write_bytes(zip_payload(files) if kind == "wheel" else tar_payload(files))
    # Isolate the whole-authority requirement: all other source/closure checks
    # still qualify. This does not create an approval or a publisher receipt.
    with monkeypatch.context() as patch:
        patch.setattr(
            qualified_index,
            "released_values",
            {k: values - {selected} for k, values in qualified_index.released_values.items()},
        )
        scanner.discover_inventory(bundle, admitted["source"])
    with pytest.raises((ValueError, RuntimeError), match="missing released packaged authority"):
        scanner.create_cohort(bundle, admitted["source"])


def test_all_publishers_gate_both_jobs_and_never_rebuild() -> None:
    for filename in ("publish-pypi.yml", "publish-npm.yml"):
        workflow = yaml.safe_load((ROOT / ".github/workflows" / filename).read_text())
        for name in ("resolve-bundle", "publish"):
            text = yaml.safe_dump(workflow["jobs"][name])
            assert "release_authority_promotion.py download" in text
            assert "release_authority_promotion.py verify" in text
            assert "python -m build" not in text and "npm run build" not in text
        steps = workflow["jobs"]["publish"]["steps"]
        gate = next(
            i
            for i, s in enumerate(steps)
            if "release_authority_promotion.py verify" in s.get("run", "")
        )
        publish = next(
            i
            for i, s in enumerate(steps)
            if "gh-action-pypi-publish" in s.get("uses", "") or "npm publish" in s.get("run", "")
        )
        assert gate < publish


@pytest.mark.parametrize("name", ["../escape", "/absolute", "a\\b", "C:/escape", "a//b", "./a"])
def test_archive_path_attacks_fail(name: str) -> None:
    with pytest.raises((ValueError, RuntimeError)):
        scanner.archive_members(zip_payload({name: b"data"}), True)


def test_production_has_no_fixture_approval_switch() -> None:
    source = (ROOT / "scripts/release_authority_promotion.py").read_text()
    assert "--allow-fixture" not in source and "--trust-local" not in source
    assert "github-approved-review" not in source  # No owner self-review requirement.


def test_generated_authority_duplicate_members_are_not_silently_skipped() -> None:
    with pytest.raises((ValueError, RuntimeError), match="duplicate JSON"):
        list(scanner.json_objects('{"semanticContractFamily":"x","semanticContractFamily":"y"}'))


@pytest.mark.parametrize(
    "mutation", ["changed-history", "wrong-ancestry", "changed-snapshot", "missing-record"]
)
def test_durable_evidence_is_external_and_immutable(
    admitted: dict[str, Any], mutation: str
) -> None:
    a = admitted
    source = a["source"]
    if mutation == "changed-history":
        a["responses"][
            f"commits?path=.github/authority-promotions/{source}.json&sha=main&per_page=100"
        ].append({"sha": "d" * 40})
    elif mutation == "wrong-ancestry":
        a["responses"][f"compare/{source}...{'c' * 40}"]["status"] = "diverged"
    elif mutation == "changed-snapshot":
        key = f"contents/.github/authority-promotions/{source}.json?ref={'c' * 40}"
        a["responses"][key] = {**a["responses"][key], "sha": "d" * 40}
    else:
        a["responses"][f"contents/.github/authority-promotions/{source}.json?ref=main"][
            "type"
        ] = "directory"
    with pytest.raises((ValueError, RuntimeError)):
        promotion.retrieve_attestation(source)


def test_validly_recomputed_unauthorized_definition_is_rejected(admitted: dict[str, Any]) -> None:
    from adr_kit.semantic_contract import (
        calculate_semantic_contract_fingerprint,
        verify_semantic_contract,
    )

    bundle = admitted["bundle"]
    wheel = next((bundle / "python-dist").glob("*.whl"))
    files = scanner.archive_members(wheel.read_bytes(), True)
    name = next(n for n in files if n.endswith("definitions/architecture-interpretation-1.5.json"))
    value = json.loads(files[name])
    value["resourceManifest"][0]["role"] = "interpretation-rule"
    computed = calculate_semantic_contract_fingerprint(value)
    assert computed.success
    value["semanticContractFingerprint"] = computed.semantic_contract_fingerprint
    assert verify_semantic_contract(value).success
    files[name] = json.dumps(value).encode()
    wheel.write_bytes(zip_payload(files))
    with pytest.raises((ValueError, RuntimeError), match="unknown or changed"):
        scanner.create_cohort(bundle, admitted["source"])


def test_missing_member_in_one_package_is_not_supplied_by_another(admitted: dict[str, Any]) -> None:
    bundle = admitted["bundle"]
    wheel = next((bundle / "python-dist").glob("*.whl"))
    files = scanner.archive_members(wheel.read_bytes(), True)
    files = {
        k: v
        for k, v in files.items()
        if not k.endswith("architecture-interpretation-1.5-identity-representation-recipes.json")
    }
    wheel.write_bytes(zip_payload(files))
    with pytest.raises((ValueError, RuntimeError), match="incomplete|missing"):
        scanner.create_cohort(bundle, admitted["source"])


def test_authenticated_download_binds_actual_zip(
    admitted: dict[str, Any], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    class Response:
        def __enter__(self) -> Response:
            return self

        def __exit__(self, *args: Any) -> None:
            return None

        def read(self, limit: int) -> bytes:
            return admitted["bundle"].with_suffix(".zip").read_bytes()[:limit]

    class Opener:
        def open(self, request: Any, timeout: int) -> Response:
            assert (
                request.full_url
                == f"https://api.github.com/repos/{promotion.REPOSITORY}/actions/artifacts/55/zip"
            )
            assert request.get_header("Authorization") == "Bearer test-transport-token"
            return Response()

    monkeypatch.setattr(promotion.urllib.request, "build_opener", lambda *args: Opener())
    destination = tmp_path / "downloaded"
    promotion.download_bundle(88, admitted["source"], destination)
    assert (
        destination.with_suffix(".zip").read_bytes()
        == admitted["bundle"].with_suffix(".zip").read_bytes()
    )
    assert promotion.bundle_evidence(destination, admitted["source"], 88) == admitted["evidence"]


def test_candidate_changes_are_not_frozen_but_genuine_promotions_are(
    admitted: dict[str, Any],
) -> None:
    inventory = {"authorities": copy.deepcopy(admitted["evidence"]["approved_authorities"])}
    selected = next(
        r
        for r in inventory["authorities"]
        if r["family"] == "architecture-interpretation" and r["version"] == "1.5"
    )
    selected["scf"] = "scf:v1:sha256:" + "f" * 64
    promotion.enforce_promoted(inventory, [])
    with pytest.raises((ValueError, RuntimeError), match="immutable promoted authority changed"):
        promotion.enforce_promoted(inventory, [admitted["attestation"]])


@pytest.mark.parametrize(
    "location",
    [
        "https://fixture.blob.core.windows.net/bundle?sig=public-test",
        "http://fixture.blob.core.windows.net/bundle",
        "https://api.github.com.evil.test/bundle",
    ],
)
def test_signed_blob_redirect_never_receives_github_token(
    admitted: dict[str, Any], monkeypatch: pytest.MonkeyPatch, tmp_path: Path, location: str
) -> None:
    class Opener:
        def open(self, request: Any, timeout: int) -> Any:
            headers = Message()
            headers["Location"] = location
            raise HTTPError(request.full_url, 302, "redirect", headers, None)

    class Response:
        def __enter__(self) -> Response:
            return self

        def __exit__(self, *args: Any) -> None:
            return None

        def read(self, limit: int) -> bytes:
            return admitted["bundle"].with_suffix(".zip").read_bytes()[:limit]

    def blob(url: str, timeout: int) -> Response:
        assert isinstance(url, str) and url == location
        # Passing only the signed URL means no API Request/Authorization headers.
        return Response()

    monkeypatch.setattr(promotion.urllib.request, "build_opener", lambda *args: Opener())
    monkeypatch.setattr(promotion.urllib.request, "urlopen", blob)
    destination = tmp_path / "redirected"
    if location.startswith("https://fixture.blob.core.windows.net/"):
        promotion.download_bundle(88, admitted["source"], destination)
        assert destination.is_dir()
    else:
        with pytest.raises((ValueError, RuntimeError), match="untrusted artifact redirect"):
            promotion.download_bundle(88, admitted["source"], destination)
        assert not destination.exists()


@pytest.mark.parametrize("mutation", ["missing", "resource", "SCF"])
def test_promoted_identity_cannot_be_dropped_or_silently_replaced(
    admitted: dict[str, Any], mutation: str
) -> None:
    inventory = {"authorities": copy.deepcopy(admitted["evidence"]["approved_authorities"])}
    if mutation == "missing":
        inventory["authorities"].pop()
    elif mutation == "resource":
        inventory["authorities"][0]["resources"][0]["digest"] = "sha256:" + "0" * 64
    else:
        inventory["authorities"][0]["scf"] = "scf:v1:sha256:" + "0" * 64
    with pytest.raises((ValueError, RuntimeError), match="promoted authority"):
        promotion.enforce_promoted(inventory, [admitted["attestation"]])


@pytest.mark.parametrize(
    "mutation", [None, "actor", "comment", "policy", "wrong-run", "changed-subject", "ambiguous"]
)
def test_historical_freeze_requires_actual_original_human_evidence(
    admitted: dict[str, Any], monkeypatch: pytest.MonkeyPatch, mutation: str | None
) -> None:
    previous = admitted["source"]
    monkeypatch.setattr(promotion, "recorded_promotion_sources", lambda *args, **kwargs: [previous])
    admitted["responses"][f"contents/PROJECT.yaml?ref={previous}"] = {
        "type": "file",
        "encoding": "base64",
        "content": base64.b64encode((ROOT / "PROJECT.yaml").read_bytes()).decode(),
    }
    if mutation == "actor":
        admitted["review"]["user"]["login"] = "unauthorized"
    elif mutation == "comment":
        admitted["review"]["comment"] += " forged"
    elif mutation == "policy":
        admitted["responses"][f"contents/PROJECT.yaml?ref={previous}"]["content"] = (
            base64.b64encode(
                b"integrations: {scm: {required_approvers: ['someone-else']}}"
            ).decode()
        )
    elif mutation == "wrong-run":
        admitted["run"]["head_sha"] = "f" * 40
    elif mutation == "changed-subject":
        record = copy.deepcopy(admitted["attestation"])
        record["retained_bundle"]["digest"] = "sha256:" + "0" * 64
        admitted["responses"][f"contents/.github/authority-promotions/{previous}.json?ref=main"][
            "content"
        ] = base64.b64encode(canonical_bytes(record)).decode()
    elif mutation == "ambiguous":
        admitted["responses"]["actions/runs/99/approvals"].append(copy.deepcopy(admitted["review"]))
    if mutation:
        with pytest.raises((ValueError, RuntimeError)):
            promotion.qualified_prior_promotions("f" * 40)
    else:
        admitted["artifact"]["expired"] = True
        assert promotion.qualified_prior_promotions("f" * 40) == [admitted["attestation"]]
        with pytest.raises((ValueError, RuntimeError), match="expired"):
            promotion.verify_promotion(admitted["bundle"], previous, 88)


def test_cached_release_evidence_cannot_replace_registry_identity(tmp_path: Path) -> None:
    if os.name == "nt" and not str(tmp_path).startswith("\\\\?\\"):
        tmp_path = Path("\\\\?\\" + str(tmp_path.resolve()))
    classification = json.loads(
        (ROOT / "adrs/migrations/semantic-contract-lifecycle-classification.json").read_bytes()
    )
    cache = tmp_path / ".tmp/released-authority-evidence"
    cache.mkdir(parents=True)
    (cache / classification["release_evidence"][0]["sha256"]).write_bytes(b"forged")
    with pytest.raises((ValueError, RuntimeError), match="released package evidence mutation"):
        list(scanner.released_payloads(classification, tmp_path))


def test_authentically_accepted_governance_is_required(
    admitted: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        promotion,
        "qualify_repository",
        lambda root: {
            "effective_replacements": [],
            "activation": "inactive_without_independent_human_evidence",
        },
    )
    with pytest.raises((ValueError, RuntimeError), match="authentically active"):
        promotion.bundle_evidence(admitted["bundle"], admitted["source"], 88)


@pytest.mark.parametrize(
    "member",
    [
        "contracts/example/v1.5/rules.json",
        "src/adr_kit/core/semantic-core.wasm",
        "src/adr_kit/schema/member.json",
        "src/adr_kit/compatibility/member.json",
    ],
)
@pytest.mark.parametrize("mutation", ["tracked", "untracked", "ignored"])
def test_source_commit_excludes_changed_or_uncommitted_authority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, member: str, mutation: str
) -> None:
    # Real temporary Git commits bind source bytes. This fixture does not activate
    # repository governance or substitute for authentic human acceptance.
    root = tmp_path / "source"
    root.mkdir()

    def git(*args: str) -> str:
        return subprocess.check_output(
            ["git", *args], cwd=root, text=True, stderr=subprocess.STDOUT
        ).strip()

    git("init")
    path = root / member
    path.parent.mkdir(parents=True)
    path.write_bytes(b"original")
    (root / ".gitignore").write_text("*.pyc\nignored/\n", encoding="utf-8")
    git("add", ".")
    git(
        "-c",
        "user.name=Test Fixture",
        "-c",
        "user.email=fixture@example.invalid",
        "commit",
        "-m",
        "Source byte fixture",
    )
    source = git("rev-parse", "HEAD")
    monkeypatch.setattr(
        promotion,
        "qualify_repository",
        lambda _: {"effective_replacements": ["fixture"], "activation": "fixture"},
    )
    # Ordinary interpreter cache files must not invalidate a clean source.
    (path.parent / "module.pyc").write_bytes(b"cache")
    promotion.verify_source(source, root)
    if mutation == "tracked":
        path.write_bytes(b"changed")
    elif mutation == "untracked":
        path.with_name("extra" + path.suffix).write_bytes(b"uncommitted authority")
    else:
        hidden = path.parent / "ignored"
        hidden.mkdir()
        (hidden / path.name).write_bytes(b"ignored authority")
    with pytest.raises((ValueError, RuntimeError), match="source authority"):
        promotion.verify_source(source, root)


def test_released_schema_only_and_protocol_authorities_remain_protected(
    qualified_index: scanner.AuthorityIndex,
) -> None:
    assert {
        ("authoring", v) for v in ("1.2", "1.3", "1.4", "1.5", "1.6", "1.7")
    } <= qualified_index.released
    assert {("semantic-core", v) for v in ("1.0", "1.1", "1.2", "1.3")} <= qualified_index.released


@pytest.mark.parametrize("status", ["added", "modified", "removed", "renamed"])
def test_live_history_cannot_erase_a_promotion_after_the_source_snapshot(
    monkeypatch: pytest.MonkeyPatch, status: str
) -> None:
    source, old, snapshot = "a" * 40, "b" * 40, "c" * 40
    path = f".github/authority-promotions/{old}.json"
    monkeypatch.setattr(promotion.subprocess, "check_output", lambda *args, **kwargs: "")
    monkeypatch.setattr(promotion, "api_list", lambda *args: [{"sha": "d" * 40}])
    monkeypatch.setattr(promotion.github, "_token", lambda: "test-token")
    monkeypatch.setattr(
        promotion.github, "_paginate", lambda *args: [{"filename": path, "status": status}]
    )
    responses = {
        "git/ref/heads/main": {"object": {"sha": snapshot}},
        f"contents/.github?ref={snapshot}": [{"name": "authority-promotions", "type": "dir"}],
        f"contents/.github/authority-promotions?ref={snapshot}": [
            {"name": old + ".json", "path": path, "type": "file"}
        ],
    }
    monkeypatch.setattr(promotion, "api", lambda path: responses[path])
    if status == "added":
        assert promotion.recorded_promotion_sources(source, ROOT, live=True) == [old]
    else:
        with pytest.raises((ValueError, RuntimeError), match="historical promotion record"):
            promotion.recorded_promotion_sources(source, ROOT, live=True)


def test_new_workflow_never_auto_approves_or_publishes() -> None:
    workflow = yaml.safe_load((ROOT / ".github/workflows/authority-promotion.yml").read_text())
    assert workflow["jobs"]["attest"]["environment"]["name"] == promotion.ENVIRONMENT
    text = yaml.safe_dump(workflow)
    assert "npm publish" not in text and "gh-action-pypi-publish" not in text
    assert "actions: write" not in text and "contents: write" not in text
    assert "release_authority_promotion.py attest" in text
    certification = (ROOT / ".github/workflows/release-certification.yml").read_text()
    assert "release_manifest.py inventory" in certification
    assert (
        "authority-inventory.json" in certification and "authority-manifest.json" in certification
    )
