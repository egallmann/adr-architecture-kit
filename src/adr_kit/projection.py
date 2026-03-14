"""Shared projection discovery and rendering logic."""

from __future__ import annotations

from pathlib import Path

from .compiler import ArchitectureCompiler, CompilerConfig
from .generators.manifest_generator import ManifestGenerator
from .generators.system_overview_generator import SystemOverviewGenerator
from .generators.views.markdown import MarkdownGenerator
from .integrity import (
    ArtifactKind,
    GeneratedArtifact,
    GeneratorIdentity,
    LEGACY_ENTITY_REGISTRY_GENERATOR,
    compute_source_hash,
    legacy_entity_registry_source_inputs,
)
from .parser import ADRParser


class ProjectionInspector:
    """Inspect generated artifacts using shared discovery and rendering rules."""

    def __init__(self, parser: ADRParser | None = None):
        self.parser = parser or ADRParser()

    @staticmethod
    def compute_source_hash(scope_root: Path, inputs: list[Path], generator_identity: GeneratorIdentity) -> str:
        return compute_source_hash(scope_root, inputs, generator_identity)

    def inspect(self, artifact: GeneratedArtifact) -> tuple[str, list[Path], GeneratorIdentity]:
        if artifact.artifact_kind == ArtifactKind.MANIFEST:
            generator = ManifestGenerator(parser=self.parser)
            body, source_inputs = generator.render_for_scope(artifact.scope)
            return body, source_inputs, generator.generator_identity

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
                item for item in result.artifacts if item.path.as_posix() == "adrs/entities/registry.yaml"
            )
            return (
                registry_artifact.content.decode("utf-8"),
                legacy_entity_registry_source_inputs(artifact.scope),
                LEGACY_ENTITY_REGISTRY_GENERATOR,
            )

        if artifact.artifact_kind == ArtifactKind.RENDERED_ADR_MARKDOWN:
            generator = MarkdownGenerator()
            body, source_inputs = generator.render_existing_artifact(artifact.artifact_path, artifact.scope)
            return body, source_inputs, generator.generator_identity

        if artifact.artifact_kind == ArtifactKind.SYSTEM_OVERVIEW:
            generator = SystemOverviewGenerator()
            body, source_inputs = generator.render_with_inputs(artifact.scope.root / "SYSTEM-OVERVIEW.md")
            return body, source_inputs, generator.generator_identity

        raise ValueError(f"Unsupported artifact kind: {artifact.artifact_kind}")
