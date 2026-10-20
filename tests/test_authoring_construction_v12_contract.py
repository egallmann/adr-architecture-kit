"""Publication guards for ACC 1.2 authority; these do not execute composition."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import rfc8785
import yaml
from jsonschema import Draft7Validator, Draft202012Validator, RefResolver

from adr_kit.core import semantic_core_capabilities
from adr_kit.semantic_contract import (
    calculate_semantic_contract_fingerprint,
    get_semantic_contract,
    list_semantic_contracts,
    load_semantic_resource,
    validate_semantic_resource_closure,
    verify_semantic_contract,
)

ROOT = Path(__file__).resolve().parents[1]
ACC = ROOT / "contracts/authoring-construction/v1.2"
CANONICAL = ROOT / "contracts/semantic-contract/v1.0"
BUNDLED = ROOT / "src/adr_kit/semantic_contract/v1_0"
KEY = "authoring-construction/1.2/composition-bindings"
SCF = "scf:v1:sha256:8da499420e996c446cbc416dc7db9b4bbb2692ea5039f14461f668aaa48b9e0c"


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(rfc8785.dumps(value)).hexdigest()


def _resources() -> list[dict[str, Any]]:
    return [
        {
            "canonicalResourceKey": item["canonicalResourceKey"],
            "content": load_semantic_resource(item["canonicalResourceKey"]),
        }
        for item in _read(ACC / "contract.json")["resourceManifest"]
    ]


def _validator(schema: dict[str, Any]) -> Draft202012Validator:
    store: dict[str, Any] = {}
    for item in _resources():
        value = item["content"]
        if isinstance(value, dict) and "$id" in value:
            store[value["$id"]] = value
            store[
                "https://adr-kit.dev/semantic-contract/resources/"
                + item["canonicalResourceKey"]
                + ".json"
            ] = value
    return Draft202012Validator(schema, resolver=RefResolver(schema["$id"], schema, store=store))


def _assert_binding_authorities(table: dict[str, Any]) -> None:
    """One-way publication guard over qualified canonical JSON, never a resolver."""
    assert len(table["rows"]) == 1
    row = table["rows"][0]
    ai = load_semantic_resource(row["ai_authority"]["canonical_resource_key"])
    assert row["ai_authority"]["content_digest"] == _digest(ai)
    field = next(
        field
        for semantic_type in ai["semantic_types"]
        for field in semantic_type["field_dispositions"]
        if field["semantic_field_key"] == row["semantic_field_key"]
    )
    assert row["required_ai_disposition"] == {
        key: field[key] for key in row["required_ai_disposition"]
    }
    assert set(row["required_ai_disposition"]) == {
        "disposition",
        "destination_ref",
        "ordering",
        "matching_identity_ref",
        "multiplicity",
        "value_semantics",
    }
    adc = load_semantic_resource(row["adc_authority"]["canonical_resource_key"])
    assert row["adc_authority"]["content_digest"] == _digest(adc)
    assert row["adc_policies_consulted"] == ["composition_policy", "identity_policy"]
    for role in ("parent", "child"):
        kind, name = row[f"{role}_semantic_type"].split("/")
        definition = next(
            item for item in adc["types"] if item["key"] == {"kind": kind, "name": name}
        )
        assert row["required_adc_policy"][role] == {
            policy: definition[policy] for policy in row["adc_policies_consulted"]
        }
        schema = load_semantic_resource(row[f"{role}_schema"]["canonical_resource_key"])
        assert row[f"{role}_schema"]["content_digest"] == _digest(schema)
    assert row["child_field_authority"] == "child_schema"
    assert row["child_schema"]["schema_pointer"] == "/definitions/decision"
    assert (
        row["parent_schema"]["canonical_resource_key"] == "authoring/1.7/schema/adr-logical.schema"
    )
    parent = load_semantic_resource(row["parent_schema"]["canonical_resource_key"])
    assert (
        parent["properties"][row["parent_property"]]["items"]["$ref"]
        == "adr-common.schema.json#/definitions/decision"
    )


def test_exact_acc12_definition_and_complete_closure_verify_in_rust() -> None:
    contract = _read(ACC / "contract.json")
    assert contract["semanticContractFamily"] == "authoring-construction"
    assert contract["semanticContractVersion"] == "1.2"
    assert contract["fingerprintScheme"] == "scf:v1:sha256"
    assert contract["semanticContractFingerprint"] == SCF
    assert contract["frozenNormativeConformanceResources"] == [
        "authoring-construction/1.2/conformance"
    ]
    assert verify_semantic_contract(contract).success
    assert (
        calculate_semantic_contract_fingerprint(contract).semantic_contract_fingerprint
        == contract["semanticContractFingerprint"]
    )
    exact = get_semantic_contract("authoring-construction", "1.2")
    assert exact.semantic_contract_fingerprint == contract["semanticContractFingerprint"]
    assert exact != get_semantic_contract("authoring-construction", "1.1")
    with pytest.raises(LookupError):
        get_semantic_contract("authoring-construction", "1.3")
    resources = _resources()
    result = validate_semantic_resource_closure(contract, resources)
    assert result.success and result.closure_valid
    manifest = {item["canonicalResourceKey"]: item for item in contract["resourceManifest"]}
    assert manifest[KEY]["role"] == "interpretation-rule"
    assert manifest[KEY + ".schema"]["role"] == "source-contract-schema"
    predecessor = _read(ROOT / "contracts/authoring-construction/v1.1/contract.json")
    for item in predecessor["resourceManifest"]:
        assert manifest[item["canonicalResourceKey"]] == item
    assert "authoring-construction/1.2/ledger.schema" not in manifest
    assert not (ACC / "resources/ledger.schema.json").exists()
    assert contract["semanticContractFingerprint"] not in json.dumps(resources)


def test_closed_binding_table_matches_exact_ai_adc_and_authoring_authorities() -> None:
    table = _read(ACC / "resources/composition-bindings.json")
    schema = _read(ACC / "resources/composition-bindings.schema.json")
    Draft202012Validator.check_schema(schema)
    _validator(schema).validate(table)
    _assert_binding_authorities(table)
    extra = copy.deepcopy(table)
    extra["rows"].append(extra["rows"][0])
    assert list(_validator(schema).iter_errors(extra))
    extra = copy.deepcopy(table)
    extra["rows"][0]["ambient_policy"] = "forbidden"
    assert list(_validator(schema).iter_errors(extra))
    for field in ("required_ai_disposition", "required_adc_policy", "adc_identity"):
        bad = copy.deepcopy(table)
        if field == "required_ai_disposition":
            bad["rows"][0][field]["ordering"] = "unordered"
        elif field == "required_adc_policy":
            bad["rows"][0][field]["child"]["composition_policy"]["mode"] = "root_fragment"
        else:
            bad["rows"][0]["required_adc_policy"]["child"]["identity_policy"][
                "supplied_identity"
            ] = "replace"
        with pytest.raises(AssertionError):
            _assert_binding_authorities(bad)


def test_one_way_publication_guard_matches_accepted_adr_l0035() -> None:
    adr_path = next((ROOT / "adrs/logical").glob("ADR-L-0035-*.yaml"))
    adr = yaml.safe_load(adr_path.read_text(encoding="utf-8"))
    assert adr["status"] == "accepted" and adr["gaps"] == []
    decisions = {item["alias_id"]: item["rationale"] for item in adr["decisions"]}
    assert set(decisions) == {f"DEC-{number:04}" for number in range(274, 280)}
    row = _read(ACC / "resources/composition-bindings.json")["rows"][0]
    for key in (
        "parent_semantic_type",
        "child_semantic_type",
        "relation",
        "parent_property",
        "semantic_field_key",
    ):
        assert (
            f"{key.replace('_', ' ')}: {row[key]}" in decisions["DEC-0274"]
            or (
                key == "parent_property"
                and f"Authoring 1.7 property: {row[key]}" in decisions["DEC-0274"]
            )
            or (
                key == "semantic_field_key"
                and f"AI 1.2 semantic_field_key: {row[key]}" in decisions["DEC-0274"]
            )
        )
    assert row["binding_id"] == "adr-logical.decisions.contains.entity-decision"
    assert row["binding_id"] in decisions["DEC-0279"]
    assert row["endpoint_resolution"] == "same_request_create_fragment_request_key"
    assert row["operations"] == {"parent": "create", "child": "create"}
    assert row["input_modes"] == ["prepared"]
    assert row["byte_owner"] == "compiler"
    assert row["prepared_parent_property"] == "absent"
    assert row["child_object"] == "prepared_fields_plus_established_id"
    assert row["ordering"]["sort"] == "ascending_integer"
    assert row["ordering"]["semantic_value"] == "ordered_child_canonical_uuids"
    assert row["ordering"]["request_array_order_semantic"] is False
    assert "input_contract" not in row["adc_policies_consulted"]


@pytest.mark.parametrize(
    "fault",
    ["missing_table", "missing_schema", "modified_table", "wrong_digest", "wrong_scf"],
)
def test_exact_closure_rejects_missing_modified_or_misqualified_authority(
    fault: str,
) -> None:
    contract = _read(ACC / "contract.json")
    resources = _resources()
    if fault.startswith("missing"):
        key = KEY if fault == "missing_table" else KEY + ".schema"
        resources = [item for item in resources if item["canonicalResourceKey"] != key]
    elif fault == "modified_table":
        next(item["content"] for item in resources if item["canonicalResourceKey"] == KEY)["rows"][
            0
        ]["byte_owner"] = "host"
    elif fault == "wrong_digest":
        next(item for item in contract["resourceManifest"] if item["canonicalResourceKey"] == KEY)[
            "contentDigest"
        ] = ("sha256:" + "0" * 64)
    else:
        contract["semanticContractFingerprint"] = get_semantic_contract(
            "authoring-construction", "1.1"
        ).semantic_contract_fingerprint
        assert not verify_semantic_contract(contract).success
        return
    result = validate_semantic_resource_closure(contract, resources)
    assert not result.success and not result.closure_valid
    assert result.diagnostics


def test_request_and_future_evidence_shapes_preserve_exact_version_and_complete_proofs() -> None:
    from tests.test_authoring_construction_v11_contract import _minimal_acc11_request

    schema = _read(ACC / "schema.json")
    Draft202012Validator.check_schema(schema)
    validator = _validator(schema)
    validator.validate(_read(ACC / "contract.json"))
    request = _minimal_acc11_request()
    assert list(validator.iter_errors(request))
    request["contract_version"] = "1.2"
    request["basis"]["acc"]["version"] = "1.2"
    request["basis"]["acc"]["semantic_contract_fingerprint"] = get_semantic_contract(
        "authoring-construction", "1.2"
    ).semantic_contract_fingerprint
    validator.validate(request)
    request["basis"]["acc"]["version"] = "1.1"
    assert list(validator.iter_errors(request))
    defs = schema["$defs"]
    assert defs["uuid_v7"] == {"$ref": "../1.1/schema.json#/$defs/uuid_v7"}
    assert defs["normalized_result"] == {"$ref": "../1.1/schema.json#/$defs/normalized_result"}
    authority = defs["construction_qualification"]["properties"]["authority"]
    assert {"acc", "composition_binding"} <= set(authority["required"])
    assert authority["properties"]["composition_binding"] == {
        "$ref": "#/$defs/composition_binding_qualification"
    }
    assert defs["construction_qualification"]["properties"]["expected_ledger"] == {
        "$ref": "../1.1/ledger.schema.json"
    }
    record = defs["composition_record"]
    assert set(record["required"]) == {"semantic", "integrity", "qualification"}
    assert {
        "parent_canonical_uuid",
        "child_canonical_uuid",
        "ordering",
        "semantic_field_key",
        "binding_id",
        "resolution_kind",
    } <= set(record["properties"]["semantic"]["required"])
    proof = record["properties"]["integrity"]
    for name in (
        "prepared_property_absent",
        "exact_subtree",
        "child_candidate_artifact_retained",
        "child_source_root_omitted",
    ):
        assert proof["properties"][name] == {"const": True}
        assert name in proof["required"]
    assert "composition_records" in defs["construction_result"]["allOf"][1]["required"]

    binding = _read(ACC / "resources/composition-bindings.json")
    row = binding["rows"][0]
    basis = request["basis"]
    basis["acc"]["version"] = "1.2"
    member = {"canonical_resource_key": KEY, "content_digest": _digest(binding)}
    authority_value = {
        "acc": basis["acc"],
        "composition_binding": member,
        "architecture_interpretation": basis["architecture_interpretation"],
        "authoring_domain": {
            "contract_id": "adr-kit.authoring-domain",
            "version": "1.1",
            "content_digest": row["adc_authority"]["content_digest"],
        },
        "authoring": basis["authoring"],
        "normalized_model": basis["normalized_model"],
        "custom_entity": {
            "family": "custom-entity",
            "version": "1.0",
            "resources": [
                {
                    "canonical_resource_key": "custom-entity/1.0/contract",
                    "content_digest": "sha256:" + "0" * 64,
                }
            ],
        },
    }
    evidence = {
        "semantic": {
            **{
                key: row[key]
                for key in (
                    "binding_id",
                    "parent_semantic_type",
                    "child_semantic_type",
                    "relation",
                    "semantic_field_key",
                )
            },
            "parent_canonical_uuid": "01900000-0000-7000-8000-000000000001",
            "child_canonical_uuid": "01900000-0000-7000-8000-000000000002",
            "authoring_property": "decisions",
            "ordering": 10,
            "resolution_kind": "request",
        },
        "integrity": {
            "parent_request_key": "parent",
            "child_request_key": "child",
            "parent_source_ref": "candidate:parent",
            "child_source_ref": "candidate:child",
            "parent_content_digest": "sha256:" + "0" * 64,
            "child_content_digest": "sha256:" + "1" * 64,
            "composition_binding_resource_key": KEY,
            "composition_binding_content_digest": member["content_digest"],
            "induced_sequence_index": 0,
            "identity_disposition": {"parent": "preserved", "child": "preserved"},
            **{
                key: True
                for key in (
                    "prepared_property_absent",
                    "exact_subtree",
                    "child_candidate_artifact_retained",
                    "child_source_root_omitted",
                )
            },
        },
        "qualification": authority_value,
    }
    record_schema = dict(schema)
    del record_schema["oneOf"]
    record_schema["$ref"] = "#/$defs/composition_record"
    record_validator = _validator(record_schema)
    record_validator.validate(evidence)
    for key in (
        "prepared_property_absent",
        "exact_subtree",
        "child_candidate_artifact_retained",
        "child_source_root_omitted",
    ):
        invalid = copy.deepcopy(evidence)
        invalid["integrity"][key] = False
        assert list(record_validator.iter_errors(invalid))
    invalid = copy.deepcopy(evidence)
    del invalid["qualification"]["composition_binding"]
    assert list(record_validator.iter_errors(invalid))


def test_rules_select_the_exact_manifest_table_without_adr_or_protocol_authority() -> None:
    contract = _read(ACC / "contract.json")
    manifest = {item["canonicalResourceKey"]: item for item in contract["resourceManifest"]}
    rules = _read(ACC / "resources/rules.json")
    binding = rules["composition"]["binding_authority"]
    assert binding == {
        "canonical_resource_key": KEY,
        "content_digest": manifest[KEY]["contentDigest"],
    }
    assert (
        rules["authority"]["architecture_interpretation"]["fingerprint"]
        == get_semantic_contract("architecture-interpretation", "1.2").semantic_contract_fingerprint
    )
    assert not any("semantic-core" in key or key.startswith("adrs/") for key in manifest)
    # This exact check obtains the complete authority from packaged resources;
    # no ADR prose or repository acquisition participates in qualification.
    assert validate_semantic_resource_closure(contract, _resources()).closure_valid


def test_frozen_oracle_is_schema_valid_and_explicitly_authority_only() -> None:
    conformance = _read(ACC / "resources/conformance.json")
    schema = _read(ACC / "resources/conformance.schema.json")
    _validator(schema).validate(conformance)
    cases = conformance["cases"]
    assert [case["case_id"] for case in cases] == [
        f"ACC12-{number:02}" for number in range(1, len(cases) + 1)
    ]
    assert len(cases) == 41
    assert {case["runtime_coverage"] for case in cases} == {"authority_only_not_implemented"}
    codes = {
        assertion["expected"]
        for case in cases
        for assertion in case["assertions"]
        if assertion["path"] == "diagnostics.codes" and isinstance(assertion["expected"], str)
    }
    rules = _read(ACC / "resources/rules.json")
    assert {item["code"] for item in rules["composition"]["diagnostics"]} - {
        "authoring_construction.authority.unavailable"
    } <= codes
    positive = cases[0]
    child = next(
        item["expected"] for item in positive["assertions"] if item["path"] == "embedded_child"
    )
    common = load_semantic_resource("authoring/1.7/schema/adr-common.schema")
    types = load_semantic_resource("authoring/1.7/schema/types.schema")
    Draft7Validator(
        common["definitions"]["decision"],
        resolver=RefResolver(common["$id"], common, store={types["$id"]: types}),
    ).validate(child)
    assert rules["outcomes"]["precedence"] == [
        "Rejected",
        "Unavailable",
        "Unresolved",
        "Constructed",
    ]
    assert rules["outcomes"]["all_independent_diagnostics_retained"] is True


def test_frozen_history_protocol_and_current_selection_are_unchanged() -> None:
    expected = {
        "contracts/authoring-construction/v1.0": "sha256:c4f95b7aa43d8456a9e3a74714e5401f93c0b51fc78a1a589175378bdf2580f9",
        "contracts/authoring-construction/v1.1": "sha256:6a730b790da6673c1523bcdc2477619d312803c12fa0ecc1c4542542df2ab21d",
        "contracts/semantic-core/v1.5": "sha256:eb136a9bbb2c204118acc8bcad020b1bab0e286b3c0598fd244552dfa0a1b800",
    }
    for directory, fingerprint in expected.items():
        root = ROOT / directory
        assert (
            _digest(
                {
                    path.relative_to(root).as_posix(): _read(path)
                    for path in sorted(root.rglob("*.json"))
                }
            )
            == fingerprint
        )
    current = _read(CANONICAL / "current/semantic-contract-current-1.0.json")
    assert (
        current["semanticContractSetId"]
        == "scs:v1:sha256:d12ce535f0a90c23741dfa516d207091197c2772dbcd538fabb133bdf5b79af6"
    )
    assert all(
        item.semantic_contract_family != "authoring-construction"
        for item in list_semantic_contracts()
    )
    handshake = semantic_core_capabilities()
    assert not any(
        "1_2" in operation and "construction" in operation
        for operations in handshake["operations_by_version"].values()
        for operation in operations
    )
    rules = _read(ACC / "resources/rules.json")
    assert rules["publication_posture"] == {
        "status": "published_authority_only",
        "execution_capability_advertised": False,
        "execution_implemented": False,
        "current_semantic_contract_selection": False,
    }
    assert rules["composition"]["protocol_1_5_composition_resolution"] is False


def test_repository_generator_and_package_mirrors_are_byte_deterministic() -> None:
    roots = [CANONICAL, BUNDLED, ACC]
    before = {path: path.read_bytes() for root in roots for path in root.rglob("*.json")}
    for _ in range(2):
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/generate_semantic_contract_assets.py"),
            ],
            cwd=ROOT,
            check=True,
        )
        assert before == {
            path: path.read_bytes() for root in roots for path in root.rglob("*.json")
        }
    for path in (CANONICAL / "resources").glob("authoring-construction-1.2-*.json"):
        assert path.read_bytes() == (BUNDLED / "resources" / path.name).read_bytes()
    assert (ACC / "contract.json").read_bytes() == (
        CANONICAL / "definitions/authoring-construction-1.2.json"
    ).read_bytes()
    assert (ACC / "contract.json").read_bytes() == (
        BUNDLED / "definitions/authoring-construction-1.2.json"
    ).read_bytes()
    assert (ACC / "contract.json").read_bytes() == (
        BUNDLED / "authoring-construction-1.2.json"
    ).read_bytes()
