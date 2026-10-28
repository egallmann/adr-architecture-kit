"""Canonical candidate inputs, deterministic derived views and closed references."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import pytest

from scripts import candidate_contract_assets as assets
from scripts import qualify_ai15_publication as ai
from scripts import qualify_acc15_publication as acc
from adr_kit.semantic_contract import verify_semantic_contract

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
    expected = json.loads((ROOT / f"contracts/{family}/v1.5/contract.json").read_text())
    assert result == expected


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
