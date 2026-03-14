"""Manifest emission for the unified compiler driver."""

from __future__ import annotations

from pathlib import Path

from ...generators.manifest_generator import ManifestGenerator
from ...scope import ProjectScope
from .common import EmittedArtifact


def emit_manifest_artifact(
    *,
    generator: ManifestGenerator,
    scope: ProjectScope,
) -> EmittedArtifact:
    """Serialize the scope manifest into one emitted artifact."""

    body, source_inputs = generator.render_for_scope(scope)
    header = generator.build_integrity_header(scope, body, source_inputs)
    return EmittedArtifact(
        path=Path("adrs/manifest.yaml"),
        content=(header + body).encode("utf-8"),
        kind="manifest",
        integrity_header=header,
    )
