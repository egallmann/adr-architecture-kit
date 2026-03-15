"""Validation helpers for implementation attribution evidence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from adr_kit.decorators import implements_adr
from adr_kit.models import (
    ImplementationAttributionEvidence,
    NormalizedArchitectureModel,
    NormalizedEntityRegistry,
)
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


@implements_adr("ADR-L-0004", "ADR-L-0013")
def validate_implementation_attribution_evidence(
    entity_registry: NormalizedEntityRegistry | NormalizedArchitectureModel,
    evidence: ImplementationAttributionEvidence,
    *,
    profile: ContractProfile = "greenfield",
) -> ImplementationAttributionValidationResult:
    """Validate implementation attribution claims against canonical ADR state."""
    issues: list[ImplementationAttributionIssue] = []
    model = coerce_to_normalized_model(
        entity_registry,
        fingerprint="implementation-attribution-validation",
        generator="implementation-attribution-validation",
        extraction_phase="implementation_attribution_validation.coerce_model",
    )
    adr_status_by_id = model.adr_status_map()

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
