"""Public architecture-materialization binding over semantic-core protocol 1.1."""

from __future__ import annotations

import json
from importlib import resources
from typing import Any, Mapping

from .. import __version__
from ..core import execute_validated_semantic_core_request
from ..semantic_contract import (
    get_semantic_contract_profile,
    list_semantic_contracts,
    list_semantic_contract_sets,
    load_semantic_resource,
)
from ._contracts import (
    API_CONTRACT_VERSION,
    ArchitectureMaterializationRequest,
    ArchitectureMaterializationResult,
    Diagnostic,
    MaterializationAuthorityProvider,
    MaterializationCapabilityLimitation,
    MaterializationProviderProvenance,
    MaterializationSemanticBasis,
    MaterializationSourceBasis,
    MaterializationSourceContract,
)
from ._errors import OperationError


def _load_asset(relative: str) -> Any:
    resource = resources.files("adr_kit.semantic_contract.v1_0").joinpath(relative)
    return json.loads(resource.read_text(encoding="utf-8"))


def _authority_definitions() -> list[dict[str, Any]]:
    definitions: list[dict[str, Any]] = []
    for contract in list_semantic_contracts():
        definitions.append(
            {
                "definition": contract.to_wire(),
                "resources": [
                    {
                        "canonicalResourceKey": entry.canonical_resource_key,
                        "content": load_semantic_resource(entry.canonical_resource_key),
                    }
                    for entry in contract.resource_manifest
                ],
            }
        )
    return definitions


def _authority_inputs(profile_id: str) -> dict[str, Any]:
    return {
        "profile": get_semantic_contract_profile(profile_id).to_wire(),
        "definitions": _authority_definitions(),
        "sets": [dict(value) for value in list_semantic_contract_sets()],
        "qualifications": _load_asset("qualifications/architecture-materialization-1.0.json"),
        "catalog": _load_asset("catalog/semantic-contract-catalog-1.0.json"),
        "policy": _load_asset("policy/semantic-contract-policy-1.0.json"),
    }


def _diagnostics(value: object) -> tuple[Diagnostic, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(
        Diagnostic(
            severity=str(item.get("severity", "error")),  # type: ignore[arg-type]
            code=str(item.get("code", "core.unknown")),
            message=str(item.get("message", "")),
            path=item.get("path") if isinstance(item.get("path"), str) else None,
            source_ref=item.get("sourceRef") if isinstance(item.get("sourceRef"), str) else None,
            field=item.get("field") if isinstance(item.get("field"), str) else None,
        )
        for item in value
        if isinstance(item, Mapping)
    )


def _provider(value: object) -> MaterializationAuthorityProvider | None:
    if not isinstance(value, Mapping):
        return None
    kind = value.get("kind")
    namespace = value.get("architectureNamespace")
    if not isinstance(kind, str) or not isinstance(namespace, str):
        return None
    return MaterializationAuthorityProvider(kind=kind, architecture_namespace=namespace)


def _provenance(value: object) -> MaterializationProviderProvenance | None:
    if not isinstance(value, Mapping):
        return None
    return MaterializationProviderProvenance(
        semantic_core_contract_version=str(value.get("semanticCoreContractVersion", "")),
        package_version=str(value.get("packageVersion", "")),
        host_binding=str(value.get("hostBinding", "")),
    )


def _result(
    request: ArchitectureMaterializationRequest, value: Mapping[str, Any]
) -> ArchitectureMaterializationResult:
    basis = value.get("semanticBasis")
    basis = basis if isinstance(basis, Mapping) else {}
    outcome = value.get("outcome", "Rejected")
    if outcome not in {"Materialized", "Rejected", "Unavailable"}:
        outcome = "Rejected"
    source_basis_value = value.get("sourceBasis")
    source_basis = (
        MaterializationSourceBasis.from_wire(source_basis_value)
        if isinstance(source_basis_value, Mapping)
        else None
    )
    return ArchitectureMaterializationResult(
        request=request,
        success=bool(value.get("success", False)),
        outcome=outcome,
        authority_provider=_provider(value.get("authorityProvider")),
        source_basis=source_basis,
        source_contract_closure=tuple(
            MaterializationSourceContract.from_wire(item)
            for item in value.get("sourceContractClosure", ())
            if isinstance(item, Mapping)
        ),
        semantic_basis=MaterializationSemanticBasis(
            semantic_contract_set_id=(
                basis.get("semanticContractSetId")
                if isinstance(basis.get("semanticContractSetId"), str)
                else None
            ),
            authority_state_fingerprint=(
                basis.get("authorityStateFingerprint")
                if isinstance(basis.get("authorityStateFingerprint"), str)
                else None
            ),
        ),
        normalized_model=(
            value.get("normalizedModel")
            if isinstance(value.get("normalizedModel"), Mapping)
            else None
        ),
        source_capability_limitations=tuple(
            MaterializationCapabilityLimitation(
                source_contract=MaterializationSourceContract.from_wire(item["sourceContractRef"]),
                semantic_capability=str(item["semanticCapability"]),
                classification="not_expressible_by_source_contract",
            )
            for item in value.get("sourceCapabilityLimitations", ())
            if isinstance(item, Mapping) and isinstance(item.get("sourceContractRef"), Mapping)
        ),
        provider_provenance=_provenance(value.get("providerProvenance")),
        diagnostics=_diagnostics(value.get("diagnostics")),
        package_version=__version__,
        api_contract_version=API_CONTRACT_VERSION,
    )


def materialize_architecture(
    request: ArchitectureMaterializationRequest,
) -> ArchitectureMaterializationResult:
    """Materialize explicit host-parsed sources through semantic-core 1.1.

    This adapter never resolves a current pointer and never interprets source
    documents. It supplies the exact packaged authority closure selected by
    ``request.semantic_contract_set_id`` and delegates all meaning-affecting
    work to the canonical Rust/WASM boundary.
    """

    if not isinstance(request, ArchitectureMaterializationRequest):
        raise TypeError("request must be an ArchitectureMaterializationRequest")
    wire: dict[str, Any] = {
        "core_contract_version": "1.1",
        "operation": "materialize_architecture",
        "materializationContractVersion": "1.0",
        "semanticContractSetId": request.semantic_contract_set_id,
        "authorityProvider": request.authority_provider.to_wire(),
        "sourceBasis": request.source_basis.to_wire() if request.source_basis else None,
        "providerProvenance": {
            "semanticCoreContractVersion": "1.1",
            "packageVersion": __version__,
            "hostBinding": "public-host",
        },
        "targetOperation": "materialize_architecture",
        "direction": request.direction,
        "useMode": request.use_mode,
        **_authority_inputs(request.profile_id),
    }
    try:
        result = execute_validated_semantic_core_request(wire)
    except OperationError:
        raise
    except Exception as exc:
        raise OperationError("Architecture materialization could not complete") from exc
    return _result(request, result)


__all__ = ["materialize_architecture"]
