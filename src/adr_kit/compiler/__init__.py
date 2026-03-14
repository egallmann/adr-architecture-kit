"""Compiler scaffolding for the architecture migration path."""

from .config import CompilationMode, CompilerConfig
from .diagnostics import Diagnostic, DiagnosticLevel, DiagnosticLog
from .frontend import ArchModelBuilder, CachedADRParser, FrontendBuildResult, build_arch_model
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
    "ArchModelBuilder",
    "CachedADRParser",
    "CompilationMeta",
    "CompilationMode",
    "CompilerConfig",
    "Diagnostic",
    "DiagnosticLevel",
    "DiagnosticLog",
    "EntityGraph",
    "FrontendBuildResult",
    "IREntity",
    "IRRelationship",
    "IRUnresolved",
    "ParsedCorpus",
    "QualifiedEntityId",
    "RelGraph",
    "UnresolvedList",
    "build_arch_model",
]
