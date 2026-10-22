"""Standalone NM 2.5 publication conformance without runtime model registration."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
from importlib import resources
from pathlib import Path
from typing import Any

import pytest
import rfc8785
from jsonschema import Draft7Validator
from referencing import Registry, Resource

from adr_kit.semantic_contract import (
    SemanticContractVersion,
    calculate_semantic_contract_fingerprint,
    get_semantic_contract,
    list_semantic_contracts,
    load_semantic_resource,
    validate_semantic_resource_closure,
    verify_semantic_contract,
)

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_ROOT = ROOT / "schema" / "normalized-model" / "v2.5"
OLD_ROOT = ROOT / "schema" / "normalized-model" / "v2.4"
CONTRACT_ROOT = ROOT / "contracts" / "semantic-contract" / "v1.0"
BUNDLED = ROOT / "src" / "adr_kit" / "semantic_contract" / "v1_0"
NAMES = ["normalized-architecture-model.schema.json","normalized-entity-registry.schema.json","normalized-entity.schema.json","relationship-record.schema.json","relationship-registry.schema.json","unresolved-registry.schema.json"]
EXPECTED_SCF = "scf:v1:sha256:bb48720502668e434d378445004aec7783346a0e74254c9e0d3cb01a8798d9d7"
UUID = "019109a0-b1c2-7def-8a00-112233445566"
BASELINE_GIT_BLOBS = {
  "contracts/compatibility/host-capabilities.json": "c1f0c7c9d1bede96b1645141a00da63f3e37a0d3",
  "contracts/semantic-contract/v1.0/catalog/semantic-contract-catalog-1.0.json": "4659545c9b93af7b7e72d93a404ad8e4930f5bb5",
  "contracts/semantic-contract/v1.0/current/semantic-contract-current-1.0.json": "4383eb0bf08795823bed583b4169eb0a2bf4e677",
  "contracts/semantic-contract/v1.0/definitions/architecture-interpretation-1.1.json": "71b7248658c387a7bf23ac3cc51317d4d696b9b6",
  "contracts/semantic-contract/v1.0/definitions/architecture-interpretation-1.2.json": "e297a2fcbe07ba47cebcbc873d11b82249004dc5",
  "contracts/semantic-contract/v1.0/definitions/architecture-interpretation.json": "9f044344c33fc3479549d5558675451d48574a75",
  "contracts/semantic-contract/v1.0/definitions/authoring-construction-1.0.json": "b00fd399e1870b9577f8f7ec54dfc67f66196069",
  "contracts/semantic-contract/v1.0/definitions/authoring-construction-1.1.json": "14981aefe18f9780152f0f96348e29e00a2f8cab",
  "contracts/semantic-contract/v1.0/definitions/authoring-construction-1.2.json": "1918ad7eb7bf27ef2de187dc0215f6f399f3dc2b",
  "contracts/semantic-contract/v1.0/definitions/normalized-model-2.4.json": "a0559a5bda8fd65b90b5b0d9b79949c745df464c",
  "contracts/semantic-contract/v1.0/definitions/normalized-model.json": "6b49bd32ff0fd91198a531654c911da1e9f4e925",
  "contracts/semantic-contract/v1.0/definitions/normative-semantics-1.0.json": "2ae295dee7b7f6a9d353839ec8b019798a670464",
  "contracts/semantic-contract/v1.0/definitions/normative-semantics.json": "2ae295dee7b7f6a9d353839ec8b019798a670464",
  "contracts/semantic-contract/v1.0/policy/semantic-contract-policy-1.0.json": "363e8535ddc8f5fdffcc7f375ebb9b13bf40f562",
  "contracts/semantic-contract/v1.0/resources/normalized-model-2.4-conformance.json": "47ec0af3b6c59774aacc85ed6ef4eddbe2a63b3a",
  "contracts/semantic-contract/v1.0/resources/normalized-model-2.4-schema-normalized-architecture-model.schema.json": "51ab6b0fc9538696946a7bd617600898fda16e4b",
  "contracts/semantic-contract/v1.0/resources/normalized-model-2.4-schema-normalized-entity-registry.schema.json": "36cfa43d043f52a6e5f716958f33925580f92cf3",
  "contracts/semantic-contract/v1.0/resources/normalized-model-2.4-schema-normalized-entity.schema.json": "392c89dc7cfd91dfa2e93ba08448cac9b9d63c9c",
  "contracts/semantic-contract/v1.0/resources/normalized-model-2.4-schema-relationship-record.schema.json": "1fe37c1195387bcd7e8eeb791f6dca0df3295588",
  "contracts/semantic-contract/v1.0/resources/normalized-model-2.4-schema-relationship-registry.schema.json": "8d0c87b1d460e1c3d15f72693eca74278331718f",
  "contracts/semantic-contract/v1.0/resources/normalized-model-2.4-schema-unresolved-registry.schema.json": "3a799c04c6c3244034422d380711e862f1bc0146",
  "contracts/semantic-contract/v1.0/sets/scs-v1-sha256-2cf903fe80c50b97443645369b28443c7fa186ed758e2e22d7ce758ccb0d6020.json": "a038827f86a122d71bb8ae148f69bf7e1acc8598",
  "contracts/semantic-contract/v1.0/sets/scs-v1-sha256-d12ce535f0a90c23741dfa516d207091197c2772dbcd538fabb133bdf5b79af6.json": "361a336464c8ce0dc1bf936145066dd4b8d6be8f",
  "packages/node/src/generated/semantic-core.wasm": "7ad5c0594effa63b8246e77e5926e20545fd34f3",
  "schema/normalized-model/v2.3/normalized-architecture-model.schema.json": "c5caf6b3f008b9d32dacaeed9d251e2978773004",
  "schema/normalized-model/v2.3/normalized-entity-registry.schema.json": "c3ba0f7648127dc874bf6887bf59dc33e430bcab",
  "schema/normalized-model/v2.3/normalized-entity.schema.json": "cc5bd2bac84978bd3a82fa99b480767df21d8926",
  "schema/normalized-model/v2.3/relationship-record.schema.json": "e3e3ebe44c510f83e8b819fd2b07efbf8aa8a24d",
  "schema/normalized-model/v2.3/relationship-registry.schema.json": "f48a86f505c95cb4b426f2183d68f0273e4da0e2",
  "schema/normalized-model/v2.3/unresolved-registry.schema.json": "a53140c599338ae13f285c29a6ac18315e204958",
  "schema/normalized-model/v2.4/normalized-architecture-model.schema.json": "51ab6b0fc9538696946a7bd617600898fda16e4b",
  "schema/normalized-model/v2.4/normalized-entity-registry.schema.json": "36cfa43d043f52a6e5f716958f33925580f92cf3",
  "schema/normalized-model/v2.4/normalized-entity.schema.json": "392c89dc7cfd91dfa2e93ba08448cac9b9d63c9c",
  "schema/normalized-model/v2.4/relationship-record.schema.json": "1fe37c1195387bcd7e8eeb791f6dca0df3295588",
  "schema/normalized-model/v2.4/relationship-registry.schema.json": "8d0c87b1d460e1c3d15f72693eca74278331718f",
  "schema/normalized-model/v2.4/unresolved-registry.schema.json": "3a799c04c6c3244034422d380711e862f1bc0146",
  "src/adr_kit/semantic_contract/v1_0/catalog/semantic-contract-catalog-1.0.json": "4659545c9b93af7b7e72d93a404ad8e4930f5bb5",
  "src/adr_kit/semantic_contract/v1_0/current/semantic-contract-current-1.0.json": "4383eb0bf08795823bed583b4169eb0a2bf4e677",
  "src/adr_kit/semantic_contract/v1_0/definitions/architecture-interpretation-1.1.json": "71b7248658c387a7bf23ac3cc51317d4d696b9b6",
  "src/adr_kit/semantic_contract/v1_0/definitions/architecture-interpretation-1.2.json": "e297a2fcbe07ba47cebcbc873d11b82249004dc5",
  "src/adr_kit/semantic_contract/v1_0/definitions/authoring-construction-1.0.json": "b00fd399e1870b9577f8f7ec54dfc67f66196069",
  "src/adr_kit/semantic_contract/v1_0/definitions/authoring-construction-1.1.json": "14981aefe18f9780152f0f96348e29e00a2f8cab",
  "src/adr_kit/semantic_contract/v1_0/definitions/authoring-construction-1.2.json": "1918ad7eb7bf27ef2de187dc0215f6f399f3dc2b",
  "src/adr_kit/semantic_contract/v1_0/definitions/normalized-model-2.4.json": "a0559a5bda8fd65b90b5b0d9b79949c745df464c",
  "src/adr_kit/semantic_contract/v1_0/definitions/normative-semantics-1.0.json": "2ae295dee7b7f6a9d353839ec8b019798a670464",
  "src/adr_kit/semantic_contract/v1_0/normalized-model-2.4.json": "a0559a5bda8fd65b90b5b0d9b79949c745df464c",
  "src/adr_kit/semantic_contract/v1_0/normalized-model.json": "6b49bd32ff0fd91198a531654c911da1e9f4e925",
  "src/adr_kit/semantic_contract/v1_0/policy/semantic-contract-policy-1.0.json": "363e8535ddc8f5fdffcc7f375ebb9b13bf40f562",
  "src/adr_kit/semantic_contract/v1_0/resources/normalized-model-2.4-conformance.json": "47ec0af3b6c59774aacc85ed6ef4eddbe2a63b3a",
  "src/adr_kit/semantic_contract/v1_0/resources/normalized-model-2.4-schema-normalized-architecture-model.schema.json": "51ab6b0fc9538696946a7bd617600898fda16e4b",
  "src/adr_kit/semantic_contract/v1_0/resources/normalized-model-2.4-schema-normalized-entity-registry.schema.json": "36cfa43d043f52a6e5f716958f33925580f92cf3",
  "src/adr_kit/semantic_contract/v1_0/resources/normalized-model-2.4-schema-normalized-entity.schema.json": "392c89dc7cfd91dfa2e93ba08448cac9b9d63c9c",
  "src/adr_kit/semantic_contract/v1_0/resources/normalized-model-2.4-schema-relationship-record.schema.json": "1fe37c1195387bcd7e8eeb791f6dca0df3295588",
  "src/adr_kit/semantic_contract/v1_0/resources/normalized-model-2.4-schema-relationship-registry.schema.json": "8d0c87b1d460e1c3d15f72693eca74278331718f",
  "src/adr_kit/semantic_contract/v1_0/resources/normalized-model-2.4-schema-unresolved-registry.schema.json": "3a799c04c6c3244034422d380711e862f1bc0146",
  "src/adr_kit/semantic_contract/v1_0/sets/scs-v1-sha256-2cf903fe80c50b97443645369b28443c7fa186ed758e2e22d7ce758ccb0d6020.json": "a038827f86a122d71bb8ae148f69bf7e1acc8598",
  "src/adr_kit/semantic_contract/v1_0/sets/scs-v1-sha256-d12ce535f0a90c23741dfa516d207091197c2772dbcd538fabb133bdf5b79af6.json": "361a336464c8ce0dc1bf936145066dd4b8d6be8f"
}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def schemas() -> dict[str, dict[str, Any]]:
    return {name: read_json(SCHEMA_ROOT / name) for name in NAMES}


def refuse_network(uri: str) -> Resource[Any]:
    raise AssertionError(f"External schema reference forbidden: {uri}")


def validator(name: str) -> Draft7Validator:
    documents = schemas()
    registry = Registry(retrieve=refuse_network).with_resources(
        (document["$id"], Resource.from_contents(document))
        for document in documents.values()
    )
    return Draft7Validator(documents[name], registry=registry)


def regular_entity() -> dict[str, Any]:
    return {
        "id": UUID,
        "alias_id": "SYS-0001",
        "alias_name": "platform-system",
        "alias_ref": "SYS-0001:platform-system",
        "entity_type": "system",
        "name": "Platform",
        "summary": "Platform system.",
        "uri": f"adr://kit/entities/{UUID}",
        "created_at": "2026-10-22T00:00:00Z",
        "entity_fingerprint": "sha256:" + "0" * 64,
        "lifecycle_stage": "proposed",
        "canonical_source": {},
        "completeness": {},
        "provenance": {},
    }


def normative_proposition() -> dict[str, Any]:
    proposition = regular_entity()
    proposition.pop("lifecycle_stage")
    proposition.update(
        alias_id="NP-0001",
        entity_type="normative_proposition",
        statement="Normative propositions MUST remain lifecycle-free.",
        normative_force="MUST",
        scope="unknown",
        declaring_adr={
            "provider": "adr-kit",
            "id": UUID,
            "alias_id": "ADR-L-0001",
            "alias_name": "normative-authority",
        },
        source_artifact={
            "source_type": "logical_adr",
            "source_ref": "adr#np",
            "artifact_path": "adrs/logical/ADR-L-0001.yaml",
            "content_digest": "sha256:" + "1" * 64,
        },
        source_contract={
            "family": "authoring",
            "version": "1.7",
            "fingerprint": "sha256:" + "2" * 64,
        },
    )
    return proposition


def relationship() -> dict[str, Any]:
    return {
        "record_kind": "canonical",
        "id": "019109a0-b1c2-7def-8a00-223344556677",
        "alias_id": "REL-0001",
        "alias_name": "platform-calls-platform",
        "relationship_type": "calls",
        "from_entity_id": UUID,
        "to_entity_id": "019109a0-b1c2-7def-8a00-223344556677",
        "canonical_source_ref": "test#relationship",
    }


def normalized_root(version: str = "2.5") -> dict[str, Any]:
    return {
        "schema_version": version,
        "type": "normalized_architecture_model",
        "mode": "normalized",
        "scope_root": "test",
        "fingerprint": "sha256:" + "1" * 64,
        "entities": [regular_entity()],
        "relationships": [relationship()],
        "unresolved": [{"code": "missing", "message": "Missing."}],
    }


def contract_and_resources() -> tuple[SemanticContractVersion, list[dict[str, Any]]]:
    contract = get_semantic_contract("normalized-model", "2.5")
    resources_list = [
        {
            "canonicalResourceKey": entry.canonical_resource_key,
            "content": load_semantic_resource(entry.canonical_resource_key),
        }
        for entry in contract.resource_manifest
    ]
    return contract, resources_list


def test_nm25_schemas_are_draft07_and_all_refs_resolve_without_network() -> None:
    for name, schema in schemas().items():
        Draft7Validator.check_schema(schema)
        assert schema["$id"].endswith("/v2.5/" + name)
        assert schema["$schema"] == "http://json-schema.org/draft-07/schema#"
        assert "v2.4" not in json.dumps(schema)
        assert validator(name).is_valid(
            normalized_root() if name == NAMES[0]
            else {"schema_version": "2.5", "type": "normalized_entity_registry", "entities": []}
            if name == NAMES[1] else regular_entity()
            if name == NAMES[2] else relationship()
            if name == NAMES[3]
            else {"schema_version": "2.5", "type": "relationship_registry", "relationships": []}
            if name == NAMES[4]
            else {"schema_version": "2.5", "type": "unresolved_registry", "unresolved": []}
        )


def test_nm25_changes_exactly_version_identification_and_lifecycle_accepted() -> None:
    for name in NAMES:
        predecessor = (OLD_ROOT / name).read_text(encoding="utf-8")
        expected = predecessor.replace("v2.4", "v2.5").replace('"2.4"', '"2.5"')
        if name == "normalized-entity.schema.json":
            expected = expected.replace(
                '"proposed", "active", "deprecated", "superseded"',
                '"proposed", "accepted", "active", "deprecated", "superseded"',
            )
        assert (SCHEMA_ROOT / name).read_text(encoding="utf-8") == expected


@pytest.mark.parametrize(
    "stage", ("proposed", "accepted", "active", "deprecated", "superseded")
)
def test_nm25_all_regular_lifecycle_values(stage: str) -> None:
    entity = regular_entity()
    entity["lifecycle_stage"] = stage
    assert validator(NAMES[2]).is_valid(entity)
    root = normalized_root()
    root["entities"] = [entity]
    assert validator(NAMES[0]).is_valid(root)


@pytest.mark.parametrize("stage", ("unknown", "constructed", "", None, 22))
def test_nm25_rejects_non_domain_lifecycle_values(stage: Any) -> None:
    entity = regular_entity()
    entity["lifecycle_stage"] = stage
    assert not validator(NAMES[2]).is_valid(entity)


@pytest.mark.parametrize(
    "field",
    (
        "lifecycle_stage",
        "applicability",
        "materiality",
        "authority_competence",
        "effectivity",
        "implementation_attribution",
    ),
)
def test_nm25_normative_propositions_remain_lifecycle_free(field: str) -> None:
    proposition = normative_proposition()
    assert validator(NAMES[2]).is_valid(proposition)
    proposition[field] = "accepted"
    assert not validator(NAMES[2]).is_valid(proposition)


def test_nm25_rejects_other_version_selectors_and_accepts_open_metadata() -> None:
    assert not validator(NAMES[0]).is_valid(normalized_root("2.4"))
    for name, kind, field in (
        (NAMES[1], "normalized_entity_registry", "entities"),
        (NAMES[4], "relationship_registry", "relationships"),
        (NAMES[5], "unresolved_registry", "unresolved"),
    ):
        record = {"schema_version": "2.5", "type": kind, field: []}
        assert validator(name).is_valid(record)
        record["schema_version"] = "2.4"
        assert not validator(name).is_valid(record)
    entity = regular_entity()
    entity["metadata"] = {
        "ai_lifecycle_provenance": {"uninterpreted": True, "raw": ["accepted", 12]},
        "independent_unknown_key": [1, {"nested": "permitted"}],
    }
    assert validator(NAMES[2]).is_valid(entity)


def test_nm25_uuidv7_and_relationship_constraints_are_retained() -> None:
    assert validator(NAMES[3]).is_valid(relationship())
    record = relationship()
    record["from_entity_id"] = "not-a-uuid"
    assert not validator(NAMES[3]).is_valid(record)
    entity = regular_entity()
    entity["id"] = "ffffffff-ffff-4fff-bfff-ffffffffffff"
    assert not validator(NAMES[2]).is_valid(entity)
    assert validator(NAMES[4]).is_valid(
        {
            "schema_version": "2.5",
            "type": "relationship_registry",
            "relationships": [relationship()],
        }
    )


def test_nm25_conformance_distinguishes_normative_from_executable_cases() -> None:
    document = read_json(CONTRACT_ROOT / "resources" / "normalized-model-2.5-conformance.json")
    cases = document["cases"]
    assert len(cases) == 16
    assert [case["id"] for case in cases] == [
        f"NM25-{number:03d}" for number in range(1, 17)
    ]
    assert all(
        case["classification"] == "inherited-normative-proposition"
        for case in cases[:4]
    )
    assert all(
        case["classification"] == "executable-schema-assertion"
        for case in cases[4:]
    )
    assert document["schemaVersion"] == "2.5"
    assert document["schemas"] == NAMES


def test_nm25_exact_definition_and_complete_closure_are_valid() -> None:
    contract, bundle = contract_and_resources()
    assert contract.semantic_contract_fingerprint == EXPECTED_SCF
    calculated = calculate_semantic_contract_fingerprint(contract)
    assert calculated.success
    assert calculated.semantic_contract_fingerprint == EXPECTED_SCF
    assert verify_semantic_contract(contract).success
    keys = [entry.canonical_resource_key for entry in contract.resource_manifest]
    assert keys == sorted(keys)
    assert len(keys) == len(set(keys)) == 7
    assert contract.frozen_normative_conformance_resources == (
        "normalized-model/2.5/conformance",
    )
    result = validate_semantic_resource_closure(contract, bundle)
    assert result.success and result.closure_valid
    for entry, resource in zip(contract.resource_manifest, bundle):
        assert entry.canonical_resource_key == resource["canonicalResourceKey"]
        assert entry.content_digest == (
            "sha256:" + hashlib.sha256(rfc8785.dumps(resource["content"])).hexdigest()
        )


def test_nm25_bad_digests_dependencies_missing_extra_duplicate_rejected() -> None:
    contract, bundle = contract_and_resources()
    assert not validate_semantic_resource_closure(contract, bundle[1:]).success
    altered = copy.deepcopy(bundle)
    altered[0]["content"]["schemaVersion"] = "9.9"
    assert not validate_semantic_resource_closure(contract, altered).success
    assert not validate_semantic_resource_closure(contract, [*bundle, bundle[0]]).success
    extra = {"canonicalResourceKey": "normalized-model/2.5/extra", "content": {}}
    assert not validate_semantic_resource_closure(contract, [*bundle, extra]).success
    invalid = contract.to_wire()
    invalid["semanticContractFingerprint"] = "scf:v1:sha256:" + "0" * 64
    assert not verify_semantic_contract(invalid).success
    invalid = contract.to_wire()
    declared = next(item for item in invalid["resourceManifest"] if item["dependencies"])
    declared["dependencies"].pop()
    recalc = calculate_semantic_contract_fingerprint(invalid)
    assert recalc.success
    invalid["semanticContractFingerprint"] = recalc.semantic_contract_fingerprint
    assert not validate_semantic_resource_closure(
        SemanticContractVersion.from_wire(invalid), bundle
    ).success


def test_nm25_exact_discovery_does_not_change_historical_selection() -> None:
    assert get_semantic_contract("normalized-model", "2.4").semantic_contract_version == "2.4"
    assert next(
        version for version in list_semantic_contracts()
        if version.semantic_contract_family == "normalized-model"
    ).semantic_contract_version == "2.3"
    with pytest.raises(LookupError):
        get_semantic_contract("normalized-model", "2.6")
    for name in (
        "normalized-model/2.6/conformance",
        "normalized-model/2.5/schema/not-published",
    ):
        with pytest.raises(LookupError):
            load_semantic_resource(name)


def test_nm25_python_package_and_semantic_resource_mirrors_are_byte_exact() -> None:
    for name in NAMES:
        canonical = (SCHEMA_ROOT / name).read_bytes()
        assert canonical == resources.files("adr_kit.schema.v2_5").joinpath(name).read_bytes()
        filename = "normalized-model-2.5-schema-" + name
        assert canonical == (CONTRACT_ROOT / "resources" / filename).read_bytes()
        assert canonical == (BUNDLED / "resources" / filename).read_bytes()
    conformance = "normalized-model-2.5-conformance.json"
    assert (CONTRACT_ROOT / "resources" / conformance).read_bytes() == (
        BUNDLED / "resources" / conformance
    ).read_bytes()
    authority = (CONTRACT_ROOT / "definitions" / conformance.replace(
        "-conformance", ""
    )).read_bytes()
    assert authority == (BUNDLED / "definitions" / "normalized-model-2.5.json").read_bytes()
    assert authority == (BUNDLED / "normalized-model-2.5.json").read_bytes()
    assert '"adr_kit.schema.v2_5" = ["*.json"]' in (
        ROOT / "pyproject.toml"
    ).read_text(encoding="utf-8")


def test_nm25_successor_only_generation_is_byte_deterministic() -> None:
    targets = [
        CONTRACT_ROOT / "definitions" / "normalized-model-2.5.json",
        BUNDLED / "definitions" / "normalized-model-2.5.json",
        BUNDLED / "normalized-model-2.5.json",
        CONTRACT_ROOT / "resources" / "normalized-model-2.5-conformance.json",
        BUNDLED / "resources" / "normalized-model-2.5-conformance.json",
        *[
            CONTRACT_ROOT / "resources" / ("normalized-model-2.5-schema-" + name)
            for name in NAMES
        ],
        *[
            BUNDLED / "resources" / ("normalized-model-2.5-schema-" + name)
            for name in NAMES
        ],
    ]
    original = {path: path.read_bytes() for path in targets}
    for _ in range(2):
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "generate_semantic_contract_assets.py"),
                "--publish-nm25-only",
            ],
            check=True,
            cwd=ROOT,
        )
        assert {path: path.read_bytes() for path in targets} == original
        assert read_json(targets[0])["semanticContractFingerprint"] == EXPECTED_SCF


def test_nm25_historical_authorities_and_capabilities_are_unmodified() -> None:
    for relative, expected_sha in BASELINE_GIT_BLOBS.items():
        content = (ROOT / relative).read_bytes()
        actual_sha = hashlib.sha1(
            b"blob " + str(len(content)).encode("ascii") + b"\0" + content
        ).hexdigest()
        assert actual_sha == expected_sha, relative
