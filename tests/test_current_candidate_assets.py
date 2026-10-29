"""Canonical candidate inputs, deterministic derived views and closed references."""

from __future__ import annotations

import copy
import io
import json
import os
import shutil
import subprocess
import tarfile
from pathlib import Path

import pytest

from scripts import candidate_contract_assets as assets
from scripts import qualify_ai15_publication as ai
from scripts import qualify_acc15_publication as acc
from adr_kit.semantic_contract import (
    get_semantic_contract,
    validate_semantic_resource_closure,
    verify_semantic_contract,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    "family,qualifier",
    [
        ("architecture-interpretation", ai),
        ("authoring-construction", acc),
    ],
)
def test_rehashed_proposed_definition_does_not_authorize_wrong_roles(family, qualifier) -> None:
    proposed, _ = assets.assemble(ROOT, family)
    member = next(
        m
        for m in proposed["resourceManifest"]
        if m["canonicalResourceKey"] == family + "/1.5/rules"
    )
    member["role"] = "normative-definition"
    forged = assets.definition(
        family,
        proposed["resourceManifest"],
        proposed["frozenNormativeConformanceResources"],
        version="1.5",
    )
    assert verify_semantic_contract(forged).success
    with pytest.raises(qualifier.PublicationError, match="role"):
        qualifier.qualify(ROOT, candidate_definition=forged)


@pytest.mark.parametrize("family", ["architecture-interpretation", "authoring-construction"])
def test_current_canonical_inputs_reproduce_their_qualified_definition(family: str) -> None:
    result, _ = assets.assemble(ROOT, family)
    source = ROOT / f"contracts/{family}/v1.5/contract.json"
    expected = json.loads(source.read_text())
    assert result == expected
    assert get_semantic_contract(family, "1.5").to_wire() == expected
    for mirror in (
        f"contracts/semantic-contract/v1.0/definitions/{family}-1.5.json",
        f"src/adr_kit/semantic_contract/v1_0/definitions/{family}-1.5.json",
        f"src/adr_kit/semantic_contract/v1_0/{family}-1.5.json",
    ):
        assert (ROOT / mirror).read_bytes() == source.read_bytes()


@pytest.fixture
def candidate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    if os.name == "nt" and not str(tmp_path).startswith("\\\\?\\"):
        tmp_path = Path("\\\\?\\" + str(tmp_path.resolve()))
    source = "contracts/architecture-interpretation/v1.5"
    shutil.copytree(ROOT / source, tmp_path / source)
    real = assets.canonical_resource
    monkeypatch.setattr(assets, "canonical_resource", lambda _, key: real(ROOT, key))
    return tmp_path


def test_candidate_resources_are_inputs_not_reconstructed_outputs(candidate: Path) -> None:
    path = candidate / "contracts/architecture-interpretation/v1.5/resources/rules.json"
    original = json.loads(path.read_text())
    path.write_text(json.dumps(original, indent=4) + "\n", encoding="utf-8")
    raw = path.read_bytes()
    result, contents = assets.assemble(candidate, "architecture-interpretation")
    for folder in (
        "contracts/semantic-contract/v1.0/resources",
        "src/adr_kit/semantic_contract/v1_0/resources",
    ):
        (candidate / folder).mkdir(parents=True)
    assets.distribute(candidate, "architecture-interpretation", result, contents)
    assert path.read_bytes() == raw
    assert (
        candidate
        / "contracts/semantic-contract/v1.0/resources/architecture-interpretation-1.5-rules.json"
    ).read_bytes() == raw
    assert (
        candidate
        / "src/adr_kit/semantic_contract/v1_0/resources/architecture-interpretation-1.5-rules.json"
    ).read_bytes() == raw


