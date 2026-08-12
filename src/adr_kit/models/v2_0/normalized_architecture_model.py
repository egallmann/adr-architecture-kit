"""Normalized architecture model v2.0 with UUID identity."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from ..architecture_discovery import (
    SourceCoverageSummary,
    UnresolvedRecord,
    ValidationSummary,
)
from ...decorators import implements_adr
from .normalized_entity import NormalizedEntityV2
from .relationship_record import RelationshipRecordV2


@implements_adr("ADR-L-0019", "ADR-L-0013")
class NormalizedArchitectureModelV2(BaseModel):
    """UUID-identity-bearing semantic view over one loaded architecture scope."""

    schema_version: str = "2.0"
    type: Literal["normalized_architecture_model"] = "normalized_architecture_model"
    mode: Literal["normalized", "legacy"]
    scope_root: str
    architecture_namespace: str | None = None
    fingerprint: str
    entities: list[NormalizedEntityV2] = Field(default_factory=list)
    relationships: list[RelationshipRecordV2] = Field(default_factory=list)
    unresolved: list[UnresolvedRecord] = Field(default_factory=list)
    validation_summary: ValidationSummary | None = None
    source_coverage: SourceCoverageSummary | None = None

    def entity_ids(self) -> list[str]:
        """Return deterministic UUID entity IDs."""
        return sorted(entity.id for entity in self.entities)

    def relationship_records(self) -> list[RelationshipRecordV2]:
        """Return deterministic relationships sorted by relationship_id."""
        return sorted(self.relationships, key=lambda r: r.relationship_id)

    def find_entity(self, entity_id: str) -> NormalizedEntityV2 | None:
        """Find entity by UUID."""
        return next((e for e in self.entities if e.id == entity_id), None)

    def find_entity_by_alias_id(self, alias_id: str) -> NormalizedEntityV2 | None:
        """Find entity by legacy alias_id."""
        return next((e for e in self.entities if e.alias_id == alias_id), None)

    def entities_by_type(self, entity_type: str) -> list[NormalizedEntityV2]:
        """Return entities matching the provided semantic type."""
        return [e for e in self.entities if e.entity_type == entity_type]

    def relationships_for_entity(
        self,
        entity_id: str,
        *,
        relationship_type: str | None = None,
        direction: Literal["any", "incoming", "outgoing"] = "any",
    ) -> list[RelationshipRecordV2]:
        """Return deterministic relationships attached to an entity."""
        rels = [
            r
            for r in self.relationships
            if (
                direction == "any"
                and (r.from_entity_id == entity_id or r.to_entity_id == entity_id)
            )
            or (direction == "incoming" and r.to_entity_id == entity_id)
            or (direction == "outgoing" and r.from_entity_id == entity_id)
        ]
        if relationship_type is not None:
            rels = [r for r in rels if r.relationship_type == relationship_type]
        return sorted(rels, key=lambda r: r.relationship_id)
