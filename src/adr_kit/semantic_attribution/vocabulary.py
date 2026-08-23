"""Versioned semantic attribution vocabulary selection."""

from __future__ import annotations

import json
from functools import lru_cache
from importlib import resources
from typing import Any, Mapping

RELATIONSHIP_ORDER = ("implements", "enforces", "embodies")


class SemanticAttributionVocabularyError(ValueError):
    """Vocabulary document is missing or malformed."""


@lru_cache(maxsize=2)
def load_semantic_attribution_vocabulary(version: str = "1.5") -> dict[str, Any]:
    """Load the canonical vocabulary for one supported evidence schema version."""

    if version not in {"1.5", "1.6"}:
        raise SemanticAttributionVocabularyError(f"unsupported vocabulary version: {version!r}")
    package = f"adr_kit.schema.v{version.replace('.', '_')}"

    payload = (
        resources.files(package)
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


def relationship_names(version: str = "1.5") -> tuple[str, ...]:
    vocabulary = load_semantic_attribution_vocabulary(version)
    names = tuple(vocabulary["relationships"].keys())
    return names


def allowed_target_entity_types(relationship: str, *, version: str = "1.5") -> frozenset[str]:
    vocabulary = load_semantic_attribution_vocabulary(version)
    spec = vocabulary["relationships"].get(relationship)
    if not isinstance(spec, Mapping):
        raise SemanticAttributionVocabularyError(f"unknown relationship: {relationship}")
    allowed = spec.get("allowed_target_entity_types")
    if not isinstance(allowed, list) or not all(isinstance(item, str) for item in allowed):
        raise SemanticAttributionVocabularyError(
            f"relationship {relationship} is missing allowed_target_entity_types"
        )
    return frozenset(allowed)


def canonical_claims_attribute(version: str = "1.5") -> str:
    vocabulary = load_semantic_attribution_vocabulary(version)
    name = vocabulary.get("canonical_claims_attribute", "__architecture_attribution_claims__")
    if not isinstance(name, str) or not name:
        raise SemanticAttributionVocabularyError("canonical_claims_attribute must be a string")
    return name


def uuid_decorator_name(relationship: str, *, version: str = "1.5") -> str:
    vocabulary = load_semantic_attribution_vocabulary(version)
    spec = vocabulary["relationships"][relationship]
    name = spec["uuid_decorator"]
    if not isinstance(name, str):
        raise SemanticAttributionVocabularyError(f"missing uuid_decorator for {relationship}")
    return name


def uuid_sequence_decorator_name(relationship: str, *, version: str = "1.5") -> str:
    vocabulary = load_semantic_attribution_vocabulary(version)
    spec = vocabulary["relationships"][relationship]
    name = spec["uuid_sequence_decorator"]
    if not isinstance(name, str):
        raise SemanticAttributionVocabularyError(
            f"missing uuid_sequence_decorator for {relationship}"
        )
    return name
