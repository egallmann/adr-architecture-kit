"""Versioned v2.1 registry wrappers."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field

from ..architecture_discovery import UnresolvedRecord
from .normalized_entity import NormalizedEntityV21
from .relationship_record import CanonicalRelationshipV21, CompatibilityRelationshipV21

RelationshipV21 = Annotated[
    CanonicalRelationshipV21 | CompatibilityRelationshipV21,
    Field(discriminator="record_kind"),
]


class NormalizedEntityRegistryV21(BaseModel):
    schema_version: str = "2.1"
    type: Literal["normalized_entity_registry"] = "normalized_entity_registry"
    entities: list[NormalizedEntityV21] = Field(default_factory=list)


class RelationshipRegistryV21(BaseModel):
    schema_version: str = "2.1"
    type: Literal["relationship_registry"] = "relationship_registry"
    relationships: list[RelationshipV21] = Field(default_factory=list)


class UnresolvedRegistryV21(BaseModel):
    schema_version: str = "2.1"
    type: Literal["unresolved_registry"] = "unresolved_registry"
    unresolved: list[UnresolvedRecord] = Field(default_factory=list)

