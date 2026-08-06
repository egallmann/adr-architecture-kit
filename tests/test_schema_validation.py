"""Test JSON Schema validation."""

import pytest
from pathlib import Path

from adr_kit.parser import ADRParser, ADRParseError, ADRSchemaValidationError


def test_adr_parser_default_init():
    """ADRParser() with no args must resolve bundled schemas via importlib.resources."""
    parser = ADRParser()
    assert parser.schema_dir.exists(), f"Schema v1_0 dir not found: {parser.schema_dir}"
    assert parser.schema_v11_dir.exists(), f"Schema v1_1 dir not found: {parser.schema_v11_dir}"
    assert any(parser.schema_dir.glob("*.json")), "No JSON schemas in v1_0"
    assert any(parser.schema_v11_dir.glob("*.json")), "No JSON schemas in v1_1"


def test_adr_parser_loads_schemas():
    """ADRParser must populate _schemas on init (importlib.resources path must resolve)."""
    parser = ADRParser()
    assert parser._schemas, "Expected _schemas to be non-empty after init"


@pytest.fixture
def parser():
    """Create ADR parser."""
    return ADRParser()


@pytest.fixture
def fixtures_dir():
    """Get fixtures directory."""
    return Path(__file__).parent / "fixtures"


class TestValidLogicalADRs:
    """Test valid logical ADR parsing."""
    
    def test_minimal_logical_adr(self, parser, fixtures_dir):
        """Test parsing minimal valid logical ADR."""
        adr_path = fixtures_dir / "valid" / "logical-minimal.yaml"
        adr = parser.parse_logical_adr(adr_path)
        
        assert adr.id == "ADR-L-9999"
        assert adr.adr_type.value == "logical"
        assert adr.title == "Minimal Valid Logical ADR"
        assert len(adr.decisions) == 1
    
    def test_complete_logical_adr(self, parser):
        """Test parsing complete logical ADR (ADR-L-0001)."""
        adr_path = Path("adrs/logical/ADR-L-0001-ste-compliant-adr-system.yaml")
        
        if not adr_path.exists():
            pytest.skip("ADR-L-0001 not found")
        
        adr = parser.parse_logical_adr(adr_path)
        
        assert adr.id == "ADR-L-0001"
        assert adr.status.value == "accepted"
        assert len(adr.decisions) == 6
        assert len(adr.invariants) == 7
        assert len(adr.capabilities) == 7

    def test_vision_logical_adr_allows_lightweight_structure(self, parser, tmp_path):
        """ADR-V files should validate as logical ADRs without ADR-L completeness requirements."""
        adr_path = tmp_path / "ADR-V-9999-vision.yaml"
        adr_path.write_text(
            "\n".join(
                [
                    'schema_version: "1.0"',
                    "id: ADR-V-9999",
                    "adr_type: logical",
                    "vision_category: true",
                    "promotable_to_logical: true",
                    'title: "Example Vision ADR"',
                    "status: proposed",
                    'created_date: "2026-03-11"',
                    "authors: [adr-architecture-kit]",
                    "domains: [vision]",
                    "context: |",
                    "  Future-state capability framing.",
                    "capability: |",
                    "  Vision capabilities can be described without DEC entries yet.",
                ]
            ),
            encoding="utf-8",
        )

        adr = parser.parse_logical_adr(adr_path)

        assert adr.id == "ADR-V-9999"
        assert adr.vision_category is True
        assert adr.decisions == []

    def test_structural_validation_allows_empty_required_collections_for_draft(self, parser, tmp_path):
        """Structural mode should accept draft ADRs with explicit empty required sections."""
        adr_path = tmp_path / "ADR-L-9998-draft.yaml"
        adr_path.write_text(
            "\n".join(
                [
                    'schema_version: "1.0"',
                    "id: ADR-L-9998",
                    "adr_type: logical",
                    'title: "Draft Logical ADR"',
                    "status: proposed",
                    'created_date: "2026-03-13"',
                    "authors: [adr-architecture-kit]",
                    "domains: [drafting]",
                    "context: |",
                    "  Draft context pending fuller pin-down.",
                    "decisions: []",
                ]
            ),
            encoding="utf-8",
        )

        data = parser.parse_yaml(adr_path)
        parser.validate_against_schema(data, "logical", mode="structural")

    def test_complete_validation_rejects_empty_required_collections_for_draft(self, parser, tmp_path):
        """Complete mode should reject draft ADRs with empty required sections."""
        adr_path = tmp_path / "ADR-L-9997-draft.yaml"
        adr_path.write_text(
            "\n".join(
                [
                    'schema_version: "1.0"',
                    "id: ADR-L-9997",
                    "adr_type: logical",
                    'title: "Draft Logical ADR"',
                    "status: proposed",
                    'created_date: "2026-03-13"',
                    "authors: [adr-architecture-kit]",
                    "domains: [drafting]",
                    "context: |",
                    "  Draft context pending fuller pin-down.",
                    "decisions: []",
                ]
            ),
            encoding="utf-8",
        )

        data = parser.parse_yaml(adr_path)
        with pytest.raises(ADRSchemaValidationError):
            parser.validate_against_schema(data, "logical", mode="complete")


