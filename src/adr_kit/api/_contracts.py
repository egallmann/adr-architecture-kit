"""Immutable public contracts for the narrow ADR Kit SDK."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import MappingProxyType
from typing import Literal, Mapping, cast

from ..models import NormalizedArchitectureModel
from ..models.v2_1 import NormalizedArchitectureModelV21
from ..models.v2_2 import NormalizedArchitectureModelV22
from ..models.v2_0 import NormalizedArchitectureModelV2
from ..models.v2_3 import NormalizedArchitectureModelV23
from ..semantic_contract import SemanticResourceDependency
from ._errors import InvalidRequestError

API_CONTRACT_VERSION = "1.0"
VALIDATION_MODES = ("complete", "structural")
ARTIFACT_GROUPS = ("registries", "manifest", "markdown")
PROMOTION_CONTRACT_VERSIONS = ("ste.design_journal.promotion_contract/v0.1",)
CONTRACT_PROFILES = ("greenfield", "brownfield", "migration")


def _normalize_project_root(value: str | Path) -> Path:
    root = Path(value).expanduser().resolve()
    if not root.is_dir():
        raise InvalidRequestError(f"Project root is not a directory: {root}")
    if not (root / "PROJECT.yaml").is_file():
        raise InvalidRequestError(f"Project root does not contain PROJECT.yaml: {root}")
    if not (root / "adrs").is_dir():
        raise InvalidRequestError(f"Project root does not contain adrs/: {root}")
    return root


def _normalize_metadata_project_root(value: str | Path) -> Path:
    root = Path(value).expanduser().resolve()
    if not root.is_dir():
        raise InvalidRequestError(f"Project root is not a directory: {root}")
    if not (root / "PROJECT.yaml").is_file():
        raise InvalidRequestError(f"Project root does not contain PROJECT.yaml: {root}")
    return root


def _normalize_timestamp(value: str | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or "T" not in value or not value.endswith("Z"):
        raise InvalidRequestError("timestamp must be an RFC 3339 UTC value ending in Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise InvalidRequestError("timestamp must be an RFC 3339 UTC value ending in Z") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise InvalidRequestError("timestamp must use the UTC Z designator")
    return value


@dataclass(frozen=True, slots=True)
class Diagnostic:
    """Stable diagnostic representation independent of validator/compiler types."""

    severity: Literal["info", "warning", "error"]
    code: str
    message: str
    path: str | None = None
    source_ref: str | None = None
    field: str | None = None


AuthoringPolicyStatus = Literal["defined", "deferred", "not_applicable"]


@dataclass(frozen=True, slots=True)
class AuthoringTypeKey:
    """Exact, case-sensitive key for one ADC authoring type."""

    kind: Literal["adr", "entity", "relationship", "value"]
    name: str


@dataclass(frozen=True, slots=True)
class AuthoringParentConstraint:
    """One canonical composition-parent constraint from an ADC policy."""

    kind: Literal["adr", "entity", "relationship", "value"]
    name: str
    min_occurs: int
    max_occurs: int | None


@dataclass(frozen=True, slots=True)
class AuthoringPolicy:
    """Immutable ADC policy projection preserving maturity and policy values."""

    status: AuthoringPolicyStatus
    mode: str | None = None
    values: tuple[str, ...] = ()
    allowed_parents: tuple[AuthoringParentConstraint, ...] = ()
    owner: str | None = None


@dataclass(frozen=True, slots=True)
class AuthoringDiscriminator:
    """Immutable discriminator semantics for one authoring type."""

    mode: str
    field: str | None
    value: str | None


@dataclass(frozen=True, slots=True)
class AuthoringTypeSummary:
    """Consumer-facing summary returned by ADC type enumeration."""

    key: AuthoringTypeKey
    display_name: str
    description: str


@dataclass(frozen=True, slots=True)
class AuthoringTypeList:
    """Immutable, version-qualified result for ADC type enumeration."""

    contract_version: str
    types: tuple[AuthoringTypeSummary, ...]


@dataclass(frozen=True, slots=True)
class AuthoringContractDescription:
    """Immutable public projection of the ADC discovery contract description."""

    contract_id: str
    contract_version: str
    defined_capabilities: tuple[str, ...]
    discovery_operations: tuple[str, ...]
    type_kinds: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AuthoringTypeDescriptor:
    """Complete immutable consumer projection of one ADC type descriptor."""

    contract_version: str
    key: AuthoringTypeKey
    display_name: str
    description: str
    authoring_mode: Literal["direct", "embedded", "template"]
    semantic_type_ownership: Literal["adr_kit", "consumer_qualified"]
    discriminator: AuthoringDiscriminator
    input_contract: AuthoringPolicy
    identity_policy: AuthoringPolicy
    composition_policy: AuthoringPolicy
    reference_policy: AuthoringPolicy
    field_ownership_policy: AuthoringPolicy


def _freeze_json(value: object) -> object:
    """Freeze host-owned JSON without assigning it semantic meaning."""

    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze_json(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json(item) for item in value)
    return value


def _thaw_json(value: object) -> object:
    """Return ordinary JSON containers for the WASM transport."""

    if isinstance(value, Mapping):
        return {str(key): _thaw_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_thaw_json(item) for item in value]
    return value


def _require_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InvalidRequestError(f"{field} must be a non-empty string")
    return value


@dataclass(frozen=True, slots=True)
class MaterializationAuthorityProvider:
    """Explicit provider identity supplied by the host; never inferred by core."""

    kind: str
    architecture_namespace: str

    def __post_init__(self) -> None:
        _require_text(self.kind, "authority_provider.kind")
        _require_text(self.architecture_namespace, "authority_provider.architecture_namespace")

    def to_wire(self) -> dict[str, str]:
        return {"kind": self.kind, "architectureNamespace": self.architecture_namespace}


@dataclass(frozen=True, slots=True)
class MaterializationSourceContract:
    """Exact authoring schema binding and closure for one source artifact."""

    version: Literal["1.5", "1.6"]
    schema_resource: SemanticResourceDependency
    resource_closure: tuple[SemanticResourceDependency, ...]
    family: Literal["authoring"] = "authoring"

    @classmethod
    def from_wire(cls, value: Mapping[str, object]) -> "MaterializationSourceContract":
        schema = value.get("schemaResource")
        closure = value.get("resourceClosure")
        if not isinstance(schema, Mapping) or not isinstance(closure, (list, tuple)):
            raise InvalidRequestError("Malformed source contract binding")
        return cls(
            version=cast(Literal["1.5", "1.6"], str(value.get("version", ""))),
            schema_resource=SemanticResourceDependency(
                str(schema.get("canonicalResourceKey", "")),
                str(schema.get("contentDigest", "")),
            ),
            resource_closure=tuple(
                SemanticResourceDependency(
                    str(item.get("canonicalResourceKey", "")),
                    str(item.get("contentDigest", "")),
                )
                for item in closure
                if isinstance(item, Mapping)
            ),
        )

    def __post_init__(self) -> None:
        if self.version not in {"1.5", "1.6"}:
            raise InvalidRequestError(f"Unsupported source contract version: {self.version}")
        if len(self.resource_closure) < 3:
            raise InvalidRequestError("resource_closure must contain at least three resources")

    def to_wire(self) -> dict[str, object]:
        return {
            "family": self.family,
            "version": self.version,
            "schemaResource": self.schema_resource.to_wire(),
            "resourceClosure": [item.to_wire() for item in self.resource_closure],
        }


@dataclass(frozen=True, slots=True)
class MaterializationSourceArtifact:
    """One parsed source document with its explicit content and contract identity."""

    source_ref: str
    artifact_path: str
    content_digest: str
    source_contract: MaterializationSourceContract
    document: Mapping[str, object]

    @classmethod
    def from_wire(cls, value: Mapping[str, object]) -> "MaterializationSourceArtifact":
        contract = value.get("sourceContract")
        document = value.get("document")
        if not isinstance(contract, Mapping) or not isinstance(document, Mapping):
            raise InvalidRequestError("Malformed source artifact")
        return cls(
            source_ref=str(value.get("sourceRef", "")),
            artifact_path=str(value.get("artifactPath", "")),
            content_digest=str(value.get("contentDigest", "")),
            source_contract=MaterializationSourceContract.from_wire(contract),
            document=document,
        )

    def __post_init__(self) -> None:
        _require_text(self.source_ref, "source_ref")
        _require_text(self.artifact_path, "artifact_path")
        if not isinstance(self.content_digest, str) or not self.content_digest.startswith(
            "sha256:"
        ):
            raise InvalidRequestError("content_digest must use the sha256: prefix")
        if not isinstance(self.document, Mapping):
            raise InvalidRequestError("document must be a mapping")
        object.__setattr__(self, "document", _freeze_json(self.document))

    def to_wire(self) -> dict[str, object]:
        return {
            "sourceRef": self.source_ref,
            "artifactPath": self.artifact_path,
            "contentDigest": self.content_digest,
            "sourceContract": self.source_contract.to_wire(),
            "document": _thaw_json(self.document),
        }


@dataclass(frozen=True, slots=True)
class MaterializationSourceBasis:
    """Sealed source identity and parsed artifacts; ``None`` means unavailable."""

    provider_source_identity: str
    source_revision: str
    artifacts: tuple[MaterializationSourceArtifact, ...]
    sealed: Literal[True] = True
    legacy_identity_map: Mapping[str, object] | None = None

    @classmethod
    def from_wire(cls, value: Mapping[str, object]) -> "MaterializationSourceBasis":
        artifacts = value.get("artifacts")
        if not isinstance(artifacts, (list, tuple)):
            raise InvalidRequestError("Malformed source basis")
        legacy = value.get("legacyIdentityMap")
        return cls(
            provider_source_identity=str(value.get("providerSourceIdentity", "")),
            source_revision=str(value.get("sourceRevision", "")),
            artifacts=tuple(
                MaterializationSourceArtifact.from_wire(item)
                for item in artifacts
                if isinstance(item, Mapping)
            ),
            legacy_identity_map=legacy if isinstance(legacy, Mapping) else None,
        )

    def __post_init__(self) -> None:
        if self.sealed is not True:
            raise InvalidRequestError("source_basis.sealed must be True")
        _require_text(self.provider_source_identity, "provider_source_identity")
        _require_text(self.source_revision, "source_revision")
        if not self.artifacts:
            raise InvalidRequestError("source_basis.artifacts must not be empty")
        if self.legacy_identity_map is not None:
            if not isinstance(self.legacy_identity_map, Mapping):
                raise InvalidRequestError("legacy_identity_map must be a mapping or None")
            object.__setattr__(self, "legacy_identity_map", _freeze_json(self.legacy_identity_map))

    def to_wire(self) -> dict[str, object]:
        result: dict[str, object] = {
            "sealed": True,
            "providerSourceIdentity": self.provider_source_identity,
            "sourceRevision": self.source_revision,
            "artifacts": [item.to_wire() for item in self.artifacts],
        }
        if self.legacy_identity_map is not None:
            result["legacyIdentityMap"] = _thaw_json(self.legacy_identity_map)
        return result


@dataclass(frozen=True, slots=True)
class ArchitectureMaterializationRequest:
    """Fully explicit public input to the semantic-core materialization boundary."""

    semantic_contract_set_id: str
    authority_provider: MaterializationAuthorityProvider
    source_basis: MaterializationSourceBasis | None
    direction: Literal["none", "forward", "reverse"]
    use_mode: Literal["new", "historical"]
    profile_id: str

    def __post_init__(self) -> None:
        _require_text(self.semantic_contract_set_id, "semantic_contract_set_id")
        if self.direction not in {"none", "forward", "reverse"}:
            raise InvalidRequestError(f"Unsupported materialization direction: {self.direction}")
        if self.use_mode not in {"new", "historical"}:
            raise InvalidRequestError(f"Unsupported materialization use_mode: {self.use_mode}")
        if self.profile_id != "architecture-materialization@1.0":
            raise InvalidRequestError(f"Unsupported materialization profile: {self.profile_id}")


@dataclass(frozen=True, slots=True)
class MaterializationSemanticBasis:
    semantic_contract_set_id: str | None
    authority_state_fingerprint: str | None


@dataclass(frozen=True, slots=True)
class MaterializationProviderProvenance:
    """Stable evidence identifying the protocol and host binding used."""

    semantic_core_contract_version: str
    package_version: str
    host_binding: str


@dataclass(frozen=True, slots=True)
class MaterializationCapabilityLimitation:
    source_contract: MaterializationSourceContract
    semantic_capability: str
    classification: Literal["not_expressible_by_source_contract"]


@dataclass(frozen=True, slots=True)
class ArchitectureMaterializationResult:
    """Immutable result view; normalized semantics remain owned by semantic-core."""

    request: ArchitectureMaterializationRequest
    success: bool
    outcome: Literal["Materialized", "Rejected", "Unavailable"]
    authority_provider: MaterializationAuthorityProvider | None
    source_basis: MaterializationSourceBasis | None
    source_contract_closure: tuple[MaterializationSourceContract, ...]
    semantic_basis: MaterializationSemanticBasis
    normalized_model: Mapping[str, object] | None
    source_capability_limitations: tuple[MaterializationCapabilityLimitation, ...]
    provider_provenance: MaterializationProviderProvenance | None
    diagnostics: tuple[Diagnostic, ...]
    package_version: str
    api_contract_version: str

    def __post_init__(self) -> None:
        for field_name in (
            "normalized_model",
            "provider_provenance",
        ):
            value = getattr(self, field_name)
            if value is not None:
                object.__setattr__(self, field_name, _freeze_json(value))


@dataclass(frozen=True, slots=True)
class EmbodimentLinkageRequest:
    """Inputs for one read-only embodiment-to-intent projection."""

    project_root: Path
    evidence_path: Path
    profile: Literal["greenfield", "brownfield", "migration"] = "greenfield"

    def __post_init__(self) -> None:
        object.__setattr__(self, "project_root", _normalize_project_root(self.project_root))
        evidence = Path(self.evidence_path).expanduser().resolve()
        if not evidence.is_file():
            raise InvalidRequestError(f"Evidence path is not a readable file: {evidence}")
        object.__setattr__(self, "evidence_path", evidence)
        if self.profile not in {"greenfield", "brownfield", "migration"}:
            raise InvalidRequestError(f"Unsupported attribution profile: {self.profile}")


@dataclass(frozen=True, slots=True)
class AttributionShimRequest:
    """Inputs for a read-only, vocabulary-driven attribution shim projection."""

    language: Literal["python", "typescript"]

    def __post_init__(self) -> None:
        if not isinstance(self.language, str):
            raise InvalidRequestError("Shim language must be a string")
        language = self.language.strip().lower()
        if language not in {"python", "typescript"}:
            raise InvalidRequestError(
                f"Unsupported shim language: {self.language!r} (supported: python, typescript)"
            )
        object.__setattr__(self, "language", language)


@dataclass(frozen=True, slots=True)
class AttributionShimResult:
    """Immutable generated source and its digest returned by the public API."""

    request: AttributionShimRequest
    success: bool
    language: Literal["python", "typescript"]
    content: str
    sha256: str
    diagnostics: tuple[Diagnostic, ...]
    package_version: str
    api_contract_version: str


@dataclass(frozen=True, slots=True)
class LinkageProvenance:
    source_file: str
    extractor: str
    commit: str | None = None
    source_pointer: str | None = None
    start_line: int | None = None
    end_line: int | None = None


@dataclass(frozen=True, slots=True)
class LinkageOccurrence:
    confidence: Literal["declared", "inferred", "heuristic"]
    provenance: LinkageProvenance
    source_language: str | None = None


@dataclass(frozen=True, slots=True)
class EmbodimentIntentLink:
    implementation_entity_id: str
    implementation_entity_type: str
    relationship: Literal["implements", "enforces", "embodies"]
    target_entity_id: str
    target_entity_type: str
    target_alias_id: str
    target_alias_name: str
    target_lifecycle: str
    occurrences: tuple[LinkageOccurrence, ...]
    validation_status: Literal["valid", "warning"]
    diagnostics: tuple[Diagnostic, ...]
    authority_ceiling: str = "validated_derived_evidence"
    graph_admission_status: str = "not_admitted"


@dataclass(frozen=True, slots=True)
class RejectedEmbodimentClaim:
    implementation_entity_id: str
    implementation_entity_type: str
    relationship: str
    target_entity_id: str
    confidence: str
    provenance: LinkageProvenance
    diagnostics: tuple[Diagnostic, ...]
    validation_status: Literal["invalid"] = "invalid"


@dataclass(frozen=True, slots=True)
class EmbodimentLinkageResult:
    request: EmbodimentLinkageRequest
    success: bool
    evidence_schema_version: str
    architecture_fingerprint: str | None
    links: tuple[EmbodimentIntentLink, ...]
    rejected_claims: tuple[RejectedEmbodimentClaim, ...]
    diagnostics: tuple[Diagnostic, ...]
    error_count: int
    warning_count: int
    package_version: str
    api_contract_version: str

    def links_for_implementation(
        self, implementation_entity_id: str
    ) -> tuple[EmbodimentIntentLink, ...]:
        return tuple(
            link for link in self.links if link.implementation_entity_id == implementation_entity_id
        )

    def implementations_for_intent(self, target_entity_id: str) -> tuple[EmbodimentIntentLink, ...]:
        return tuple(link for link in self.links if link.target_entity_id == target_entity_id)

    def links_by_relationship(self, relationship: str) -> tuple[EmbodimentIntentLink, ...]:
        return tuple(link for link in self.links if link.relationship == relationship)


@dataclass(frozen=True, slots=True)
class ValidationRequest:
    """Inputs for validating one explicit ADR repository scope."""

    project_root: Path
    mode: Literal["complete", "structural"] = "complete"
    cross_references: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "project_root", _normalize_project_root(self.project_root))
        if self.mode not in VALIDATION_MODES:
            raise InvalidRequestError(f"Unsupported validation mode: {self.mode}")
        if not isinstance(self.cross_references, bool):
            raise InvalidRequestError("cross_references must be a bool")


@dataclass(frozen=True, slots=True)
class ProjectMetadataValidationRequest:
    """Inputs for validating one scope's PROJECT.yaml metadata."""

    project_root: Path

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "project_root", _normalize_metadata_project_root(self.project_root)
        )


