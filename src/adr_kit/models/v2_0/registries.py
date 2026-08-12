"""Versioned registry wrappers for model 2.0."""

from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel, Field

from ..architecture_discovery import UnresolvedRecord
from .normalized_entity import NormalizedEntityV2
from .relationship_record import RelationshipRecordV2


class NormalizedEntityRegistryV2(BaseModel):
    """Registry of UUID-identity-bearing normalized entities (v2.0)."""

    schema_version: str = "2.0"
    type: Literal["normalized_entity_registry"] = "normalized_entity_registry"
    entities: List[NormalizedEntityV2] = Field(default_factory=list)


class RelationshipRegistryV2(BaseModel):
    """Registry of UUID-endpoint relationships (v2.0)."""

    schema_version: str = "2.0"
    type: Literal["relationship_registry"] = "relationship_registry"
    relationships: List[RelationshipRecordV2] = Field(default_factory=list)


class UnresolvedRegistryV2(BaseModel):
    """Unresolved registry (structurally identical to 1.1 for now)."""

    schema_version: str = "2.0"
    type: Literal["unresolved_registry"] = "unresolved_registry"
    unresolved: List[UnresolvedRecord] = Field(default_factory=list)
