"""Immutable public contracts for the narrow ADR Kit SDK."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Mapping

from ..models import NormalizedArchitectureModel
from ..models.v2_1 import NormalizedArchitectureModelV21
from ..models.v2_2 import NormalizedArchitectureModelV22
from ..models.v2_0 import NormalizedArchitectureModelV2
from ..models.v2_3 import NormalizedArchitectureModelV23
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
