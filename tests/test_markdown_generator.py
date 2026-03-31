"""Test markdown view generator."""

import pytest
from pathlib import Path

from src.adr_kit.parser import ADRParser
from src.adr_kit.generators.views import MarkdownGenerator


@pytest.fixture
def parser():
    """Create ADR parser."""
    return ADRParser()


@pytest.fixture
def generator():
    """Create markdown generator."""
    return MarkdownGenerator()


class TestMarkdownGeneration:
    """Test markdown view generation."""
    
    def test_render_logical_adr(self, parser, generator):
        """Test rendering logical ADR to markdown."""
        adr_path = Path("tests/fixtures/valid/logical-minimal.yaml")
        adr = parser.parse_logical_adr(adr_path)
        
        markdown = generator.render_logical_adr(adr)
        
        assert "ADR-L-9999" in markdown
        assert "Minimal Valid Logical ADR" in markdown
        assert "## Context" in markdown
        assert "## Decisions" in markdown
    
    def test_render_physical_adr(self, parser, generator):
        """Test rendering physical ADR to markdown."""
        adr_path = Path("tests/fixtures/valid/physical-minimal.yaml")
        adr = parser.parse_physical_adr(adr_path)
        
        markdown = generator.render_physical_adr(adr)
        
        assert "ADR-P-9999" in markdown
        assert "Minimal Valid Physical ADR" in markdown
        assert "## Context" in markdown
        assert "## Technology Stack" in markdown
        assert "## Component Specifications" in markdown
    
    def test_render_adr_auto_detect(self, parser, generator):
        """Test auto-detecting ADR type for rendering."""
        logical_path = Path("tests/fixtures/valid/logical-minimal.yaml")
        logical_adr = parser.parse_logical_adr(logical_path)
        
        markdown = generator.render_adr(logical_adr)
        assert "ADR-L-9999" in markdown
        
        physical_path = Path("tests/fixtures/valid/physical-minimal.yaml")
        physical_adr = parser.parse_physical_adr(physical_path)
        
        markdown = generator.render_adr(physical_adr)
        assert "ADR-P-9999" in markdown
    
    def test_render_complete_logical_adr(self, parser, generator):
        """Test rendering complete logical ADR (ADR-L-0001)."""
        adr_path = Path("adrs/logical/ADR-L-0001-ste-compliant-adr-system.yaml")
        
        if not adr_path.exists():
            pytest.skip("ADR-L-0001 not found")
        
        adr = parser.parse_logical_adr(adr_path)
        markdown = generator.render_logical_adr(adr)
        
        assert "## Capabilities" in markdown
        assert "## Invariants" in markdown
        assert "## Decisions" in markdown
        assert "CAP-0001" in markdown
        assert "INV-0001" in markdown
