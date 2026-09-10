"""Public Python semantic-contract bindings and closure guarantees."""

from __future__ import annotations

import pytest

from adr_kit.api import (
    calculate_semantic_contract_fingerprint,
    canonicalize_semantic_json,
    compose_semantic_contract_set,
    get_semantic_contract,
    list_semantic_contracts,
    load_semantic_resource,
    validate_semantic_resource_closure,
    verify_semantic_contract,
)


def _resources(contract):
    return [
        {
            "canonicalResourceKey": entry.canonical_resource_key,
            "content": load_semantic_resource(entry.canonical_resource_key),
        }
        for entry in contract.resource_manifest
    ]


def test_bundled_contracts_are_immutable_and_content_addressed() -> None:
    contracts = list_semantic_contracts()
    assert [item.semantic_contract_family for item in contracts] == [
        "architecture-interpretation",
        "normalized-model",
        "normative-semantics",
    ]
    for contract in contracts:
        assert contract.fingerprint_scheme == "scf:v1:sha256"
        assert all(entry.dependencies is not None for entry in contract.resource_manifest)
        with pytest.raises((AttributeError, TypeError)):
            contract.semantic_contract_family = "mutable"  # type: ignore[misc]


def test_python_contract_fingerprint_and_closure_delegate_to_core() -> None:
    contract = get_semantic_contract("normative-semantics")
    fingerprint = calculate_semantic_contract_fingerprint(contract)
    assert fingerprint.success is True
    assert fingerprint.semantic_contract_fingerprint == contract.semantic_contract_fingerprint
    verified = verify_semantic_contract(contract)
    assert verified.success is True

    closure = validate_semantic_resource_closure(contract, _resources(contract))
    assert closure.success is True
    assert closure.closure_valid is True


def test_python_contract_boundary_rejects_mutable_policy_and_resource_drift() -> None:
    contract = get_semantic_contract("normative-semantics")
    definition = contract.to_wire()
    definition["deprecated"] = False
    rejected = calculate_semantic_contract_fingerprint(definition)
    assert rejected.success is False
    assert rejected.diagnostics[0].code == "semantic_contract.mutable_policy_field"

    resources = _resources(contract)
    resources[0]["content"] = {"drifted": True}
    drift = validate_semantic_resource_closure(contract, resources)
    assert drift.success is False
    assert any(
        item.code == "semantic_contract.resource_digest_mismatch" for item in drift.diagnostics
    )


def test_python_and_core_use_raw_json_for_duplicate_members_and_safe_integers() -> None:
    duplicate = canonicalize_semantic_json('{"x":1,"x":2}')
    assert duplicate.success is False
    assert duplicate.diagnostics[0].code == "semantic_contract.invalid_json"

    unsafe = canonicalize_semantic_json(9007199254740992)
    assert unsafe.success is False
    assert unsafe.diagnostics[0].code == "semantic_contract.unsafe_number"


def test_python_contract_set_composition_is_family_sorted() -> None:
    result = compose_semantic_contract_set(list_semantic_contracts())
    assert result.success is True
    assert result.semantic_contract_set_id is not None
    assert result.semantic_contract_set_id.startswith("scs:v1:sha256:")