@dataclass(frozen=True, slots=True)
class ContractValidationRequest:
    """Inputs for validating one compiled contract bundle."""

    project_root: Path
    profile: Literal["greenfield", "brownfield", "migration"] = "greenfield"
    max_sentinel_fields: int | None = None
    max_non_complete_entities: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "project_root", _normalize_project_root(self.project_root))
        if self.profile not in CONTRACT_PROFILES:
            raise InvalidRequestError(f"Unsupported contract validation profile: {self.profile}")
        for field_name in ("max_sentinel_fields", "max_non_complete_entities"):
            value = getattr(self, field_name)
            if value is not None and (isinstance(value, bool) or not isinstance(value, int)):
                raise InvalidRequestError(f"{field_name} must be a non-negative integer or None")
            if value is not None and value < 0:
                raise InvalidRequestError(f"{field_name} must be a non-negative integer or None")


@dataclass(frozen=True, slots=True)
class GeneratedDocsValidationRequest:
    """Inputs for validating one scope's generated documentation artifacts."""

    project_root: Path

    def __post_init__(self) -> None:
        object.__setattr__(self, "project_root", _normalize_project_root(self.project_root))


@dataclass(frozen=True, slots=True)
class CompilationRequest:
    """Inputs for one restricted authoring compilation."""

    project_root: Path
    artifact_groups: tuple[str, ...] = ARTIFACT_GROUPS
    write: bool = False
    output_root: Path | None = None
    timestamp: str | None = None
    check: bool = False
    include_system_overview: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "project_root", _normalize_project_root(self.project_root))
        groups = tuple(self.artifact_groups)
        if not groups:
            raise InvalidRequestError("artifact_groups must not be empty")
        if len(groups) != len(set(groups)):
            raise InvalidRequestError("artifact_groups must not contain duplicates")
        unknown = sorted(set(groups) - set(ARTIFACT_GROUPS))
        if unknown:
            raise InvalidRequestError(f"Unsupported artifact groups: {', '.join(unknown)}")
        canonical_groups = tuple(group for group in ARTIFACT_GROUPS if group in groups)
        object.__setattr__(self, "artifact_groups", canonical_groups)
        if not isinstance(self.write, bool):
            raise InvalidRequestError("write must be a bool")
        if not isinstance(self.check, bool):
            raise InvalidRequestError("check must be a bool")
        if not isinstance(self.include_system_overview, bool):
            raise InvalidRequestError("include_system_overview must be a bool")
        if self.check and self.write:
            raise InvalidRequestError("check=True and write=True are mutually exclusive")
        if self.output_root is not None and not self.write:
            raise InvalidRequestError("output_root requires write=True")
        if self.output_root is not None:
            object.__setattr__(self, "output_root", Path(self.output_root).expanduser().resolve())
        object.__setattr__(self, "timestamp", _normalize_timestamp(self.timestamp))


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """Completed validation outcome for one repository scope."""

    request: ValidationRequest
    success: bool
    validated_files: tuple[str, ...]
    diagnostics: tuple[Diagnostic, ...]
    error_count: int
    warning_count: int
    package_version: str
    api_contract_version: str


