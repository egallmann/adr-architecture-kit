"""Executable contract-level conformance for Authoring Construction Contract 1.0."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import rfc8785
from jsonschema import Draft202012Validator

from adr_kit.semantic_contract import (
    calculate_semantic_contract_fingerprint,
    validate_semantic_resource_closure,
    verify_semantic_contract,
)

ROOT = Path(__file__).resolve().parents[1]
ACC = ROOT / "contracts" / "authoring-construction" / "v1.0"
DIAGNOSTIC_NAMESPACE = "authoring_construction."
RESOURCE_FAMILIES = {
    "adc": "authoring-domain",
    "authoring": "authoring",
    "normalized_model": "normalized-model",
}
SELF_BINDING_MARKER = "$enclosing_scf"
SELF_BINDING_SOURCE = "verified_enclosing_semantic_contract_fingerprint"
SELF_BINDING_PATTERNS = (
    "/cases/*/input/basis/acc/semantic_contract_fingerprint",
    "/cases/*/expected/result/basis_qualification/acc/semantic_contract_fingerprint",
)


def _document(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _errors(validator: Draft202012Validator, instance: Any, definition: str) -> list[Any]:
    return list(validator.descend(instance, {"$ref": f"#/$defs/{definition}"}))


def _request_keys(request: dict[str, Any]) -> set[str]:
    keys = {fragment["request_key"] for fragment in request["fragments"]}
    keys.update(relationship["relationship_key"] for relationship in request["relationships"])
    for composition in request["compositions"]:
        for key in ("parent", "child"):
            if key in composition:
                keys.add(composition[key])
    return keys


def _assert_resource_set(qualification: dict[str, Any], family: str) -> None:
    assert qualification["family"] == family
    assert "semantic_contract_fingerprint" not in qualification
    assert qualification["resources"]
    assert all(
        set(resource) == {"canonical_resource_key", "content_digest"}
        for resource in qualification["resources"]
    )
    assert all(
        resource["content_digest"].startswith("sha256:") for resource in qualification["resources"]
    )


def _assert_basis(basis: dict[str, Any]) -> None:
    for key in ("acc", "architecture_interpretation"):
        assert "semantic_contract_fingerprint" in basis[key]
        assert "resources" not in basis[key]
    for key, family in RESOURCE_FAMILIES.items():
        _assert_resource_set(basis[key], family)

    custom = basis["custom_entity"]
    if custom is not None:
        _assert_resource_set(custom["contract_resources"], "custom-entity")
        assert custom["registry_source"]["content_digest"].startswith("sha256:")
        assert custom["registry_source"]["source_bytes"]
        assert custom["selected_definitions"]
        for definition in custom["selected_definitions"]:
            assert definition["semantic_type"].startswith(f"{definition['consumer_namespace']}:")
            assert definition["contract_fingerprint"].startswith("cecf:v1:sha256:")
            assert definition["definition_digest"].startswith("sha256:")

    for entry in basis["reference_basis"]["entries"]:
        assert entry["canonical_uuid"]
        assert entry["semantic_type"]
        assert "qualification" in entry
        if "source_basis" in entry and "content_digest" in entry["source_basis"]:
            assert set(entry["source_basis"]) == {
                "source_ref",
                "content_digest",
                "source_bytes",
            }
            assert entry["source_basis"]["source_bytes"]
            assert entry["source_basis"]["content_digest"].startswith("sha256:")
    for entry in basis["existing_source_basis"]["entries"]:
        assert entry["source_bytes"]
        assert entry["content_digest"].startswith("sha256:")


def _walk_scalars(value: Any, path: str = "") -> list[tuple[str, Any]]:
    if isinstance(value, dict):
        return [
            item for key, child in value.items() for item in _walk_scalars(child, f"{path}/{key}")
        ]
    if isinstance(value, list):
        return [
            item
            for index, child in enumerate(value)
            for item in _walk_scalars(child, f"{path}/{index}")
        ]
    return [(path or "/", value)]


def _marker_paths(document: dict[str, Any]) -> set[str]:
    return {
        path
        for path, value in _walk_scalars(document)
        if value == SELF_BINDING_MARKER and path != "/self_binding/marker"
    }


def _assert_self_binding_shape(corpus: dict[str, Any]) -> set[str]:
    assert set(corpus["self_binding"]) == {
        "marker",
        "source",
        "allowed_json_pointer_patterns",
    }
    assert corpus["self_binding"] == {
        "marker": SELF_BINDING_MARKER,
        "source": SELF_BINDING_SOURCE,
        "allowed_json_pointer_patterns": list(SELF_BINDING_PATTERNS),
    }
    expected_paths = {
        f"/cases/{index}/input/basis/acc/semantic_contract_fingerprint"
        for index in range(len(corpus["cases"]))
    }
    expected_paths.update(
        f"/cases/{index}/expected/result/basis_qualification/acc/semantic_contract_fingerprint"
        for index in range(len(corpus["cases"]))
    )
    assert _marker_paths(corpus) == expected_paths
    assert all(
        not (isinstance(value, str) and value.startswith("$") and value != SELF_BINDING_MARKER)
        for _, value in _walk_scalars(corpus)
    )
    return expected_paths


def _verified_bound_conformance(
    schema: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], str]:
    contract = _document(ACC / "contract.json")
    assert verify_semantic_contract(contract).success is True
    calculated = calculate_semantic_contract_fingerprint(contract)
    assert calculated.success is True
    assert calculated.semantic_contract_fingerprint == contract["semanticContractFingerprint"]

    resources = [
        {
            "canonicalResourceKey": entry["canonicalResourceKey"],
            "content": _document(
                ACC / "resources" / f"{entry['canonicalResourceKey'].split('/')[-1]}.json"
            ),
        }
        for entry in contract["resourceManifest"]
    ]
    closure = validate_semantic_resource_closure(contract, resources)
    assert closure.success is True
    assert closure.closure_valid is True

    corpus = _document(ACC / "resources" / "conformance.json")
    conformance_entry = next(
        entry
        for entry in contract["resourceManifest"]
        if entry["canonicalResourceKey"] == "authoring-construction/1.0/conformance"
    )
    digest = "sha256:" + hashlib.sha256(rfc8785.dumps(corpus)).hexdigest()
    assert conformance_entry["contentDigest"] == digest

    _assert_self_binding_shape(corpus)

    validator = Draft202012Validator(schema)
    unbound_request_errors = _errors(validator, corpus["cases"][0]["input"], "authoring_request")
    unbound_result_errors = _errors(
        validator,
        corpus["cases"][0]["expected"]["result"],
        "construction_result",
    )
    assert unbound_request_errors
    assert unbound_result_errors
    assert any(
        "semantic_contract_fingerprint" in error.absolute_path
        for error in unbound_request_errors + unbound_result_errors
    )

    bound = deepcopy(corpus)
    bound.pop("self_binding")
    verified_scf = contract["semanticContractFingerprint"]
    for case in bound["cases"]:
        case["input"]["basis"]["acc"]["semantic_contract_fingerprint"] = verified_scf
        case["expected"]["result"]["basis_qualification"]["acc"][
            "semantic_contract_fingerprint"
        ] = verified_scf

    assert _marker_paths(bound) == set()
    assert all(
        not (isinstance(value, str) and value.startswith("$")) for _, value in _walk_scalars(bound)
    )
    for index in range(len(corpus["cases"])):
        assert (
            corpus["cases"][index]["input"]["basis"]["acc"]["semantic_contract_fingerprint"]
            == SELF_BINDING_MARKER
        )
        assert (
            bound["cases"][index]["input"]["basis"]["acc"]["semantic_contract_fingerprint"]
            == verified_scf
        )
        assert (
            corpus["cases"][index]["expected"]["result"]["basis_qualification"]["acc"][
                "semantic_contract_fingerprint"
            ]
            == SELF_BINDING_MARKER
        )
        assert (
            bound["cases"][index]["expected"]["result"]["basis_qualification"]["acc"][
                "semantic_contract_fingerprint"
            ]
            == verified_scf
        )
    return corpus, bound, verified_scf


def test_acc_self_binding_rejects_unknown_and_undeclared_markers() -> None:
    corpus = _document(ACC / "resources" / "conformance.json")
    invalid_marker = deepcopy(corpus)
    invalid_marker["cases"][0]["input"]["basis"]["acc"][
        "semantic_contract_fingerprint"
    ] = "$ambient_scf"
    try:
        _assert_self_binding_shape(invalid_marker)
    except AssertionError:
        pass
    else:
        raise AssertionError("unknown self-binding marker was accepted")

    undeclared_marker = deepcopy(corpus)
    undeclared_marker["cases"][0]["input"]["request"]["request_id"] = SELF_BINDING_MARKER
    try:
        _assert_self_binding_shape(undeclared_marker)
    except AssertionError:
        pass
    else:
        raise AssertionError("undeclared self-binding location was accepted")


def test_acc_contract_schema_and_document_are_strictly_valid() -> None:
    schema = _document(ACC / "schema.json")
    contract = _document(ACC / "contract.json")
    Draft202012Validator.check_schema(schema)
    assert not list(Draft202012Validator(schema).iter_errors(contract))
    assert set(contract) == {
        "semanticContractFamily",
        "semanticContractVersion",
        "fingerprintScheme",
        "resourceManifest",
        "frozenNormativeConformanceResources",
        "semanticContractFingerprint",
    }


def test_acc_scf_and_resource_closure_are_verified_by_shared_authority() -> None:
    contract = _document(ACC / "contract.json")
    assert verify_semantic_contract(contract).success is True
    calculated = calculate_semantic_contract_fingerprint(contract)
    assert calculated.success is True
    assert calculated.semantic_contract_fingerprint == contract["semanticContractFingerprint"]

    resources = [
        {
            "canonicalResourceKey": entry["canonicalResourceKey"],
            "content": _document(
                ACC / "resources" / f"{entry['canonicalResourceKey'].split('/')[-1]}.json"
            ),
        }
        for entry in contract["resourceManifest"]
    ]
    closure = validate_semantic_resource_closure(contract, resources)
    assert closure.success is True
    assert closure.closure_valid is True

    for entry, supplied in zip(contract["resourceManifest"], resources, strict=True):
        digest = "sha256:" + hashlib.sha256(rfc8785.dumps(supplied["content"])).hexdigest()
        assert entry["contentDigest"] == digest


def test_acc_corpus_executes_operation_specific_schemas_and_exact_basis() -> None:
    schema = _document(ACC / "schema.json")
    corpus, bound_corpus, _ = _verified_bound_conformance(schema)
    cases = bound_corpus["cases"]
    validator = Draft202012Validator(schema)

    assert [case["id"] for case in cases] == [f"C{index:02d}" for index in range(1, 43)]
    assert len({case["id"] for case in cases}) == 42
    assert corpus["case_schema"]["input_schema"] == "#/$defs/authoring_request"
    assert corpus["case_schema"]["expected_result_schemas"] == {
        "construct_authoring_set": "#/$defs/construction_result",
        "validate_authoring": "#/$defs/validation_result",
    }
    fragment_reference_cases = {
        case["id"]
        for case in cases
        if any(fragment["references"] for fragment in case["input"]["request"]["fragments"])
    }
    assert {"C04", "C06", "C41", "C42"} <= fragment_reference_cases
    assert {
        reference["reference_kind"]
        for case in cases
        for fragment in case["input"]["request"]["fragments"]
        for reference in fragment["references"]
    } == {"request", "existing"}
    cases_by_id = {case["id"]: case for case in cases}
    c34 = cases_by_id["C34"]
    c34_fragment = c34["input"]["request"]["fragments"][0]
    assert c34_fragment["operation"] == "update"
    assert c34_fragment["references"] == []
    assert c34["input"]["basis"]["existing_source_basis"]["entries"] == []
    assert c34["expected"]["result"]["outcome"] == "Unavailable"
    assert c34["expected"]["result"]["diagnostics"][0]["code"] == (
        "authoring_construction.basis.existing_source_unavailable"
    )
    assert c34["expected"]["result"]["diagnostics"][0]["location"] == ("/request/fragments/0")

    c41 = cases_by_id["C41"]
    c41_fragment = c41["input"]["request"]["fragments"][0]
    c41_reference = c41_fragment["references"][0]
    c41_entries = c41["input"]["basis"]["reference_basis"]["entries"]
    assert c41_fragment["operation"] == "create"
    assert c41["input"]["operation"] == "construct_authoring_set"
    assert c41["input"]["basis"]["custom_entity"] is None
    assert c41_entries
    assert c41_reference["target"] not in {entry["reference_id"] for entry in c41_entries}
    assert c41_entries[0]["source_basis"]["source_bytes"]
    assert c41_entries[0]["qualification"] == c41_reference["qualification"]
    assert cases_by_id["C41"]["expected"]["result"]["outcome"] == "Unresolved"
    assert cases_by_id["C41"]["expected"]["result"]["diagnostics"][0]["location"] == (
        "/request/fragments/0/references/0"
    )

    c42 = cases_by_id["C42"]
    c42_fragment = c42["input"]["request"]["fragments"][0]
    c42_reference = c42_fragment["references"][0]
    c42_entries = c42["input"]["basis"]["reference_basis"]["entries"]
    c42_diagnostic = c42["expected"]["result"]["diagnostics"][0]
    assert c42_fragment["operation"] == "create"
    assert c42["input"]["basis"]["custom_entity"] is None
    assert c42_entries
    assert c42_reference["target"] in {entry["reference_id"] for entry in c42_entries}
    c42_entry = next(
        entry for entry in c42_entries if entry["reference_id"] == c42_reference["target"]
    )
    assert c42_entry["source_basis"]["source_bytes"]
    assert c42_entry["qualification"] == c42_reference["qualification"]
    assert c42["expected"]["result"]["outcome"] == "Unavailable"
    assert c42_diagnostic["code"] == "authoring_construction.custom.authority_unavailable"
    assert c42_diagnostic["location"] == "/request/fragments/0/references/0"
    assert c42_diagnostic["code"] != "authoring_construction.basis.existing_source_unavailable"

    for case in cases:
        request = case["input"]
        result = case["expected"]["result"]
        assert request["operation"] == case["operation"]
        assert result["operation"] == case["operation"]
        assert not _errors(validator, request, "authoring_request")
        result_definition = (
            "validation_result"
            if case["operation"] == "validate_authoring"
            else "construction_result"
        )
        assert not _errors(validator, result, result_definition)
        fragment_keys = [fragment["request_key"] for fragment in request["request"]["fragments"]]
        assert len(set(fragment_keys)) == len(fragment_keys)
        assert not _errors(validator, request["basis"], "basis_qualification")
        _assert_basis(request["basis"])

        request_keys = _request_keys(request["request"])
        reference_ids = {
            entry["reference_id"] for entry in request["basis"]["reference_basis"]["entries"]
        }
        for fragment in request["request"]["fragments"]:
            for reference in fragment["references"]:
                assert reference["reference_key"]
                if reference["reference_kind"] == "request":
                    assert reference["target"] in request_keys
                else:
                    if reference["target"] not in reference_ids:
                        assert case["id"] == "C41"
                        assert result.get("outcome") == "Unresolved"
        for relationship in request["request"]["relationships"]:
            for endpoint in (relationship["source"], relationship["target"]):
                if endpoint["kind"] == "request":
                    if endpoint["target"] not in request_keys:
                        assert case["id"] in {"C16", "C17", "C25"}

        diagnostics = result["diagnostics"]
        assert all(
            diagnostic["code"].startswith(DIAGNOSTIC_NAMESPACE) for diagnostic in diagnostics
        )
        assert not any(_errors(validator, diagnostic, "diagnostic") for diagnostic in diagnostics)
        codes = [diagnostic["code"] for diagnostic in diagnostics]
        for index, diagnostic in enumerate(diagnostics):
            blocked_by = diagnostic.get("blocked_by", [])
            assert all(code in codes[:index] for code in blocked_by)
        if case["operation"] == "construct_authoring_set":
            assert result["outcome"] in {
                "Constructed",
                "Rejected",
                "Unavailable",
                "Unresolved",
            }
            assert result["round_trip"]["diagnostic_codes"] == codes
            map_keys = {entry["request_key"] for entry in result["construction_map"]}
            assert map_keys <= request_keys
            for entry in result["construction_map"]:
                fragment = next(
                    (
                        item
                        for item in request["request"]["fragments"]
                        if item["request_key"] == entry["request_key"]
                    ),
                    None,
                )
                if (
                    fragment is not None
                    and "id" in fragment["fields"]
                    and entry["identity_disposition"] == "preserved"
                ):
                    assert entry["canonical_uuid"] == fragment["fields"]["id"]
            if result["outcome"] == "Constructed":
                assert result["candidate_source_basis"] is not None
                assert result["normalized_result"] is not None
                assert result["round_trip"]["qualified"] is True
                assert result["round_trip"]["comparison"] == "semantic_equivalent"
                for fragment in request["request"]["fragments"]:
                    if not fragment["references"]:
                        continue
                    candidate_fragment = next(
                        item
                        for item in result["candidate_fragments"]
                        if item["request_key"] == fragment["request_key"]
                    )
                    resolutions = candidate_fragment["resolved_references"]
                    assert {item["reference_key"] for item in resolutions} == {
                        item["reference_key"] for item in fragment["references"]
                    }
                    for reference in fragment["references"]:
                        resolution = next(
                            item
                            for item in resolutions
                            if item["reference_key"] == reference["reference_key"]
                        )
                        assert resolution["reference_kind"] == reference["reference_kind"]
                        assert resolution["target"] == reference["target"]
                        assert resolution["semantic_type"] == reference["expected_semantic_type"]
                        assert resolution["qualification"] == reference["qualification"]
            else:
                assert not (
                    result["round_trip"]["qualified"]
                    and result["round_trip"]["comparison"] == "semantic_equivalent"
                )
        else:
            assert result["validation_status"] != "Constructed"


def test_acc_result_material_is_exactly_qualified() -> None:
    cases = _document(ACC / "resources" / "conformance.json")["cases"]
    for case in cases:
        result = case["expected"]["result"]
        if case["operation"] != "construct_authoring_set":
            continue
        for fragment in result["candidate_fragments"]:
            _assert_resource_set(fragment["source_contract"], "authoring")
        for artifact in result["candidate_artifacts"]:
            _assert_resource_set(artifact["source_contract"], "authoring")
        normalized = result["normalized_result"]
        if normalized is not None:
            _assert_resource_set(normalized["normalized_contract"], "normalized-model")
        source_basis = result["candidate_source_basis"]
        if source_basis is not None:
            assert source_basis["artifacts"]
            assert all(entry["bytes"] for entry in source_basis["artifacts"])
            _assert_resource_set(source_basis["source_contract"], "authoring")


def test_acc_semantic_vectors_preserve_relationship_and_authority_doctrine() -> None:
    cases = {
        case["id"]: case for case in _document(ACC / "resources" / "conformance.json")["cases"]
    }

    c08 = cases["C08"]
    assert c08["name"] == "consumer-qualified custom relationship permitted by exact contract"
    relationship = c08["input"]["request"]["relationships"][0]
    assert relationship["relationship_type"] == "payments:depends_on"
    assert relationship["qualification"]["semantic_type"] == "payments:depends_on"
    assert c08["expected"]["result"]["construction_map"][-1]["identity_disposition"] == "minted"
    assert all(
        relationship["relationship_type"] != "relationship/depends_on"
        for case in cases.values()
        for relationship in case["input"]["request"]["relationships"]
    )

    for case_id in ("C14", "C15"):
        topology = cases[case_id]["input"]["request"]["fragments"][0]["fields"][
            "component_topology"
        ]
        for item in topology.get("relationships", []):
            assert {"from_key", "to_key", "type"} <= set(item)
            assert item["type"] in {
                "calls",
                "depends_on",
                "publishes_to",
                "subscribes_to",
                "reads_from",
                "writes_to",
            }

    assert cases["C16"]["input"]["request"]["relationships"][0]["relationship_type"] == (
        "relationship/consumes_interface"
    )
    assert cases["C17"]["input"]["request"]["relationships"][0]["relationship_type"] == (
        "relationship/composed_of"
    )
    assert "lifecycle_stage" in cases["C19"]["input"]["request"]["fragments"][0]["fields"]
    assert cases["C24"]["input"]["basis"]["reference_basis"]["entries"] == []
    assert cases["C24"]["expected"]["result"]["outcome"] == "Unresolved"
    assert cases["C25"]["expected"]["result"]["diagnostics"][1]["status"] == "blocked"
    assert cases["C12"]["expected"]["result"]["outcome"] == "Unavailable"
    assert cases["C40"]["input"]["basis"]["provenance"]["registry_selection"] == "latest"
    assert cases["C40"]["expected"]["result"]["outcome"] == "Rejected"


def test_acc_prepared_compact_identity_round_trip_and_permutation_vectors_are_complete() -> None:
    cases = {
        case["id"]: case for case in _document(ACC / "resources" / "conformance.json")["cases"]
    }
    c28_fragments = cases["C28"]["input"]["request"]["fragments"]
    assert {fragment["input_mode"] for fragment in c28_fragments} == {"compact", "prepared"}
    assert cases["C28"]["expected"]["result"]["round_trip"]["comparison"] == ("semantic_equivalent")

    assert cases["C29"]["expected"]["result"]["outcome"] == "Rejected"
    assert cases["C29"]["expected"]["result"]["diagnostics"][0]["code"].endswith(
        "compact.semantic_inference"
    )
    assert cases["C32"]["expected"]["result"]["round_trip"]["comparison"] == ("semantic_mismatch")
    assert cases["C32"]["expected"]["result"]["normalized_result"] is not None
    assert cases["C38"]["expected"]["result"]["candidate_source_basis"] is not None
    assert cases["C38"]["expected"]["result"]["round_trip"]["qualified"] is True

    c39_keys = [
        fragment["request_key"] for fragment in cases["C39"]["input"]["request"]["fragments"]
    ]
    normalized_keys = cases["C39"]["expected"]["result"]["normalized_result"]["model"][
        "fragment_keys"
    ]
    assert c39_keys == ["b", "a"]
    assert normalized_keys == sorted(c39_keys)


def test_acc_policy_resource_preserves_authority_ceiling_and_boundaries() -> None:
    rules = _document(ACC / "resources" / "rules.json")
    assert rules["outcomes"]["exact"] == [
        "Constructed",
        "Rejected",
        "Unavailable",
        "Unresolved",
    ]
    assert rules["outcomes"]["Constructed"]["partial"] is False
    assert rules["relationships"]["properties_imply_edges"] is False
    assert rules["relationships"]["forbidden"] == ["consumes_interface", "composed_of"]
    assert rules["identity"]["forbidden_derivations"] == [
        "alias",
        "prose",
        "path",
        "source_location",
        "content_hash",
        "source_order",
        "array_order",
        "composition_position",
    ]
    assert rules["detached_result"]["side_effects"] == {
        "repository": False,
        "git": False,
        "runtime": False,
        "runtime_snapshot": False,
        "admission": False,
        "alias_reservation": False,
    }
