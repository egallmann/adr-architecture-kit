"""IR to registry projection boundary."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, cast

if TYPE_CHECKING:
    from ...models.v2_0 import NormalizedEntityV2, RelationshipRecordV2

from ...models.architecture_discovery import (
    EntityRelationshipSummary,
    NormalizedEntity,
    RelationshipRecord,
    RelationshipType,
    NormalizedEntityType,
    UnresolvedRecord,
    lifecycle_stage_from_adr_status,
)
from ..ir.entity_graph import ENTITY_RELATIONSHIP_TYPES, IREntity
from ..ir.rel_graph import IRRelationship, RelGraph
from ..ir.unresolved_list import IRUnresolved

PROJECTABLE_ENTITY_TYPES = {
    "adr",
    "system",
    "component",
    "decision",
    "capability",
    "invariant",
    "boundary",
    "contract",
    "interface",
    "implementation_decision",
}


def build_relationship_summary(entity_id: str, rel_graph: RelGraph) -> EntityRelationshipSummary:
    """Rebuild the registry relationship summary for one entity."""
    buckets = {relationship_type: [] for relationship_type in ENTITY_RELATIONSHIP_TYPES}
    for relationship in rel_graph.outgoing(entity_id):
        if relationship.metadata.get("target_scope") in {"external", "expectation"}:
            continue
        if relationship.relationship_type not in buckets:
            # Namespaced extension relationships have their own canonical
            # relationship registry and never pollute the closed core summary.
            continue
        buckets[relationship.relationship_type].append(relationship.to_entity_id)
    for values in buckets.values():
        values.sort()
    return EntityRelationshipSummary(**buckets)


def _lifecycle_stage_for_projection(entity: IREntity) -> str:
    raw = entity.metadata.get("lifecycle_stage")
    if isinstance(raw, str) and raw in ("proposed", "active", "deprecated", "superseded"):
        return raw
    return lifecycle_stage_from_adr_status(
        entity.metadata.get("status") if isinstance(entity.metadata.get("status"), str) else None
    )


def project_entity(entity: IREntity, rel_graph: RelGraph | None = None) -> NormalizedEntity | None:
    """Project an IR entity to the kernel-facing registry shape."""
    if (
        entity.entity_type not in PROJECTABLE_ENTITY_TYPES
        or entity.canonical_source.source_type == "project_metadata"
    ):
        return None
    relationships = (
        build_relationship_summary(entity.id, rel_graph)
        if rel_graph is not None
        else EntityRelationshipSummary()
    )
    return NormalizedEntity(
        id=entity.id,
        entity_type=cast(NormalizedEntityType, entity.entity_type),
        name=entity.name,
        summary=entity.summary,
        lifecycle_stage=_lifecycle_stage_for_projection(entity),
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
        assertion_id=relationship.assertion_id,
        relationship_type=cast(RelationshipType, relationship.relationship_type),
        from_entity_id=relationship.from_entity_id,
        to_entity_id=relationship.to_entity_id,
        provenance_classification=relationship.provenance_classification,
        evidence=list(relationship.evidence),
        canonical_source_ref=relationship.canonical_source_ref,
        source_pointer=relationship.source_pointer,
        confidence=relationship.confidence,
        metadata=dict(relationship.metadata),
    )


def project_entity_v2(
    entity: IREntity,
    rel_graph: RelGraph | None,
    architecture_namespace: str,
) -> "NormalizedEntityV2 | None":
    """Project an IR entity to the UUID-identity-bearing v2.0 shape."""
    from ...identity import (
        derive_alias_ref,
        derive_entity_uri,
        entity_fingerprint as compute_fp,
        uuidv7_created_at,
        validate_uuidv7,
    )
    from ...models.v2_0 import NormalizedEntityV2

    if (
        entity.entity_type not in PROJECTABLE_ENTITY_TYPES
        or entity.canonical_source.source_type == "project_metadata"
    ):
        return None
    try:
        validate_uuidv7(entity.id)
    except ValueError:
        return None

    alias_id = entity.metadata.get("alias_id", entity.id)
    alias_name = entity.metadata.get("alias_name", "")
    if not alias_name:
        alias_name = entity.name.lower().replace(" ", "-")[:96]
        if len(alias_name) < 3:
            alias_name = f"{entity.entity_type}-entity"

    relationships = (
        build_relationship_summary(entity.id, rel_graph)
        if rel_graph is not None
        else EntityRelationshipSummary()
    )
    fp_record = {
        "id": entity.id,
        "alias_id": alias_id,
        "alias_name": alias_name,
        "entity_type": entity.entity_type,
        "name": entity.name,
    }
    return NormalizedEntityV2(
        id=entity.id,
        alias_id=alias_id,
        alias_name=alias_name,
        alias_ref=derive_alias_ref(alias_id, alias_name),
        entity_type=cast(NormalizedEntityType, entity.entity_type),
        name=entity.name,
        summary=entity.summary,
        uri=derive_entity_uri(architecture_namespace, entity.id),
        created_at=uuidv7_created_at(entity.id),
        entity_fingerprint=compute_fp(fp_record),
        lifecycle_stage=cast(
            Literal["proposed", "active", "deprecated", "superseded"],
            _lifecycle_stage_for_projection(entity),
        ),
        canonical_source=entity.canonical_source,
        source_refs=list(entity.source_refs),
        metadata=dict(entity.metadata),
        relationships=relationships,
        completeness=entity.completeness,
        provenance=entity.provenance,
    )


def project_entity_v21(
    entity: IREntity,
    rel_graph: RelGraph | None,
    architecture_namespace: str,
):
    """Project core or qualified extension entities to normalized v2.1."""
    from ...identity import (
        derive_alias_ref,
        derive_entity_uri,
        entity_fingerprint as compute_fp,
        uuidv7_created_at,
        validate_uuidv7,
    )
    from ...models.v2_1 import ExtensionPayloadV21, NormalizedEntityV21
    from ...semantic_extensions import is_extension_type, validate_extension_type

    if (
        not is_projectable_entity(entity)
        or entity.canonical_source.source_type == "project_metadata"
    ):
        return None
    try:
        validate_uuidv7(entity.id)
    except ValueError:
        return None
    alias_id = entity.metadata.get("alias_id", entity.id)
    alias_name = entity.metadata.get("alias_name") or entity.name.lower().replace(" ", "-")[:96]
    if len(alias_name) < 3:
        alias_name = f"{entity.entity_type.replace(':', '-')}-entity"
    extension = None
    if is_extension_type(entity.entity_type, kind="entity"):
        validate_extension_type(entity.entity_type, architecture_namespace=architecture_namespace)
        extension = ExtensionPayloadV21.model_validate(entity.extension or {})
    fp_record = {
        "id": entity.id,
        "alias_id": alias_id,
        "alias_name": alias_name,
        "entity_type": entity.entity_type,
        "name": entity.name,
        "extension": extension.model_dump(mode="json") if extension else None,
    }
    return NormalizedEntityV21(
        id=entity.id,
        alias_id=alias_id,
        alias_name=alias_name,
        alias_ref=derive_alias_ref(alias_id, alias_name),
        entity_type=entity.entity_type,
        name=entity.name,
        summary=entity.summary,
        uri=derive_entity_uri(architecture_namespace, entity.id),
        created_at=uuidv7_created_at(entity.id),
        entity_fingerprint=compute_fp(fp_record),
        lifecycle_stage=cast(
            Literal["proposed", "active", "deprecated", "superseded"],
            _lifecycle_stage_for_projection(entity),
        ),
        canonical_source=entity.canonical_source,
        source_refs=list(entity.source_refs),
        metadata=dict(entity.metadata),
        relationships=(
            build_relationship_summary(entity.id, rel_graph)
            if rel_graph is not None
            else EntityRelationshipSummary()
        ),
        completeness=entity.completeness,
        provenance=entity.provenance,
        extension=extension,
    )


def project_relationship_v2(
    relationship: IRRelationship,
) -> "RelationshipRecordV2 | None":
    """Project an IR relationship to the UUID-endpoint v2.0 shape."""
    from ...identity import validate_uuidv7
    from ...models.v2_0 import RelationshipRecordV2

    try:
        validate_uuidv7(relationship.from_entity_id)
        validate_uuidv7(relationship.to_entity_id)
    except ValueError:
        return None

    owner_id = relationship.source_owner_id
    if owner_id is None:
        return None
    try:
        validate_uuidv7(owner_id)
    except ValueError:
        return None

    from ...identity import derive_assertion_id_v13, derive_relationship_id_v13

    rel_id = derive_relationship_id_v13(
        relationship.relationship_type,
        relationship.from_entity_id,
        relationship.to_entity_id,
    )
    asrt_id = derive_assertion_id_v13(
        relationship.relationship_type,
        relationship.from_entity_id,
        relationship.to_entity_id,
        owner_id,
        relationship.source_pointer,
    )
    return RelationshipRecordV2(
        relationship_id=rel_id,
        assertion_id=asrt_id,
        relationship_type=cast(Any, relationship.relationship_type),
        from_entity_id=relationship.from_entity_id,
        to_entity_id=relationship.to_entity_id,
        source_owner_id=owner_id,
        source_pointer=relationship.source_pointer,
        provenance_classification=cast(
            Literal["explicit", "derived", "heuristic"],
            relationship.provenance_classification,
        ),
        evidence=list(relationship.evidence),
        canonical_source_ref=relationship.canonical_source_ref,
        confidence=relationship.confidence,
        metadata=dict(relationship.metadata),
    )


def project_relationship_v21(relationship: IRRelationship):
    """Project canonical authored or compatibility relationships for v2.1."""
    from ...models.v2_1 import CanonicalRelationshipV21, CompatibilityRelationshipV21, ExtensionPayloadV21
    from ...identity import validate_uuidv7

    try:
        validate_uuidv7(relationship.from_entity_id)
        validate_uuidv7(relationship.to_entity_id)
    except ValueError:
        return None
    if relationship.record_kind == "canonical" and relationship.id:
        try:
            validate_uuidv7(relationship.id)
        except ValueError:
            return None
        extension = (
            ExtensionPayloadV21.model_validate(relationship.extension)
            if ":" in relationship.relationship_type
            else None
        )
        return CanonicalRelationshipV21(
            id=relationship.id,
            alias_id=relationship.alias_id,
            alias_name=relationship.alias_name,
            relationship_type=relationship.relationship_type,
            from_entity_id=relationship.from_entity_id,
            to_entity_id=relationship.to_entity_id,
            source_owner_id=relationship.source_owner_id,
            source_pointer=relationship.source_pointer,
            provenance_classification=relationship.provenance_classification,
            evidence=list(relationship.evidence),
            canonical_source_ref=relationship.canonical_source_ref,
            confidence=relationship.confidence,
            extension=extension,
        )
    if relationship.record_kind == "compatibility":
        return CompatibilityRelationshipV21(
            relationship_id=relationship.relationship_id,
            assertion_id=relationship.assertion_id,
            relationship_type=relationship.relationship_type,
            from_entity_id=relationship.from_entity_id,
            to_entity_id=relationship.to_entity_id,
            source_owner_id=relationship.source_owner_id,
            source_pointer=relationship.source_pointer,
            provenance_classification=relationship.provenance_classification,
            evidence=list(relationship.evidence),
            canonical_source_ref=relationship.canonical_source_ref,
            confidence=relationship.confidence,
            metadata=dict(relationship.metadata),
        )
    return None


def is_projectable_entity(entity: IREntity) -> bool:
    """Return v2.1 projectability without closing qualified consumer types."""
    from ...semantic_extensions import is_extension_type

    return entity.entity_type in PROJECTABLE_ENTITY_TYPES or is_extension_type(
        entity.entity_type, kind="entity"
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