def test_same_version_candidate_revision_gets_a_new_qualified_commitment(
    candidate: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    previous, _ = assets.assemble(candidate, "architecture-interpretation")
    path = (
        candidate / "contracts/architecture-interpretation/v1.5/resources/conformance.schema.json"
    )
    schema = json.loads(path.read_text())
    # A schema annotation changes the exact authoritative bytes without changing
    # its permitted instances. This is a candidate revision, not a successor.
    schema["description"] = "Authority conformance; no instance execution is enabled."
    path.write_text(json.dumps(schema), encoding="utf-8")
    revised, contents = assets.assemble(candidate, "architecture-interpretation")
    assert revised["semanticContractVersion"] == previous["semanticContractVersion"] == "1.5"
    assert revised["semanticContractFingerprint"] != previous["semanticContractFingerprint"]
    original_read = ai.read
    monkeypatch.setattr(
        ai, "read", lambda root, key: contents[key] if key in contents else original_read(root, key)
    )
    report = ai.qualify(ROOT, candidate_definition=revised)
    assert report["output_accounting"] == {"QUALIFIED": 240, "BLOCKED": 215}
    assert report["complete_interpretation"] == "Unavailable"


def test_duplicate_source_json_is_not_silently_canonicalized(candidate: Path) -> None:
    path = candidate / "contracts/architecture-interpretation/v1.5/resources/rules.json"
    path.write_text('{"resource":"a","resource":"b"}', encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate canonical JSON member"):
        assets.assemble(candidate, "architecture-interpretation")


@pytest.mark.parametrize("mutation", ["self-reference", "missing-role", "duplicate-role"])
def test_incomplete_or_self_referential_candidate_is_not_distributed(
    candidate: Path, mutation: str
) -> None:
    base = candidate / "contracts/architecture-interpretation/v1.5"
    if mutation == "self-reference":
        path = base / "resources/rules.json"
        value = json.loads(path.read_text())
        value["semanticDependencies"].append("architecture-interpretation/1.5/contract")
        path.write_text(json.dumps(value), encoding="utf-8")
    else:
        path = base / "contract.json"
        value = json.loads(path.read_text())
        if mutation == "duplicate-role":
            value["resourceManifest"].append(dict(value["resourceManifest"][0]))
        else:
            value["resourceManifest"] = [
                m
                for m in value["resourceManifest"]
                if m["canonicalResourceKey"] != "architecture-interpretation/1.5/rules"
            ]
        path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(
        ValueError,
        match="self-referential|missing authored resource role|duplicate authored resource role",
    ):
        assets.assemble(candidate, "architecture-interpretation")
    assert not (candidate / "src").exists()


@pytest.mark.parametrize(
    "key",
    [
        "../1.5/rules",
        "architecture-interpretation/latest/rules",
        "authoring/1.7/schema/../../escape",
        "authoring//schema",
    ],
)
def test_malformed_or_ambient_resource_selection_is_rejected(key: str) -> None:
    with pytest.raises(ValueError, match="invalid canonical resource key"):
        assets.canonical_resource(ROOT, key)


def test_versionless_released_filename_is_not_a_predecessor_fallback(tmp_path: Path) -> None:
    if os.name == "nt" and not str(tmp_path).startswith("\\\\?\\"):
        tmp_path = Path("\\\\?\\" + str(tmp_path.resolve()))
    folder = tmp_path / "contracts/semantic-contract/v1.0/resources"
    folder.mkdir(parents=True)
    value = {
        "semanticContractFamily": "architecture-interpretation",
        "semanticContractVersion": "1.0",
    }
    (folder / "architecture-interpretation-shared.json").write_text(
        json.dumps(value), encoding="utf-8"
    )
    assert assets.canonical_resource(tmp_path, "architecture-interpretation/1.0/shared") == value
    with pytest.raises(ValueError, match="missing exact canonical resource"):
        assets.canonical_resource(tmp_path, "architecture-interpretation/1.5/shared")


def test_flattened_candidate_output_cannot_replace_missing_canonical_input(tmp_path: Path) -> None:
    if os.name == "nt" and not str(tmp_path).startswith("\\\\?\\"):
        tmp_path = Path("\\\\?\\" + str(tmp_path.resolve()))
    folder = tmp_path / "contracts/semantic-contract/v1.0/resources"
    folder.mkdir(parents=True)
    (folder / "architecture-interpretation-1.5-rules.json").write_text(
        json.dumps({"resource": "architecture-interpretation/1.5/rules"}), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="missing exact canonical resource"):
        assets.canonical_resource(tmp_path, "architecture-interpretation/1.5/rules")


def test_original_candidate_revision_is_reproducible_without_freezing_current_bytes() -> None:
    # This revision is historical evidence, not an expected HEAD/base or an
    # obligation to keep resolving its content from the current candidate.
    revision = "6ddc8c2b6d66531ff3ecefb0bba7b15616ac4f0c"
    archived = subprocess.check_output(
        ["git", "archive", revision, "contracts/semantic-contract/v1.0"], cwd=ROOT
    )
    with tarfile.open(fileobj=io.BytesIO(archived)) as archive:
        documents = {
            member.name: json.load(archive.extractfile(member))
            for member in archive.getmembers()
            if member.isfile() and member.name.endswith(".json")
        }
    base = "contracts/semantic-contract/v1.0/"
    for family in ("architecture-interpretation", "authoring-construction"):
        historical = documents[base + f"definitions/{family}-1.5.json"]
        supplied = []
        for member in historical["resourceManifest"]:
            key = member["canonicalResourceKey"]
            prefix, version, name = key.split("/", 2)
            paths = [base + "resources/" + key.replace("/", "-") + ".json"]
            if name == "contract":
                paths += [base + f"definitions/{prefix}-{version}.json"]
            paths += [base + f"resources/{prefix}-{name}.json"]
            selected = next(path for path in paths if path in documents)
            supplied.append({"canonicalResourceKey": key, "content": documents[selected]})
        assert verify_semantic_contract(historical).success
        assert validate_semantic_resource_closure(historical, supplied).closure_valid


def test_acc_rejects_a_differently_qualified_current_AI_definition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    proposed = copy.deepcopy(assets.canonical_resource(ROOT, acc.AI + "contract"))
    proposed["resourceManifest"][0]["role"] = "normative-definition"
    forged = assets.definition(
        "architecture-interpretation",
        proposed["resourceManifest"],
        proposed["frozenNormativeConformanceResources"],
        version="1.5",
    )
    assert verify_semantic_contract(forged).success
    original = acc.canonical_resource
    monkeypatch.setattr(
        acc,
        "canonical_resource",
        lambda root, key: forged if key == acc.AI + "contract" else original(root, key),
    )
    with pytest.raises(acc.PublicationError, match="inconsistent_current_AI_definition"):
        acc.qualify(ROOT)
