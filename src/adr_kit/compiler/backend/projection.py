"""IR to registry projection boundary."""

from __future__ import annotations

from ...models.architecture_discovery import (
    EntityRelationshipSummary,
    NormalizedEntity,
    RelationshipRecord,
    UnresolvedRecord,
)
from ..ir.entity_graph import ENTITY_RELATIONSHIP_TYPES, IREntity
from ..ir.rel_graph import IRRelationship, RelGraph
from ..ir.unresolved_list import IRUnresolved


PROJECTABLE_ENTITY_TYPES = {"adr", "system", "component", "decision", "capability", "invariant"}


def build_relationship_summary(entity_id: str, rel_graph: RelGraph) -> EntityRelationshipSummary:
    """Rebuild the registry relationship summary for one entity."""
    buckets = {relationship_type: [] for relationship_type in ENTITY_RELATIONSHIP_TYPES}
    for relationship in rel_graph.outgoing(entity_id):
        buckets[relationship.relationship_type].append(relationship.to_entity_id)
    for values in buckets.values():
        values.sort()
    return EntityRelationshipSummary(**buckets)


def project_entity(entity: IREntity, rel_graph: RelGraph | None = None) -> NormalizedEntity | None:
    """Project an IR entity to the kernel-facing registry shape."""
    if entity.entity_type not in PROJECTABLE_ENTITY_TYPES:
        return None
    relationships = build_relationship_summary(entity.id, rel_graph) if rel_graph is not None else EntityRelationshipSummary()
    return NormalizedEntity(
        id=entity.id,
        entity_type=entity.entity_type,
        name=entity.name,
        summary=entity.summary,
        canonical_source=entity.canonical_source,
        source_refs=list(entity.source_refs),
        metadata=dict(entity.metadata),
        relationships=relationships,
        completeness=entity.completeness,
        provenance=entity.provenance,
    )


def project_relationship(relationship: IRRelationship) -> RelationshipRecord:
    """Project an IR relationship to the registry shape."""
    return RelationshipRecord(
        relationship_id=relationship.relationship_id,
        relationship_type=relationship.relationship_type,
        from_entity_id=relationship.from_entity_id,
        to_entity_id=relationship.to_entity_id,
        provenance_classification=relationship.provenance_classification,
        evidence=list(relationship.evidence),
        canonical_source_ref=relationship.canonical_source_ref,
        confidence=relationship.confidence,
        metadata=dict(relationship.metadata),
    )


def project_unresolved(item: IRUnresolved) -> UnresolvedRecord:
    """Project an IR unresolved item to the registry shape."""
    return UnresolvedRecord(
        id=item.id,
        gap_class=item.gap_class,
        gap_type=item.gap_type,
        source_entity_id=item.source_entity_id,
        related_entity_id=item.related_entity_id,
        expected_relationship=item.expected_relationship,
        severity=item.severity,
        provenance=item.provenance,
        evidence=list(item.evidence),
        suggested_resolution=item.suggested_resolution,
    )
