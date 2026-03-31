"""Frontend builder compatibility facade over the explicit compiler pipeline."""

from __future__ import annotations

from pathlib import Path

from ...scope import ProjectScope, ProjectScopeResolver
from ..config import CompilerConfig
from ..diagnostics import DiagnosticLog
from ..pipeline import FrontendBuildResult, run_frontend_pipeline
from .parser import CachedADRParser
from .support import discover_source_files


class ArchModelBuilder:
    """Build compiler IR from canonical ADR sources via the explicit pipeline."""

    def __init__(
        self,
        parser: CachedADRParser | None = None,
        scope_resolver: ProjectScopeResolver | None = None,
        config: CompilerConfig | None = None,
        diagnostics: DiagnosticLog | None = None,
    ) -> None:
        self.parser = parser or CachedADRParser()
        self.scope_resolver = scope_resolver or ProjectScopeResolver()
        self.config = config or CompilerConfig()
        self.diagnostics = diagnostics or DiagnosticLog()

    def discover_source_files(self, adr_dir: Path) -> tuple[list[Path], list[Path], list[Path]]:
        return discover_source_files(adr_dir)

    def build_from_scope(self, scope: ProjectScope | None = None) -> FrontendBuildResult:
        scope = scope or self.scope_resolver.resolve()
        return run_frontend_pipeline(
            scope=scope,
            parser=self.parser,
            config=self.config,
            diagnostics=self.diagnostics,
        )

    def build_from_directory(self, adr_dir: Path, scope: ProjectScope | None = None) -> FrontendBuildResult:
        adr_dir = Path(adr_dir).resolve()
        scope = scope or self.scope_resolver.resolve(adr_dir.parent)
        return self.build_from_scope(scope)


def build_arch_model(
    scope: ProjectScope | None = None,
    *,
    parser: CachedADRParser | None = None,
    scope_resolver: ProjectScopeResolver | None = None,
    config: CompilerConfig | None = None,
    diagnostics: DiagnosticLog | None = None,
) -> FrontendBuildResult:
    """Build an ArchModel for the provided scope."""

    builder = ArchModelBuilder(
        parser=parser,
        scope_resolver=scope_resolver,
        config=config,
        diagnostics=diagnostics,
    )
    return builder.build_from_scope(scope)
