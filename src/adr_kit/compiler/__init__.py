"""Compiler scaffolding for the architecture migration path (authoring-time / parity).

Guardrail: ste-runtime is the compiler of record for machine-consumable architecture
state. Do not introduce or preserve a second authoritative IR/compiler for runtime
artifacts—see repo AUTHORING-SYSTEM.md.
"""

from __future__ import annotations

from .config import CompilationMode, CompilerConfig
from .diagnostics import Diagnostic, DiagnosticLevel, DiagnosticLog
from .ir import (
    ArchModel,
    CompilationMeta,
    EntityGraph,
    IREntity,
    IRRelationship,
    IRUnresolved,
    ParsedCorpus,
    QualifiedEntityId,
    RelGraph,
    UnresolvedList,
)

__all__ = [
    "ArchModel",
    "ArchitectureCompiler",
    "CompilationMeta",
    "CompilationResult",
    "CompilationStatistics",
    "CompilationMode",
    "CompilerConfig",
    "Diagnostic",
    "DiagnosticLevel",
    "DiagnosticLog",
    "EntityGraph",
    "IREntity",
    "IRRelationship",
    "IRUnresolved",
    "OutputArtifact",
    "ParsedCorpus",
    "QualifiedEntityId",
    "RelGraph",
    "ScopedCompilationResult",
    "UnresolvedList",
    "WorkspaceCompilationResult",
    "WorkspaceCompilationStatistics",
    "ArchModelBuilder",
    "CachedADRParser",
    "FrontendBuildResult",
    "build_arch_model",
    "CompilerPipeline",
    "CompilerPipelinePass",
    "CompilerPipelineState",
    "build_default_frontend_pipeline",
]


def __getattr__(name: str):
    if name in {"ArchModelBuilder", "CachedADRParser", "FrontendBuildResult", "build_arch_model"}:
        from .frontend import ArchModelBuilder, CachedADRParser, FrontendBuildResult, build_arch_model

        exports = {
            "ArchModelBuilder": ArchModelBuilder,
            "CachedADRParser": CachedADRParser,
            "FrontendBuildResult": FrontendBuildResult,
            "build_arch_model": build_arch_model,
        }
        return exports[name]
    if name in {
        "CompilerPipeline",
        "CompilerPipelinePass",
        "CompilerPipelineState",
        "build_default_frontend_pipeline",
    }:
        from .pipeline import (
            CompilerPipeline,
            CompilerPipelinePass,
            CompilerPipelineState,
            build_default_frontend_pipeline,
        )

        exports = {
            "CompilerPipeline": CompilerPipeline,
            "CompilerPipelinePass": CompilerPipelinePass,
            "CompilerPipelineState": CompilerPipelineState,
            "build_default_frontend_pipeline": build_default_frontend_pipeline,
        }
        return exports[name]
    if name in {
        "ArchitectureCompiler",
        "CompilationResult",
        "CompilationStatistics",
        "OutputArtifact",
        "ScopedCompilationResult",
        "WorkspaceCompilationResult",
        "WorkspaceCompilationStatistics",
    }:
        from .driver import (
            ArchitectureCompiler,
            CompilationResult,
            CompilationStatistics,
            OutputArtifact,
            ScopedCompilationResult,
            WorkspaceCompilationResult,
            WorkspaceCompilationStatistics,
        )

        exports = {
            "ArchitectureCompiler": ArchitectureCompiler,
            "CompilationResult": CompilationResult,
            "CompilationStatistics": CompilationStatistics,
            "OutputArtifact": OutputArtifact,
            "ScopedCompilationResult": ScopedCompilationResult,
            "WorkspaceCompilationResult": WorkspaceCompilationResult,
            "WorkspaceCompilationStatistics": WorkspaceCompilationStatistics,
        }
        return exports[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
