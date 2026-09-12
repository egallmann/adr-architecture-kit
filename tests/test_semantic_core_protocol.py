"""Protocol-shape checks for the versioned semantic-core boundary."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from jsonschema import Draft7Validator, Draft202012Validator, RefResolver

from adr_kit.core import execute_semantic_core_request, validate_semantic_core_protocol

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "semantic-core" / "v1.0" / "contract.json"
CONTRACT_V11 = ROOT / "contracts" / "semantic-core" / "v1.1" / "contract.json"
VECTORS = ROOT / "contracts" / "semantic-core" / "v1.0" / "vectors"
VECTORS_V11 = ROOT / "contracts" / "semantic-core" / "v1.1" / "vectors"
NORMALIZED_V23 = ROOT / "schema" / "normalized-model" / "v2.3"


def test_protocol_schema_is_valid_and_discriminates_operations() -> None:
    schema = json.loads(CONTRACT.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    checked = 0
    raw_only = 0

    for vector_path in sorted(VECTORS.glob("*.json")):
        document = json.loads(vector_path.read_text(encoding="utf-8"))
        for case in document["cases"]:
            request = case["request"]
            if request.get("core_contract_version") != "1.0":
                continue
            if case.get("executionBoundary") == "raw-core":
                raw_only += 1
                request_errors = list(validator.iter_errors(request))
                assert request_errors, (vector_path, case["name"])
                try:
                    validate_semantic_core_protocol(request)
                except ValueError:
                    pass
                else:
                    raise AssertionError(
                        f"raw-core vector must be rejected by the validated protocol: {case['name']}"
                    )
                continue
            assert not list(validator.iter_errors(request)), (vector_path, case["name"])
            result = execute_semantic_core_request(request)
            assert not list(validator.iter_errors(result)), (vector_path, case["name"], result)
            validate_semantic_core_protocol(request)
            validate_semantic_core_protocol(result)
            checked += 1

    assert checked == 42
    assert raw_only == 1


def test_protocol_rejects_unknown_operation_fields() -> None:
    request = {
        "core_contract_version": "1.0",
        "operation": "validate_architecture",
        "mode": "complete",
        "records": [],
        "unowned_semantic_rule": True,
    }
    try:
        validate_semantic_core_protocol(request)
    except ValueError as exc:
        assert "protocol violation" in str(exc)
    else:
        raise AssertionError("unknown operation fields must be rejected")


def test_protocol_accepts_the_shared_invalid_request_error_envelope() -> None:
    request = {
        "core_contract_version": "9.0",
        "operation": "validate_contract",
        "profile": "greenfield",
        "entity_registry": {"entities": []},
    }
    result = execute_semantic_core_request(request)
    assert result["outcome"] == "invalid_request"
    validate_semantic_core_protocol(result)


def test_v11_protocol_is_additive_and_routes_its_result_contract() -> None:
    schema = json.loads(CONTRACT_V11.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    result = {
        "core_contract_version": "1.1",
        "operation": "resolve_semantic_contract_set",
        "success": False,
        "diagnostics": [
            {
                "severity": "error",
                "code": "semantic_contract.exact_set_not_retained",
                "message": "the explicitly requested SCS is not present in the retained corpus",
                "path": "semanticContractSetId",
            }
        ],
    }
    assert not list(validator.iter_errors(result))
    validate_semantic_core_protocol(result)


def test_v11_only_operation_submitted_as_v10_is_rejected() -> None:
    request = {
        "core_contract_version": "1.0",
        "operation": "materialize_architecture",
    }
    result = execute_semantic_core_request(request)
    assert result["success"] is False
    assert result["core_contract_version"] == "1.0"
    validate_semantic_core_protocol(result)


def test_v11_operations_execute_through_the_packaged_wasm_boundary() -> None:
    for operation in ("resolve_semantic_contract_set", "materialize_architecture"):
        result = execute_semantic_core_request(
            {"core_contract_version": "1.1", "operation": operation}
        )
        assert result["core_contract_version"] == "1.1"
        assert result["success"] is False
        validate_semantic_core_protocol(result)


def _assert_v11_vector(
    case: dict[str, object],
    validator: Draft202012Validator,
    normalized_validator: Draft7Validator,
) -> dict[str, object]:
    request = case["request"]
    assert isinstance(request, dict)
    assert not list(validator.iter_errors(request)), case["name"]
    result = execute_semantic_core_request(request)
    assert not list(validator.iter_errors(result)), (case["name"], result)
    expected = case["expected"]
    assert isinstance(expected, dict)
    assert result.get("success") is expected["success"], case["name"]
    assert result.get("outcome") == expected["outcome"], case["name"]
    if result.get("outcome") == "Materialized":
        assert not list(normalized_validator.iter_errors(result["normalizedModel"])), case["name"]
    actual_diagnostic_codes = [item["code"] for item in result.get("diagnostics", [])]
    assert actual_diagnostic_codes == expected.get("diagnostic_codes", []), case["name"]
    actual_codes = Counter(actual_diagnostic_codes)
    assert actual_codes == Counter(expected.get("diagnostic_code_counts", {})), case["name"]
    assertions = expected.get("assertions", {})
    if "normalized_schema_version" in assertions:
        assert result["normalizedModel"]["schema_version"] == assertions["normalized_schema_version"]
    if "source_contract_versions" in assertions:
        assert [item["version"] for item in result["sourceContractClosure"]] == assertions["source_contract_versions"]
    if "normalized_entity_type" in assertions:
        assert any(item["entity_type"] == assertions["normalized_entity_type"] for item in result["normalizedModel"]["entities"])
    if "limitation_capability" in assertions:
        assert any(item["semanticCapability"] == assertions["limitation_capability"] for item in result["sourceCapabilityLimitations"])
    if "unresolved_count" in assertions:
        assert len(result["normalizedModel"]["unresolved"]) == assertions["unresolved_count"]
    if assertions.get("closure_resource_keys_are_sorted"):
        for binding in result["sourceContractClosure"]:
            keys = [item["canonicalResourceKey"] for item in binding["resourceClosure"]]
            assert keys == sorted(keys)
    if assertions.get("no_runtime_identity"):
        encoded = json.dumps(result).lower()
        assert "runtime" not in encoded
    return result


def test_v11_materialization_vectors_are_executable_and_shared() -> None:
    schema = json.loads(CONTRACT_V11.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    normalized_schema = json.loads((NORMALIZED_V23 / "normalized-architecture-model.schema.json").read_text(encoding="utf-8"))
    normalized_entity_schema = json.loads((NORMALIZED_V23 / "normalized-entity.schema.json").read_text(encoding="utf-8"))
    normalized_extension_schema = normalized_entity_schema["oneOf"][0]["properties"]["extension"]
    normalized_resources = {
        json.loads((NORMALIZED_V23 / name).read_text(encoding="utf-8"))["$id"]: json.loads((NORMALIZED_V23 / name).read_text(encoding="utf-8"))
        for name in ("normalized-entity.schema.json", "relationship-record.schema.json")
    }
    # The canonical relationship schema references the entity extension
    # fragment, which is nested inside its regular oneOf branch.  Resolve the
    # governed fragment explicitly here while preserving the committed schema
    # and its established semantic-contract identity.
    relationship_schema = normalized_resources[next(key for key in normalized_resources if key.endswith("relationship-record.schema.json"))]
    for branch in relationship_schema["oneOf"]:
        if branch.get("properties", {}).get("extension", {}).get("$ref") == "normalized-entity.schema.json#/properties/extension":
            branch["properties"]["extension"] = normalized_extension_schema
    normalized_validator = Draft7Validator(
        normalized_schema,
        resolver=RefResolver.from_schema(normalized_schema, store=normalized_resources),
    )
    checked = 0
    for vector_path in sorted(VECTORS_V11.glob("*.json")):
        document = json.loads(vector_path.read_text(encoding="utf-8"))
        for case in document["cases"]:
            result = _assert_v11_vector(case, validator, normalized_validator)
            expected = case["expected"]
            if "pairedRequest" in expected:
                paired_case = {"name": f"{case['name']}:pair", "request": expected["pairedRequest"], "expected": {"success": True, "outcome": "Materialized", "diagnostic_code_counts": {}}}
                paired = _assert_v11_vector(paired_case, validator, normalized_validator)
                assert result["normalizedModel"] == paired["normalizedModel"]
                assert result["sourceContractClosure"] == paired["sourceContractClosure"]
            checked += 1
    assert checked >= 28


def test_v11_positive_vectors_validate_the_applicable_authoring_schema() -> None:
    for vector_path in sorted(VECTORS_V11.glob("*.json")):
        document = json.loads(vector_path.read_text(encoding="utf-8"))
        for case in document["cases"]:
            if case["expected"]["outcome"] != "Materialized":
                continue
            for artifact in case["request"]["sourceBasis"]["artifacts"]:
                source = artifact["document"]
                schema_dir = ROOT / "schema" / "authoring" / f"v{source['schema_version']}"
                schema_path = schema_dir / f"adr-{source['adr_type']}.schema.json"
                schema = json.loads(schema_path.read_text(encoding="utf-8"))
                store = {}
                for path in schema_dir.glob("*.schema.json"):
                    resource = json.loads(path.read_text(encoding="utf-8"))
                    if "$id" in resource:
                        store[resource["$id"]] = resource
                errors = list(
                    Draft7Validator(
                        schema,
                        resolver=RefResolver.from_schema(schema, store=store),
                    ).iter_errors(source)
                )
                assert not errors, (case["name"], errors)