class TestValidPhysicalADRs:
    """Test valid physical ADR parsing."""
    
    def test_minimal_physical_adr(self, parser, fixtures_dir):
        """Test parsing minimal valid physical ADR."""
        adr_path = fixtures_dir / "valid" / "physical-minimal.yaml"
        adr = parser.parse_physical_adr(adr_path)
        
        assert adr.id == "ADR-P-9999"
        assert adr.adr_type.value == "physical"
        assert len(adr.implements_logical) == 1
        assert adr.implements_logical[0] == "ADR-L-9999"
    
    def test_complete_physical_adr(self, parser):
        """Test parsing complete physical ADR (ADR-P-0001)."""
        adr_path = Path("adrs/physical/ADR-P-0001-python-toolkit-implementation.yaml")
        
        if not adr_path.exists():
            pytest.skip("ADR-P-0001 not found")
        
        adr = parser.parse_physical_adr(adr_path)
        
        assert adr.id == "ADR-P-0001"
        assert adr.status.value == "superseded"
        assert "ADR-L-0001" in adr.implements_logical
        assert len(adr.component_specifications) == 4


class TestInvalidADRs:
    """Test invalid ADR detection."""
    
    def test_missing_required_field(self, parser, fixtures_dir):
        """Test that missing required field is detected."""
        adr_path = fixtures_dir / "invalid" / "missing-required-field.yaml"
        
        with pytest.raises(ADRSchemaValidationError, match="'decisions' is a required property"):
            parser.parse_logical_adr(adr_path)
    
    def test_invalid_id_format(self, parser, fixtures_dir):
        """Test that invalid ID format is detected."""
        adr_path = fixtures_dir / "invalid" / "invalid-id-format.yaml"
        
        with pytest.raises((ADRSchemaValidationError, ADRParseError)):
            parser.parse_logical_adr(adr_path)


class TestIDPatternValidation:
    """Test ID pattern validation."""
    
    def test_logical_id_pattern(self, parser, fixtures_dir):
        """Test logical ADR ID must match ADR-L-XXXX pattern."""
        adr_path = fixtures_dir / "valid" / "logical-minimal.yaml"
        adr = parser.parse_logical_adr(adr_path)
        
        assert adr.id.startswith("ADR-L-")
        assert len(adr.id) == 10  # ADR-L-0001
    
    def test_physical_id_pattern(self, parser, fixtures_dir):
        """Test physical ADR ID must match ADR-P-XXXX pattern."""
        adr_path = fixtures_dir / "valid" / "physical-minimal.yaml"
        adr = parser.parse_physical_adr(adr_path)
        
        assert adr.id.startswith("ADR-P-")
        assert len(adr.id) == 10  # ADR-P-0001
