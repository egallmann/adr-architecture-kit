"""Static backend emitter map for the unified compiler driver."""

from __future__ import annotations

from dataclasses import dataclass, field

from ...generators import ArchitectureIndexGenerator, ManifestGenerator
from ...generators.views import MarkdownGenerator
from ...parser import ADRParser
from ...scope import ProjectScope, ProjectScopeResolver
from ..diagnostics import Diagnostic
from .common import BackendEmitter, EmittedArtifact
from .manifest_emitter import emit_manifest_artifact
from .markdown_emitter import emit_markdown_artifacts
from .registry_emitter import emit_registry_artifacts


@dataclass
class RegistryBackendEmitter:
    """Emit the normalized registry bundle and legacy compatibility registry."""

    parser: ADRParser
    scope: ProjectScope

    name: str = "registries"
    artifact_group: str = "registries"
    _diagnostics: list[Diagnostic] = field(default_factory=list, init=False, repr=False)

    def emit(self) -> list[EmittedArtifact]:
        generator = ArchitectureIndexGenerator(
            parser=self.parser,
            scope_resolver=ProjectScopeResolver(explicit_scope=self.scope.root),
        )
        bundle = generator.generate_from_scope(self.scope)
        self._diagnostics = generator.diagnostics.as_list()
        return emit_registry_artifacts(bundle, generator=generator, scope=self.scope)

    def diagnostics(self) -> list[Diagnostic]:
        return list(self._diagnostics)


@dataclass
class ManifestBackendEmitter:
    """Emit the scope manifest artifact."""

    parser: ADRParser
    scope: ProjectScope

    name: str = "manifest"
    artifact_group: str = "manifest"

    def emit(self) -> list[EmittedArtifact]:
        generator = ManifestGenerator(
            parser=self.parser,
            scope_resolver=ProjectScopeResolver(explicit_scope=self.scope.root),
        )
        return [emit_manifest_artifact(generator=generator, scope=self.scope)]

    def diagnostics(self) -> list[Diagnostic]:
        return []


@dataclass
class MarkdownBackendEmitter:
    """Emit rendered ADR markdown artifacts for the selected scope."""

    parser: ADRParser
    scope: ProjectScope

    name: str = "markdown"
    artifact_group: str = "markdown"

    def emit(self) -> list[EmittedArtifact]:
        return emit_markdown_artifacts(
            parser=self.parser,
            generator=MarkdownGenerator(),
            scope=self.scope,
        )

    def diagnostics(self) -> list[Diagnostic]:
        return []


def build_backend_emitters(*, parser: ADRParser, scope: ProjectScope) -> dict[str, BackendEmitter]:
    """Build the static backend-emitter map used by the compiler driver."""

    return {
        "registries": RegistryBackendEmitter(parser=parser, scope=scope),
        "manifest": ManifestBackendEmitter(parser=parser, scope=scope),
        "markdown": MarkdownBackendEmitter(parser=parser, scope=scope),
    }
