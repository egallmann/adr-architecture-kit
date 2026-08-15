"""v1.5 evidence vocabulary is one mechanical contract across kit surfaces."""

from __future__ import annotations

import json
from pathlib import Path

from adr_kit import decorators
from adr_kit.attribution_shim_generator import generate_shim
from adr_kit.models.implementation_attribution import SemanticAttributionClaim
from adr_kit.semantic_attribution.vocabulary import (
    allowed_target_entity_types,
    load_semantic_attribution_vocabulary,
    relationship_names,
    uuid_decorator_name,
    uuid_sequence_decorator_name,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
CANONICAL = REPO_ROOT / "schema" / "evidence-attribution" / "v1.5" / "semantic-attribution-vocabulary.json"
EVIDENCE_SCHEMA = REPO_ROOT / "schema" / "evidence-attribution" / "v1.5" / "implementation-attribution-evidence.schema.json"
RELATIONSHIP_REGISTRY = REPO_ROOT / "schema" / "normalized-model" / "v1.1" / "relationship-registry.schema.json"


def test_packaged_vocabulary_matches_canonical_bytes() -> None:
    packaged = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "adr_kit"
        / "schema"
        / "v1_5"
        / "semantic-attribution-vocabulary.json"
    )
    assert CANONICAL.read_bytes() == packaged.read_bytes()
    assert (
        json.loads(CANONICAL.read_text(encoding="utf-8")) == load_semantic_attribution_vocabulary()
    )


def test_evidence_schema_relationship_enum_matches_vocabulary() -> None:
    schema = json.loads(EVIDENCE_SCHEMA.read_text(encoding="utf-8"))
    enum = schema["properties"]["records"]["items"]["properties"]["claims"]["items"]["properties"][
        "relationship"
    ]["enum"]
    assert tuple(enum) == relationship_names()


def test_pydantic_claim_relationships_match_vocabulary() -> None:
    names = set(relationship_names())
    annotation = SemanticAttributionClaim.model_fields["relationship"].annotation
    assert set(annotation.__args__) == names  # type: ignore[union-attr]


def test_decorator_names_match_vocabulary() -> None:
    for relationship in relationship_names():
        assert hasattr(decorators, uuid_decorator_name(relationship))
        assert hasattr(decorators, uuid_sequence_decorator_name(relationship))
    for name in load_semantic_attribution_vocabulary()["legacy_decorators"]:
        assert hasattr(decorators, name)


def test_generated_shims_contain_vocabulary_decorator_names() -> None:
    python_shim = generate_shim("python")
    typescript_shim = generate_shim("typescript")
    vocabulary = load_semantic_attribution_vocabulary()
    for relationship, spec in vocabulary["relationships"].items():
        assert spec["uuid_decorator"] in python_shim
        assert spec["uuid_sequence_decorator"] in python_shim
        assert spec["uuid_decorator"] in typescript_shim
        assert spec["uuid_sequence_decorator"] in typescript_shim
        assert relationship in python_shim
    for name in vocabulary["legacy_decorators"]:
        assert f"def {name}" in python_shim
        assert f"export function {name}" in typescript_shim


def test_parity_does_not_require_v11_relationship_registry_alignment() -> None:
    """v1.5 evidence verbs are not RelationshipRecordV2 / v1.1 registry enums."""
    registry = json.loads(RELATIONSHIP_REGISTRY.read_text(encoding="utf-8"))
    dumped = json.dumps(registry)
    assert "implements" in dumped or "embodies" in dumped
    # Shared English may overlap; this test must not require enum identity with v1.5.


def test_matrix_matches_authorized_pairs() -> None:
    assert allowed_target_entity_types("implements") == frozenset(
        {
            "adr",
            "decision",
            "capability",
            "contract",
            "interface",
            "implementation_decision",
        }
    )
    assert allowed_target_entity_types("enforces") == frozenset({"invariant"})
    assert allowed_target_entity_types("embodies") == frozenset({"system", "component", "boundary"})
