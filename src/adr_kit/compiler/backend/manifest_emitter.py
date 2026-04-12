"""Manifest emission for the unified compiler driver."""

from __future__ import annotations

from pathlib import Path

from ...decorators import implements_adr
from ...parser import ADRParser
from ...scope import ProjectScope
from .common import EmittedArtifact
from .manifest_rendering import build_manifest_integrity_header, render_manifest_for_scope


@implements_adr("ADR-L-0009", "ADR-L-0010", "ADR-PC-0003")
def emit_manifest_artifact(
    *,
    parser: ADRParser,
    scope: ProjectScope,
    generated_at=None,
) -> EmittedArtifact:
    """Serialize the scope manifest into one emitted artifact."""

    body, source_inputs = render_manifest_for_scope(parser=parser, scope=scope, generated_at=generated_at)
    header = build_manifest_integrity_header(scope, body, source_inputs)
    return EmittedArtifact(
        path=Path("adrs/manifest.yaml"),
        content=(header + body).encode("utf-8"),
        kind="manifest",
        integrity_header=header,
    )
