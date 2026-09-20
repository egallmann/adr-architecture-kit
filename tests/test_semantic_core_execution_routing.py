"""Raw WASM routing guards for the versioned semantic-core boundary."""

from __future__ import annotations

from adr_kit.core import execute_semantic_core_request


def _valid_v10_contract_request(version: str) -> dict[str, object]:
    return {
        "core_contract_version": version,
        "operation": "validate_contract",
        "profile": "greenfield",
        "entity_registry": {"entities": []},
    }


def _assert_generic_rejection(result: dict[str, object]) -> None:
    assert result["core_contract_version"] == "1.0"
    assert result["operation"] == "validate_contract"
    assert result["success"] is False
    assert result["outcome"] == "invalid_request"


def test_raw_wasm_v12_does_not_execute_a_valid_v10_operation() -> None:
    result = execute_semantic_core_request(_valid_v10_contract_request("1.2"))
    _assert_generic_rejection(result)


def test_raw_wasm_v12_does_not_execute_v11_operations() -> None:
    for operation in ("resolve_semantic_contract_set", "materialize_architecture"):
        result = execute_semantic_core_request(
            {"core_contract_version": "1.2", "operation": operation}
        )
        _assert_generic_rejection(result)


def test_raw_wasm_v12_authoring_operations_remain_non_executable() -> None:
    for operation in ("validate_authoring", "construct_authoring_set"):
        result = execute_semantic_core_request(
            {"core_contract_version": "1.2", "operation": operation}
        )
        _assert_generic_rejection(result)


def test_raw_wasm_unsupported_version_cannot_execute_v10_or_v11_operations() -> None:
    result = execute_semantic_core_request(_valid_v10_contract_request("9.9"))
    _assert_generic_rejection(result)

    for operation in ("resolve_semantic_contract_set", "materialize_architecture"):
        result = execute_semantic_core_request(
            {"core_contract_version": "9.9", "operation": operation}
        )
        _assert_generic_rejection(result)
