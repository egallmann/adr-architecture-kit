from __future__ import annotations

from src.adr_kit.models import (
    CanonicalSource,
    Completeness,
    DiscoveryProvenance,
    Entity,
    EntityOwnership,
    EntityRegistry,
    EntityRelationships,
    EntityType,
    LifecycleStage,
    NormalizedArchitectureModel,
    NormalizedEntity,
    NormalizedEntityRegistry,
    SourceArtifactType,
    SourceRef,
    UnresolvedRecord,
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
        source_refs=[
            SourceRef(
                source_type="logical_adr",
                source_ref="ADR-L-0001#reference",
                artifact_path="adrs/logical/ADR-L-0001.yaml",
                mention_role="reference",
            )
        ],
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
    assert result.canonical_source_ref_for_entity("ADR-L-0001") == "ADR-L-0001#root"
    assert [item.source_ref for item in result.source_refs_for_entity("ADR-L-0001")] == ["ADR-L-0001#reference"]


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


def test_coerce_to_normalized_model_preserves_legacy_ownership_and_source_refs() -> None:
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
                related_adrs=["ADR-L-0002"],
                realized_by=["ADR-PC-0001"],
                ownership=EntityOwnership(
                    architecture_authority="platform-arch",
                    implementation_owners=["team-runtime"],
                ),
                relationships=EntityRelationships(),
            )
        ]
    )

    result = coerce_to_normalized_model(
        registry,
        fingerprint="legacy-ownership",
        architecture_namespace="legacy-scope",
        generator="test",
        extraction_phase="test",
    )

    entity = result.find_entity("COMP-0001")
    assert entity is not None
    assert result.architecture_namespace == "legacy-scope"
    assert entity.metadata["ownership"] == {
        "architecture_authority": "platform-arch",
        "implementation_owners": ["team-runtime"],
    }
    assert [item.source_ref for item in result.source_refs_for_entity("COMP-0001")] == [
        "ADR-L-0002",
        "ADR-PC-0001",
    ]
    assert result.canonical_source_ref_for_entity("COMP-0001") == "ADR-L-0001#COMP-0001"
    provenance = result.provenance_for_entity("COMP-0001")
    assert provenance is not None
    assert provenance.source_ref == "adrs/entities/registry.yaml#COMP-0001"


def test_coerce_to_normalized_model_maps_legacy_implementation_decision_to_decision() -> None:
    registry = EntityRegistry(
        entities=[
            Entity(
                entity_id="DEC-0001",
                entity_type=EntityType.IMPLEMENTATION_DECISION,
                name="Implementation decision",
                introduced_by="ADR-PC-0001",
                lifecycle_stage=LifecycleStage.ACTIVE,
                source_path="adrs/physical-component/ADR-PC-0001.yaml",
                source_artifact_type=SourceArtifactType.PHYSICAL_COMPONENT_ADR,
                domains=["runtime"],
                related_adrs=[],
                realized_by=[],
                relationships=EntityRelationships(),
            )
        ]
    )

    result = coerce_to_normalized_model(
        registry,
        fingerprint="legacy-impl-decision",
        generator="test",
        extraction_phase="test",
    )

    entity = result.find_entity("DEC-0001")
    assert entity is not None
    assert entity.entity_type == "decision"


def test_normalized_model_treats_colon_bearing_ids_and_source_refs_as_opaque() -> None:
    entity = _normalized_entity("workspace:CAP-0001", "capability")
    entity = entity.model_copy(
        update={
            "canonical_source": CanonicalSource(
                source_type="logical_adr",
                source_ref="workspace:ADR-L-0001#workspace:CAP-0001",
                artifact_path="adrs/logical/ADR-L-0001.yaml",
            ),
            "source_refs": [
                SourceRef(
                    source_type="logical_adr",
                    source_ref="workspace:ADR-L-0002#reference",
                    artifact_path="adrs/logical/ADR-L-0002.yaml",
                    mention_role="reference",
                )
            ],
        }
    )
    model = NormalizedArchitectureModel(
        mode="normalized",
        scope_root=".",
        architecture_namespace="workspace",
        fingerprint="opaque-ids",
        entities=[entity],
        relationships=[],
        unresolved=[],
        validation_summary=None,
        source_coverage=None,
    )

    assert model.canonical_source_ref_for_entity("workspace:CAP-0001") == "workspace:ADR-L-0001#workspace:CAP-0001"
    assert [item.source_ref for item in model.source_refs_for_entity("workspace:CAP-0001")] == [
        "workspace:ADR-L-0002#reference"
    ]
    assert model.canonical_adr_refs_for_entity("workspace:CAP-0001") == []


def test_normalized_model_exposes_deterministic_unresolved_traversal() -> None:
    model = NormalizedArchitectureModel(
        mode="normalized",
        scope_root=".",
        architecture_namespace="test",
        fingerprint="unresolved-model",
        entities=[_normalized_entity("COMP-0001", "component"), _normalized_entity("CAP-0001", "capability")],
        relationships=[],
        unresolved=[
            UnresolvedRecord(
                id="GAP-0002",
                gap_class="generator_derived",
                gap_type="missing_relationship_target",
                source_entity_id="COMP-0001",
                related_entity_id="CAP-0001",
                expected_relationship="related_to",
                severity="important",
                provenance=DiscoveryProvenance(
                    source_type="derived_registry",
                    source_ref="ADR-L-0001#COMP-0001",
                    extraction_phase="detect_unresolved",
                    classification="derived",
                    generator="test",
                ),
                evidence=[],
            ),
            UnresolvedRecord(
                id="GAP-0001",
                gap_class="generator_derived",
                gap_type="missing_relationship_target",
                source_entity_id="COMP-0001",
                related_entity_id=None,
                expected_relationship="related_to",
                severity="important",
                provenance=DiscoveryProvenance(
                    source_type="derived_registry",
                    source_ref="ADR-L-0001#COMP-0001",
                    extraction_phase="detect_unresolved",
                    classification="derived",
                    generator="test",
                ),
                evidence=[],
            ),
        ],
        validation_summary=None,
        source_coverage=None,
    )

    assert [item.id for item in model.unresolved_records()] == ["GAP-0001", "GAP-0002"]
    assert [item.id for item in model.unresolved_for_entity("COMP-0001", role="source")] == ["GAP-0001", "GAP-0002"]
    assert [item.id for item in model.unresolved_for_entity("CAP-0001", role="related")] == ["GAP-0002"]
    assert model.unresolved_related_entity_ids("COMP-0001", role="source") == ["CAP-0001"]
