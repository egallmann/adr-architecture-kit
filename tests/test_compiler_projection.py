from __future__ import annotations

from adr_kit.compiler.backend.projection import (
    build_relationship_summary,
    project_entity,
    project_relationship,
    project_unresolved,
)
from adr_kit.compiler.ir import IREntity, IRRelationship, IRUnresolved, RelGraph
from adr_kit.models.architecture_discovery import CanonicalSource, DiscoveryProvenance
from adr_kit.parser import ADRParser
from adr_kit.repository.registry_loader import (
    load_architecture_index,
    load_normalized_entity_registry,
    load_relationship_registry,
    load_unresolved_registry,
)
from adr_kit.repository.registry_paths import discover_repository_paths, resolve_index_reference
from tests.golden.helpers import generate_deterministic_outputs


def _load_generated_bundle(scope_root):
    parser = ADRParser()
    paths = discover_repository_paths(scope_root)
    architecture_index = load_architecture_index(parser, paths.architecture_index)
    entity_registry = load_normalized_entity_registry(
        parser,
        resolve_index_reference(scope_root, architecture_index.entity_registry_path),
    )
    relationship_registry = load_relationship_registry(
        parser,
        resolve_index_reference(scope_root, architecture_index.relationship_registry_path),
    )
    unresolved_registry = load_unresolved_registry(
        parser,
        resolve_index_reference(scope_root, architecture_index.unresolved_registry_path),
    )
    return architecture_index, entity_registry, relationship_registry, unresolved_registry


def _repo_root():
    return __import__("pathlib").Path(__file__).resolve().parents[1]


def test_build_relationship_summary_matches_current_registry_shape(tmp_path):
    generate_deterministic_outputs(_repo_root(), tmp_path / "workspace")
    _, entity_registry, relationship_registry, _ = _load_generated_bundle(tmp_path / "workspace")

    rel_graph = RelGraph()
    for relationship in relationship_registry.relationships:
        rel_graph.add(
            IRRelationship(
                relationship_id=relationship.relationship_id,
                relationship_type=relationship.relationship_type,
                from_entity_id=relationship.from_entity_id,
                to_entity_id=relationship.to_entity_id,
                provenance_classification=relationship.provenance_classification,
                evidence=list(relationship.evidence),
                canonical_source_ref=relationship.canonical_source_ref,
                confidence=relationship.confidence,
                metadata=dict(relationship.metadata),
            )
        )

    for entity in entity_registry.entities:
        assert build_relationship_summary(entity.id, rel_graph).model_dump(mode="json") == entity.relationships.model_dump(mode="json")


def test_projection_round_trips_current_registry_models(tmp_path):
    generate_deterministic_outputs(_repo_root(), tmp_path / "workspace")
    _, entity_registry, relationship_registry, unresolved_registry = _load_generated_bundle(tmp_path / "workspace")

    rel_graph = RelGraph()
    for relationship in relationship_registry.relationships:
        rel_graph.add(
            IRRelationship(
                relationship_id=relationship.relationship_id,
                relationship_type=relationship.relationship_type,
                from_entity_id=relationship.from_entity_id,
                to_entity_id=relationship.to_entity_id,
                provenance_classification=relationship.provenance_classification,
                evidence=list(relationship.evidence),
                canonical_source_ref=relationship.canonical_source_ref,
                confidence=relationship.confidence,
                metadata=dict(relationship.metadata),
            )
        )

    projected_entities = [
        project_entity(
            IREntity(
                id=entity.id,
                entity_type=entity.entity_type,
                name=entity.name,
                summary=entity.summary,
                canonical_source=entity.canonical_source,
                source_refs=list(entity.source_refs),
                metadata=dict(entity.metadata),
                completeness=entity.completeness,
                provenance=entity.provenance,
            ),
            rel_graph,
        ).model_dump(mode="json")
        for entity in entity_registry.entities
    ]
    projected_relationships = [
        project_relationship(
            IRRelationship(
                relationship_id=relationship.relationship_id,
                relationship_type=relationship.relationship_type,
                from_entity_id=relationship.from_entity_id,
                to_entity_id=relationship.to_entity_id,
                provenance_classification=relationship.provenance_classification,
                evidence=list(relationship.evidence),
                canonical_source_ref=relationship.canonical_source_ref,
                confidence=relationship.confidence,
                metadata=dict(relationship.metadata),
            )
        ).model_dump(mode="json")
        for relationship in relationship_registry.relationships
    ]
    projected_unresolved = [
        project_unresolved(
            IRUnresolved(
                id=item.id,
                gap_class=item.gap_class,
                gap_type=item.gap_type,
                source_entity_id=item.source_entity_id,
                related_entity_id=item.related_entity_id,
                expected_relationship=item.expected_relationship,
                severity=item.severity,
                provenance=item.provenance,
                evidence=list(item.evidence),
                suggested_resolution=item.suggested_resolution,
            )
        ).model_dump(mode="json")
        for item in unresolved_registry.unresolved
    ]

    assert projected_entities == [entity.model_dump(mode="json") for entity in entity_registry.entities]
    assert projected_relationships == [item.model_dump(mode="json") for item in relationship_registry.relationships]
    assert projected_unresolved == [item.model_dump(mode="json") for item in unresolved_registry.unresolved]


def test_project_entity_skips_non_registry_ir_types():
    entity = IREntity(
        id="CONST-1000",
        entity_type="constraint",
        name="Constraint",
        summary="Not emitted yet.",
        canonical_source=CanonicalSource(
            source_type="logical_adr",
            source_ref="ADR-L-0001#CONST-1000",
            artifact_path="adrs/logical/ADR-L-0001.yaml",
        ),
        provenance=DiscoveryProvenance(
            source_type="logical_adr",
            source_ref="ADR-L-0001#CONST-1000",
            extraction_phase="test",
            classification="explicit",
            generator="test",
        ),
    )

    assert project_entity(entity) is None
