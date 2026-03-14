"""Stable semantic model exposed by the architecture repository boundary."""

from __future__ import annotations

from typing import Iterable
from typing import Literal

from pydantic import BaseModel, Field

from .architecture_discovery import (
    DiscoveryProvenance,
    NormalizedEntity,
    RelationshipRecord,
    SourceCoverageSummary,
    UnresolvedRecord,
    ValidationSummary,
)


class NormalizedArchitectureModel(BaseModel):
    """Typed semantic view over one loaded architecture scope."""

    schema_version: str = "1.0"
    type: Literal["normalized_architecture_model"] = "normalized_architecture_model"
    mode: Literal["normalized", "legacy"]
    scope_root: str
    architecture_namespace: str | None = None
    fingerprint: str
    entities: list[NormalizedEntity] = Field(default_factory=list)
    relationships: list[RelationshipRecord] = Field(default_factory=list)
    unresolved: list[UnresolvedRecord] = Field(default_factory=list)
    validation_summary: ValidationSummary | None = None
    source_coverage: SourceCoverageSummary | None = None

    def find_entity(self, entity_id: str) -> NormalizedEntity | None:
        """Return the entity with the provided ID."""

        return next((entity for entity in self.entities if entity.id == entity_id), None)

    def entities_by_type(self, entity_type: str) -> list[NormalizedEntity]:
        """Return entities matching the provided semantic type."""

        return [entity for entity in self.entities if entity.entity_type == entity_type]

    def adr_entities(self) -> list[NormalizedEntity]:
        """Return normalized ADR entities."""

        return self.entities_by_type("adr")

    def adr_status(self, adr_id: str) -> str | None:
        """Return the semantic status for one ADR entity if present."""

        entity = self.find_entity(adr_id)
        if entity is None or entity.entity_type != "adr":
            return None
        status = (entity.metadata or {}).get("status")
        return str(status) if status is not None else None

    def provenance_for_entity(self, entity_id: str) -> DiscoveryProvenance | None:
        """Return semantic provenance for one entity if present."""

        entity = self.find_entity(entity_id)
        return entity.provenance if entity is not None else None

    def canonical_adr_refs_for_entity(self, entity_id: str) -> list[str]:
        """Return deterministic ADR references attached to one semantic entity."""

        entity = self.find_entity(entity_id)
        if entity is None:
            return []
        refs: set[str] = set()
        canonical_ref = entity.canonical_source.source_ref.split("#")[0]
        if canonical_ref.startswith("ADR-"):
            refs.add(canonical_ref)
        refs.update(
            ref.source_ref.split("#")[0]
            for ref in entity.source_refs
            if ref.source_ref.startswith("ADR-")
        )
        for metadata_ref_key in ("adr_id", "defined_in", "introduced_by"):
            metadata_ref = (entity.metadata or {}).get(metadata_ref_key)
            if isinstance(metadata_ref, str) and metadata_ref.startswith("ADR-"):
                refs.add(metadata_ref)
        refs.update(item for item in entity.relationships.declared_in if item.startswith("ADR-"))
        return sorted(refs)

    def relationships_for_entity(
        self,
        entity_id: str,
        *,
        relationship_type: str | None = None,
        direction: Literal["any", "incoming", "outgoing"] = "any",
    ) -> list[RelationshipRecord]:
        """Return deterministic relationships attached to an entity."""

        relationships = [
            relationship
            for relationship in self.relationships
            if (
                direction == "any"
                and (relationship.from_entity_id == entity_id or relationship.to_entity_id == entity_id)
            )
            or (direction == "incoming" and relationship.to_entity_id == entity_id)
            or (direction == "outgoing" and relationship.from_entity_id == entity_id)
        ]
        if relationship_type is not None:
            relationships = [
                relationship
                for relationship in relationships
                if relationship.relationship_type == relationship_type
            ]
        return sorted(relationships, key=lambda item: item.relationship_id)

    def related_entity_ids(
        self,
        entity_id: str,
        *,
        relationship_type: str | None = None,
        direction: Literal["any", "incoming", "outgoing"] = "outgoing",
    ) -> list[str]:
        """Return deterministic adjacent entity IDs for one entity."""

        if direction == "incoming":
            related: Iterable[str] = (
                relationship.from_entity_id
                for relationship in self.relationships_for_entity(
                    entity_id,
                    relationship_type=relationship_type,
                    direction="incoming",
                )
            )
        elif direction == "outgoing":
            related = (
                relationship.to_entity_id
                for relationship in self.relationships_for_entity(
                    entity_id,
                    relationship_type=relationship_type,
                    direction="outgoing",
                )
            )
        else:
            related = (
                (
                    relationship.to_entity_id
                    if relationship.from_entity_id == entity_id
                    else relationship.from_entity_id
                )
                for relationship in self.relationships_for_entity(
                    entity_id,
                    relationship_type=relationship_type,
                    direction="any",
                )
            )
        return sorted(set(related))

    def unresolved_for_entity(self, entity_id: str) -> list[UnresolvedRecord]:
        """Return unresolved records attached to the entity."""

        return sorted(
            [item for item in self.unresolved if item.source_entity_id == entity_id],
            key=lambda item: item.id,
        )
