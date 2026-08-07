"""Shared semantic adaptation helpers for boundary consumers."""

from __future__ import annotations

from typing import cast

from ..decorators import implements_adr
from ..models import (
    CanonicalSource,
    Completeness,
    DiscoveryProvenance,
    Entity,
    EntityRegistry,
    NormalizedArchitectureModel,
    NormalizedEntity,
    NormalizedEntityRegistry,
    RelationshipRecord,
    SourceRef,
    ValidationSummary,
)
from ..models.architecture_discovery import NormalizedEntityType, RelationshipType


@implements_adr("ADR-L-0013")
def coerce_to_normalized_model(
    value: EntityRegistry | NormalizedEntityRegistry | NormalizedArchitectureModel,
    *,
    fingerprint: str,
    scope_root: str = ".",
    architecture_namespace: str | None = None,
    generator: str,
    extraction_phase: str,
) -> NormalizedArchitectureModel:
    """Return one semantic model for normalized, normalized-registry, or legacy inputs."""

    if getattr(value, "type", None) == "normalized_architecture_model":
        return NormalizedArchitectureModel.model_validate(
            value.model_dump(mode="json", exclude_none=True)
        )

    if getattr(value, "type", None) == "normalized_entity_registry":
        entities = [
            NormalizedEntity.model_validate(entity.model_dump(mode="json", exclude_none=True))
            for entity in value.entities
        ]
        return NormalizedArchitectureModel(
            mode="normalized",
            scope_root=scope_root,
            architecture_namespace=architecture_namespace,
            fingerprint=fingerprint,
            entities=entities,
            relationships=[],
            unresolved=[],
            validation_summary=ValidationSummary(
                hard_failures=0,
                warnings=0,
                unresolved_entries=0,
            ),
            source_coverage=None,
        )

    entities = [
        legacy_entity_to_normalized(entity, extraction_phase=extraction_phase, generator=generator)
        for entity in value.entities
    ]
    relationships = legacy_relationships(entities)
    return NormalizedArchitectureModel(
        mode="legacy",
        scope_root=scope_root,
        architecture_namespace=architecture_namespace,
        fingerprint=fingerprint,
        entities=entities,
        relationships=relationships,
        unresolved=[],
        validation_summary=ValidationSummary(
            hard_failures=0,
            warnings=0,
            unresolved_entries=0,
        ),
        source_coverage=None,
    )


@implements_adr("ADR-L-0013")
def legacy_entity_to_normalized(
    entity: Entity,
    *,
    extraction_phase: str,
    generator: str,
) -> NormalizedEntity:
    """Adapt one legacy entity into the semantic boundary model."""

    entity_type = entity.entity_type.value
    if entity_type == "implementation_decision":
        entity_type = "decision"
    canonical_ref = f"{entity.introduced_by}#{entity.entity_id}"
    metadata = {
        "status": entity.lifecycle_stage.value,
        "domains": list(entity.domains or []),
        "legacy_source_artifact_type": entity.source_artifact_type.value,
        "introduced_by": entity.introduced_by,
    }
    if entity.ownership is not None:
        metadata["ownership"] = entity.ownership.model_dump(mode="json", exclude_none=True)

    relationships = getattr(entity, "relationships", None)
    related_to = list(getattr(relationships, "depends_on", []) or [])
    enables = list(getattr(relationships, "implements", []) or [])
    enforces = list(getattr(relationships, "realizes", []) or [])

    source_refs = [
        SourceRef(
            source_type="legacy_related_adr",
            source_ref=ref,
            artifact_path=entity.source_path,
            mention_role="reference",
        )
        for ref in sorted(
            {
                *list(entity.related_adrs or []),
                *list(entity.realized_by or []),
            }
        )
        if ref.startswith("ADR-")
    ]

    return NormalizedEntity(
        id=entity.entity_id,
        entity_type=cast(NormalizedEntityType, entity_type),
        name=entity.name,
        summary=entity.name,
        lifecycle_stage=str(entity.lifecycle_stage.value),
        canonical_source=CanonicalSource(
            source_type=entity.source_artifact_type.value,
            source_ref=canonical_ref,
            artifact_path=entity.source_path,
        ),
        source_refs=source_refs,
        metadata=metadata,
        relationships={
            "declared_in": [entity.introduced_by],
            "related_to": related_to,
            "enables": enables,
            "enforces": enforces,
        },
        completeness=Completeness(status="partial", missing_fields=["legacy_normalized_semantics"]),
        provenance=DiscoveryProvenance(
            source_type="legacy_entity_registry",
            source_ref=f"adrs/entities/registry.yaml#{entity.entity_id}",
            extraction_phase=extraction_phase,
            classification="derived",
            generator=generator,
        ),
    )


@implements_adr("ADR-L-0013")
def legacy_relationships(entities: list[NormalizedEntity]) -> list[RelationshipRecord]:
    """Derive deterministic semantic relationships for adapted legacy entities."""

    known_ids = {entity.id for entity in entities}
    relationships: list[RelationshipRecord] = []
    for entity in entities:
        relationships.extend(
            _relationship_records_for_targets(
                entity=entity,
                relationship_type="declared_in",
                targets=list(entity.relationships.declared_in),
                known_ids=known_ids,
            )
        )
        relationships.extend(
            _relationship_records_for_targets(
                entity=entity,
                relationship_type="related_to",
                targets=list(entity.relationships.related_to),
                known_ids=known_ids,
            )
        )
        relationships.extend(
            _relationship_records_for_targets(
                entity=entity,
                relationship_type="enables",
                targets=list(entity.relationships.enables),
                known_ids=known_ids,
            )
        )
        relationships.extend(
            _relationship_records_for_targets(
                entity=entity,
                relationship_type="enforces",
                targets=list(entity.relationships.enforces),
                known_ids=known_ids,
            )
        )
    return sorted(relationships, key=lambda item: item.relationship_id)


def _relationship_records_for_targets(
    *,
    entity: NormalizedEntity,
    relationship_type: RelationshipType,
    targets: list[str],
    known_ids: set[str],
) -> list[RelationshipRecord]:
    records: list[RelationshipRecord] = []
    for target in sorted(set(targets)):
        if target not in known_ids and not target.startswith("ADR-"):
            continue
        records.append(
            RelationshipRecord(
                relationship_id=f"{relationship_type}:{entity.id}:{target}",
                relationship_type=relationship_type,
                from_entity_id=entity.id,
                to_entity_id=target,
                provenance_classification="derived",
                evidence=[f"Adapted from legacy entity registry for {entity.id}"],
                canonical_source_ref=entity.canonical_source.source_ref,
                confidence=1.0,
            )
        )
    return records
