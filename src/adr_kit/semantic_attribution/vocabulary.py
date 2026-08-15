"""Mechanical v1.5 semantic attribution vocabulary."""

from __future__ import annotations

import json
from functools import lru_cache
from importlib import resources
from typing import Any, Mapping

RELATIONSHIP_ORDER = ("implements", "enforces", "embodies")


class SemanticAttributionVocabularyError(ValueError):
    """Vocabulary document is missing or malformed."""


@lru_cache(maxsize=1)
def load_semantic_attribution_vocabulary() -> dict[str, Any]:
    """Load the packaged v1.5 vocabulary (byte-identical to canonical evidence-attribution)."""

    payload = (
        resources.files("adr_kit.schema.v1_5")
        .joinpath("semantic-attribution-vocabulary.json")
        .read_text(encoding="utf-8")
    )
    data = json.loads(payload)
    if not isinstance(data, dict):
        raise SemanticAttributionVocabularyError("vocabulary document must be an object")
    relationships = data.get("relationships")
    if not isinstance(relationships, dict) or not relationships:
        raise SemanticAttributionVocabularyError("vocabulary is missing relationships")
    return data


def relationship_names() -> tuple[str, ...]:
    vocabulary = load_semantic_attribution_vocabulary()
    names = tuple(vocabulary["relationships"].keys())
    return names


def allowed_target_entity_types(relationship: str) -> frozenset[str]:
    vocabulary = load_semantic_attribution_vocabulary()
    spec = vocabulary["relationships"].get(relationship)
    if not isinstance(spec, Mapping):
        raise SemanticAttributionVocabularyError(f"unknown relationship: {relationship}")
    allowed = spec.get("allowed_target_entity_types")
    if not isinstance(allowed, list) or not all(isinstance(item, str) for item in allowed):
        raise SemanticAttributionVocabularyError(
            f"relationship {relationship} is missing allowed_target_entity_types"
        )
    return frozenset(allowed)


def canonical_claims_attribute() -> str:
    vocabulary = load_semantic_attribution_vocabulary()
    name = vocabulary.get("canonical_claims_attribute", "__architecture_attribution_claims__")
    if not isinstance(name, str) or not name:
        raise SemanticAttributionVocabularyError("canonical_claims_attribute must be a string")
    return name


def uuid_decorator_name(relationship: str) -> str:
    vocabulary = load_semantic_attribution_vocabulary()
    spec = vocabulary["relationships"][relationship]
    name = spec["uuid_decorator"]
    if not isinstance(name, str):
        raise SemanticAttributionVocabularyError(f"missing uuid_decorator for {relationship}")
    return name


def uuid_sequence_decorator_name(relationship: str) -> str:
    vocabulary = load_semantic_attribution_vocabulary()
    spec = vocabulary["relationships"][relationship]
    name = spec["uuid_sequence_decorator"]
    if not isinstance(name, str):
        raise SemanticAttributionVocabularyError(
            f"missing uuid_sequence_decorator for {relationship}"
        )
    return name
