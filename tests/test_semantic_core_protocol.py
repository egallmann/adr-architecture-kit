"""Protocol-shape checks for the versioned semantic-core boundary."""

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from adr_kit.core import execute_semantic_core_request, validate_semantic_core_protocol

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "semantic-core" / "v1.0" / "contract.json"
VECTORS = ROOT / "contracts" / "semantic-core" / "v1.0" / "vectors"


def test_protocol_schema_is_valid_and_discriminates_operations() -> None:
    schema = json.loads(CONTRACT.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    checked = 0

    for vector_path in sorted(VECTORS.glob("*.json")):
        document = json.loads(vector_path.read_text(encoding="utf-8"))
        for case in document["cases"]:
            request = case["request"]
            if request.get("core_contract_version") != "1.0":
                continue
            assert not list(validator.iter_errors(request)), (vector_path, case["name"])
            result = execute_semantic_core_request(request)
            assert not list(validator.iter_errors(result)), (vector_path, case["name"], result)
            validate_semantic_core_protocol(request)
            validate_semantic_core_protocol(result)
            checked += 1

    assert checked == 42


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
