"""Markdown view generator using Jinja2 templates."""

from pathlib import Path
from typing import Union

from jinja2 import Environment, FileSystemLoader, Template

from ...integrity import (
    ArtifactKind,
    GeneratorIdentity,
    GENERATED_MARKER,
    HASH_ALGORITHM,
    INTEGRITY_SCHEMA_VERSION,
    HashInput,
    build_markdown_header,
    compute_rendered_hash,
    compute_source_hash,
)
from ...models import LogicalADR, PhysicalADR
from ...scope import ProjectScope


class MarkdownGenerator:
    """Generate markdown views from ADR models."""

    generator_identity = GeneratorIdentity("adr-rendered-markdown", 1)
    
    def __init__(self, template_dir: Path = None):
        """Initialize generator.
        
        Args:
            template_dir: Path to templates directory (defaults to package templates/)
        """
        if template_dir is None:
            template_dir = Path(__file__).parent.parent.parent / "templates"
        
        self.template_dir = Path(template_dir)
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
        )
    
    def render_logical_adr(self, adr: LogicalADR) -> str:
        """Render logical ADR to markdown.
        
        Args:
            adr: LogicalADR model
            
        Returns:
            Rendered markdown string
        """
        template = self.env.get_template("adr-logical.md.jinja2")
        return template.render(adr=adr)
    
    def render_physical_adr(self, adr: PhysicalADR) -> str:
        """Render physical ADR to markdown.
        
        Args:
            adr: PhysicalADR model
            
        Returns:
            Rendered markdown string
        """
        template = self.env.get_template("adr-physical.md.jinja2")
        return template.render(adr=adr)

    def template_path_for_adr(self, adr: Union[LogicalADR, PhysicalADR]) -> Path:
        """Return the template path used for the ADR."""
        if isinstance(adr, LogicalADR):
            return self.template_dir / "adr-logical.md.jinja2"
        if isinstance(adr, PhysicalADR):
            return self.template_dir / "adr-physical.md.jinja2"
        raise ValueError(f"Unknown ADR type: {type(adr)}")

    def render_adr(self, adr: Union[LogicalADR, PhysicalADR]) -> str:
        """Render ADR to markdown (auto-detect type).
        
        Args:
            adr: LogicalADR or PhysicalADR model
            
        Returns:
            Rendered markdown string
        """
        if isinstance(adr, LogicalADR):
            return self.render_logical_adr(adr)
        elif isinstance(adr, PhysicalADR):
            return self.render_physical_adr(adr)
        else:
            raise ValueError(f"Unknown ADR type: {type(adr)}")

    def render_existing_artifact(self, artifact_path: Path, scope: ProjectScope) -> tuple[str, list[Path | HashInput]]:
        """Re-render an existing rendered ADR markdown artifact."""
        adr_id = Path(artifact_path).stem
        for directory in (scope.logical_dir, scope.physical_dir, scope.adr_dir / "physical-system", scope.adr_dir / "physical-component"):
            if not directory.exists():
                continue
            matches = sorted(directory.glob(f"{adr_id}-*.yaml"))
            if not matches:
                continue
            adr = self._parse_adr(matches[0])
            body = self.render_adr(adr)
            return body, [
                matches[0].resolve(),
                HashInput(
                    f"__generator__/templates/{self.template_path_for_adr(adr).name}",
                    self.template_path_for_adr(adr).resolve().read_bytes(),
                ),
            ]
        raise ValueError(f"Could not locate source ADR for rendered artifact: {artifact_path}")

    def _parse_adr(self, file_path: Path) -> Union[LogicalADR, PhysicalADR]:
        from ...parser import ADRParser

        parser = ADRParser()
        return parser.parse_adr(file_path)

    def build_integrity_header(
        self,
        scope: ProjectScope,
        body: str,
        source_inputs: list[Path | HashInput],
    ) -> str:
        """Build deterministic markdown integrity header."""
        header_fields = {
            "integrity_schema_version": str(INTEGRITY_SCHEMA_VERSION),
            "generated": GENERATED_MARKER,
            "artifact_kind": ArtifactKind.RENDERED_ADR_MARKDOWN.value,
            "generator_id": self.generator_identity.generator_id,
            "generator_version": str(self.generator_identity.generator_version),
            "hash_algorithm": HASH_ALGORITHM,
            "source_hash": compute_source_hash(scope.root, source_inputs, self.generator_identity),
            "rendered_hash": compute_rendered_hash(body),
        }
        return build_markdown_header(header_fields)

    def render_to_file(
        self,
        adr: Union[LogicalADR, PhysicalADR],
        output_path: Path,
        scope: ProjectScope | None = None,
        source_path: Path | None = None,
    ):
        """Render ADR and save to file.
        
        Args:
            adr: ADR model
            output_path: Path to save markdown file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        markdown = self.render_adr(adr)
        if scope is not None and source_path is not None:
            header = self.build_integrity_header(
                scope,
                markdown,
                [
                    source_path.resolve(),
                    HashInput(
                        f"__generator__/templates/{self.template_path_for_adr(adr).name}",
                        self.template_path_for_adr(adr).resolve().read_bytes(),
                    ),
                ],
            )
        else:
            header = ""

        with open(output_path, 'w', encoding='utf-8', newline="\n") as f:
            f.write(header)
            f.write(markdown)
