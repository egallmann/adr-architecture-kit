"""Validation helpers for implementation attribution evidence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Mapping, Protocol, cast

from adr_kit.decorators import enforces, enforces_invariant, implements, implements_adr
from adr_kit.identity import UUIDV7_PATTERN
from adr_kit.models import (
    ImplementationAttributionEvidence,
    ImplementationAttributionEvidenceV15,
    ImplementationAttributionEvidenceV16,
    NormalizedArchitectureModel,
    NormalizedEntityRegistry,
)
from adr_kit.models.v2_0 import NormalizedArchitectureModelV2, NormalizedEntityV2
from adr_kit.repository.semantic_adapter import coerce_to_normalized_model
from adr_kit.schema.contract_validation import ContractProfile
from adr_kit.semantic_attribution.normalize import collect_duplicate_errors, semantic_records
from adr_kit.semantic_attribution.vocabulary import allowed_target_entity_types

ImplementationAttributionSeverity = Literal["error", "warning"]
ImplementationAttributionOutcome = Literal["compliant", "non_compliant"]

INSUFFICIENT_V15_CONTEXT = (
    "v1.5 semantic attribution validation requires architecture context capable of "
    "canonical UUID lookup and resolved entity typing "
    "(ArchitectureRepository or normalized model 2.0)"
)


class _UuidLookup(Protocol):
    def find_entity_by_uuid(self, uuid: str) -> Any | None: ...

    def find_entity_by_alias_id(self, alias_id: str) -> Any | None: ...


@dataclass(frozen=True)
class ImplementationAttributionIssue:
    severity: ImplementationAttributionSeverity
    path: str
    message: str


@dataclass(frozen=True)
class ImplementationAttributionValidationResult:
    profile: ContractProfile
    outcome: ImplementationAttributionOutcome
    issues: tuple[ImplementationAttributionIssue, ...]

    @property
    def error_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == "warning")

    @property
    def is_valid(self) -> bool:
        return self.error_count == 0


def _adr_status_map_from_v2(model: NormalizedArchitectureModelV2) -> dict[str, str]:
    """Index ADR status by both alias_id and UUID for attribution citations."""
    result: dict[str, str] = {}
    for entity in model.entities:
        if not isinstance(entity, NormalizedEntityV2) or entity.entity_type != "adr":
            continue
        status = str(entity.metadata.get("status") or entity.lifecycle_stage)
        result[entity.alias_id] = status
        result[entity.id] = status
    return result


def _resolve_adr_status_map(
    entity_registry: (
        NormalizedEntityRegistry
        | NormalizedArchitectureModel
        | NormalizedArchitectureModelV2
        | Mapping[str, str]
        | object
    ),
) -> dict[str, str]:
    get_model_v2 = getattr(entity_registry, "get_model_v2", None)
    model_version = getattr(entity_registry, "model_version", None)
    if callable(get_model_v2) and model_version == "2.0":
        return _adr_status_map_from_v2(get_model_v2())
    get_model = getattr(entity_registry, "get_model", None)
    if callable(get_model) and not isinstance(entity_registry, Mapping):
        loaded = get_model()
        if isinstance(loaded, NormalizedArchitectureModelV2):
            return _adr_status_map_from_v2(loaded)
        if isinstance(loaded, NormalizedArchitectureModel):
            return loaded.adr_status_map()
    if isinstance(entity_registry, Mapping) and not hasattr(entity_registry, "entities"):
        return {str(key): str(value) for key, value in entity_registry.items()}
    if isinstance(entity_registry, NormalizedArchitectureModelV2):
        return _adr_status_map_from_v2(entity_registry)
    model = coerce_to_normalized_model(
        entity_registry,  # type: ignore[arg-type]
        fingerprint="implementation-attribution-validation",
        generator="implementation-attribution-validation",
        extraction_phase="implementation_attribution_validation.coerce_model",
    )
    return model.adr_status_map()


class _ModelV2Lookup:
    def __init__(self, model: NormalizedArchitectureModelV2) -> None:
        self._by_uuid = {entity.id: entity for entity in model.entities}
        self._by_alias: dict[str, list[NormalizedEntityV2]] = {}
        for entity in model.entities:
            self._by_alias.setdefault(entity.alias_id, []).append(entity)

    def find_entity_by_uuid(self, uuid: str) -> NormalizedEntityV2 | None:
        return self._by_uuid.get(uuid)

    def find_entity_by_alias_id(self, alias_id: str) -> NormalizedEntityV2 | None:
        matches = self._by_alias.get(alias_id, [])
        if not matches:
            return None
        if len(matches) > 1:
            raise ValueError(f"Ambiguous alias_id {alias_id!r}: matches {len(matches)} entities")
        return matches[0]


def _uuid_lookup(architecture_context: object) -> _UuidLookup | None:
    if hasattr(architecture_context, "find_entity_by_uuid") and hasattr(
        architecture_context, "find_entity_by_alias_id"
    ):
        return cast(_UuidLookup, architecture_context)
    if isinstance(architecture_context, NormalizedArchitectureModelV2):
        return _ModelV2Lookup(architecture_context)
    return None


def _entity_status(entity: Any) -> str:
    metadata = getattr(entity, "metadata", None)
    if isinstance(metadata, Mapping) and metadata.get("status"):
        return str(metadata["status"])
    return str(getattr(entity, "lifecycle_stage", "active"))


def _entity_type(entity: Any) -> str:
    return str(getattr(entity, "entity_type"))


@implements_adr("ADR-L-0004", "ADR-L-0013")
@enforces_invariant("INV-0027", "INV-0028", "INV-0029")
@implements("019ffdba-3c42-7f40-b339-204a447bec81")
@enforces("019ffdba-3c42-7c85-a63f-689e71c5236a")
def validate_implementation_attribution_evidence(
    architecture_context: (
        NormalizedEntityRegistry
        | NormalizedArchitectureModel
        | NormalizedArchitectureModelV2
        | Mapping[str, str]
        | object
    ),
    evidence: (
        ImplementationAttributionEvidence
        | ImplementationAttributionEvidenceV15
        | ImplementationAttributionEvidenceV16
    ),
    *,
    profile: ContractProfile = "greenfield",
) -> ImplementationAttributionValidationResult:
    """Validate implementation attribution claims against canonical ADR state."""
    if isinstance(
        evidence, (ImplementationAttributionEvidenceV15, ImplementationAttributionEvidenceV16)
    ):
        return _validate_v15(architecture_context, evidence, profile=profile)
    return _validate_legacy(architecture_context, evidence, profile=profile)


def _validate_legacy(
    architecture_context: (
        NormalizedEntityRegistry
        | NormalizedArchitectureModel
        | NormalizedArchitectureModelV2
        | Mapping[str, str]
        | object
    ),
    evidence: ImplementationAttributionEvidence,
    *,
    profile: ContractProfile,
) -> ImplementationAttributionValidationResult:
    issues: list[ImplementationAttributionIssue] = []
    adr_status_by_id = _resolve_adr_status_map(architecture_context)

    for index, record in enumerate(evidence.records):
        if not record.attributed_adrs:
            severity: ImplementationAttributionSeverity = (
                "error" if profile == "greenfield" else "warning"
            )
            issues.append(
                ImplementationAttributionIssue(
                    severity=severity,
                    path=f"records[{index}].attributed_adrs",
                    message="implementation artifact is missing required architecture attribution",
                )
            )
            continue

        for adr_index, adr_id in enumerate(record.attributed_adrs):
            status = adr_status_by_id.get(adr_id)
            if status is None:
                issues.append(
                    ImplementationAttributionIssue(
                        severity="error",
                        path=f"records[{index}].attributed_adrs[{adr_index}]",
                        message=f"referenced ADR does not exist: {adr_id}",
                    )
                )
                continue
            if status == "superseded":
                issues.append(
                    ImplementationAttributionIssue(
                        severity="warning",
                        path=f"records[{index}].attributed_adrs[{adr_index}]",
                        message=f"referenced ADR is superseded: {adr_id}",
                    )
                )

    outcome: ImplementationAttributionOutcome = (
        "non_compliant" if any(issue.severity == "error" for issue in issues) else "compliant"
    )
    return ImplementationAttributionValidationResult(
        profile=profile,
        outcome=outcome,
        issues=tuple(issues),
    )


def _validate_v15(
    architecture_context: object,
    evidence: ImplementationAttributionEvidenceV15 | ImplementationAttributionEvidenceV16,
    *,
    profile: ContractProfile,
) -> ImplementationAttributionValidationResult:
    issues: list[ImplementationAttributionIssue] = []
    lookup = _uuid_lookup(architecture_context)
    if lookup is None:
        return ImplementationAttributionValidationResult(
            profile=profile,
            outcome="non_compliant",
            issues=(
                ImplementationAttributionIssue(
                    severity="error",
                    path="architecture_context",
                    message=INSUFFICIENT_V15_CONTEXT,
                ),
            ),
        )

    for message in collect_duplicate_errors(evidence):
        issues.append(
            ImplementationAttributionIssue(severity="error", path="records", message=message)
        )

    for index, record in enumerate(semantic_records(evidence)):
        if not record.claims:
            severity: ImplementationAttributionSeverity = (
                "error" if profile == "greenfield" else "warning"
            )
            issues.append(
                ImplementationAttributionIssue(
                    severity=severity,
                    path=f"records[{index}].claims",
                    message="implementation artifact is missing required architecture attribution",
                )
            )
            continue
        for claim_index, claim in enumerate(record.claims):
            path = f"records[{index}].claims[{claim_index}]"
            if (
                evidence.schema_version == "1.6"
                and claim.relationship == "enforces"
                and claim.confidence != "declared"
            ):
                issues.append(
                    ImplementationAttributionIssue(
                        severity="error",
                        path=f"{path}.confidence",
                        message="v1.6 enforces claims require confidence declared",
                    )
                )
                continue
            target = claim.target_entity_id
            if not UUIDV7_PATTERN.match(target):
                issues.append(
                    ImplementationAttributionIssue(
                        severity="error",
                        path=f"{path}.target_entity_id",
                        message=f"v{evidence.schema_version} target_entity_id must be a lowercase UUIDv7, not an alias: {target}",
                    )
                )
                continue
            entity = lookup.find_entity_by_uuid(target)
            if entity is None:
                issues.append(
                    ImplementationAttributionIssue(
                        severity="error",
                        path=f"{path}.target_entity_id",
                        message=f"referenced architecture entity does not exist: {target}",
                    )
                )
                continue
            resolved_type = _entity_type(entity)
            if (
                claim.asserted_target_entity_type is not None
                and claim.asserted_target_entity_type != resolved_type
            ):
                issues.append(
                    ImplementationAttributionIssue(
                        severity="error",
                        path=f"{path}.asserted_target_entity_type",
                        message=(
                            f"asserted_target_entity_type {claim.asserted_target_entity_type} "
                            f"does not match resolved type {resolved_type}"
                        ),
                    )
                )
                continue
            allowed = allowed_target_entity_types(claim.relationship)
            if resolved_type not in allowed:
                issues.append(
                    ImplementationAttributionIssue(
                        severity="error",
                        path=f"{path}.relationship",
                        message=(
                            f"relationship {claim.relationship} does not admit resolved "
                            f"target entity type {resolved_type}"
                        ),
                    )
                )
                continue
            status = _entity_status(entity)
            if status in {"superseded", "deprecated"}:
                issues.append(
                    ImplementationAttributionIssue(
                        severity="warning",
                        path=f"{path}.target_entity_id",
                        message=f"referenced architecture entity is {status}: {target}",
                    )
                )

    outcome: ImplementationAttributionOutcome = (
        "non_compliant" if any(issue.severity == "error" for issue in issues) else "compliant"
    )
    return ImplementationAttributionValidationResult(
        profile=profile,
        outcome=outcome,
        issues=tuple(issues),
    )
