"""Pydantic v2.0 normalized semantic models with UUID identity."""

from .normalized_entity import NormalizedEntityV2
from .relationship_record import RelationshipRecordV2
from .normalized_architecture_model import NormalizedArchitectureModelV2
from .registries import (
    NormalizedEntityRegistryV2,
    RelationshipRegistryV2,
    UnresolvedRegistryV2,
)

__all__ = [
    "NormalizedEntityV2",
    "RelationshipRecordV2",
    "NormalizedArchitectureModelV2",
    "NormalizedEntityRegistryV2",
    "RelationshipRegistryV2",
    "UnresolvedRegistryV2",
]
