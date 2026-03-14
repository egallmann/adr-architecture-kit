"""Rendered markdown emission for the unified compiler driver."""

from __future__ import annotations

from pathlib import Path

from ...integrity import HashInput
from ...generators.views import MarkdownGenerator
from ...parser import ADRParser
from ...scope import ProjectScope
from .common import EmittedArtifact


def discover_scope_adr_files(scope: ProjectScope) -> list[Path]:
    """Discover canonical ADR source files for rendered markdown emission."""

    files: list[Path] = []
    for directory in (
        scope.logical_dir,
        scope.physical_dir,
        scope.adr_dir / "physical-system",
        scope.adr_dir / "physical-component",
    ):
        if not directory.exists():
            continue
        files.extend(sorted(path for path in directory.glob("*.yaml") if path.is_file() and not path.is_symlink()))
    return files


def emit_markdown_artifacts(
    *,
    parser: ADRParser,
    generator: MarkdownGenerator,
    scope: ProjectScope,
) -> list[EmittedArtifact]:
    """Serialize rendered ADR markdown artifacts for the selected scope."""

    artifacts: list[EmittedArtifact] = []
    for source_path in discover_scope_adr_files(scope):
        adr = parser.parse_adr(source_path)
        body = generator.render_adr(adr)
        header = generator.build_integrity_header(
            scope,
            body,
            [
                source_path.resolve(),
                HashInput(
                    f"__generator__/templates/{generator.template_path_for_adr(adr).name}",
                    generator.template_path_for_adr(adr).resolve().read_bytes(),
                ),
            ],
        )
        artifacts.append(
            EmittedArtifact(
                path=Path("adrs/rendered") / f"{adr.id}.md",
                content=(header + body).encode("utf-8"),
                kind="markdown",
                integrity_header=header,
            )
        )
    return artifacts
