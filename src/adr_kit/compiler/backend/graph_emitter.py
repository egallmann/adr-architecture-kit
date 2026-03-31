"""Architecture graph emission for the unified compiler driver."""

from __future__ import annotations

from pathlib import Path

from ...scope import ProjectScope
from ..frontend.builder import FrontendBuildResult
from .common import EmittedArtifact
from .graph_rendering import (
    build_architecture_graph,
    build_graph_integrity_header,
    discover_graph_source_inputs,
    render_graph_yaml,
)


def emit_graph_artifact(
    *,
    scope: ProjectScope,
    build_result: FrontendBuildResult,
) -> EmittedArtifact:
    """Serialize the additive architecture graph artifact."""

    graph = build_architecture_graph(build_result)
    body = render_graph_yaml(graph)
    source_inputs = discover_graph_source_inputs(scope)
    header = build_graph_integrity_header(scope, body, source_inputs)
    return EmittedArtifact(
        path=Path("adrs/index/architecture-graph.yaml"),
        content=(header + body).encode("utf-8"),
        kind="graph",
        integrity_header=header,
    )
