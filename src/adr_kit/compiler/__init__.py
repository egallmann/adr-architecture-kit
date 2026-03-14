"""Compiler scaffolding for the architecture migration path."""

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
    "CompilationMeta",
    "CompilationMode",
    "CompilerConfig",
    "Diagnostic",
    "DiagnosticLevel",
    "DiagnosticLog",
    "EntityGraph",
    "IREntity",
    "IRRelationship",
    "IRUnresolved",
    "ParsedCorpus",
    "QualifiedEntityId",
    "RelGraph",
    "UnresolvedList",
    "ArchModelBuilder",
    "CachedADRParser",
    "FrontendBuildResult",
    "build_arch_model",
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
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
