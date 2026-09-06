"""Shared projection discovery and rendering logic."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from .compiler import ArchitectureCompiler, CompilerConfig
from .compiler.backend.graph_rendering import GRAPH_GENERATOR_IDENTITY, discover_graph_source_inputs
from .compiler.backend.manifest_rendering import (
    MANIFEST_GENERATOR_IDENTITY,
    render_manifest_for_scope,
)
from .compiler.backend.markdown_rendering import (
    MARKDOWN_GENERATOR_IDENTITY,
    render_existing_markdown_artifact,
)
from .decorators import implements_adr
from .generators.system_overview_generator import SystemOverviewGenerator
from .integrity import (
    ArtifactKind,
    GeneratedArtifact,
    GeneratorIdentity,
    HashInput,
    LEGACY_ENTITY_REGISTRY_GENERATOR,
    compute_source_hash,
    extract_body_without_header,
    legacy_entity_registry_source_inputs,
)
from .parser import ADRParser

ProjectionInputs = Sequence[Path | HashInput]


@implements_adr("ADR-L-0007")
class ProjectionInspector:
    """Inspect generated artifacts using shared discovery and rendering rules."""

    def __init__(self, parser: ADRParser | None = None):
        self.parser = parser or ADRParser()

    @staticmethod
    def compute_source_hash(
        scope_root: Path,
        inputs: ProjectionInputs,
        generator_identity: GeneratorIdentity,
    ) -> str:
        return compute_source_hash(scope_root, inputs, generator_identity)

    def inspect(
        self, artifact: GeneratedArtifact
    ) -> tuple[str, ProjectionInputs, GeneratorIdentity]:
        if artifact.artifact_kind == ArtifactKind.MANIFEST:
            body, manifest_inputs = render_manifest_for_scope(
                parser=self.parser, scope=artifact.scope
            )
            return body, manifest_inputs, MANIFEST_GENERATOR_IDENTITY

        if artifact.artifact_kind == ArtifactKind.ARCHITECTURE_GRAPH:
            compiler = ArchitectureCompiler()
            result = compiler.compile(
                artifact.scope,
                CompilerConfig(
                    emit={"graph"},
                    dry_run=True,
                ),
            )
            graph_artifact = next(
                item
                for item in result.artifacts
                if item.path.as_posix() == "adrs/index/architecture-graph.yaml"
            )
            return (
                extract_body_without_header(graph_artifact.content.decode("utf-8")),
                discover_graph_source_inputs(artifact.scope),
                GRAPH_GENERATOR_IDENTITY,
            )

        if artifact.artifact_kind == ArtifactKind.LEGACY_ENTITY_REGISTRY:
            compiler = ArchitectureCompiler()
            result = compiler.compile(
                artifact.scope,
                CompilerConfig(
                    emit={"registries"},
                    dry_run=True,
                ),
            )
            registry_artifact = next(
                item
                for item in result.artifacts
                if item.path.as_posix() == "adrs/entities/registry.yaml"
            )
            return (
                registry_artifact.content.decode("utf-8"),
                legacy_entity_registry_source_inputs(artifact.scope),
                LEGACY_ENTITY_REGISTRY_GENERATOR,
            )

        if artifact.artifact_kind == ArtifactKind.RENDERED_ADR_MARKDOWN:
            body, markdown_inputs = render_existing_markdown_artifact(
                artifact.artifact_path,
                scope=artifact.scope,
                parser=self.parser,
            )
            return body, markdown_inputs, MARKDOWN_GENERATOR_IDENTITY

        if artifact.artifact_kind == ArtifactKind.SYSTEM_OVERVIEW:
            from .compiler.pipeline import run_frontend_pipeline

            frontend = run_frontend_pipeline(scope=artifact.scope)
            generator = SystemOverviewGenerator(
                scope=artifact.scope, build_result=frontend
            )
            body, overview_inputs = generator.render_with_inputs(
                artifact.scope.root / "SYSTEM-OVERVIEW.md"
            )
            return body, overview_inputs, generator.generator_identity

        raise ValueError(f"Unsupported artifact kind: {artifact.artifact_kind}")
