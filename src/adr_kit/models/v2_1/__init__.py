"""Normalized-model v2.1 contracts for canonical extensions."""

from .normalized_architecture_model import NormalizedArchitectureModelV21
from .normalized_entity import ExtensionPayloadV21, NormalizedEntityV21
from .registries import (
    NormalizedEntityRegistryV21,
    RelationshipRegistryV21,
    UnresolvedRegistryV21,
)
from .relationship_record import (
    CanonicalRelationshipV21,
    CompatibilityRelationshipV21,
)

__all__ = [
    "ExtensionPayloadV21",
    "NormalizedEntityV21",
    "CanonicalRelationshipV21",
    "CompatibilityRelationshipV21",
    "NormalizedArchitectureModelV21",
    "NormalizedEntityRegistryV21",
    "RelationshipRegistryV21",
    "UnresolvedRegistryV21",
]
