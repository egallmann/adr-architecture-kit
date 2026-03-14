"""Compiler scaffolding for the architecture migration path."""

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
]
