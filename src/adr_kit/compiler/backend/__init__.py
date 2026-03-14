"""Compiler backend helpers."""

from __future__ import annotations

from .common import BackendEmitter, EmittedArtifact

__all__ = [
    "BackendEmitter",
    "EmittedArtifact",
    "PROJECTABLE_ENTITY_TYPES",
    "build_backend_emitters",
    "build_relationship_summary",
    "discover_scope_adr_files",
    "emit_manifest_artifact",
    "emit_graph_artifact",
    "emit_markdown_artifacts",
    "emit_registry_artifacts",
    "build_architecture_graph",
    "build_graph_integrity_header",
    "discover_graph_source_inputs",
    "render_graph_yaml",
    "render_existing_markdown_artifact",
    "render_manifest_for_scope",
    "project_entity",
    "project_relationship",
    "project_unresolved",
]


def __getattr__(name: str):
    if name == "build_backend_emitters":
        from .emitters import build_backend_emitters

        return build_backend_emitters
    if name in {"emit_manifest_artifact"}:
        from .manifest_emitter import emit_manifest_artifact

        return emit_manifest_artifact
    if name in {
        "build_architecture_graph",
        "build_graph_integrity_header",
        "discover_graph_source_inputs",
        "render_graph_yaml",
    }:
        from .graph_rendering import (
            build_architecture_graph,
            build_graph_integrity_header,
            discover_graph_source_inputs,
            render_graph_yaml,
        )

        exports = {
            "build_architecture_graph": build_architecture_graph,
            "build_graph_integrity_header": build_graph_integrity_header,
            "discover_graph_source_inputs": discover_graph_source_inputs,
            "render_graph_yaml": render_graph_yaml,
        }
        return exports[name]
    if name == "emit_graph_artifact":
        from .graph_emitter import emit_graph_artifact

        return emit_graph_artifact
    if name in {"discover_scope_adr_files", "emit_markdown_artifacts"}:
        from .markdown_emitter import discover_scope_adr_files, emit_markdown_artifacts

        exports = {
            "discover_scope_adr_files": discover_scope_adr_files,
            "emit_markdown_artifacts": emit_markdown_artifacts,
        }
        return exports[name]
    if name in {"render_manifest_for_scope"}:
        from .manifest_rendering import render_manifest_for_scope

        return render_manifest_for_scope
    if name in {"render_existing_markdown_artifact"}:
        from .markdown_rendering import render_existing_markdown_artifact

        return render_existing_markdown_artifact
    if name in {
        "PROJECTABLE_ENTITY_TYPES",
        "build_relationship_summary",
        "project_entity",
        "project_relationship",
        "project_unresolved",
    }:
        from .projection import (
            PROJECTABLE_ENTITY_TYPES,
            build_relationship_summary,
            project_entity,
            project_relationship,
            project_unresolved,
        )

        exports = {
            "PROJECTABLE_ENTITY_TYPES": PROJECTABLE_ENTITY_TYPES,
            "build_relationship_summary": build_relationship_summary,
            "project_entity": project_entity,
            "project_relationship": project_relationship,
            "project_unresolved": project_unresolved,
        }
        return exports[name]
    if name == "emit_registry_artifacts":
        from .registry_emitter import emit_registry_artifacts

        return emit_registry_artifacts
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
