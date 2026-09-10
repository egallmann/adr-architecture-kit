"""Public bindings for the immutable ADR-Kit semantic contracts.

This module deliberately contains no canonicalization, closure, or fingerprint
algorithm. Those meaning-affecting rules execute in the packaged semantic core;
the Python layer only loads the governed resources, adapts names, and exposes
immutable Python views of the result.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from importlib import resources
from typing import Any, Mapping, Sequence

from ..api._contracts import Diagnostic
from ..core.semantic_core import execute_validated_semantic_core_request

SCF_SCHEME = "scf:v1:sha256"
SCS_SCHEME = "scs:v1:sha256"


@dataclass(frozen=True, slots=True)
class SemanticResourceDependency:
    """One explicit content-addressed edge in a semantic resource graph."""

    canonical_resource_key: str
    content_digest: str

    @classmethod
    def from_wire(cls, value: Mapping[str, Any]) -> "SemanticResourceDependency":
        return cls(
            canonical_resource_key=str(value["canonicalResourceKey"]),
            content_digest=str(value["contentDigest"]),
        )

    def to_wire(self) -> dict[str, Any]:
        return {
            "canonicalResourceKey": self.canonical_resource_key,
            "contentDigest": self.content_digest,
        }


@dataclass(frozen=True, slots=True)
class SemanticResourceManifestEntry:
    """An immutable resource identity and its explicit dependency edges."""

    canonical_resource_key: str
    content_digest: str
    role: str
    dependencies: tuple[SemanticResourceDependency, ...] = ()

    @classmethod
    def from_wire(cls, value: Mapping[str, Any]) -> "SemanticResourceManifestEntry":
        return cls(
            canonical_resource_key=str(value["canonicalResourceKey"]),
            content_digest=str(value["contentDigest"]),
            role=str(value["role"]),
            dependencies=tuple(
                SemanticResourceDependency.from_wire(item) for item in value["dependencies"]
            ),
        )

    def to_wire(self) -> dict[str, Any]:
        return {
            "canonicalResourceKey": self.canonical_resource_key,
            "contentDigest": self.content_digest,
            "role": self.role,
            "dependencies": [item.to_wire() for item in self.dependencies],
        }


@dataclass(frozen=True, slots=True)
class SemanticContractVersion:
    """Immutable semantic meaning; lifecycle and catalog policy are excluded."""

    semantic_contract_family: str
    semantic_contract_version: str
    fingerprint_scheme: str
    resource_manifest: tuple[SemanticResourceManifestEntry, ...]
    frozen_normative_conformance_resources: tuple[str, ...]
    semantic_contract_fingerprint: str

    @classmethod
    def from_wire(cls, value: Mapping[str, Any]) -> "SemanticContractVersion":
        return cls(
            semantic_contract_family=str(value["semanticContractFamily"]),
            semantic_contract_version=str(value["semanticContractVersion"]),
            fingerprint_scheme=str(value["fingerprintScheme"]),
            resource_manifest=tuple(
                SemanticResourceManifestEntry.from_wire(item) for item in value["resourceManifest"]
            ),
            frozen_normative_conformance_resources=tuple(
                str(item) for item in value["frozenNormativeConformanceResources"]
            ),
            semantic_contract_fingerprint=str(value["semanticContractFingerprint"]),
        )

    def to_wire(self) -> dict[str, Any]:
        return {
            "semanticContractFamily": self.semantic_contract_family,
            "semanticContractVersion": self.semantic_contract_version,
            "fingerprintScheme": self.fingerprint_scheme,
            "resourceManifest": [item.to_wire() for item in self.resource_manifest],
            "frozenNormativeConformanceResources": list(
                self.frozen_normative_conformance_resources
            ),
            "semanticContractFingerprint": self.semantic_contract_fingerprint,
        }


@dataclass(frozen=True, slots=True)
class SemanticOperationResult:
    """Immutable, host-neutral result view returned by a semantic operation."""

    success: bool
    diagnostics: tuple[Diagnostic, ...]
    canonical_preimage_json: str | None = None
    canonical_preimage_hex: str | None = None
    fingerprint: str | None = None
    semantic_contract_fingerprint: str | None = None
    semantic_contract_set_id: str | None = None
    mode: str | None = None
    closure_valid: bool | None = None


def _result(value: Mapping[str, Any]) -> SemanticOperationResult:
    diagnostics = tuple(
        Diagnostic(
            severity=str(item.get("severity", "error")),  # type: ignore[arg-type]
            code=str(item.get("code", "core.unknown")),
            message=str(item.get("message", "")),
            path=item.get("path"),
        )
        for item in value.get("diagnostics", [])
        if isinstance(item, Mapping)
    )
    return SemanticOperationResult(
        success=bool(value.get("success", False)),
        diagnostics=diagnostics,
        canonical_preimage_json=value.get("canonical_preimage_json"),
        canonical_preimage_hex=value.get("canonical_preimage_hex"),
        fingerprint=value.get("fingerprint"),
        semantic_contract_fingerprint=value.get("semantic_contract_fingerprint"),
        semantic_contract_set_id=value.get("semantic_contract_set_id"),
        mode=value.get("mode"),
        closure_valid=value.get("closure_valid"),
    )


def _execute(operation: str, **fields: Any) -> SemanticOperationResult:
    request: dict[str, Any] = {
        "core_contract_version": "1.0",
        "operation": operation,
        **fields,
    }
    return _result(execute_validated_semantic_core_request(request))


def canonicalize_semantic_json(value: Any) -> SemanticOperationResult:
    """Canonicalize a JSON value through the shared semantic boundary.

    Passing a JSON string treats it as raw JSON source, preserving duplicate
    members and integer spelling until the Rust parser can validate them.
    """

    if isinstance(value, str):
        return _execute("canonicalize_semantic_json", value_json=value)
    return _execute("canonicalize_semantic_json", value=value)


def calculate_semantic_contract_fingerprint(
    definition: SemanticContractVersion | Mapping[str, Any],
) -> SemanticOperationResult:
    """Calculate an immutable semantic-contract fingerprint in explicit calculate mode."""

    wire = (
        definition.to_wire()
        if isinstance(definition, SemanticContractVersion)
        else dict(definition)
    )
    return _execute("fingerprint_semantic_contract", definition=wire, mode="calculate")


def verify_semantic_contract(
    definition: SemanticContractVersion | Mapping[str, Any],
) -> SemanticOperationResult:
    """Verify the declared fingerprint of an immutable semantic contract."""

    wire = (
        definition.to_wire()
        if isinstance(definition, SemanticContractVersion)
        else dict(definition)
    )
    return _execute("fingerprint_semantic_contract", definition=wire, mode="verify")


def validate_semantic_resource_closure(
    definition: SemanticContractVersion | Mapping[str, Any],
    resources: Sequence[Mapping[str, Any]],
) -> SemanticOperationResult:
    """Validate that every manifest resource is supplied and digest-correct."""

    wire = (
        definition.to_wire()
        if isinstance(definition, SemanticContractVersion)
        else dict(definition)
    )
    return _execute(
        "validate_semantic_resource_closure",
        definition=wire,
        resources=[dict(item) for item in resources],
    )


def compose_semantic_contract_set(
    contracts: Sequence[SemanticContractVersion | Mapping[str, Any]],
) -> SemanticOperationResult:
    """Compose SCF references into the Slice B set fingerprint primitive."""

    wire = []
    for item in contracts:
        value = item.to_wire() if isinstance(item, SemanticContractVersion) else dict(item)
        wire.append(
            {
                key: value[key]
                for key in (
                    "semanticContractFamily",
                    "semanticContractVersion",
                    "semanticContractFingerprint",
                )
                if key in value
            }
        )
    return _execute("compose_semantic_contract_set", contracts=wire)


def _load_definition(name: str) -> SemanticContractVersion:
    resource = resources.files("adr_kit.semantic_contract.v1_0").joinpath(name)
    value = json.loads(resource.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError(f"semantic contract definition is not an object: {name}")
    return SemanticContractVersion.from_wire(value)


def list_semantic_contracts() -> tuple[SemanticContractVersion, ...]:
    """Return the bundled immutable definitions in deterministic family order."""

    return tuple(
        sorted(
            (
                _load_definition(name)
                for name in (
                    "architecture-interpretation.json",
                    "normative-semantics.json",
                    "normalized-model.json",
                )
            ),
            key=lambda item: item.semantic_contract_family,
        )
    )


def get_semantic_contract(family: str, version: str) -> SemanticContractVersion:
    """Load one bundled immutable definition using an exact caller version."""

    for contract in list_semantic_contracts():
        if (
            contract.semantic_contract_family == family
            and contract.semantic_contract_version == version
        ):
            return contract
    raise LookupError(f"Unsupported semantic contract: {family}:{version}")


def load_semantic_resource(key: str) -> Any:
    """Load one bundled resource by canonical key for closure verification."""

    parts = key.split("/")
    if len(parts) < 3 or parts[1] not in {"1.0", "1.5", "1.6", "2.3"}:
        raise LookupError(f"Unsupported semantic resource: {key}")
    package = resources.files("adr_kit.semantic_contract.v1_0.resources")
    candidates = [f"{key.replace('/', '-')}.json"]
    if len(parts) == 3:
        candidates.append(f"{parts[0]}-{parts[2]}.json")
    for name in candidates:
        resource = package.joinpath(name)
        if resource.is_file():
            return json.loads(resource.read_text(encoding="utf-8"))
    raise LookupError(f"Bundled semantic resource is missing: {key}")


__all__ = [
    "SCF_SCHEME",
    "SCS_SCHEME",
    "SemanticContractVersion",
    "SemanticOperationResult",
    "SemanticResourceDependency",
    "SemanticResourceManifestEntry",
    "calculate_semantic_contract_fingerprint",
    "canonicalize_semantic_json",
    "compose_semantic_contract_set",
    "get_semantic_contract",
    "list_semantic_contracts",
    "load_semantic_resource",
    "validate_semantic_resource_closure",
    "verify_semantic_contract",
]
