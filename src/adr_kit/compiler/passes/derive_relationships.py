"""Relationship derivation pass helper."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ...models import (
    LogicalADR,
    NormalizedEntity,
    PhysicalADR,
    PhysicalComponentADR,
    PhysicalSystemADR,
    RelationshipRecord,
    StandaloneInvariant,
)
from ...models.architecture_discovery import RelationshipType


@dataclass(frozen=True)
class DerivedGapSignal:
    """Structured unresolved precursor emitted during relationship derivation."""

    gap_id: str
    gap_type: str
    source_entity_id: str
    severity: str
    source_ref: str
    evidence: list[str]
    related_entity_id: str | None = None
    expected_relationship: str | None = None


@dataclass
class RelationshipDerivationResult:
    """Derived relationships plus unresolved precursor signals."""

    relationships: list[RelationshipRecord] = field(default_factory=list)
    generator_gaps: list[DerivedGapSignal] = field(default_factory=list)


@dataclass(frozen=True)
class DeriveRelationshipsPass:
    """Pass-shaped helper for relationship derivation."""

    name = "derive_relationships"
    required = True
    depends_on: tuple[str, ...] = ()
    halts_on_error = True

    def run(
        self,
        *,
        entities: dict[str, NormalizedEntity],
        logical_adrs: list[tuple[LogicalADR, Path]],
        standalone_invariants: list[tuple[StandaloneInvariant, Path]],
        physical_adrs: list[tuple[PhysicalADR | PhysicalSystemADR | PhysicalComponentADR, Path]],
        system_ids: dict[str, str],
        relationship_id,
    ) -> RelationshipDerivationResult:
        return derive_relationships(
            entities=entities,
            logical_adrs=logical_adrs,
            standalone_invariants=standalone_invariants,
            physical_adrs=physical_adrs,
            system_ids=system_ids,
            relationship_id=relationship_id,
        )


def derive_relationships(
    *,
    entities: dict[str, NormalizedEntity],
    logical_adrs: list[tuple[LogicalADR, Path]],
    standalone_invariants: list[tuple[StandaloneInvariant, Path]],
    physical_adrs: list[tuple[PhysicalADR | PhysicalSystemADR | PhysicalComponentADR, Path]],
    system_ids: dict[str, str],
    relationship_id,
) -> RelationshipDerivationResult:
    """Derive relationships and unresolved precursor signals using current generator rules."""

    relationships: dict[str, RelationshipRecord] = {}
    result = RelationshipDerivationResult()

    def add_relationship(
        relationship_type: RelationshipType,
        from_id: str,
        to_id: str,
        source_ref: str,
        evidence: list[str],
        *,
        classification: str = "explicit",
        confidence: float = 1.0,
        metadata: dict | None = None,
    ) -> None:
        if from_id not in entities or to_id not in entities:
            return
        rel_id = relationship_id(relationship_type, from_id, to_id)
        if rel_id in relationships:
            return
        relationships[rel_id] = RelationshipRecord(
            relationship_id=rel_id,
            relationship_type=relationship_type,
            from_entity_id=from_id,
            to_entity_id=to_id,
            provenance_classification=classification,
            evidence=sorted(set(evidence)),
            canonical_source_ref=source_ref,
            confidence=confidence,
            metadata=metadata or {},
        )

    def add_gap(
        gap_id: str,
        gap_type: str,
        source_entity_id: str,
        severity: str,
        source_ref: str,
        evidence: list[str],
        *,
        related_entity_id: str | None = None,
        expected_relationship: str | None = None,
    ) -> None:
        result.generator_gaps.append(
            DerivedGapSignal(
                gap_id=gap_id,
                gap_type=gap_type,
                source_entity_id=source_entity_id,
                severity=severity,
                source_ref=source_ref,
                evidence=evidence,
                related_entity_id=related_entity_id,
                expected_relationship=expected_relationship,
            )
        )

    for entity in list(entities.values()):
        if entity.entity_type != "adr":
            adr_id = entity.canonical_source.source_ref.split("#")[0]
            if adr_id in entities:
                add_relationship(
                    "declared_in",
                    entity.id,
                    adr_id,
                    entity.canonical_source.source_ref,
                    [entity.canonical_source.source_ref],
                )

    for adr, _ in logical_adrs:
        for related in adr.related_adrs:
            if related in entities:
                add_relationship("references", adr.id, related, adr.id, [adr.id])
        for capability in adr.capabilities:
            for component_id in capability.implemented_by_components:
                if component_id in entities:
                    add_relationship(
                        "implemented_by",
                        capability.id,
                        component_id,
                        f"{adr.id}#{capability.id}",
                        [adr.id],
                    )
                else:
                    add_gap(
                        f"GAP-IMPL-{capability.id}-{component_id}",
                        "capability_without_implementing_component",
                        capability.id,
                        "important",
                        f"{adr.id}#{capability.id}",
                        [adr.id, component_id],
                        related_entity_id=component_id,
                        expected_relationship="implemented_by",
                    )
        for contract in adr.interaction_contracts:
            for party in contract.parties:
                if party in entities:
                    add_relationship(
                        "related_to",
                        contract.id,
                        party,
                        f"{adr.id}#{contract.id}",
                        [adr.id],
                    )
        for decision in adr.decisions:
            for invariant_id in sorted(
                set(decision.related_invariants + decision.enforces_invariants)
            ):
                if invariant_id in entities:
                    add_relationship(
                        "enforces", decision.id, invariant_id, f"{adr.id}#{decision.id}", [adr.id]
                    )
                else:
                    add_gap(
                        f"GAP-INV-{decision.id}-{invariant_id}",
                        "unresolved_reference",
                        decision.id,
                        "important",
                        f"{adr.id}#{decision.id}",
                        [adr.id, invariant_id],
                        related_entity_id=invariant_id,
                        expected_relationship="enforces",
                    )
            for capability_id in decision.enables_capabilities:
                if capability_id in entities:
                    add_relationship(
                        "enables", decision.id, capability_id, f"{adr.id}#{decision.id}", [adr.id]
                    )
                    add_relationship(
                        "enabled_by",
                        capability_id,
                        decision.id,
                        f"{adr.id}#{decision.id}",
                        [adr.id],
                        classification="derived",
                    )
                else:
                    add_gap(
                        f"GAP-CAP-{decision.id}-{capability_id}",
                        "unresolved_reference",
                        decision.id,
                        "important",
                        f"{adr.id}#{decision.id}",
                        [adr.id, capability_id],
                        related_entity_id=capability_id,
                        expected_relationship="enables",
                    )
            for component_id in decision.governs_components:
                if component_id in entities:
                    add_relationship(
                        "governs", decision.id, component_id, f"{adr.id}#{decision.id}", [adr.id]
                    )
            for target in decision.supersedes:
                if target in entities:
                    add_relationship(
                        "supersedes", decision.id, target, f"{adr.id}#{decision.id}", [adr.id]
                    )
                    add_relationship(
                        "superseded_by",
                        target,
                        decision.id,
                        f"{adr.id}#{decision.id}",
                        [adr.id],
                        classification="derived",
                    )
            for target in decision.refines:
                if target in entities:
                    add_relationship(
                        "refines", decision.id, target, f"{adr.id}#{decision.id}", [adr.id]
                    )
        for invariant in adr.invariants:
            for target in getattr(invariant, "supersedes", []) or []:
                if target in entities:
                    add_relationship(
                        "supersedes", invariant.id, target, f"{adr.id}#{invariant.id}", [adr.id]
                    )
                    add_relationship(
                        "superseded_by",
                        target,
                        invariant.id,
                        f"{adr.id}#{invariant.id}",
                        [adr.id],
                        classification="derived",
                    )

    for invariant, _ in standalone_invariants:
        if invariant.id not in entities:
            continue
        for target in invariant.enforced_by:
            if target in entities:
                add_relationship("enforces", invariant.id, target, invariant.id, [invariant.id])

    for adr, _ in physical_adrs:
        if isinstance(adr, PhysicalComponentADR):
            for component in adr.component_specifications:
                component_id = component.component_id or component.id
                for interface in component.interfaces:
                    add_relationship(
                        "provides_interface",
                        component_id,
                        interface.id,
                        f"{adr.id}#{interface.id}",
                        [adr.id],
                    )
                for capability_id in component.implements_capabilities:
                    if capability_id in entities:
                        add_relationship(
                            "implemented_by",
                            capability_id,
                            component_id,
                            f"{adr.id}#{component_id}",
                            [adr.id],
                        )
                    else:
                        add_gap(
                            f"GAP-MISSING-CAP-{component_id}-{capability_id}",
                            "unresolved_reference",
                            component_id,
                            "important",
                            f"{adr.id}#{component_id}",
                            [adr.id, capability_id],
                            related_entity_id=capability_id,
                            expected_relationship="implemented_by",
                        )
                for system_id in adr.implements_system:
                    resolved_system_id = system_ids.get(
                        system_id, f"SYS-{system_id.replace('ADR-PS-', '')}"
                    )
                    if resolved_system_id in entities:
                        add_relationship(
                            "embodied_in",
                            component_id,
                            resolved_system_id,
                            f"{adr.id}#{component_id}",
                            [adr.id],
                        )
                    else:
                        add_gap(
                            f"GAP-MISSING-SYS-{component_id}-{system_id}",
                            "component_without_system",
                            component_id,
                            "important",
                            f"{adr.id}#{component_id}",
                            [adr.id, system_id],
                            related_entity_id=system_id,
                            expected_relationship="embodied_in",
                        )
                for dep in component.dependencies:
                    if dep in entities:
                        add_relationship(
                            "related_to",
                            component_id,
                            dep,
                            f"{adr.id}#{component_id}",
                            [adr.id],
                            classification="derived",
                            confidence=0.8,
                        )
            for implementation_decision in adr.implementation_decisions:
                for invariant_id in implementation_decision.implements_invariants:
                    if invariant_id in entities:
                        add_relationship(
                            "enforces",
                            implementation_decision.id,
                            invariant_id,
                            f"{adr.id}#{implementation_decision.id}",
                            [adr.id],
                        )
        if isinstance(adr, PhysicalSystemADR):
            system_id = system_ids[adr.id]
            for topology_component in (
                adr.component_topology.components if adr.component_topology else []
            ):
                if topology_component.id is not None:
                    add_relationship(
                        "composed_of",
                        system_id,
                        topology_component.id,
                        f"{adr.id}#{topology_component.id}",
                        [adr.id],
                    )
        if isinstance(adr, PhysicalSystemADR) and adr.references_components:
            for component_adr in adr.references_components:
                if component_adr in entities:
                    add_relationship(
                        "related_to",
                        adr.id,
                        component_adr,
                        adr.id,
                        [adr.id],
                        classification="derived",
                        confidence=0.8,
                    )

    result.relationships = sorted(relationships.values(), key=lambda item: item.relationship_id)
    result.generator_gaps.sort(key=lambda item: item.gap_id)
    return result
