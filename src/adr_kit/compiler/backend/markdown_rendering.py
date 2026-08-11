"""Compiler-owned ADR human projection markdown helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Union

from jinja2 import Environment, FileSystemLoader

from ...decorators import implements_adr
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
from ...models.common import ADRType
from ...parser import ADRParser
from ...scope import ProjectScope
from ..frontend.adr_access import adr_type_of, field_get
from ..frontend.builder import ArchModelBuilder
from ..pipeline import FrontendBuildResult
from .common import EmittedArtifact
from .human_adr_projection import (
    HumanAdrProjectionContext,
    build_human_adr_projection_context,
    format_present_ref,
)
from .projection_paths import projection_relative_path, stem_matches_adr


MARKDOWN_GENERATOR_IDENTITY = GeneratorIdentity("adr-projection-markdown", 2)
DEFAULT_TEMPLATE_DIR = Path(__file__).resolve().parents[2] / "templates"


def _jinja_presentation_id(value: Any) -> str:
    from ..frontend.adr_access import presentation_id

    return presentation_id(value)


def build_markdown_environment(
    template_dir: Path | None = None,
    *,
    ctx: HumanAdrProjectionContext | None = None,
) -> Environment:
    """Build the deterministic Jinja environment for ADR human projections."""
    resolved_template_dir = Path(template_dir or DEFAULT_TEMPLATE_DIR)
    env = Environment(
        loader=FileSystemLoader(str(resolved_template_dir)),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["presentation_id"] = _jinja_presentation_id

    def present_ref_filter(value: Any) -> str:
        ref_id = str(value)
        if ctx is None:
            return ref_id
        ref = ctx.present_refs.get(ref_id)
        if ref is None:
            return ref_id
        return format_present_ref(ref)

    env.filters["present_ref"] = present_ref_filter
    return env


def template_path_for_adr(
    adr: Union[LogicalADR, PhysicalADR, PhysicalSystemADR, PhysicalComponentADR],
    *,
    template_dir: Path | None = None,
) -> Path:
    """Return the template path used for one ADR."""
    resolved_template_dir = Path(template_dir or DEFAULT_TEMPLATE_DIR)
    adr_type = adr_type_of(adr)
    if adr_type == ADRType.LOGICAL:
        return resolved_template_dir / "adr-logical.md.jinja2"
    if adr_type in (ADRType.PHYSICAL, ADRType.PHYSICAL_SYSTEM, ADRType.PHYSICAL_COMPONENT):
        return resolved_template_dir / "adr-physical.md.jinja2"
    raise ValueError(f"Unknown ADR type: {type(adr)}")


@implements_adr("ADR-L-0007")
def render_adr_markdown(
    adr: Union[LogicalADR, PhysicalADR, PhysicalSystemADR, PhysicalComponentADR],
    *,
    template_dir: Path | None = None,
    ctx: HumanAdrProjectionContext | None = None,
) -> str:
    """Render one ADR model to markdown."""
    env = build_markdown_environment(template_dir, ctx=ctx)
    template_name = template_path_for_adr(adr, template_dir=template_dir).name
    return env.get_template(template_name).render(adr=adr, ctx=ctx)


def discover_scope_adr_files(scope: ProjectScope) -> list[Path]:
    """Discover canonical ADR source files for human projection emission."""
    files: list[Path] = []
    for directory in (
        scope.logical_dir,
        scope.physical_dir,
        scope.adr_dir / "physical-system",
        scope.adr_dir / "physical-component",
    ):
        if not directory.exists():
            continue
        files.extend(
            sorted(path for path in directory.glob("*.yaml") if path.is_file() and not path.is_symlink())
        )
    return files


def markdown_source_inputs_for_adr(
    adr: Union[LogicalADR, PhysicalADR, PhysicalSystemADR, PhysicalComponentADR],
    *,
    source_path: Path,
    template_dir: Path | None = None,
    render_dependencies: list[Path | HashInput] | None = None,
) -> list[Path | HashInput]:
    """Return the canonical source inputs for one ADR human projection artifact."""
    if render_dependencies is not None:
        return list(render_dependencies)
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


def _resolve_build_result(
    *,
    scope: ProjectScope,
    build_result: FrontendBuildResult | None,
) -> FrontendBuildResult:
    if build_result is not None:
        return build_result
    return ArchModelBuilder().build_from_scope(scope)


@implements_adr("ADR-L-0007")
def render_existing_markdown_artifact(
    artifact_path: Path,
    *,
    scope: ProjectScope,
    parser: ADRParser,
    template_dir: Path | None = None,
    build_result: FrontendBuildResult | None = None,
) -> tuple[str, list[Path | HashInput]]:
    """Re-render an existing ADR human projection markdown artifact."""
    stem = Path(artifact_path).stem
    resolved_template_dir = Path(template_dir or DEFAULT_TEMPLATE_DIR)
    frontend = _resolve_build_result(scope=scope, build_result=build_result)
    for directory in (
        scope.logical_dir,
        scope.physical_dir,
        scope.adr_dir / "physical-system",
        scope.adr_dir / "physical-component",
    ):
        if not directory.exists():
            continue
        for source_path in sorted(path for path in directory.glob("*.yaml") if path.is_file()):
            try:
                adr = parser.parse_adr(source_path)
            except Exception:
                continue
            if not stem_matches_adr(adr, stem):
                continue
            template_name = template_path_for_adr(adr, template_dir=resolved_template_dir).name
            ctx = build_human_adr_projection_context(
                adr=adr,
                source_path=source_path,
                scope=scope,
                build_result=frontend,
                template_dir=resolved_template_dir,
                template_name=template_name,
            )
            body = render_adr_markdown(adr, template_dir=resolved_template_dir, ctx=ctx)
            return body, list(ctx.render_dependencies)
    raise ValueError(f"Could not locate source ADR for projection artifact: {artifact_path}")


@implements_adr("ADR-L-0007")
def emit_markdown_artifacts(
    *,
    parser: ADRParser,
    scope: ProjectScope,
    template_dir: Path | None = None,
    build_result: FrontendBuildResult | None = None,
) -> list[EmittedArtifact]:
    """Serialize ADR human projection markdown artifacts for the selected scope."""
    resolved_template_dir = Path(template_dir or DEFAULT_TEMPLATE_DIR)
    frontend = _resolve_build_result(scope=scope, build_result=build_result)
    artifacts: list[EmittedArtifact] = []
    for source_path in discover_scope_adr_files(scope):
        adr = parser.parse_adr(source_path)
        template_name = template_path_for_adr(adr, template_dir=resolved_template_dir).name
        ctx = build_human_adr_projection_context(
            adr=adr,
            source_path=source_path,
            scope=scope,
            build_result=frontend,
            template_dir=resolved_template_dir,
            template_name=template_name,
        )
        body = render_adr_markdown(adr, template_dir=resolved_template_dir, ctx=ctx)
        source_inputs = list(ctx.render_dependencies)
        header = build_markdown_integrity_header(scope, body, source_inputs)
        artifacts.append(
            EmittedArtifact(
                path=projection_relative_path(adr),
                content=(header + body).encode("utf-8"),
                kind="markdown",
                integrity_header=header,
                logical_id=str(field_get(adr, "id")),
            )
        )
    return artifacts
