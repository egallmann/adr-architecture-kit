"""Rendered markdown generator compatibility wrapper."""

from pathlib import Path
from typing import Union

from ...compiler.backend.markdown_rendering import (
    DEFAULT_TEMPLATE_DIR,
    MARKDOWN_GENERATOR_IDENTITY,
    build_markdown_environment,
    build_markdown_integrity_header,
    markdown_source_inputs_for_adr,
    render_adr_markdown,
    render_existing_markdown_artifact,
    template_path_for_adr as compiler_template_path_for_adr,
)
from ...integrity import GeneratorIdentity, HashInput
from ...models import LogicalADR, PhysicalADR, PhysicalComponentADR, PhysicalSystemADR
from ...parser import ADRParser
from ...scope import ProjectScope


class MarkdownGenerator:
    """Render ADR markdown while delegating rendering authority to compiler helpers.

    Context-free ``render_*`` methods preserve legacy/local rendering for pre-v1.5
    templates. Authoring v1.5 Projection v3 full-fidelity output requires the
    scope-aware compiler path (``render_existing_artifact`` or ``emit_markdown_artifacts``).
    """

    generator_identity = GeneratorIdentity(
        MARKDOWN_GENERATOR_IDENTITY.generator_id,
        MARKDOWN_GENERATOR_IDENTITY.generator_version,
    )

    def __init__(self, template_dir: Path = None):
        self.template_dir = Path(template_dir or DEFAULT_TEMPLATE_DIR)
        self.env = build_markdown_environment(self.template_dir)

    def render_logical_adr(self, adr: LogicalADR) -> str:
        return render_adr_markdown(adr, template_dir=self.template_dir)

    def render_physical_adr(self, adr: PhysicalADR | PhysicalSystemADR | PhysicalComponentADR) -> str:
        return render_adr_markdown(adr, template_dir=self.template_dir)

    def template_path_for_adr(self, adr: Union[LogicalADR, PhysicalADR, PhysicalSystemADR, PhysicalComponentADR]) -> Path:
        return compiler_template_path_for_adr(adr, template_dir=self.template_dir)

    def render_adr(self, adr: Union[LogicalADR, PhysicalADR, PhysicalSystemADR, PhysicalComponentADR]) -> str:
        return render_adr_markdown(adr, template_dir=self.template_dir)

    def render_existing_artifact(self, artifact_path: Path, scope: ProjectScope) -> tuple[str, list[Path | HashInput]]:
        return render_existing_markdown_artifact(
            artifact_path,
            scope=scope,
            parser=ADRParser(),
            template_dir=self.template_dir,
        )

    def _parse_adr(self, file_path: Path) -> Union[LogicalADR, PhysicalADR, PhysicalSystemADR, PhysicalComponentADR]:
        parser = ADRParser()
        return parser.parse_adr(file_path)

    def build_integrity_header(
        self,
        scope: ProjectScope,
        body: str,
        source_inputs: list[Path | HashInput],
    ) -> str:
        return build_markdown_integrity_header(scope, body, source_inputs)

    def render_to_file(
        self,
        adr: Union[LogicalADR, PhysicalADR, PhysicalSystemADR, PhysicalComponentADR],
        output_path: Path,
        scope: ProjectScope | None = None,
        source_path: Path | None = None,
    ):
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        markdown = self.render_adr(adr)
        if scope is not None and source_path is not None:
            header = self.build_integrity_header(
                scope,
                markdown,
                markdown_source_inputs_for_adr(
                    adr,
                    source_path=source_path,
                    template_dir=self.template_dir,
                ),
            )
        else:
            header = ""

        with open(output_path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(header)
            handle.write(markdown)
