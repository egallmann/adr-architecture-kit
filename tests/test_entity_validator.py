from __future__ import annotations

from pathlib import Path

from src.adr_kit.models import (
    CanonicalSource,
    Completeness,
    DiscoveryProvenance,
    NormalizedArchitectureModel,
    NormalizedEntity,
    RelationshipRecord,
    UnresolvedRecord,
)
from src.adr_kit.validators import EntityValidator


def _entity(entity_id: str, entity_type: str) -> NormalizedEntity:
    return NormalizedEntity(
        id=entity_id,
        entity_type=entity_type,  # type: ignore[arg-type]
        name=entity_id,
        summary=entity_id,
        canonical_source=CanonicalSource(
            source_type="logical_adr",
            source_ref=f"ADR-L-0001#{entity_id}",
            artifact_path="adrs/logical/ADR-L-0001.yaml",
        ),
        metadata={"status": "accepted"},
        completeness=Completeness(status="complete", missing_fields=[]),
        provenance=DiscoveryProvenance(
            source_type="adr",
            source_ref=f"ADR-L-0001#{entity_id}",
            extraction_phase="test",
            classification="explicit",
            generator="test",
        ),
    )


def _model(
    *,
    entities: list[NormalizedEntity],
    relationships: list[RelationshipRecord] | None = None,
    unresolved: list[UnresolvedRecord] | None = None,
) -> NormalizedArchitectureModel:
    return NormalizedArchitectureModel(
        mode="normalized",
        scope_root=".",
        architecture_namespace="test",
        fingerprint="test",
        entities=entities,
        relationships=relationships or [],
        unresolved=unresolved or [],
        validation_summary=None,
        source_coverage=None,
    )


def test_validate_entity_relationships_accepts_semantic_model() -> None:
    validator = EntityValidator()
    model = _model(
        entities=[_entity("CAP-0001", "capability"), _entity("COMP-0001", "component")],
        relationships=[
            RelationshipRecord(
                relationship_id="related_to:COMP-0001:CAP-0001",
                relationship_type="related_to",
                from_entity_id="COMP-0001",
                to_entity_id="CAP-0001",
                provenance_classification="explicit",
                evidence=[],
                canonical_source_ref="ADR-L-0001#COMP-0001",
            )
        ],
    )

    assert validator.validate_entity_relationships(model) == []


def test_validate_entity_relationships_reports_unknown_targets_and_unresolved_sources() -> None:
    validator = EntityValidator()
    model = _model(
        entities=[_entity("CAP-0001", "capability")],
        relationships=[
            RelationshipRecord(
                relationship_id="related_to:CAP-0001:COMP-4040",
                relationship_type="related_to",
                from_entity_id="CAP-0001",
                to_entity_id="COMP-4040",
                provenance_classification="derived",
                evidence=[],
                canonical_source_ref="ADR-L-0001#CAP-0001",
            )
        ],
        unresolved=[
            UnresolvedRecord(
                id="GAP-0001",
                gap_class="generator_derived",
                gap_type="missing_relationship_target",
                source_entity_id="COMP-4040",
                related_entity_id="CAP-0001",
                expected_relationship="related_to",
                severity="important",
                provenance=DiscoveryProvenance(
                    source_type="derived_registry",
                    source_ref="ADR-L-0001#CAP-0001",
                    extraction_phase="detect_unresolved",
                    classification="derived",
                    generator="test",
                ),
                evidence=[],
            )
        ],
    )

    errors = validator.validate_entity_relationships(model)

    assert any("unknown target entity COMP-4040" in error for error in errors)
    assert any("unknown source entity COMP-4040" in error for error in errors)


def test_entity_validator_no_longer_declares_private_legacy_adapter() -> None:
    source = Path("src/adr_kit/validators/entity_validator.py").read_text(encoding="utf-8")

    assert "def _legacy_registry_to_model(" not in source
    assert "def _relationship_records_for_targets(" not in source
