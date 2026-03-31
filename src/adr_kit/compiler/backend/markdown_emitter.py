"""Rendered markdown emission for the unified compiler driver."""

from __future__ import annotations

from ...parser import ADRParser
from ...scope import ProjectScope
from .common import EmittedArtifact
from .markdown_rendering import discover_scope_adr_files, emit_markdown_artifacts as emit_compiler_markdown_artifacts


def emit_markdown_artifacts(
    *,
    parser: ADRParser,
    scope: ProjectScope,
) -> list[EmittedArtifact]:
    """Serialize rendered ADR markdown artifacts for the selected scope."""
    return emit_compiler_markdown_artifacts(parser=parser, scope=scope)
