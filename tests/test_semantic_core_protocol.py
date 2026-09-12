"""Protocol-shape checks for the versioned semantic-core boundary."""

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from adr_kit.core import execute_semantic_core_request, validate_semantic_core_protocol

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "semantic-core" / "v1.0" / "contract.json"
CONTRACT_V11 = ROOT / "contracts" / "semantic-core" / "v1.1" / "contract.json"
VECTORS = ROOT / "contracts" / "semantic-core" / "v1.0" / "vectors"


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
