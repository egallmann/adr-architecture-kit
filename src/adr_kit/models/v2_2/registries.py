"""Versioned v2.2 registry wrappers."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field

from ..architecture_discovery import UnresolvedRecord
from .normalized_entity import NormalizedEntityV22
from .relationship_record import CanonicalRelationshipV22, CompatibilityRelationshipV22

RelationshipV22 = Annotated[
    CanonicalRelationshipV22 | CompatibilityRelationshipV22,
    Field(discriminator="record_kind"),
]


class NormalizedEntityRegistryV22(BaseModel):
    schema_version: str = "2.2"
    type: Literal["normalized_entity_registry"] = "normalized_entity_registry"
    entities: list[NormalizedEntityV22] = Field(default_factory=list)


class RelationshipRegistryV22(BaseModel):
    schema_version: str = "2.2"
    type: Literal["relationship_registry"] = "relationship_registry"
    relationships: list[RelationshipV22] = Field(default_factory=list)


class UnresolvedRegistryV22(BaseModel):
    schema_version: str = "2.2"
    type: Literal["unresolved_registry"] = "unresolved_registry"
    unresolved: list[UnresolvedRecord] = Field(default_factory=list)
