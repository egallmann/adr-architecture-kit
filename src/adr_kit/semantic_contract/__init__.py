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
from pathlib import Path
from typing import Any, Mapping, Sequence
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
    diagnostics: tuple[Any, ...]
    canonical_preimage_json: str | None = None
    canonical_preimage_hex: str | None = None
    fingerprint: str | None = None
    semantic_contract_fingerprint: str | None = None
    semantic_contract_set_id: str | None = None
    mode: str | None = None
    closure_valid: bool | None = None
    no_op: bool | None = None
    emitted_immutable_artifacts: tuple[Mapping[str, Any], ...] = ()
    mutable_changes: tuple[Mapping[str, Any], ...] = ()
    resolved: Mapping[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class SemanticContractProfile:
    """An immutable profile that selects members without redefining meaning."""

    profile_family: str
    profile_version: str
    profile_id: str
    participating_families: tuple[Mapping[str, Any], ...]
    operations: tuple[str, ...]
    selection_purposes: tuple[str, ...]

    @classmethod
    def from_wire(cls, value: Mapping[str, Any]) -> "SemanticContractProfile":
        return cls(
            profile_family=str(value["profileFamily"]),
            profile_version=str(value["profileVersion"]),
            profile_id=str(value["profileId"]),
            participating_families=tuple(value["participatingFamilies"]),
            operations=tuple(str(item) for item in value["operations"]),
            selection_purposes=tuple(str(item) for item in value["selectionPurposes"]),
        )

    def to_wire(self) -> dict[str, Any]:
        return {
            "profileFamily": self.profile_family,
            "profileVersion": self.profile_version,
            "profileId": self.profile_id,
            "participatingFamilies": [dict(item) for item in self.participating_families],
            "operations": list(self.operations),
            "selectionPurposes": list(self.selection_purposes),
        }


def _result(value: Mapping[str, Any]) -> SemanticOperationResult:
    # Import lazily so ``import adr_kit.semantic_contract`` does not first
    # initialize the broader ``adr_kit.api`` facade and create a cycle.
    from ..api._contracts import Diagnostic

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
        semantic_contract_set_id=value.get(
            "semanticContractSetId", value.get("semantic_contract_set_id")
        ),
        mode=value.get("mode"),
        closure_valid=value.get("closure_valid"),
        no_op=value.get("noOp"),
        emitted_immutable_artifacts=tuple(
            item for item in value.get("emittedImmutableArtifacts", []) if isinstance(item, Mapping)
        ),
        mutable_changes=tuple(
            item for item in value.get("mutableChanges", []) if isinstance(item, Mapping)
        ),
        resolved=value.get("resolved") if isinstance(value.get("resolved"), Mapping) else None,
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


def _load_json_asset(relative: str) -> Any:
    package = resources.files("adr_kit.semantic_contract.v1_0")
    resource = package.joinpath(relative.replace("/", "/"))
    return json.loads(resource.read_text(encoding="utf-8"))


def list_semantic_contract_profiles() -> tuple[SemanticContractProfile, ...]:
    """Return governed profiles bundled with this host distribution."""

    profile = _load_json_asset("profiles/architecture-materialization-1.0.json")
    return (SemanticContractProfile.from_wire(profile),)


def get_semantic_contract_profile(profile_id: str) -> SemanticContractProfile:
    """Select one exact profile; no current/default alias is accepted."""

    for profile in list_semantic_contract_profiles():
        if profile.profile_id == profile_id:
            return profile
    raise LookupError(f"Unsupported semantic-contract profile: {profile_id}")


def validate_semantic_contract_profile(
    profile: SemanticContractProfile | Mapping[str, Any],
) -> SemanticOperationResult:
    wire = profile.to_wire() if isinstance(profile, SemanticContractProfile) else dict(profile)
    return _execute("validate_semantic_contract_profile", profile=wire)


def validate_semantic_contract_qualification(
    profile: SemanticContractProfile | Mapping[str, Any],
    members: Sequence[Mapping[str, Any]],
    operation: str,
    qualification: Mapping[str, Any],
    direction: str = "none",
) -> SemanticOperationResult:
    profile_wire = (
        profile.to_wire() if isinstance(profile, SemanticContractProfile) else dict(profile)
    )
    return _execute(
        "validate_semantic_contract_qualification",
        profile=profile_wire,
        members=[dict(item) for item in members],
        targetOperation=operation,
        direction=direction,
        qualification=dict(qualification),
    )


def preview_semantic_contract_set_assembly(
    request: Mapping[str, Any],
) -> SemanticOperationResult:
    """Preview deterministic assembly without performing filesystem writes."""

    return _execute("assemble_semantic_contract_set", **dict(request))


def validate_semantic_contract_corpus(request: Mapping[str, Any]) -> SemanticOperationResult:
    """Validate every retained immutable definition, set, and policy record."""

    return _execute("validate_semantic_contract_corpus", **dict(request))


def resolve_current_semantic_contract_set(request: Mapping[str, Any]) -> SemanticOperationResult:
    """Resolve a floating current pointer to one immutable exact SCS identity."""

    return _execute("resolve_current_semantic_contract_set", **dict(request))


def list_semantic_contract_sets() -> tuple[Mapping[str, Any], ...]:
    """List immutable bundled SCS artifacts without treating catalog state as identity."""

    package = resources.files("adr_kit.semantic_contract.v1_0").joinpath("sets")
    return tuple(
        json.loads(item.read_text(encoding="utf-8"))
        for item in sorted(package.iterdir(), key=lambda item: item.name)
        if item.name.endswith(".json")
    )


def apply_semantic_contract_set_assembly(
    repository_root: str | Path,
    request: Mapping[str, Any],
) -> dict[str, Any]:
    """Apply only the core-approved missing immutable artifacts.

    The host performs the requested filesystem mutation only after the shared
    core reports success. Existing immutable bytes are never overwritten.
    """

    result = preview_semantic_contract_set_assembly(request)
    wire = dict(request)
    if not result.success:
        return {"success": False, "no_op": False, "result": result}
    set_id = result.semantic_contract_set_id or ""
    root = Path(repository_root)
    target = root / "semantic-contract" / "sets" / f"{set_id.replace(':', '-')}.json"
    emitted = tuple(
        value
        for value in (getattr(result, "emitted_immutable_artifacts", None) or ())
        if isinstance(value, Mapping)
    )
    # Results are intentionally returned as the typed core view; this fallback
    # supports older result DTOs while keeping the apply boundary explicit.
    if not emitted and not bool(wire.get("retainedSets")) and set_id:
        members = wire.get("requestedMembers", ())
        emitted = ({"scsScheme": SCS_SCHEME, "semanticContractSetId": set_id, "members": members},)
    created: list[str] = []
    if not result.semantic_contract_set_id:
        return {"success": False, "no_op": False, "result": result}
    if emitted:
        content = json.dumps(emitted[0], ensure_ascii=False, indent=2) + "\n"
        if target.exists():
            if target.read_text(encoding="utf-8") != content:
                raise ValueError("refusing to overwrite an immutable SCS artifact")
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8", newline="\n")
            created.append(str(target))
    return {
        "success": True,
        "no_op": not created,
        "created_artifacts": tuple(created),
        "result": result,
    }


def compose_semantic_contract_set(
    contracts: Sequence[SemanticContractVersion | Mapping[str, Any]],
) -> SemanticOperationResult:
    """Compose SCF references through the shared SCS identity primitive."""

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
    "SemanticContractProfile",
    "SemanticOperationResult",
    "SemanticResourceDependency",
    "SemanticResourceManifestEntry",
    "calculate_semantic_contract_fingerprint",
    "canonicalize_semantic_json",
    "compose_semantic_contract_set",
    "list_semantic_contract_profiles",
    "get_semantic_contract_profile",
    "validate_semantic_contract_profile",
    "validate_semantic_contract_qualification",
    "preview_semantic_contract_set_assembly",
    "apply_semantic_contract_set_assembly",
    "validate_semantic_contract_corpus",
    "list_semantic_contract_sets",
    "resolve_current_semantic_contract_set",
    "get_semantic_contract",
    "list_semantic_contracts",
    "load_semantic_resource",
    "validate_semantic_resource_closure",
    "verify_semantic_contract",
]
