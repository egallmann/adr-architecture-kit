"""Validation-only tooling for consumer-owned semantic alias allocations.

The caller supplies the authoritative consumer allocation document.  ADR-Kit
never persists or treats its own repository allocation ledger as a registry for
external consumer prefixes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from ..semantic_extensions import ExtensionValidationError, validate_alias_registration


@dataclass(frozen=True)
class AliasAllocationDiagnostic:
    code: str
    message: str
    semantic_type: str | None = None


@dataclass(frozen=True)
class ConsumerAllocationReport:
    registrations: dict[str, str]
    diagnostics: tuple[AliasAllocationDiagnostic, ...]
    candidate_inventory: tuple[dict[str, str], ...]

    @property
    def valid(self) -> bool:
        return not self.diagnostics


def build_candidate_inventory(records: list[Mapping[str, Any]]) -> tuple[dict[str, str], ...]:
    """Build a deterministic, non-mutating promoted-record inventory."""
    inventory: list[dict[str, str]] = []
    for record in records:
        if not isinstance(record.get("id"), str) or not isinstance(record.get("alias_id"), str):
            continue
        inventory.append({"id": record["id"], "alias_id": record["alias_id"]})
    return tuple(sorted(inventory, key=lambda item: (item["alias_id"], item["id"])))


def collision_report(records: list[Mapping[str, Any]]) -> tuple[AliasAllocationDiagnostic, ...]:
    """Report duplicate canonical UUIDs or aliases before a migration map is sealed."""
    seen: dict[str, str] = {}
    diagnostics: list[AliasAllocationDiagnostic] = []
    for item in build_candidate_inventory(records):
        for key in ("id", "alias_id"):
            value = item[key]
            prior = seen.get(f"{key}:{value}")
            if prior is not None:
                diagnostics.append(AliasAllocationDiagnostic("collision", f"Duplicate {key}: {value}"))
            seen[f"{key}:{value}"] = item["id"]
    return tuple(diagnostics)


def verify_sealed_map(candidate_map: Mapping[str, Any]) -> None:
    """Require an explicitly SEALED map before any caller applies migration."""
    if str(candidate_map.get("status", "")).upper() != "SEALED":
        raise ValueError("Candidate allocation map is not SEALED; migration application is blocked")


def validate_consumer_alias_allocations(
    allocation: Mapping[str, Any],
    *,
    reserved_prefixes: tuple[str, ...] = (),
) -> ConsumerAllocationReport:
    """Validate one consumer corpus's allocation state without mutating it."""

    raw = allocation.get("registrations", allocation)
    architecture_namespace = allocation.get("architecture_namespace")
    diagnostics: list[AliasAllocationDiagnostic] = []
    registrations: dict[str, str] = {}
    if not isinstance(raw, Mapping):
        return ConsumerAllocationReport(
            registrations={},
            diagnostics=(AliasAllocationDiagnostic("invalid_scope", "registrations must be a mapping"),),
            candidate_inventory=(),
        )
    for semantic_type, prefix in raw.items():
        if not isinstance(semantic_type, str) or not isinstance(prefix, str):
            diagnostics.append(AliasAllocationDiagnostic("invalid_registration", "type and prefix must be strings"))
            continue
        try:
            validate_alias_registration(
                semantic_type=semantic_type,
                alias_id=f"{prefix}-0001",
                architecture_namespace=architecture_namespace if isinstance(architecture_namespace, str) else None,
                registrations=registrations,
                reserved_prefixes=reserved_prefixes,
            )
            registrations[semantic_type] = prefix
        except ExtensionValidationError as exc:
            diagnostics.append(AliasAllocationDiagnostic("invalid_registration", str(exc), semantic_type))
    candidates = tuple(
        {"semantic_type": semantic_type, "alias_prefix": prefix}
        for semantic_type, prefix in sorted(registrations.items())
    )
    return ConsumerAllocationReport(dict(registrations), tuple(diagnostics), candidates)


def dry_run_consumer_allocation(allocation: Mapping[str, Any]) -> ConsumerAllocationReport:
    """Alias for the non-mutating migration-gate dry run."""

    return validate_consumer_alias_allocations(allocation)
