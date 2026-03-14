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
    "emit_markdown_artifacts",
    "emit_registry_artifacts",
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
    if name in {"discover_scope_adr_files", "emit_markdown_artifacts"}:
        from .markdown_emitter import discover_scope_adr_files, emit_markdown_artifacts

        exports = {
            "discover_scope_adr_files": discover_scope_adr_files,
            "emit_markdown_artifacts": emit_markdown_artifacts,
        }
        return exports[name]
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
