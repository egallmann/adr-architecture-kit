"""Public ADC discovery projections over the canonical contract artifact.

This module deliberately contains no authoring model, compiler registry, or
construction logic.  The checked-in compatibility resource is a mechanically
generated mirror of ``contracts/authoring-domain/v1.0/contract.json``; the
binding only turns that language-neutral authority into immutable Python DTOs.
"""

from __future__ import annotations

import json
from functools import lru_cache
from importlib import resources
from typing import Any, Mapping, cast

from ._contracts import (
    AuthoringContractDescription,
    AuthoringDiscriminator,
    AuthoringParentConstraint,
    AuthoringPolicy,
    AuthoringTypeDescriptor,
    AuthoringTypeKey,
    AuthoringTypeList,
    AuthoringTypeSummary,
    Diagnostic,
)
from ._errors import AuthoringDiscoveryError, InvalidRequestError, OperationError


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise OperationError(f"Canonical ADC resource field is not an object: {label}")
    return value


@lru_cache(maxsize=1)
def _canonical_contract() -> Mapping[str, Any]:
    """Load the generated package mirror without exposing mutable JSON."""

    resource = resources.files("adr_kit.compatibility").joinpath("authoring-domain-v1.0.json")
    payload = json.loads(resource.read_text(encoding="utf-8"))
    return _mapping(payload, "contract")


def _diagnostic(code: str, message: str, path: str) -> Diagnostic:
    return Diagnostic(severity="error", code=code, message=message, path=path)


def _selection_error(code: str, message: str, path: str) -> AuthoringDiscoveryError:
    return AuthoringDiscoveryError(code, message, (_diagnostic(code, message, path),))


def _require_version(contract_version: str) -> Mapping[str, Any]:
    if not isinstance(contract_version, str):
        raise InvalidRequestError("contract_version must be a string")
    contract = _canonical_contract()
    expected = contract.get("contract_version")
    if contract_version != expected:
        raise _selection_error(
            "contract.unsupported_version",
            f"Unsupported authoring-domain contract version: {contract_version}",
            "contract_version",
        )
    return contract


def _type_key(value: object) -> AuthoringTypeKey:
    item = _mapping(value, "type.key")
    return AuthoringTypeKey(
        kind=cast(Any, item["kind"]),
        name=str(item["name"]),
    )


def _parent(value: object) -> AuthoringParentConstraint:
    item = _mapping(value, "composition_policy.allowed_parents")
    max_occurs = item.get("max_occurs")
    if max_occurs is not None and not isinstance(max_occurs, int):
        raise OperationError("Canonical ADC max_occurs must be an integer or null")
    return AuthoringParentConstraint(
        kind=cast(Any, item["kind"]),
        name=str(item["name"]),
        min_occurs=int(item["min_occurs"]),
        max_occurs=max_occurs,
    )


def _policy(value: object) -> AuthoringPolicy:
    item = _mapping(value, "policy")
    status = item.get("status")
    if status not in {"defined", "deferred", "not_applicable"}:
        raise OperationError(f"Canonical ADC policy has unsupported status: {status}")
    raw_values = item.get("values", ())
    raw_parents = item.get("allowed_parents", ())
    if not isinstance(raw_values, (list, tuple)) or not isinstance(raw_parents, (list, tuple)):
        raise OperationError("Canonical ADC policy collections must be arrays")
    return AuthoringPolicy(
        status=cast(Any, status),
        mode=item.get("mode") if isinstance(item.get("mode"), str) else None,
        values=tuple(str(entry) for entry in raw_values),
        allowed_parents=tuple(_parent(entry) for entry in raw_parents),
        owner=item.get("owner") if isinstance(item.get("owner"), str) else None,
    )


def _descriptor(value: object) -> AuthoringTypeDescriptor:
    item = _mapping(value, "type descriptor")
    discriminator = _mapping(item["discriminator"], "discriminator")
    return AuthoringTypeDescriptor(
        contract_version=str(item["contract_version"]),
        key=_type_key(item["key"]),
        display_name=str(item["display_name"]),
        description=str(item["description"]),
        authoring_mode=cast(Any, item["authoring_mode"]),
        semantic_type_ownership=cast(Any, item["semantic_type_ownership"]),
        discriminator=AuthoringDiscriminator(
            mode=str(discriminator["mode"]),
            field=(discriminator["field"] if isinstance(discriminator.get("field"), str) else None),
            value=(discriminator["value"] if isinstance(discriminator.get("value"), str) else None),
        ),
        input_contract=_policy(item["input_contract"]),
        identity_policy=_policy(item["identity_policy"]),
        composition_policy=_policy(item["composition_policy"]),
        reference_policy=_policy(item["reference_policy"]),
        field_ownership_policy=_policy(item["field_ownership_policy"]),
    )


def _type_values(contract: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    values = contract.get("types")
    if not isinstance(values, list):
        raise OperationError("Canonical ADC contract types must be an array")
    return tuple(_mapping(value, "types[]") for value in values)


def _validate_kind(contract: Mapping[str, Any], kind: str) -> None:
    kinds = contract.get("type_kinds")
    if not isinstance(kinds, list) or kind not in kinds:
        raise _selection_error(
            "authoring.unknown_type_kind",
            f"Unknown authoring type kind: {kind}",
            "kind",
        )


def describe_authoring_contract(contract_version: str) -> AuthoringContractDescription:
    """Describe the exact ADC version supported by this binding."""

    contract = _require_version(contract_version)
    return AuthoringContractDescription(
        contract_id=str(contract["contract_id"]),
        contract_version=str(contract["contract_version"]),
        defined_capabilities=tuple(str(value) for value in contract["defined_capabilities"]),
        discovery_operations=tuple(str(value) for value in contract["discovery_operations"]),
        type_kinds=tuple(str(value) for value in contract["type_kinds"]),
    )


def list_authoring_types(contract_version: str, *, kind: str | None = None) -> AuthoringTypeList:
    """List ADC types using an optional exact, case-sensitive kind filter."""

    contract = _require_version(contract_version)
    if kind is not None:
        if not isinstance(kind, str):
            raise InvalidRequestError("kind must be a string or None")
        _validate_kind(contract, kind)
    values = [
        value
        for value in _type_values(contract)
        if kind is None or _mapping(value["key"], "type.key").get("kind") == kind
    ]
    values.sort(
        key=lambda value: (
            str(_mapping(value["key"], "type.key")["kind"]),
            str(_mapping(value["key"], "type.key")["name"]),
        )
    )
    return AuthoringTypeList(
        contract_version=str(contract["contract_version"]),
        types=tuple(
            AuthoringTypeSummary(
                key=_type_key(value["key"]),
                display_name=str(value["display_name"]),
                description=str(value["description"]),
            )
            for value in values
        ),
    )


def describe_authoring_type(
    contract_version: str, *, kind: str, name: str
) -> AuthoringTypeDescriptor:
    """Describe one ADC type selected by the exact ``(kind, name)`` pair."""

    contract = _require_version(contract_version)
    if not isinstance(kind, str) or not isinstance(name, str):
        raise InvalidRequestError("kind and name must be strings")
    _validate_kind(contract, kind)
    for value in _type_values(contract):
        key = _mapping(value["key"], "type.key")
        if key.get("kind") == kind and key.get("name") == name:
            return _descriptor(value)
    raise _selection_error(
        "authoring.unknown_type",
        f"Unknown authoring type: {kind}/{name}",
        "name",
    )


__all__ = [
    "describe_authoring_contract",
    "list_authoring_types",
    "describe_authoring_type",
]
