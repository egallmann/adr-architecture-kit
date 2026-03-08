"""Markdown view generator using Jinja2 templates."""

from pathlib import Path
from typing import Union

from jinja2 import Environment, FileSystemLoader, Template

from ...models import LogicalADR, PhysicalADR


class MarkdownGenerator:
    """Generate markdown views from ADR models."""
    
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
    
    def render_to_file(self, adr: Union[LogicalADR, PhysicalADR], output_path: Path):
        """Render ADR and save to file.
        
        Args:
            adr: ADR model
            output_path: Path to save markdown file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        markdown = self.render_adr(adr)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(markdown)
