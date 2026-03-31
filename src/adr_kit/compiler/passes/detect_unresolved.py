"""Generator-derived unresolved detection pass helper."""

from __future__ import annotations

from dataclasses import dataclass, field

from ...models import UnresolvedRecord
from .derive_relationships import DerivedGapSignal


@dataclass
class UnresolvedDetectionResult:
    """Generator-derived unresolved records."""

    unresolved: list[UnresolvedRecord] = field(default_factory=list)


@dataclass(frozen=True)
class DetectUnresolvedPass:
    """Pass-shaped helper for converting derived gaps into unresolved records."""

    name = "detect_unresolved"
    required = True
    depends_on: tuple[str, ...] = ()
    halts_on_error = True

    def run(self, generator_gaps: list[DerivedGapSignal], *, provenance) -> UnresolvedDetectionResult:
        return detect_unresolved(generator_gaps, provenance=provenance)


def detect_unresolved(
    generator_gaps: list[DerivedGapSignal],
    *,
    provenance,
) -> UnresolvedDetectionResult:
    """Convert relationship-derivation gap signals into unresolved registry records."""

    return UnresolvedDetectionResult(
        unresolved=[
            UnresolvedRecord(
                id=gap.gap_id,
                gap_class="generator_derived",
                gap_type=gap.gap_type,
                source_entity_id=gap.source_entity_id,
                related_entity_id=gap.related_entity_id,
                expected_relationship=gap.expected_relationship,
                severity=gap.severity,
                provenance=provenance("derived_registry", gap.source_ref, "detect_unresolved", "derived"),
                evidence=list(gap.evidence),
            )
            for gap in generator_gaps
        ]
    )
