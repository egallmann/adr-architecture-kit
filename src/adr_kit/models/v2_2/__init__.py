"""Normalized-model v2.2 contracts."""

from .normalized_architecture_model import NormalizedArchitectureModelV22
from .normalized_entity import ExtensionPayloadV22, NormalizedEntityV22
from .registries import (
    NormalizedEntityRegistryV22,
    RelationshipRegistryV22,
    RelationshipV22,
    UnresolvedRegistryV22,
)
from .relationship_record import CanonicalRelationshipV22, CompatibilityRelationshipV22

__all__ = [
    "ExtensionPayloadV22",
    "NormalizedEntityV22",
    "CanonicalRelationshipV22",
    "CompatibilityRelationshipV22",
    "NormalizedArchitectureModelV22",
    "NormalizedEntityRegistryV22",
    "RelationshipRegistryV22",
    "RelationshipV22",
    "UnresolvedRegistryV22",
]
