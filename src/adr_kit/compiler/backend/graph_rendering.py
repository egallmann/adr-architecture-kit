"""Compiler-owned architecture graph rendering helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import yaml

from ...integrity import (
    ArtifactKind,
    GENERATED_MARKER,
    HASH_ALGORITHM,
    INTEGRITY_SCHEMA_VERSION,
    GeneratorIdentity,
    build_yaml_header,
    compute_rendered_hash,
    compute_source_hash,
)
from ...models import ArchitectureGraph, ArchitectureGraphEdge, ArchitectureGraphNode
from ...scope import ProjectScope
from ..frontend.builder import FrontendBuildResult
from .manifest_rendering import discover_manifest_source_inputs
from .projection import PROJECTABLE_ENTITY_TYPES, project_entity, project_relationship

GRAPH_GENERATOR_IDENTITY = GeneratorIdentity("adr-architecture-graph", 1)


def build_architecture_graph(build_result: FrontendBuildResult) -> ArchitectureGraph:
    """Project the additive architecture graph from compiler-owned IR."""

    generated_at = build_result.model.metadata.generated_at or datetime.now(timezone.utc).replace(
        microsecond=0
    )
    projected_entities = [
        projected
        for entity in build_result.model.entities.values()
        if entity.entity_type in PROJECTABLE_ENTITY_TYPES
        and (projected := project_entity(entity, build_result.model.relationships)) is not None
    ]
    nodes = [
        ArchitectureGraphNode(
            id=entity.id,
            entity_type=entity.entity_type,
            name=entity.name,
            canonical_source=entity.canonical_source,
        )
        for entity in projected_entities
    ]
    node_ids = {node.id for node in nodes}
    edges = [
        ArchitectureGraphEdge(
            relationship_id=relationship.relationship_id,
            assertion_id=relationship.assertion_id,
            relationship_type=relationship.relationship_type,
            source_entity_id=relationship.from_entity_id,
            target_entity_id=relationship.to_entity_id,
            provenance_classification=relationship.provenance_classification,
            evidence=list(relationship.evidence),
            canonical_source_ref=relationship.canonical_source_ref,
            source_pointer=relationship.source_pointer,
            confidence=relationship.confidence,
            metadata=dict(relationship.metadata),
        )
        for relationship in (
            project_relationship(item) for item in build_result.model.relationships.values()
        )
        if relationship.from_entity_id in node_ids and relationship.to_entity_id in node_ids
    ]
    return ArchitectureGraph(
        architecture_namespace=build_result.namespace,
        generated_at=generated_at,
        nodes=sorted(nodes, key=lambda item: item.id),
        edges=sorted(edges, key=lambda item: item.relationship_id),
    )


def render_graph_yaml(graph: ArchitectureGraph) -> str:
    """Render the architecture graph body without the integrity header."""

    return yaml.safe_dump(
        graph.model_dump(mode="json", exclude_none=True),
        sort_keys=False,
        allow_unicode=True,
    )


def discover_graph_source_inputs(scope: ProjectScope) -> list[Path]:
    """Discover canonical source inputs for the architecture graph artifact."""

    return discover_manifest_source_inputs(scope.adr_dir)


def build_graph_integrity_header(scope: ProjectScope, body: str, source_inputs: list[Path]) -> str:
    """Build the architecture graph integrity header."""

    return build_yaml_header(
        {
            "integrity_schema_version": str(INTEGRITY_SCHEMA_VERSION),
            "generated": GENERATED_MARKER,
            "artifact_kind": ArtifactKind.ARCHITECTURE_GRAPH.value,
            "generator_id": GRAPH_GENERATOR_IDENTITY.generator_id,
            "generator_version": str(GRAPH_GENERATOR_IDENTITY.generator_version),
            "hash_algorithm": HASH_ALGORITHM,
            "source_hash": compute_source_hash(scope.root, source_inputs, GRAPH_GENERATOR_IDENTITY),
            "rendered_hash": compute_rendered_hash(body),
        }
    )
