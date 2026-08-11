"""Validation helpers for implementation attribution evidence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Mapping

from adr_kit.decorators import enforces_invariant, implements_adr
from adr_kit.models import (
    ImplementationAttributionEvidence,
    NormalizedArchitectureModel,
    NormalizedEntityRegistry,
)
from adr_kit.models.v2_0 import NormalizedArchitectureModelV2, NormalizedEntityV2
from adr_kit.repository.semantic_adapter import coerce_to_normalized_model
from adr_kit.schema.contract_validation import ContractProfile

ImplementationAttributionSeverity = Literal["error", "warning"]
ImplementationAttributionOutcome = Literal["compliant", "non_compliant"]


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
    ),
) -> dict[str, str]:
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


@implements_adr("ADR-L-0004", "ADR-L-0013")
@enforces_invariant("INV-0027", "INV-0028", "INV-0029")
def validate_implementation_attribution_evidence(
    entity_registry: (
        NormalizedEntityRegistry
        | NormalizedArchitectureModel
        | NormalizedArchitectureModelV2
        | Mapping[str, str]
    ),
    evidence: ImplementationAttributionEvidence,
    *,
    profile: ContractProfile = "greenfield",
) -> ImplementationAttributionValidationResult:
    """Validate implementation attribution claims against canonical ADR state."""
    issues: list[ImplementationAttributionIssue] = []
    adr_status_by_id = _resolve_adr_status_map(entity_registry)

    for index, record in enumerate(evidence.records):
        if not record.attributed_adrs:
            severity: ImplementationAttributionSeverity = "error" if profile == "greenfield" else "warning"
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

    outcome: ImplementationAttributionOutcome = "non_compliant" if any(
        issue.severity == "error" for issue in issues
    ) else "compliant"
    return ImplementationAttributionValidationResult(
        profile=profile,
        outcome=outcome,
        issues=tuple(issues),
    )
