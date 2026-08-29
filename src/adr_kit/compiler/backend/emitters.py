"""Static backend emitter map for the unified compiler driver."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ...parser import ADRParser
from ...scope import ProjectScope
from ..frontend.builder import FrontendBuildResult
from ..diagnostics import Diagnostic, DiagnosticLog
from ..registry_bundle import assemble_registry_bundle
from .common import BackendEmitter, EmittedArtifact
from .graph_emitter import emit_graph_artifact
from .manifest_emitter import emit_manifest_artifact
from .markdown_emitter import emit_markdown_artifacts
from .registry_emitter import emit_registry_artifacts


@dataclass
class RegistryBackendEmitter:
    """Emit the normalized registry bundle and legacy compatibility registry."""

    parser: ADRParser
    scope: ProjectScope
    build_result: FrontendBuildResult

    name: str = "registries"
    artifact_group: str = "registries"
    _diagnostics: list[Diagnostic] = field(default_factory=list, init=False, repr=False)

    def emit(self) -> list[EmittedArtifact]:
        diagnostics = DiagnosticLog()
        bundle = assemble_registry_bundle(
            self.build_result.model,
            coverage=self.build_result.coverage,
            namespace=self.build_result.namespace,
            generated_at=self.build_result.model.metadata.generated_at,
            diagnostics=diagnostics,
            model_version=getattr(self.build_result, "model_version", "1.1"),
        )
        self._diagnostics = diagnostics.as_list()
        return emit_registry_artifacts(bundle, scope=self.scope)

    def diagnostics(self) -> list[Diagnostic]:
        return list(self._diagnostics)


@dataclass
class ManifestBackendEmitter:
    """Emit the scope manifest artifact."""

    parser: ADRParser
    scope: ProjectScope
    build_result: FrontendBuildResult

    name: str = "manifest"
    artifact_group: str = "manifest"

    def emit(self) -> list[EmittedArtifact]:
        return [
            emit_manifest_artifact(
                parser=self.parser,
                scope=self.scope,
                generated_at=self.build_result.model.metadata.generated_at,
            )
        ]

    def diagnostics(self) -> list[Diagnostic]:
        return []


@dataclass
class MarkdownBackendEmitter:
    """Emit ADR human projection markdown artifacts for the selected scope."""

    parser: ADRParser
    scope: ProjectScope
    build_result: FrontendBuildResult
    include_system_overview: bool = True

    name: str = "markdown"
    artifact_group: str = "markdown"

    def emit(self) -> list[EmittedArtifact]:
        artifacts = emit_markdown_artifacts(
            parser=self.parser,
            scope=self.scope,
            build_result=self.build_result,
        )
        if self.include_system_overview:
            artifacts.extend(
                _emit_system_overview_artifact(
                    scope=self.scope, build_result=self.build_result
                )
            )
        return artifacts

    def diagnostics(self) -> list[Diagnostic]:
        return []


@dataclass
class GraphBackendEmitter:
    """Emit the additive architecture graph artifact."""

    parser: ADRParser
    scope: ProjectScope
    build_result: FrontendBuildResult

    name: str = "graph"
    artifact_group: str = "graph"

    def emit(self) -> list[EmittedArtifact]:
        return [emit_graph_artifact(scope=self.scope, build_result=self.build_result)]

    def diagnostics(self) -> list[Diagnostic]:
        return []


def _emit_system_overview_artifact(
    *,
    scope: ProjectScope,
    build_result: FrontendBuildResult,
) -> list[EmittedArtifact]:
    from ...generators.system_overview_generator import SystemOverviewGenerator

    generator = SystemOverviewGenerator(scope=scope, build_result=build_result)
    output_path = Path("SYSTEM-OVERVIEW.md")
    body, source_inputs = generator.render_with_inputs(scope.root / output_path)
    header = generator.build_integrity_header(scope.root / output_path, body, source_inputs)
    return [
        EmittedArtifact(
            path=output_path,
            content=(header + body).encode("utf-8"),
            kind="markdown",
            integrity_header=header,
            logical_id="system-overview",
        )
    ]


def build_backend_emitters(
    *,
    parser: ADRParser,
    scope: ProjectScope,
    build_result: FrontendBuildResult,
    include_system_overview: bool = True,
) -> dict[str, BackendEmitter]:
    """Build the static backend-emitter map used by the compiler driver."""

    return {
        "registries": RegistryBackendEmitter(parser=parser, scope=scope, build_result=build_result),
        "manifest": ManifestBackendEmitter(parser=parser, scope=scope, build_result=build_result),
        "markdown": MarkdownBackendEmitter(
            parser=parser,
            scope=scope,
            build_result=build_result,
            include_system_overview=include_system_overview,
        ),
        "graph": GraphBackendEmitter(parser=parser, scope=scope, build_result=build_result),
    }
