"""Semantic implementation attribution helpers."""

from typing import Any

from .vocabulary import (
    allowed_target_entity_types,
    canonical_claims_attribute,
    load_semantic_attribution_vocabulary,
    relationship_names,
)

__all__ = [
    "AttributionNormalizationError",
    "allowed_target_entity_types",
    "canonical_claims_attribute",
    "evidence_to_canonical_dict",
    "load_semantic_attribution_vocabulary",
    "normalize_attribution_evidence",
    "relationship_names",
    "relationship_occurrence_counts",
    "unique_semantic_edges",
]


def __getattr__(name: str) -> Any:
    if name in {
        "AttributionNormalizationError",
        "evidence_to_canonical_dict",
        "normalize_attribution_evidence",
        "relationship_occurrence_counts",
        "unique_semantic_edges",
    }:
        from . import normalize

        return getattr(normalize, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
