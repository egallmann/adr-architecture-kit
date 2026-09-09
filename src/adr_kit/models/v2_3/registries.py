"""Versioned v2.3 registry wrappers."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field

from ..architecture_discovery import UnresolvedRecord
from ..v2_2.relationship_record import CanonicalRelationshipV22, CompatibilityRelationshipV22
from .normalized_entity import NormalizedEntityVariantV23

RelationshipV23 = Annotated[
    CanonicalRelationshipV22 | CompatibilityRelationshipV22,
    Field(discriminator="record_kind"),
]


class NormalizedEntityRegistryV23(BaseModel):
    schema_version: str = "2.3"
    type: Literal["normalized_entity_registry"] = "normalized_entity_registry"
    entities: list[NormalizedEntityVariantV23] = Field(default_factory=list)


class RelationshipRegistryV23(BaseModel):
    schema_version: str = "2.3"
    type: Literal["relationship_registry"] = "relationship_registry"
    relationships: list[RelationshipV23] = Field(default_factory=list)


class UnresolvedRegistryV23(BaseModel):
    schema_version: str = "2.3"
    type: Literal["unresolved_registry"] = "unresolved_registry"
    unresolved: list[UnresolvedRecord] = Field(default_factory=list)
