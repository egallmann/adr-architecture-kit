"""Authoring-time validation helpers for compiled repository contract bundles.

This module validates compiled repository-normalized discovery artifacts
(architecture index, entity registry, relationship registry, unresolved
registry) against authoring-time contract rules.

It does not own the normative cross-repo Architecture IR contract; that
authority belongs to ste-spec. Validation here is subordinate and
compatibility-focused: it checks that this repository's compiled outputs
conform to the contract shape, not that the contract shape itself is correct.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from adr_kit.decorators import implements_adr
from adr_kit.models.architecture_discovery import (
    ArchitectureIndex,
    NormalizedEntity,
    NormalizedEntityRegistry,
    RelationshipRegistry,
    UnresolvedRegistry,
)
from adr_kit.models.remediation_ledger import RemediationLedger

ContractProfile = Literal["greenfield", "brownfield", "migration"]
ContractValidationOutcome = Literal["compliant", "sentinel_compliant", "non_compliant"]

SENTINEL_VALUES = {
    "__LEGACY_UNSPECIFIED__",
    "__NOT_YET_MODELED__",
    "__MIGRATION_PLACEHOLDER__",
}

REQUIRED_METADATA_KEYS: dict[str, set[str]] = {
    "adr": {"status", "domains", "tags"},
    "capability": {"adr_id", "domains", "implemented_by_components", "enabled_by_decisions"},
    "decision": {
        "adr_id",
        "related_invariants",
        "enforces_invariants",
        "enables_capabilities",
        "governs_components",
        "supersedes",
        "refines",
    },
    "invariant": {"scope", "statement", "enforcement_level", "declaration_mode", "upheld_by_decisions"},
    "system": {"adr_id", "implements_logical", "technologies"},
    "component": {"adr_id", "technologies", "module_path", "implements_capabilities", "implements_system"},
}

ALLOWED_COMPLETENESS_BY_PROFILE: dict[ContractProfile, set[str]] = {
    "greenfield": {"complete"},
    "migration": {"complete", "partial"},
    "brownfield": {"complete", "partial", "reference_only"},
}


@dataclass(frozen=True)
class ContractValidationIssue:
    path: str
    message: str


@dataclass(frozen=True)
class ContractValidationResult:
    profile: ContractProfile
    outcome: ContractValidationOutcome
    issues: tuple[ContractValidationIssue, ...]
    sentinel_field_count: int = 0
    non_complete_entity_count: int = 0
    completeness_counts: dict[str, int] | None = None

    @property
    def is_valid(self) -> bool:
        return self.outcome != "non_compliant"

    @property
    def has_sentinels(self) -> bool:
        return self.sentinel_field_count > 0

    def require_valid(self) -> None:
        if not self.is_valid:
            raise ContractValidationError(list(self.issues))


class ContractValidationError(ValueError):
    """Raised when compiled artifacts violate contract validation rules."""

    def __init__(self, issues: list[ContractValidationIssue]):
        self.issues = issues
        joined = "; ".join(f"{issue.path}: {issue.message}" for issue in issues)
        super().__init__(joined)


@implements_adr("ADR-L-0010", "ADR-L-0011")
def validate_adr_contract_bundle(
    architecture_index: ArchitectureIndex,
    entity_registry: NormalizedEntityRegistry,
    relationship_registry: RelationshipRegistry,
    unresolved_registry: UnresolvedRegistry,
    *,
    profile: ContractProfile = "greenfield",
    remediation_ledger: RemediationLedger | None = None,
) -> ContractValidationResult:
    """Validate compiled repository contract bundle semantics beyond schema shape.

    Checks that the compiled repository-normalized discovery artifacts conform
    to the authoring-time contract rules for the given profile. This function
    does not own the normative cross-repo Architecture IR schema; it validates
    that this repository's outputs are internally consistent and profile-compliant.
    """
    del architecture_index, relationship_registry, unresolved_registry
    issues: list[ContractValidationIssue] = []
    sentinel_hits = 0
    field_values: dict[str, object] = {}
    completeness_counts: dict[str, int] = {}

    for idx, entity in enumerate(entity_registry.entities):
        issues.extend(_validate_entity_metadata(entity, idx))
        completeness_issues = _validate_entity_completeness(entity, idx, profile=profile)
        issues.extend(completeness_issues)
        completeness_counts[entity.completeness.status] = completeness_counts.get(entity.completeness.status, 0) + 1
        entity_issues, entity_sentinel_hits, entity_field_values = _validate_entity_sentinels(entity, idx, profile=profile)
        issues.extend(entity_issues)
        sentinel_hits += entity_sentinel_hits
        field_values.update(entity_field_values)

    non_complete_entity_count = sum(
        count for status, count in completeness_counts.items() if status != "complete"
    )

    if remediation_ledger is not None:
        issues.extend(_validate_remediation_ledger(remediation_ledger, field_values))

    if issues:
        return ContractValidationResult(
            profile=profile,
            outcome="non_compliant",
            issues=tuple(issues),
            sentinel_field_count=sentinel_hits,
            non_complete_entity_count=non_complete_entity_count,
            completeness_counts=completeness_counts,
        )

    outcome: ContractValidationOutcome = "sentinel_compliant" if sentinel_hits > 0 else "compliant"
    return ContractValidationResult(
        profile=profile,
        outcome=outcome,
        issues=(),
        sentinel_field_count=sentinel_hits,
        non_complete_entity_count=non_complete_entity_count,
        completeness_counts=completeness_counts,
    )


# Pre-1.0 rename: validate_kernel_contract_bundle → validate_adr_contract_bundle.
# The old name implied this repository owns the kernel contract authority, which
# it does not. This alias preserves compatibility during the transition and will
# be removed in a future release.
validate_kernel_contract_bundle = validate_adr_contract_bundle


def _validate_entity_metadata(entity: NormalizedEntity, index: int) -> list[ContractValidationIssue]:
    required = REQUIRED_METADATA_KEYS.get(entity.entity_type, set())
    metadata_keys = set(entity.metadata)
    missing = sorted(required - metadata_keys)
    return [
        ContractValidationIssue(
            path=f"entities[{index}].metadata.{key}",
            message=f"missing required metadata key for entity_type={entity.entity_type}",
        )
        for key in missing
    ]


def _validate_entity_completeness(
    entity: NormalizedEntity,
    index: int,
    *,
    profile: ContractProfile,
) -> list[ContractValidationIssue]:
    status = entity.completeness.status
    allowed = ALLOWED_COMPLETENESS_BY_PROFILE[profile]
    if status in allowed:
        return []

    if status == "conflicted":
        message = "conflicted completeness is not allowed in any contract profile"
    else:
        message = f"completeness.status={status} is not allowed for profile={profile}"

    return [
        ContractValidationIssue(
            path=f"entities[{index}].completeness.status",
            message=message,
        )
    ]


def _validate_entity_sentinels(
    entity: NormalizedEntity,
    index: int,
    *,
    profile: ContractProfile,
) -> tuple[list[ContractValidationIssue], int, dict[str, object]]:
    issues: list[ContractValidationIssue] = []
    sentinel_hits = 0
    field_values: dict[str, object] = {}
    sentinels_allowed = profile in {"brownfield", "migration"}

    def check_value(path: str, value: object, *, allowed_when_enabled: bool = False) -> None:
        nonlocal sentinel_hits
        if isinstance(value, str) and value in SENTINEL_VALUES:
            if not sentinels_allowed:
                issues.append(
                    ContractValidationIssue(
                        path=path,
                        message=f"sentinel-backed content is not allowed for profile={profile}",
                    )
                )
                return
            if not allowed_when_enabled:
                issues.append(
                    ContractValidationIssue(
                        path=path,
                        message="sentinel value is forbidden in this structural field",
                    )
                )
                return
            sentinel_hits += 1

    # Structural top-level fields are never sentinel-capable.
    check_value(f"entities[{index}].id", entity.id)
    check_value(f"entities[{index}].entity_type", entity.entity_type)
    check_value(f"entities[{index}].name", entity.name)
    check_value(f"entities[{index}].canonical_source.source_ref", entity.canonical_source.source_ref)
    check_value(f"entities[{index}].canonical_source.artifact_path", entity.canonical_source.artifact_path)
    check_value(f"entities[{index}].completeness.status", entity.completeness.status)

    # Narrative content can be sentinel-backed only when explicitly allowed.
    field_values[f"entity:{entity.id}.summary"] = entity.summary
    check_value(f"entities[{index}].summary", entity.summary, allowed_when_enabled=True)

    for key, value in entity.metadata.items():
        allowed_when_enabled = (
            entity.entity_type == "invariant" and key == "statement"
        ) or (
            entity.entity_type == "component" and key == "module_path"
        )
        if allowed_when_enabled:
            field_values[f"entity:{entity.id}.metadata.{key}"] = value
        check_value(
            f"entities[{index}].metadata.{key}",
            value,
            allowed_when_enabled=allowed_when_enabled,
        )

    return issues, sentinel_hits, field_values


def _validate_remediation_ledger(
    remediation_ledger: RemediationLedger,
    field_values: dict[str, object],
) -> list[ContractValidationIssue]:
    issues: list[ContractValidationIssue] = []
    seen_refs: set[str] = set()

    for index, entry in enumerate(remediation_ledger.entries):
        path_prefix = f"remediation_ledger.entries[{index}]"
        if entry.field_ref in seen_refs:
            issues.append(
                ContractValidationIssue(
                    path=f"{path_prefix}.field_ref",
                    message="duplicate remediation ledger entry for field_ref",
                )
            )
            continue
        seen_refs.add(entry.field_ref)

        if entry.field_ref not in field_values:
            issues.append(
                ContractValidationIssue(
                    path=f"{path_prefix}.field_ref",
                    message="field_ref does not resolve to a sentinel-capable contract field",
                )
            )
            continue

        value = field_values[entry.field_ref]
        is_sentinel = isinstance(value, str) and value in SENTINEL_VALUES

        if entry.state == "sentinel" and not is_sentinel:
            issues.append(
                ContractValidationIssue(
                    path=f"{path_prefix}.state",
                    message="sentinel ledger entry requires current field value to remain sentinel-backed",
                )
            )
        elif entry.state == "pending_approval" and is_sentinel:
            issues.append(
                ContractValidationIssue(
                    path=f"{path_prefix}.state",
                    message="pending_approval ledger entry requires current field value to be non-sentinel",
                )
            )
        elif entry.state == "approved" and is_sentinel:
            issues.append(
                ContractValidationIssue(
                    path=f"{path_prefix}.state",
                    message="approved field cannot regress to sentinel-backed content",
                )
            )

    return issues
