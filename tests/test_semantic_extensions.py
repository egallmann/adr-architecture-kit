from __future__ import annotations

import pytest

from adr_kit.migrators.consumer_alias_allocation import (
    collision_report,
    validate_consumer_alias_allocations,
    verify_sealed_map,
)
from adr_kit.models.v1_4 import ExtensionEntityV14
from adr_kit.models.v2_1 import (
    CanonicalRelationshipV21,
    CompatibilityRelationshipV21,
    ExtensionPayloadV21,
    NormalizedEntityV21,
)
from adr_kit.semantic_extensions import ExtensionValidationError, validate_extension_type

UUID_A = "018f4f20-0000-7000-8000-000000000001"
UUID_B = "018f4f20-0000-7000-8000-000000000002"
UUID_R = "018f4f20-0000-7000-8000-000000000003"


def test_consumer_allocations_are_independent_and_validation_only() -> None:
    first = validate_consumer_alias_allocations({"registrations": {"acme:widget": "WID"}})
    second = validate_consumer_alias_allocations({"registrations": {"other:gadget": "GAD"}})
    assert first.valid and second.valid
    assert first.candidate_inventory == ({"semantic_type": "acme:widget", "alias_prefix": "WID"},)
    assert second.candidate_inventory == ({"semantic_type": "other:gadget", "alias_prefix": "GAD"},)


def test_extension_type_requires_containing_namespace_and_rejects_core_shadowing() -> None:
    assert validate_extension_type("acme:widget", architecture_namespace="acme") == "acme:widget"
    with pytest.raises(ExtensionValidationError):
        validate_extension_type("foreign:widget", architecture_namespace="acme")
    with pytest.raises(ExtensionValidationError):
        validate_extension_type("acme:decision", architecture_namespace="acme")


def test_extension_payload_is_typed_and_round_trips_exactly() -> None:
    authored = {
        "properties": {"region": "us-east", "rank": 2, "flags": ["a", "b"]},
        "rationale": "consumer-owned meaning",
    }
    payload = ExtensionPayloadV21.model_validate(authored)
    assert payload.model_dump(mode="json") == authored
    entity = ExtensionEntityV14(
        id=UUID_A,
        alias_id="WID-0001",
        alias_name="widget",
        entity_type="acme:widget",
        properties=authored["properties"],
        rationale=authored["rationale"],
    )
    normalized = NormalizedEntityV21(
        id=UUID_A,
        alias_id="WID-0001",
        alias_name="Widget",
        alias_ref="WID-0001:Widget",
        entity_type="acme:widget",
        name="Widget",
        summary="Widget",
        uri="adr://acme/entities/018f4f20-0000-7000-8000-000000000001",
        created_at="2024-01-01T00:00:00Z",
        entity_fingerprint="sha256:" + "0" * 64,
        canonical_source={
            "source_type": "logical_adr",
            "source_ref": "ADR-L-0001",
            "artifact_path": "x.yaml",
        },
        completeness={"status": "complete", "missing_fields": []},
        provenance={
            "source_type": "compiler",
            "source_ref": "x",
            "extraction_phase": "projection",
            "classification": "derived",
            "generator": "test",
        },
        extension=payload,
    )
    assert normalized.extension is not None
    assert normalized.extension.model_dump(mode="json") == authored
    assert entity.model_dump(mode="json")["properties"] == authored["properties"]


def test_core_normalized_entity_cannot_acquire_extension_payload() -> None:
    with pytest.raises(ValueError, match="Core normalized entities"):
        NormalizedEntityV21(
            id=UUID_A,
            alias_id="DEC-0001",
            alias_name="Decision",
            alias_ref="DEC-0001:Decision",
            entity_type="decision",
            name="Decision",
            summary="Decision",
            uri="adr://acme/entities/018f4f20-0000-7000-8000-000000000001",
            created_at="2024-01-01T00:00:00Z",
            entity_fingerprint="sha256:" + "0" * 64,
            canonical_source={
                "source_type": "logical_adr",
                "source_ref": "ADR-L-0001",
                "artifact_path": "x.yaml",
            },
            completeness={"status": "complete", "missing_fields": []},
            provenance={
                "source_type": "compiler",
                "source_ref": "x",
                "extraction_phase": "projection",
                "classification": "derived",
                "generator": "test",
            },
            extension={"properties": {}, "rationale": "invalid on core"},
        )


def test_canonical_and_compatibility_relationships_are_disjoint() -> None:
    canonical = CanonicalRelationshipV21(
        id=UUID_R,
        alias_id="REL-0001",
        alias_name="Widget relation",
        relationship_type="acme:connects",
        from_entity_id=UUID_A,
        to_entity_id=UUID_B,
        canonical_source_ref="ADR-L-0001#extension_relationships[0]",
        extension={"properties": {"mode": "sync"}, "rationale": "consumer relationship"},
    )
    assert canonical.id == UUID_R
    with pytest.raises(ValueError, match="canonical identity"):
        CompatibilityRelationshipV21(
            relationship_id="rel-" + "0" * 64,
            assertion_id="asrt-" + "0" * 64,
            relationship_type="acme:connects",
            from_entity_id=UUID_A,
            to_entity_id=UUID_B,
            provenance_classification="explicit",
            canonical_source_ref="legacy",
        )


def test_hash_only_legacy_relationship_cannot_be_canonical_graph_state() -> None:
    legacy = CompatibilityRelationshipV21(
        relationship_id="rel-" + "0" * 64,
        assertion_id="asrt-" + "0" * 64,
        relationship_type="references",
        from_entity_id=UUID_A,
        to_entity_id=UUID_B,
        provenance_classification="explicit",
        canonical_source_ref="legacy",
    )
    assert legacy.record_kind == "compatibility"
    assert not hasattr(legacy, "id")


def test_feature_gate_can_stop_before_sealed_migration() -> None:
    # The validation-only report is the completed milestone; no map is sealed
    # and no corpus mutation is implied by this API.
    report = validate_consumer_alias_allocations({"registrations": {"acme:widget": "WID"}})
    assert report.valid
    assert report.candidate_inventory
    assert collision_report(
        [{"id": UUID_A, "alias_id": "WID-0001"}, {"id": UUID_A, "alias_id": "WID-0001"}]
    )
    with pytest.raises(ValueError, match="not SEALED"):
        verify_sealed_map({"status": "candidate"})
