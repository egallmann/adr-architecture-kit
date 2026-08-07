"""Stable semantic model exposed by the architecture repository boundary."""

from __future__ import annotations

from typing import Iterable
from typing import Literal

from pydantic import BaseModel, Field

from ..decorators import implements_adr
from .architecture_discovery import (
    DiscoveryProvenance,
    NormalizedEntity,
    RelationshipRecord,
    SourceCoverageSummary,
    SourceRef,
    UnresolvedRecord,
    ValidationSummary,
)


@implements_adr("ADR-L-0013")
class NormalizedArchitectureModel(BaseModel):
    """Typed semantic view over one loaded architecture scope."""

    schema_version: str = "1.1"
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

    @implements_adr("ADR-L-0013")
    def entity_ids(self) -> list[str]:
        """Return deterministic semantic entity IDs for the loaded scope."""

        return sorted(entity.id for entity in self.entities)

    @implements_adr("ADR-L-0013")
    def relationship_records(self) -> list[RelationshipRecord]:
        """Return deterministic semantic relationships for the loaded scope."""

        return sorted(self.relationships, key=lambda item: item.relationship_id)

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

    @implements_adr("ADR-L-0013")
    def provenance_for_entity(self, entity_id: str) -> DiscoveryProvenance | None:
        """Return semantic provenance for one entity if present."""

        entity = self.find_entity(entity_id)
        return entity.provenance if entity is not None else None

    @implements_adr("ADR-L-0013")
    def canonical_source_ref_for_entity(self, entity_id: str) -> str | None:
        """Return the canonical source reference for one semantic entity if present."""

        entity = self.find_entity(entity_id)
        if entity is None:
            return None
        return entity.canonical_source.source_ref

    @implements_adr("ADR-L-0013")
    def source_refs_for_entity(self, entity_id: str) -> list[SourceRef]:
        """Return deterministic source references for one semantic entity."""

        entity = self.find_entity(entity_id)
        if entity is None:
            return []
        return sorted(
            list(entity.source_refs),
            key=lambda item: (item.source_ref, item.mention_role, item.artifact_path),
        )

    @implements_adr("ADR-L-0013")
    def entity_status(self, entity_id: str) -> str | None:
        """Return one entity status from semantic metadata if present."""

        entity = self.find_entity(entity_id)
        if entity is None:
            return None
        status = (entity.metadata or {}).get("status")
        return str(status) if status is not None else None

    @implements_adr("ADR-L-0013")
    def entity_domains(self, entity_id: str) -> list[str]:
        """Return deterministic semantic domains for one entity."""

        entity = self.find_entity(entity_id)
        if entity is None:
            return []
        domains = (entity.metadata or {}).get("domains", [])
        if not isinstance(domains, list):
            return []
        return sorted(str(domain) for domain in domains)

    @implements_adr("ADR-L-0013")
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

    @implements_adr("ADR-L-0013")
    def adr_status_map(self) -> dict[str, str]:
        """Return deterministic ADR status lookup for validator consumers."""

        result: dict[str, str] = {}
        for entity in self.adr_entities():
            status = self.entity_status(entity.id)
            if status is not None:
                result[entity.id] = status
        return result

    @implements_adr("ADR-L-0013")
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

    @implements_adr("ADR-L-0013")
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

    @implements_adr("ADR-L-0013")
    def unresolved_records(
        self,
        *,
        role: Literal["source", "related", "any"] = "any",
    ) -> list[UnresolvedRecord]:
        """Return deterministic unresolved records across the model, optionally filtered by role."""

        if role == "source":
            unresolved = [item for item in self.unresolved if item.source_entity_id]
        elif role == "related":
            unresolved = [item for item in self.unresolved if item.related_entity_id is not None]
        else:
            unresolved = list(self.unresolved)
        return sorted(unresolved, key=lambda item: item.id)

    @implements_adr("ADR-L-0013")
    def unresolved_for_entity(
        self,
        entity_id: str,
        *,
        role: Literal["source", "related", "any"] = "source",
    ) -> list[UnresolvedRecord]:
        """Return deterministic unresolved records attached to one entity by role."""

        if role == "source":
            unresolved = [item for item in self.unresolved if item.source_entity_id == entity_id]
        elif role == "related":
            unresolved = [item for item in self.unresolved if item.related_entity_id == entity_id]
        else:
            unresolved = [
                item
                for item in self.unresolved
                if item.source_entity_id == entity_id or item.related_entity_id == entity_id
            ]
        return sorted(unresolved, key=lambda item: item.id)

    @implements_adr("ADR-L-0013")
    def unresolved_related_entity_ids(
        self,
        entity_id: str,
        *,
        role: Literal["source", "related", "any"] = "source",
    ) -> list[str]:
        """Return deterministic adjacent entity IDs from unresolved records."""

        related_ids: set[str] = set()
        for item in self.unresolved_for_entity(entity_id, role=role):
            if item.source_entity_id == entity_id and item.related_entity_id:
                related_ids.add(item.related_entity_id)
            elif item.related_entity_id == entity_id:
                related_ids.add(item.source_entity_id)
        return sorted(related_ids)
