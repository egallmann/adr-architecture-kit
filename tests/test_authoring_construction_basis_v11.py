"""Executable boundary tests for ACC 1.1 detached candidate-basis preparation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest

from adr_kit.core import (
    execute_validated_semantic_core_request,
    semantic_core_capabilities,
    supports_semantic_core_operation,
)
from adr_kit.semantic_contract import load_semantic_resource

pytestmark = pytest.mark.fast

ROOT = Path(__file__).resolve().parents[1]
ACC11 = ROOT / "contracts" / "authoring-construction" / "v1.1"
AI12 = ROOT / "contracts" / "architecture-interpretation" / "v1.2"
PROTOCOL = ROOT / "contracts" / "semantic-core" / "v1.5" / "contract.json"
OPERATION = "prepare_authoring_construction_basis_1_1"
ACC_FP = "scf:v1:sha256:dcb38e2247396759ed3cbf0ee308ba4c02c087bf47599e72a342cc5efe6a79c5"
AI_FP = "scf:v1:sha256:2a9300b1d7bdc9a80421cb94294fbd2f345531b5147644d02ae4bcc5c436d75a"
IDENTITY_A = "018f0000-0000-7000-8000-000000000001"
IDENTITY_B = "018f0000-0000-7000-8000-000000000002"


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _authority_request() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    definition = cast(dict[str, Any], _read(ACC11 / "contract.json"))
    resources = [
        {
            "canonicalResourceKey": item["canonicalResourceKey"],
            "content": load_semantic_resource(item["canonicalResourceKey"]),
        }
        for item in definition["resourceManifest"]
    ]
    return definition, resources


def _resource_qualification(family: str, version: str, prefix: str) -> dict[str, Any]:
    definition, _ = _authority_request()
    members = [
        {
            "canonical_resource_key": item["canonicalResourceKey"],
            "content_digest": item["contentDigest"],
        }
        for item in definition["resourceManifest"]
        if item["canonicalResourceKey"].startswith(prefix)
    ]
    return {"family": family, "version": version, "resources": members}


def _basis() -> dict[str, Any]:
    definition, _ = _authority_request()
    ai_contract = cast(dict[str, Any], _read(AI12 / "contract.json"))
    ai_closure = {
        "family": "architecture-interpretation",
        "version": "1.2",
        "resources": [
            {
                "canonical_resource_key": item["canonicalResourceKey"],
                "content_digest": item["contentDigest"],
            }
            for item in ai_contract["resourceManifest"]
        ],
    }
    return {
        "acc": {
            "family": "authoring-construction",
            "version": "1.1",
            "semantic_contract_fingerprint": ACC_FP,
        },
        "adc": _resource_qualification("authoring-domain", "1.1", "authoring-domain/1.1/"),
        "authoring": _resource_qualification("authoring", "1.7", "authoring/1.7/schema/"),
        "normalized_model": _resource_qualification(
            "normalized-model", "2.4", "normalized-model/2.4/schema/"
        ),
        "architecture_interpretation": {
            "family": "architecture-interpretation",
            "version": "1.2",
            "semantic_contract_fingerprint": AI_FP,
            "authority_closure": ai_closure,
        },
        "custom_entity": None,
        "reference_basis": {"sealed": True, "entries": []},
        "existing_source_basis": {"sealed": True, "entries": []},
        "identity_establishment": {
            "phase": "before_deterministic_interpretation",
            "supplied_uuidv7": "preserve",
            "absent_on_create": "mint_uuidv7_allowed_for_identity_bearing_types",
            "absent_on_update": "reject",
            "composition": "does_not_create_or_replace_identity",
            "derivations_forbidden": [
                "alias",
                "prose",
                "path",
                "source_location",
                "content_hash",
                "source_order",
                "array_order",
                "composition_position",
            ],
        },
        "provenance": {},
    }


def _fragment(
    key: str, identity: str, references: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    return {
        "request_key": key,
        "semantic_kind": "entity",
        "semantic_type": "entity/decision",
        "operation": "create",
        "input_mode": "prepared",
        "fields": {
            "id": identity,
            "alias_id": "DEC-0001",
            "alias_name": f"decision-{key}",
            "summary": f"Summary for {key}",
            "rationale": "Explicit.",
        },
        "contract_qualification": _resource_qualification(
            "authoring", "1.7", "authoring/1.7/schema/"
        ),
        "references": references or [],
        "composition_keys": [],
    }


def _construction_request(
    fragments: list[dict[str, Any]], compositions: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    return {
        "contract_family": "authoring_construction",
        "contract_version": "1.1",
        "operation": "construct_authoring_set",
        "request": {
            "request_id": "basis-test",
            "fragments": fragments,
            "compositions": compositions or [],
            "relationships": [],
        },
        "basis": _basis(),
    }


def _protocol_request(construction: dict[str, Any]) -> dict[str, Any]:
    definition, resources = _authority_request()
    return {
        "core_contract_version": "1.5",
        "operation": OPERATION,
        "request": {
            "operation": OPERATION,
            "definition": definition,
            "resources": resources,
            "construction_request": construction,
        },
    }


def _execute(value: dict[str, Any]) -> dict[str, Any]:
    return cast(dict[str, Any], execute_validated_semantic_core_request(value)["result"])


def test_exact_authority_and_trivial_candidate_seal_basis_without_constructed() -> None:
    result = _execute(_protocol_request(_construction_request([_fragment("alpha", IDENTITY_A)])))
    assert result["authority"] == {
        "available": True,
        "fingerprint": ACC_FP,
        "architecture_interpretation_fingerprint": AI_FP,
    }
    assert result["basis_status"] == "Sealed"
    assert result["candidate_source_basis"]["sealed"] is True
    assert result["candidate_source_basis"]["artifacts"][0]["content_digest"].startswith("sha256:")
    assert result["detached_context"]["scope_root"].startswith(
        "urn:adr-kit:detached-candidate:v1:source-basis:sha256:"
    )
    assert "outcome" not in result
    assert result["capabilities"]["construct_authoring_set"] is False
    assert result["capabilities"]["complete_acc11_qualification"] is False


def test_tampered_acc_resource_prevents_protocol_15_authority_qualification() -> None:
    request = _protocol_request(_construction_request([_fragment("alpha", IDENTITY_A)]))
    request["request"]["resources"][0]["content"] = {"tampered": True}
    result = _execute(request)
    assert result["authority"]["available"] is False
    assert result["basis_status"] == "Unavailable"
    assert result["candidate_source_basis"] is None


def test_missing_acc_resource_prevents_protocol_15_authority_qualification() -> None:
    request = _protocol_request(_construction_request([_fragment("alpha", IDENTITY_A)]))
    request["request"]["resources"].pop()
    result = _execute(request)
    assert result["authority"]["available"] is False
    assert result["basis_status"] == "Unavailable"
    assert result["candidate_source_basis"] is None


def test_wrong_exact_ai12_fingerprint_prevents_candidate_basis_sealing() -> None:
    construction = _construction_request([_fragment("alpha", IDENTITY_A)])
    construction["basis"]["architecture_interpretation"]["semantic_contract_fingerprint"] = (
        "scf:v1:sha256:" + "0" * 64
    )
    result = _execute(_protocol_request(construction))
    assert result["authority"]["available"] is True
    assert result["basis_status"] == "Unavailable"
    assert result["candidate_source_basis"] is None


def test_request_local_reference_evidence_is_complete_and_identity_keyed() -> None:
    reference = {
        "reference_key": "decision_ref",
        "reference_kind": "request",
        "target": "target",
        "expected_semantic_type": "entity/decision",
    }
    result = _execute(
        _protocol_request(
            _construction_request(
                [_fragment("source", IDENTITY_A, [reference]), _fragment("target", IDENTITY_B)]
            )
        )
    )
    assert result["basis_status"] == "Sealed"
    source = next(item for item in result["candidate_fragments"] if item["request_key"] == "source")
    assert source["identity"] == IDENTITY_A
    assert source["resolved_references"] == [
        {
            "reference_key": "decision_ref",
            "reference_kind": "request",
            "target": "target",
            "canonical_uuid": IDENTITY_B,
            "semantic_type": "entity/decision",
            "qualification": _resource_qualification("authoring", "1.7", "authoring/1.7/schema/"),
            "disposition": "resolved",
        }
    ]


def test_existing_reference_reuses_exact_reference_basis_identity_and_qualification() -> None:
    basis = _basis()
    target_qualification = basis["authoring"]
    basis["reference_basis"]["entries"] = [
        {
            "reference_id": "existing-decision",
            "canonical_uuid": IDENTITY_B,
            "semantic_kind": "entity",
            "semantic_type": "entity/decision",
            "qualification": target_qualification,
            "existence_state": "active",
        }
    ]
    request = _construction_request(
        [
            _fragment(
                "source",
                IDENTITY_A,
                [
                    {
                        "reference_key": "existing_ref",
                        "reference_kind": "existing",
                        "target": "existing-decision",
                    }
                ],
            )
        ]
    )
    request["basis"] = basis
    result = _execute(_protocol_request(request))
    assert result["basis_status"] == "Sealed"
    resolved = result["candidate_fragments"][0]["resolved_references"][0]
    assert resolved["canonical_uuid"] == IDENTITY_B
    assert resolved["semantic_type"] == "entity/decision"
    assert resolved["qualification"] == target_qualification
    assert resolved["disposition"] == "reused"


def test_unqualified_existing_reference_prevents_basis_sealing() -> None:
    basis = _basis()
    basis["reference_basis"]["entries"] = [
        {
            "reference_id": "existing-decision",
            "canonical_uuid": IDENTITY_B,
            "semantic_kind": "entity",
            "semantic_type": "entity/decision",
            "qualification": _resource_qualification("authoring", "1.6", "authoring/1.6/schema/"),
            "existence_state": "active",
        }
    ]
    request = _construction_request(
        [
            _fragment(
                "source",
                IDENTITY_A,
                [
                    {
                        "reference_key": "existing_ref",
                        "reference_kind": "existing",
                        "target": "existing-decision",
                    }
                ],
            )
        ]
    )
    request["basis"] = basis
    result = _execute(_protocol_request(request))
    assert result["basis_status"] == "Unavailable"
    assert result["candidate_source_basis"] is None
    assert result["diagnostics"][0]["code"] == "authoring_construction.reference.unqualified"


def test_missing_create_identity_is_minted_as_uuidv7() -> None:
    fragment = _fragment("minted", IDENTITY_A)
    del fragment["fields"]["id"]
    result = _execute(_protocol_request(_construction_request([fragment])))
    assert result["basis_status"] == "Sealed"
    identity = result["candidate_fragments"][0]["identity"]
    assert len(identity) == 36
    assert identity[14] == "7"
    assert identity[19] in "89ab"
    assert result["construction_map"][0]["identity_disposition"] == "minted"


def test_duplicate_canonical_identity_is_rejected() -> None:
    result = _execute(
        _protocol_request(
            _construction_request([_fragment("first", IDENTITY_A), _fragment("second", IDENTITY_A)])
        )
    )
    assert result["basis_status"] == "Rejected"
    assert result["candidate_source_basis"] is None
    assert any(
        item["code"] == "authoring_construction.identity.duplicate"
        for item in result["diagnostics"]
    )


def test_supplied_identity_and_sealed_basis_are_stable_under_fragment_reordering() -> None:
    first = _construction_request([_fragment("alpha", IDENTITY_A), _fragment("beta", IDENTITY_B)])
    reordered = _construction_request(
        [_fragment("beta", IDENTITY_B), _fragment("alpha", IDENTITY_A)]
    )
    first_result = _execute(_protocol_request(first))
    reordered_result = _execute(_protocol_request(reordered))
    assert first_result["basis_status"] == reordered_result["basis_status"] == "Sealed"
    assert (
        first_result["candidate_source_basis"]["basis_digest"]
        == reordered_result["candidate_source_basis"]["basis_digest"]
    )


def test_missing_reference_is_unresolved_and_never_omitted_as_sealed() -> None:
    reference = {"reference_key": "missing", "reference_kind": "request", "target": "absent"}
    result = _execute(
        _protocol_request(_construction_request([_fragment("source", IDENTITY_A, [reference])]))
    )
    assert result["basis_status"] == "Unresolved"
    assert result["candidate_source_basis"] is None
    assert [item["code"] for item in result["diagnostics"]] == [
        "authoring_construction.reference.unresolved"
    ]


def test_composition_requests_fail_closed_until_acc_can_carry_resolution_evidence() -> None:
    composition = {"parent": "parent", "child": "child", "relation": "contains", "ordering": 0}
    request = _construction_request(
        [_fragment("parent", IDENTITY_A), _fragment("child", IDENTITY_B)], [composition]
    )
    result = _execute(_protocol_request(request))
    assert result["basis_status"] == "Unavailable"
    assert result["candidate_source_basis"] is None
    assert result["capabilities"]["composition_resolution"] is False


def test_fragment_composition_keys_cannot_be_silently_omitted() -> None:
    fragment = _fragment("parent", IDENTITY_A)
    fragment["composition_keys"] = ["child-membership"]
    result = _execute(_protocol_request(_construction_request([fragment])))
    assert result["basis_status"] == "Unavailable"
    assert result["candidate_source_basis"] is None
    assert result["diagnostics"][0]["code"] == (
        "authoring_construction.composition.evidence_unavailable"
    )


def test_missing_update_identity_is_rejected_not_unavailable() -> None:
    fragment = _fragment("update", IDENTITY_A)
    fragment["operation"] = "update"
    del fragment["fields"]["id"]
    result = _execute(_protocol_request(_construction_request([fragment])))
    assert result["basis_status"] == "Rejected"
    assert result["candidate_source_basis"] is None
    assert result["diagnostics"][0]["code"] == "authoring_construction.identity.update_missing"


def test_capability_handshake_is_explicitly_protocol_qualified() -> None:
    handshake = semantic_core_capabilities()
    assert supports_semantic_core_operation("1.5", OPERATION)
    assert OPERATION in handshake["operations_by_version"]["1.5"]
    assert not supports_semantic_core_operation("1.4", OPERATION)


def test_published_protocol_schema_has_no_construction_outcome_field() -> None:
    schema = cast(dict[str, Any], _read(PROTOCOL))
    result = schema["$defs"]["basis_result"]
    assert "basis_status" in result["properties"]
    assert "outcome" not in result["properties"]
