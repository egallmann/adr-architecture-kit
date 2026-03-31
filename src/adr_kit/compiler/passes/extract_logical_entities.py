"""Logical entity extraction pass helper."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ...models import (
    CanonicalSource,
    Completeness,
    DiscoveryProvenance,
    LogicalADR,
    NormalizedEntity,
    SourceRef,
    UnresolvedRecord,
)


@dataclass(frozen=True)
class ExtractedEntity:
    """Entity plus duplicate-handling hint for generator consumption."""

    entity: NormalizedEntity
    allow_reference_merge: bool = False


@dataclass(frozen=True)
class InvariantMention:
    """Captured invariant mention prior to canonical selection."""

    payload: dict
    artifact_path: str
    source_ref: str


@dataclass
class LogicalExtractionResult:
    """Logical extraction output."""

    entities: list[ExtractedEntity] = field(default_factory=list)
    invariant_mentions: dict[str, list[InvariantMention]] = field(default_factory=dict)
    unresolved: list[UnresolvedRecord] = field(default_factory=list)


@dataclass(frozen=True)
class ExtractLogicalEntitiesPass:
    """Pass-shaped helper for logical ADR extraction."""

    name = "extract_logical_entities"
    required = True
    depends_on: tuple[str, ...] = ()
    halts_on_error = True

    def run(
        self,
        logical_adrs: list[tuple[LogicalADR, Path]],
        *,
        source_path,
        canonical,
        provenance,
        summary,
        complete,
        classify_author_gap,
    ) -> LogicalExtractionResult:
        return extract_logical_entities(
            logical_adrs,
            source_path=source_path,
            canonical=canonical,
            provenance=provenance,
            summary=summary,
            complete=complete,
            classify_author_gap=classify_author_gap,
        )


def extract_logical_entities(
    logical_adrs: list[tuple[LogicalADR, Path]],
    *,
    source_path,
    canonical,
    provenance,
    summary,
    complete,
    classify_author_gap,
) -> LogicalExtractionResult:
    """Extract ADR, capability, and decision entities plus logical-only side data."""

    result = LogicalExtractionResult()

    for adr, path in logical_adrs:
        artifact = source_path(path)
        governance = adr.governance
        result.entities.append(
            ExtractedEntity(
                entity=NormalizedEntity(
                    id=adr.id,
                    entity_type="adr",
                    name=adr.title,
                    summary=summary(adr.context),
                    canonical_source=canonical("logical_adr", adr.id, artifact),
                    metadata={
                        "status": adr.status.value,
                        "domains": list(adr.domains),
                        "tags": list(adr.tags),
                        "implementation_authority": governance.implementation_authority.value if governance and governance.implementation_authority else None,
                        "related_reviews": list(governance.related_reviews) if governance else [],
                        "related_overrides": list(governance.related_overrides) if governance else [],
                    },
                    completeness=complete(),
                    provenance=provenance("logical_adr", adr.id, "extract_adr", "explicit"),
                )
            )
        )

        for capability in adr.capabilities:
            source_ref = f"{adr.id}#{capability.id}"
            result.entities.append(
                ExtractedEntity(
                    entity=NormalizedEntity(
                        id=capability.id,
                        entity_type="capability",
                        name=capability.name,
                        summary=summary(capability.description),
                        canonical_source=canonical("logical_adr", source_ref, artifact),
                        metadata={
                            "adr_id": adr.id,
                            "domains": list(adr.domains),
                            "implemented_by_components": list(capability.implemented_by_components),
                            "enabled_by_decisions": list(capability.enabled_by_decisions),
                        },
                        completeness=complete(),
                        provenance=provenance("logical_adr", source_ref, "extract_capability", "explicit"),
                    )
                )
            )

        for decision in adr.decisions:
            source_ref = f"{adr.id}#{decision.id}"
            result.entities.append(
                ExtractedEntity(
                    entity=NormalizedEntity(
                        id=decision.id,
                        entity_type="decision",
                        name=decision.summary,
                        summary=summary(decision.rationale),
                        canonical_source=canonical("logical_adr", source_ref, artifact),
                        metadata={
                            "adr_id": adr.id,
                            "related_invariants": list(decision.related_invariants),
                            "enforces_invariants": list(decision.enforces_invariants),
                            "enables_capabilities": list(decision.enables_capabilities),
                            "governs_components": list(decision.governs_components),
                            "supersedes": list(decision.supersedes),
                            "refines": list(decision.refines),
                        },
                        completeness=complete(),
                        provenance=provenance("logical_adr", source_ref, "extract_decision", "explicit"),
                    )
                )
            )

        for invariant in adr.invariants:
            result.invariant_mentions.setdefault(invariant.id, []).append(
                InvariantMention(
                    payload={
                        "name": invariant.id,
                        "summary": summary(invariant.statement),
                        "metadata": {
                            "adr_id": adr.id,
                            "scope": invariant.scope,
                            "statement": invariant.statement,
                            "enforcement_level": invariant.enforcement_level.value,
                            "declaration_mode": invariant.declaration_mode or "local",
                            "upheld_by_decisions": list(invariant.upheld_by_decisions),
                        },
                    },
                    artifact_path=artifact,
                    source_ref=f"{adr.id}#{invariant.id}",
                )
            )

        for gap in adr.gaps:
            unresolved = UnresolvedRecord(
                id=f"UGAP-{adr.id}-{gap.id}",
                gap_class="author_declared",
                gap_type=classify_author_gap(gap),
                source_entity_id=adr.id,
                severity="important" if gap.blocking else "advisory",
                provenance=provenance("derived_registry", f"{adr.id}#{gap.id}", "detect_unresolved", "explicit"),
                evidence=[adr.id, gap.question],
            )
            result.unresolved.append(unresolved)

    result.unresolved.sort(key=lambda item: item.id)
    return result
