from __future__ import annotations

from pathlib import Path

import yaml

from src.adr_kit.compiler import ArchitectureCompiler, CompilerConfig
from src.adr_kit.scope import ProjectScopeResolver
from tests.test_compiler_driver import _create_recursive_workspace
from tests.golden.helpers import clone_scope_sources


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _artifact_content(result, relative_path: str) -> dict:
    artifact = next(item for item in result.artifacts if item.path.as_posix() == relative_path)
    return yaml.safe_load(artifact.content.decode("utf-8"))


def test_compiler_graph_nodes_and_edges_match_registry_projection(tmp_path):
    workspace = tmp_path / "workspace"
    clone_scope_sources(_repo_root(), workspace)

    compiler = ArchitectureCompiler(scope_resolver=ProjectScopeResolver(explicit_scope=workspace))
    result = compiler.compile(
        config=CompilerConfig(
            dry_run=True,
            emit={"registries", "graph"},
            pinned_timestamp="2026-01-01T00:00:00Z",
        )
    )

    graph = _artifact_content(result, "adrs/index/architecture-graph.yaml")
    entities = _artifact_content(result, "adrs/index/entity-registry.yaml")
    relationships = _artifact_content(result, "adrs/index/relationship-registry.yaml")

    assert [node["id"] for node in graph["nodes"]] == sorted(entity["id"] for entity in entities["entities"])
    assert [
        {
            "id": node["id"],
            "entity_type": node["entity_type"],
            "name": node["name"],
            "canonical_source": node["canonical_source"],
        }
        for node in graph["nodes"]
    ] == [
        {
            "id": entity["id"],
            "entity_type": entity["entity_type"],
            "name": entity["name"],
            "canonical_source": entity["canonical_source"],
        }
        for entity in entities["entities"]
    ]
    assert [
        {
            "relationship_id": edge["relationship_id"],
            "relationship_type": edge["relationship_type"],
            "source_entity_id": edge["source_entity_id"],
            "target_entity_id": edge["target_entity_id"],
            "provenance_classification": edge["provenance_classification"],
            "evidence": edge["evidence"],
            "canonical_source_ref": edge["canonical_source_ref"],
            "confidence": edge["confidence"],
            "metadata": edge["metadata"],
        }
        for edge in graph["edges"]
    ] == [
        {
            "relationship_id": relationship["relationship_id"],
            "relationship_type": relationship["relationship_type"],
            "source_entity_id": relationship["from_entity_id"],
            "target_entity_id": relationship["to_entity_id"],
            "provenance_classification": relationship["provenance_classification"],
            "evidence": relationship["evidence"],
            "canonical_source_ref": relationship["canonical_source_ref"],
            "confidence": relationship["confidence"],
            "metadata": relationship["metadata"],
        }
        for relationship in relationships["relationships"]
    ]


def test_recursive_compile_emits_scope_local_graphs(tmp_path):
    workspace = tmp_path / "workspace"
    _create_recursive_workspace(workspace)

    compiler = ArchitectureCompiler(scope_resolver=ProjectScopeResolver(explicit_scope=workspace))
    result = compiler.compile_recursive(
        config=CompilerConfig(
            dry_run=True,
            emit={"graph"},
            pinned_timestamp="2026-01-01T00:00:00Z",
        )
    )

    assert result.success is True
    assert [item.scope.name for item in result.scope_results] == ["workspace-root", "workspace-sub"]
    for scoped in result.scope_results:
        artifact_paths = {artifact.path.as_posix() for artifact in scoped.result.artifacts}
        assert artifact_paths == {"adrs/index/architecture-graph.yaml"}
