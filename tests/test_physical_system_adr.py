"""Tests for Physical-System ADR parsing and validation."""

import pytest
from pathlib import Path

from adr_kit.parser import ADRParser, ADRParseError
from adr_kit.validators import ADRValidator
from adr_kit.models import PhysicalSystemADR


def test_parse_physical_system_minimal():
    """Test parsing minimal valid Physical-System ADR."""
    parser = ADRParser()
    fixture_path = Path(__file__).parent / "fixtures" / "valid" / "physical-system-minimal.yaml"
    
    adr = parser.parse_physical_system_adr(fixture_path)
    
    assert isinstance(adr, PhysicalSystemADR)
    assert adr.id == "ADR-PS-0001"
    assert adr.adr_type.value == "physical-system"
    assert adr.title == "User Service System Architecture"
    assert len(adr.implements_logical) == 1
    assert adr.implements_logical[0] == "ADR-L-0001"
    assert len(adr.system_boundaries) == 1
    assert adr.system_boundaries[0].id == "SYSBOUND-0001"


def test_parse_adr_auto_detect_physical_system():
    """Test auto-detection of Physical-System ADR type."""
    parser = ADRParser()
    fixture_path = Path(__file__).parent / "fixtures" / "valid" / "physical-system-minimal.yaml"
    
    adr = parser.parse_adr(fixture_path)
    
    assert isinstance(adr, PhysicalSystemADR)
    assert adr.id == "ADR-PS-0001"


def test_validate_physical_system_adr():
    """Test validation of Physical-System ADR."""
    parser = ADRParser()
    validator = ADRValidator(parser=parser)
    fixture_path = Path(__file__).parent / "fixtures" / "valid" / "physical-system-minimal.yaml"
    
    result = validator.validate_file(fixture_path)
    
    assert result.valid
    assert len(result.errors) == 0


def test_physical_system_requires_logical_reference():
    """Test that Physical-System ADR must reference logical ADR."""
    from adr_kit.models import PhysicalSystemADR, ADRType, Status
    from datetime import date
    
    with pytest.raises(Exception):  # Pydantic validation error
        PhysicalSystemADR(
            schema_version="1.0",
            adr_type=ADRType.PHYSICAL_SYSTEM,
            id="ADR-PS-0001",
            title="Test System",
            status=Status.PROPOSED,
            created_date=date.today(),
            authors=["test"],
            domains=["test"],
            implements_logical=[],  # Empty - should fail
            context="Test context",
            technology_stack=[],
            system_boundaries=[],
        )


def test_physical_system_requires_system_boundaries():
    """Test that Physical-System ADR must have system boundaries."""
    from adr_kit.models import PhysicalSystemADR, ADRType, Status, TechnologyChoice
    from datetime import date
    
    with pytest.raises(Exception):  # Pydantic validation error
        PhysicalSystemADR(
            schema_version="1.0",
            adr_type=ADRType.PHYSICAL_SYSTEM,
            id="ADR-PS-0001",
            title="Test System",
            status=Status.PROPOSED,
            created_date=date.today(),
            authors=["test"],
            domains=["test"],
            implements_logical=["ADR-L-0001"],
            context="Test context",
            technology_stack=[
                TechnologyChoice(
                    category="language",
                    name="Python",
                    version="3.10",
                    rationale="Test"
                )
            ],
            system_boundaries=[],  # Empty - should fail
        )


def test_physical_system_id_format():
    """Test that Physical-System ADR ID must match ADR-PS-XXXX format."""
    from adr_kit.models import PhysicalSystemADR, ADRType, Status, TechnologyChoice, SystemBoundary
    from datetime import date
    
    with pytest.raises(Exception):  # Pydantic validation error
        PhysicalSystemADR(
            schema_version="1.0",
            adr_type=ADRType.PHYSICAL_SYSTEM,
            id="ADR-P-0001",  # Wrong prefix - should be ADR-PS-
            title="Test System",
            status=Status.PROPOSED,
            created_date=date.today(),
            authors=["test"],
            domains=["test"],
            implements_logical=["ADR-L-0001"],
            context="Test context",
            technology_stack=[
                TechnologyChoice(
                    category="language",
                    name="Python",
                    version="3.10",
                    rationale="Test"
                )
            ],
            system_boundaries=[
                SystemBoundary(
                    id="SYSBOUND-0001",
                    name="Test Boundary",
                    description="Test"
                )
            ],
        )
