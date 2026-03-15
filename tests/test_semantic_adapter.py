from __future__ import annotations

from src.adr_kit.models import (
    CanonicalSource,
    Completeness,
    DiscoveryProvenance,
    Entity,
    EntityRegistry,
    EntityRelationships,
    EntityType,
    LifecycleStage,
    NormalizedArchitectureModel,
    NormalizedEntity,
    NormalizedEntityRegistry,
    SourceArtifactType,
)
from src.adr_kit.repository.semantic_adapter import coerce_to_normalized_model


def _normalized_entity(entity_id: str, entity_type: str = "adr") -> NormalizedEntity:
    return NormalizedEntity(
        id=entity_id,
        entity_type=entity_type,  # type: ignore[arg-type]
        name=entity_id,
        summary=entity_id,
        canonical_source=CanonicalSource(
            source_type="logical_adr",
            source_ref=f"{entity_id}#root" if entity_id.startswith("ADR-") else f"ADR-L-0001#{entity_id}",
            artifact_path="adrs/logical/ADR-L-0001.yaml",
        ),
        metadata={"status": "accepted", "domains": ["test"]},
        completeness=Completeness(status="complete", missing_fields=[]),
        provenance=DiscoveryProvenance(
            source_type="logical_adr",
            source_ref=f"ADR-L-0001#{entity_id}",
            extraction_phase="test",
            classification="explicit",
            generator="test",
        ),
    )


def test_coerce_to_normalized_model_preserves_normalized_model_input() -> None:
    model = NormalizedArchitectureModel(
        mode="normalized",
        scope_root=".",
        architecture_namespace="test",
        fingerprint="existing-model",
        entities=[_normalized_entity("ADR-L-0001")],
        relationships=[],
        unresolved=[],
        validation_summary=None,
        source_coverage=None,
    )

    result = coerce_to_normalized_model(
        model,
        fingerprint="ignored",
        generator="test",
        extraction_phase="test",
    )

    assert result.type == "normalized_architecture_model"
    assert result.mode == "normalized"
    assert result.fingerprint == "existing-model"
    assert [entity.id for entity in result.entities] == ["ADR-L-0001"]


def test_coerce_to_normalized_model_adapts_normalized_entity_registry() -> None:
    registry = NormalizedEntityRegistry(entities=[_normalized_entity("ADR-L-0001")])

    result = coerce_to_normalized_model(
        registry,
        fingerprint="registry-adapter",
        architecture_namespace="test",
        generator="test",
        extraction_phase="test",
    )

    assert result.mode == "normalized"
    assert result.fingerprint == "registry-adapter"
    assert result.adr_status_map() == {"ADR-L-0001": "accepted"}


def test_coerce_to_normalized_model_adapts_legacy_entity_registry() -> None:
    registry = EntityRegistry(
        entities=[
            Entity(
                entity_id="COMP-0001",
                entity_type=EntityType.COMPONENT,
                name="Component",
                introduced_by="ADR-L-0001",
                lifecycle_stage=LifecycleStage.ACTIVE,
                source_path="adrs/logical/ADR-L-0001.yaml",
                source_artifact_type=SourceArtifactType.LOGICAL_ADR,
                domains=["runtime"],
                related_adrs=["ADR-L-0001"],
                realized_by=[],
                relationships=EntityRelationships(depends_on=["CAP-0001"], implements=["CAP-0001"], realizes=[]),
            ),
            Entity(
                entity_id="CAP-0001",
                entity_type=EntityType.CAPABILITY,
                name="Capability",
                introduced_by="ADR-L-0001",
                lifecycle_stage=LifecycleStage.ACTIVE,
                source_path="adrs/logical/ADR-L-0001.yaml",
                source_artifact_type=SourceArtifactType.LOGICAL_ADR,
                domains=["runtime"],
                related_adrs=["ADR-L-0001"],
                realized_by=[],
                relationships=EntityRelationships(),
            ),
        ]
    )

    result = coerce_to_normalized_model(
        registry,
        fingerprint="legacy-adapter",
        generator="test",
        extraction_phase="test",
    )

    assert result.mode == "legacy"
    assert [entity.id for entity in result.entities] == ["COMP-0001", "CAP-0001"]
    assert result.canonical_adr_refs_for_entity("COMP-0001") == ["ADR-L-0001"]
    assert [relationship.relationship_id for relationship in result.relationships] == [
        "declared_in:CAP-0001:ADR-L-0001",
        "declared_in:COMP-0001:ADR-L-0001",
        "enables:COMP-0001:CAP-0001",
        "related_to:COMP-0001:CAP-0001",
    ]
