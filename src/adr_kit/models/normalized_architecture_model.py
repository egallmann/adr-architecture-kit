"""Stable semantic model exposed by the architecture repository boundary."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from .architecture_discovery import (
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

    def relationships_for_entity(self, entity_id: str) -> list[RelationshipRecord]:
        """Return all relationships attached to an entity."""

        return [
            relationship
            for relationship in self.relationships
            if relationship.from_entity_id == entity_id or relationship.to_entity_id == entity_id
        ]

    def unresolved_for_entity(self, entity_id: str) -> list[UnresolvedRecord]:
        """Return unresolved records attached to the entity."""

        return [item for item in self.unresolved if item.source_entity_id == entity_id]
