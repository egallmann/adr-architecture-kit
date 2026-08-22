"""Normalized architecture model v2.1."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from ..architecture_discovery import SourceCoverageSummary, UnresolvedRecord, ValidationSummary
from .normalized_entity import NormalizedEntityV21
from .registries import RelationshipV21


class NormalizedArchitectureModelV21(BaseModel):
    schema_version: str = "2.1"
    type: Literal["normalized_architecture_model"] = "normalized_architecture_model"
    mode: Literal["normalized", "legacy"]
    scope_root: str
    architecture_namespace: str | None = None
    fingerprint: str
    entities: list[NormalizedEntityV21] = Field(default_factory=list)
    relationships: list[RelationshipV21] = Field(default_factory=list)
    unresolved: list[UnresolvedRecord] = Field(default_factory=list)
    validation_summary: ValidationSummary | None = None
    source_coverage: SourceCoverageSummary | None = None

    def find_entity(self, entity_id: str) -> NormalizedEntityV21 | None:
        return next((entity for entity in self.entities if entity.id == entity_id), None)

    def find_entity_by_alias_id(self, alias_id: str) -> NormalizedEntityV21 | None:
        return next((entity for entity in self.entities if entity.alias_id == alias_id), None)

    def entities_by_type(self, entity_type: str) -> list[NormalizedEntityV21]:
        return [entity for entity in self.entities if entity.entity_type == entity_type]

    def relationships_for_entity(
        self,
        entity_id: str,
        *,
        relationship_type: str | None = None,
        direction: Literal["any", "incoming", "outgoing"] = "any",
    ) -> list[RelationshipV21]:
        return [
            relationship
            for relationship in self.relationships
            if (relationship_type is None or relationship.relationship_type == relationship_type)
            and (
                direction == "any"
                or (direction == "outgoing" and relationship.from_entity_id == entity_id)
                or (direction == "incoming" and relationship.to_entity_id == entity_id)
            )
        ]
