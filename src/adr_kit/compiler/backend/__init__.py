"""Compiler backend helpers."""

from .common import BackendEmitter, EmittedArtifact
from .emitters import build_backend_emitters
from .manifest_emitter import emit_manifest_artifact
from .markdown_emitter import discover_scope_adr_files, emit_markdown_artifacts
from .projection import (
    PROJECTABLE_ENTITY_TYPES,
    build_relationship_summary,
    project_entity,
    project_relationship,
    project_unresolved,
)
from .registry_emitter import emit_registry_artifacts

__all__ = [
    "EmittedArtifact",
    "PROJECTABLE_ENTITY_TYPES",
    "build_relationship_summary",
    "build_backend_emitters",
    "discover_scope_adr_files",
    "emit_manifest_artifact",
    "emit_markdown_artifacts",
    "emit_registry_artifacts",
    "BackendEmitter",
    "project_entity",
    "project_relationship",
    "project_unresolved",
]
