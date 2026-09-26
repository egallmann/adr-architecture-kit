"""Thin public Authoring Construction adapters over semantic-core protocol 1.2."""

from __future__ import annotations

from typing import Mapping, cast

from .. import __version__
from ..core import execute_validated_semantic_core_request, supports_semantic_core_operation
from ._contracts import (
    API_CONTRACT_VERSION,
    AuthoringConstructionOutcome,
    AuthoringConstructionResult,
    AuthoringDiagnostic,
    AuthoringRequest,
    AuthoringValidationResult,
    AuthoringValidationStatus,
)
from ._errors import InvalidRequestError, OperationError

SEMANTIC_CORE_PROTOCOL_VERSION = "1.2"


def _mapping(value: object, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise OperationError(f"Semantic core returned malformed {field}")
    return value


def _mapping_list(value: object, field: str) -> tuple[Mapping[str, object], ...]:
    if not isinstance(value, list):
        raise OperationError(f"Semantic core returned malformed {field}")
    items: list[Mapping[str, object]] = []
    for item in value:
        items.append(_mapping(item, field))
    return tuple(items)


def _diagnostics(value: object) -> tuple[AuthoringDiagnostic, ...]:
    if not isinstance(value, list):
        raise OperationError("Semantic core returned malformed diagnostics")
    diagnostics: list[AuthoringDiagnostic] = []
    for item in value:
        if not isinstance(item, Mapping):
            raise OperationError("Semantic core returned malformed diagnostics")
        try:
            diagnostics.append(AuthoringDiagnostic.from_wire(item))
        except InvalidRequestError as exc:
            raise OperationError("Semantic core returned malformed diagnostics") from exc
    return tuple(diagnostics)


def _result(envelope: Mapping[str, object]) -> Mapping[str, object]:
    result = envelope.get("result")
    return _mapping(result, "result")


def _execute(request: AuthoringRequest) -> Mapping[str, object]:
    operation = request.operation
    if not supports_semantic_core_operation(SEMANTIC_CORE_PROTOCOL_VERSION, operation):
        raise OperationError(
            f"Loaded semantic core does not advertise protocol {SEMANTIC_CORE_PROTOCOL_VERSION} "
            f"operation {operation}"
        )
    wire = {
        "core_contract_version": SEMANTIC_CORE_PROTOCOL_VERSION,
        "operation": operation,
        "request": request.to_wire(),
    }
    try:
        return _result(execute_validated_semantic_core_request(wire))
    except OperationError:
        raise
    except Exception as exc:
        raise OperationError(f"Authoring operation {operation} could not complete") from exc


def _base_result_fields(value: Mapping[str, object], operation: str) -> tuple[
    Mapping[str, object],
    tuple[AuthoringDiagnostic, ...],
    Mapping[str, object],
]:
    if value.get("contract_family") != "authoring_construction":
        raise OperationError("Semantic core returned an unexpected authoring contract family")
    if value.get("contract_version") != "1.0":
        raise OperationError("Semantic core returned an unexpected authoring contract version")
    if value.get("operation") != operation:
        raise OperationError("Semantic core returned an unexpected authoring operation")
    return (
        _mapping(value.get("basis_qualification"), "basis_qualification"),
        _diagnostics(value.get("diagnostics")),
        _mapping(value.get("provenance"), "provenance"),
    )


def validate_authoring(request: AuthoringRequest) -> AuthoringValidationResult:
    """Validate one exact ACC request through semantic-core protocol 1.2."""

    if not isinstance(request, AuthoringRequest):
        raise TypeError("request must be an AuthoringRequest")
    if request.operation != "validate_authoring":
        raise InvalidRequestError("validate_authoring requires operation='validate_authoring'")
    value = _execute(request)
    basis, diagnostics, provenance = _base_result_fields(value, "validate_authoring")
    status = value.get("validation_status")
    if status not in {"valid", "invalid", "unavailable", "unresolved"}:
        raise OperationError("Semantic core returned an invalid validation_status")
    return AuthoringValidationResult(
        request=request,
        contract_family="authoring_construction",
        contract_version="1.0",
        operation="validate_authoring",
        validation_status=cast(AuthoringValidationStatus, status),
        diagnostics=diagnostics,
        basis_qualification=basis,
        provenance=provenance,
        package_version=__version__,
        api_contract_version=API_CONTRACT_VERSION,
    )


def construct_authoring_set(request: AuthoringRequest) -> AuthoringConstructionResult:
    """Construct one detached ACC candidate set through protocol 1.2."""

    if not isinstance(request, AuthoringRequest):
        raise TypeError("request must be an AuthoringRequest")
    if request.operation != "construct_authoring_set":
        raise InvalidRequestError(
            "construct_authoring_set requires operation='construct_authoring_set'"
        )
    value = _execute(request)
    basis, diagnostics, provenance = _base_result_fields(value, "construct_authoring_set")
    outcome = value.get("outcome")
    if outcome not in {"Constructed", "Rejected", "Unavailable", "Unresolved"}:
        raise OperationError("Semantic core returned an invalid construction outcome")
    source_basis = value.get("candidate_source_basis")
    normalized = value.get("normalized_result")
    return AuthoringConstructionResult(
        request=request,
        contract_family="authoring_construction",
        contract_version="1.0",
        operation="construct_authoring_set",
        outcome=cast(AuthoringConstructionOutcome, outcome),
        diagnostics=diagnostics,
        basis_qualification=basis,
        candidate_fragments=_mapping_list(value.get("candidate_fragments"), "candidate_fragments"),
        candidate_artifacts=_mapping_list(value.get("candidate_artifacts"), "candidate_artifacts"),
        candidate_source_basis=(
            _mapping(source_basis, "candidate_source_basis") if source_basis is not None else None
        ),
        construction_map=_mapping_list(value.get("construction_map"), "construction_map"),
        normalized_result=(
            _mapping(normalized, "normalized_result") if normalized is not None else None
        ),
        round_trip=_mapping(value.get("round_trip"), "round_trip"),
        provenance=provenance,
        package_version=__version__,
        api_contract_version=API_CONTRACT_VERSION,
    )


__all__ = ["construct_authoring_set", "validate_authoring"]
