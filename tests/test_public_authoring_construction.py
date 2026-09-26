"""Public Python Authoring Construction facade contract and authority tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest

from adr_kit.api import (
    AuthoringRequest,
    OperationError,
    construct_authoring_set,
    validate_authoring,
)

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "contracts" / "authoring-construction" / "v1.0" / "resources" / "conformance.json"
ACC_CONTRACT = ROOT / "contracts" / "authoring-construction" / "v1.0" / "contract.json"


def _bind_markers(value: Any, fingerprint: str) -> Any:
    if isinstance(value, str):
        return fingerprint if value == "$enclosing_scf" else value
    if isinstance(value, list):
        return [_bind_markers(item, fingerprint) for item in value]
    if isinstance(value, dict):
        return {key: _bind_markers(item, fingerprint) for key, item in value.items()}
    return value


def _request(case_id: str) -> AuthoringRequest:
    corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
    fingerprint = json.loads(ACC_CONTRACT.read_text(encoding="utf-8"))[
        "semanticContractFingerprint"
    ]
    case = next(item for item in corpus["cases"] if item["id"] == case_id)
    return AuthoringRequest.from_wire(_bind_markers(case["input"], fingerprint))


def _case(case_id: str) -> dict[str, Any]:
    corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
    fingerprint = json.loads(ACC_CONTRACT.read_text(encoding="utf-8"))[
        "semanticContractFingerprint"
    ]
    case = next(item for item in corpus["cases"] if item["id"] == case_id)
    return cast(dict[str, Any], _bind_markers(case, fingerprint))


def test_validate_authoring_reaches_protocol_1_2(monkeypatch: pytest.MonkeyPatch) -> None:
    from adr_kit.api import _construction

    captured: dict[str, object] = {}

    def fake_execute(request: dict[str, object]) -> dict[str, object]:
        captured.update(request)
        return {
            "core_contract_version": "1.2",
            "operation": "validate_authoring",
            "result": {
                "contract_family": "authoring_construction",
                "contract_version": "1.0",
                "operation": "validate_authoring",
                "validation_status": "valid",
                "basis_qualification": {},
                "diagnostics": [],
                "provenance": {},
            },
        }

    monkeypatch.setattr(_construction, "execute_validated_semantic_core_request", fake_execute)
    result = validate_authoring(
        _request("C27").__class__(
            request=_request("C27").request,
            basis=_request("C27").basis,
            operation="validate_authoring",
        )
    )
    assert captured["core_contract_version"] == "1.2"
    assert captured["operation"] == "validate_authoring"
    assert result.validation_status == "valid"


def test_validate_authoring_preserves_shared_invalid_case() -> None:
    result = validate_authoring(_request("C27"))
    expected = _case("C27")["expected"]["result"]
    assert result.validation_status == expected["validation_status"]
    assert [item.code for item in result.diagnostics] == [
        item["code"] for item in expected["diagnostics"]
    ]
    assert result.basis_qualification
    assert result.provenance


@pytest.mark.parametrize(
    ("case_id", "outcome"),
    [("C01", "Constructed"), ("C32", "Rejected"), ("C33", "Unavailable"), ("C41", "Unresolved")],
)
def test_construct_authoring_set_returns_all_governed_outcomes(case_id: str, outcome: str) -> None:
    request = _request(case_id)
    result = construct_authoring_set(request)
    assert result.outcome == outcome
    assert isinstance(result.diagnostics, tuple)
    assert isinstance(result.candidate_fragments, tuple)
    assert isinstance(result.candidate_artifacts, tuple)
    assert isinstance(result.construction_map, tuple)
    assert result.request is request


def test_constructed_result_preserves_detached_candidate_and_round_trip() -> None:
    result = construct_authoring_set(_request("C01"))
    assert result.candidate_source_basis is not None
    assert result.normalized_result is not None
    assert result.round_trip["qualified"] is True
    assert result.candidate_artifacts[0]["bytes"]


@pytest.mark.parametrize("case_id", ["C01", "C32", "C33", "C41"])
def test_construct_authoring_set_preserves_shared_case_result(case_id: str) -> None:
    result = construct_authoring_set(_request(case_id))
    expected = _case(case_id)["expected"]["result"]
    assert result.outcome == expected["outcome"]
    assert [item.code for item in result.diagnostics] == [
        item["code"] for item in expected["diagnostics"]
    ]
    assert result.basis_qualification
    assert result.round_trip
    assert result.provenance


def test_core_failures_are_host_exceptions(monkeypatch: pytest.MonkeyPatch) -> None:
    from adr_kit.api import _construction

    def fail(_: dict[str, object]) -> dict[str, object]:
        raise ValueError("protocol failure")

    monkeypatch.setattr(_construction, "execute_validated_semantic_core_request", fail)
    with pytest.raises(OperationError):
        construct_authoring_set(_request("C01"))


def test_missing_protocol_capability_is_a_host_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    from adr_kit.api import _construction

    monkeypatch.setattr(_construction, "supports_semantic_core_operation", lambda *_: False)
    with pytest.raises(OperationError, match="does not advertise"):
        construct_authoring_set(_request("C01"))
