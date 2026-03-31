"""Compiler-owned rendered markdown helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Union

from jinja2 import Environment, FileSystemLoader

from ...integrity import (
    ArtifactKind,
    GENERATED_MARKER,
    HASH_ALGORITHM,
    INTEGRITY_SCHEMA_VERSION,
    GeneratorIdentity,
    HashInput,
    build_markdown_header,
    compute_rendered_hash,
    compute_source_hash,
)
from ...models import LogicalADR, PhysicalADR, PhysicalComponentADR, PhysicalSystemADR
from ...parser import ADRParser
from ...scope import ProjectScope
from .common import EmittedArtifact


MARKDOWN_GENERATOR_IDENTITY = GeneratorIdentity("adr-rendered-markdown", 1)
DEFAULT_TEMPLATE_DIR = Path(__file__).resolve().parents[2] / "templates"


def build_markdown_environment(template_dir: Path | None = None) -> Environment:
    """Build the deterministic Jinja environment for rendered ADR markdown."""
    resolved_template_dir = Path(template_dir or DEFAULT_TEMPLATE_DIR)
    return Environment(
        loader=FileSystemLoader(str(resolved_template_dir)),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def template_path_for_adr(
    adr: Union[LogicalADR, PhysicalADR, PhysicalSystemADR, PhysicalComponentADR],
    *,
    template_dir: Path | None = None,
) -> Path:
    """Return the template path used for one ADR."""
    resolved_template_dir = Path(template_dir or DEFAULT_TEMPLATE_DIR)
    if isinstance(adr, LogicalADR):
        return resolved_template_dir / "adr-logical.md.jinja2"
    if isinstance(adr, (PhysicalADR, PhysicalSystemADR, PhysicalComponentADR)):
        return resolved_template_dir / "adr-physical.md.jinja2"
    raise ValueError(f"Unknown ADR type: {type(adr)}")


def render_adr_markdown(
    adr: Union[LogicalADR, PhysicalADR, PhysicalSystemADR, PhysicalComponentADR],
    *,
    template_dir: Path | None = None,
) -> str:
    """Render one ADR model to markdown."""
    env = build_markdown_environment(template_dir)
    template_name = template_path_for_adr(adr, template_dir=template_dir).name
    return env.get_template(template_name).render(adr=adr)


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


def markdown_source_inputs_for_adr(
    adr: Union[LogicalADR, PhysicalADR, PhysicalSystemADR, PhysicalComponentADR],
    *,
    source_path: Path,
    template_dir: Path | None = None,
) -> list[Path | HashInput]:
    """Return the canonical source inputs for one rendered ADR markdown artifact."""
    template_path = template_path_for_adr(adr, template_dir=template_dir)
    return [
        source_path.resolve(),
        HashInput(
            f"__generator__/templates/{template_path.name}",
            template_path.resolve().read_bytes(),
        ),
    ]


def build_markdown_integrity_header(
    scope: ProjectScope,
    body: str,
    source_inputs: list[Path | HashInput],
) -> str:
    """Build the deterministic markdown integrity header."""
    header_fields = {
        "integrity_schema_version": str(INTEGRITY_SCHEMA_VERSION),
        "generated": GENERATED_MARKER,
        "artifact_kind": ArtifactKind.RENDERED_ADR_MARKDOWN.value,
        "generator_id": MARKDOWN_GENERATOR_IDENTITY.generator_id,
        "generator_version": str(MARKDOWN_GENERATOR_IDENTITY.generator_version),
        "hash_algorithm": HASH_ALGORITHM,
        "source_hash": compute_source_hash(scope.root, source_inputs, MARKDOWN_GENERATOR_IDENTITY),
        "rendered_hash": compute_rendered_hash(body),
    }
    return build_markdown_header(header_fields)


def render_existing_markdown_artifact(
    artifact_path: Path,
    *,
    scope: ProjectScope,
    parser: ADRParser,
    template_dir: Path | None = None,
) -> tuple[str, list[Path | HashInput]]:
    """Re-render an existing rendered ADR markdown artifact."""
    adr_id = Path(artifact_path).stem
    for directory in (scope.logical_dir, scope.physical_dir, scope.adr_dir / "physical-system", scope.adr_dir / "physical-component"):
        if not directory.exists():
            continue
        matches = sorted(directory.glob(f"{adr_id}-*.yaml"))
        if not matches:
            continue
        source_path = matches[0]
        adr = parser.parse_adr(source_path)
        body = render_adr_markdown(adr, template_dir=template_dir)
        return body, markdown_source_inputs_for_adr(adr, source_path=source_path, template_dir=template_dir)
    raise ValueError(f"Could not locate source ADR for rendered artifact: {artifact_path}")


def emit_markdown_artifacts(
    *,
    parser: ADRParser,
    scope: ProjectScope,
    template_dir: Path | None = None,
) -> list[EmittedArtifact]:
    """Serialize rendered ADR markdown artifacts for the selected scope."""
    artifacts: list[EmittedArtifact] = []
    for source_path in discover_scope_adr_files(scope):
        adr = parser.parse_adr(source_path)
        body = render_adr_markdown(adr, template_dir=template_dir)
        source_inputs = markdown_source_inputs_for_adr(adr, source_path=source_path, template_dir=template_dir)
        header = build_markdown_integrity_header(scope, body, source_inputs)
        artifacts.append(
            EmittedArtifact(
                path=Path("adrs/rendered") / f"{adr.id}.md",
                content=(header + body).encode("utf-8"),
                kind="markdown",
                integrity_header=header,
            )
        )
    return artifacts