@dataclass(frozen=True, slots=True)
class ProjectMetadataValidationResult:
    """Completed PROJECT.yaml metadata validation outcome."""

    request: ProjectMetadataValidationRequest
    success: bool
    diagnostics: tuple[Diagnostic, ...]
    package_version: str
    api_contract_version: str


@dataclass(frozen=True, slots=True)
class ContractValidationIssue:
    """Immutable public view of one compiled-contract validation issue."""

    path: str
    message: str


@dataclass(frozen=True, slots=True)
class ContractValidationResult:
    """Completed compiled-contract validation outcome."""

    request: ContractValidationRequest
    success: bool
    profile: Literal["greenfield", "brownfield", "migration"]
    outcome: Literal["compliant", "sentinel_compliant", "non_compliant"]
    sentinel_field_count: int
    non_complete_entity_count: int
    completeness_counts: Mapping[str, int]
    issues: tuple[ContractValidationIssue, ...]
    diagnostics: tuple[Diagnostic, ...]
    package_version: str
    api_contract_version: str


@dataclass(frozen=True, slots=True)
class GeneratedArtifactValidation:
    """Immutable public view of one generated-artifact validation result."""

    artifact_path: str
    artifact_kind: str
    status: Literal[
        "valid",
        "stale_generated_output",
        "tampered_generated_output",
        "missing_or_malformed_integrity_header",
        "unsupported_artifact_kind",
    ]
    reason_code: str
    expected_source_hash: str | None = None
    actual_source_hash: str | None = None
    expected_rendered_hash: str | None = None
    actual_rendered_hash: str | None = None
    notes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class GeneratedDocsValidationResult:
    """Completed generated-document integrity validation outcome."""

    request: GeneratedDocsValidationRequest
    success: bool
    artifacts: tuple[GeneratedArtifactValidation, ...]
    diagnostics: tuple[Diagnostic, ...]
    package_version: str
    api_contract_version: str


