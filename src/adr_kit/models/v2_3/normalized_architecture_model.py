"""Normalized architecture model v2.3."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from ..architecture_discovery import SourceCoverageSummary, UnresolvedRecord, ValidationSummary
from ..v2_2.registries import RelationshipV22
from .normalized_entity import NormalizedEntityVariantV23


class NormalizedArchitectureModelV23(BaseModel):
    schema_version: str = "2.3"
    type: Literal["normalized_architecture_model"] = "normalized_architecture_model"
    mode: Literal["normalized", "legacy"]
    scope_root: str
    architecture_namespace: str | None = None
    fingerprint: str
    entities: list[NormalizedEntityVariantV23] = Field(default_factory=list)
    relationships: list[RelationshipV22] = Field(default_factory=list)
    unresolved: list[UnresolvedRecord] = Field(default_factory=list)
    validation_summary: ValidationSummary | None = None
    source_coverage: SourceCoverageSummary | None = None

    def find_entity(self, entity_id: str) -> NormalizedEntityVariantV23 | None:
        return next((entity for entity in self.entities if entity.id == entity_id), None)

    def find_entity_by_alias_id(self, alias_id: str) -> NormalizedEntityVariantV23 | None:
        return next((entity for entity in self.entities if entity.alias_id == alias_id), None)

    def entities_by_type(self, entity_type: str) -> list[NormalizedEntityVariantV23]:
        return [entity for entity in self.entities if entity.entity_type == entity_type]