@dataclass(frozen=True, slots=True)
class ArtifactDescriptor:
    """Immutable SDK view of one emitted authoring artifact."""

    artifact_id: str
    group: str
    kind: str
    relative_path: str
    written_path: Path | None
    content: bytes
    size_bytes: int
    sha256: str
    integrity_header: str | None


@dataclass(frozen=True, slots=True)
class CompilationResult:
    """Completed restricted authoring compilation outcome."""

    request: CompilationRequest
    success: bool
    partial: bool
    artifacts: tuple[ArtifactDescriptor, ...]
    diagnostics: tuple[Diagnostic, ...]
    model: (
        NormalizedArchitectureModel
        | NormalizedArchitectureModelV2
        | NormalizedArchitectureModelV21
        | NormalizedArchitectureModelV22
        | NormalizedArchitectureModelV23
        | None
    )
    fingerprint: str | None
    source_files: int
    parse_errors: int
    entities_extracted: int
    relationships_derived: int
    unresolved_detected: int
    artifacts_emitted: int
    package_version: str
    api_contract_version: str


@dataclass(frozen=True, slots=True)
class CapabilityManifest:
    """Deterministic, local description of the supported SDK boundary."""

    package_version: str
    api_contract_version: str
    operations: tuple[str, ...]
    supported_promotion_contract_versions: tuple[str, ...]
    validation_modes: tuple[str, ...]
    artifact_groups: tuple[str, ...]
    supported_adr_schema_versions: tuple[str, ...]
    stable_adr_schema_versions: tuple[str, ...]
    provisional_adr_schema_versions: tuple[str, ...]
    normalized_model_schema_version: str
    supported_normalized_model_schema_versions: tuple[str, ...]
    supported_evidence_attribution_versions: tuple[str, ...]
    preferred_evidence_attribution_version: str
    supported_authoring_domain_versions: tuple[str, ...]
    preferred_authoring_domain_version: str
    authoring_capabilities: tuple[str, ...]
    host_operations: tuple[str, ...] = (
        "capabilities",
        "validate_project_metadata",
        "validate_contract",
        "open_repository",
        "open_provider_registry",
        "build_embodiment_linkage",
        "list_semantic_contracts",
        "get_semantic_contract",
        "canonicalize_semantic_json",
        "calculate_semantic_contract_fingerprint",
        "verify_semantic_contract",
        "validate_semantic_resource_closure",
        "compose_semantic_contract_set",
    )
    pending_host_operations: tuple[str, ...] = ()
    browser_operations: tuple[str, ...] = ("capabilities",)

    def as_dict(self) -> dict[str, object]:
        """Return the ordered JSON-safe Phase 1 serialization contract."""

        return {
            key: list(value) if isinstance(value, tuple) else value
            for key, value in asdict(self).items()
        }
