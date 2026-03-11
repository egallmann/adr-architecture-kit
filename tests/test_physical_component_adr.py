"""Tests for Physical-Component ADR parsing and validation."""

import pytest
from pathlib import Path

from adr_kit.parser import ADRParser
from adr_kit.validators import ADRValidator
from adr_kit.models import PhysicalComponentADR


def test_parse_physical_component_minimal():
    """Test parsing minimal valid Physical-Component ADR."""
    parser = ADRParser()
    fixture_path = Path(__file__).parent / "fixtures" / "valid" / "physical-component-minimal.yaml"
    
    adr = parser.parse_physical_component_adr(fixture_path)
    
    assert isinstance(adr, PhysicalComponentADR)
    assert adr.id == "ADR-PC-0001"
    assert adr.adr_type.value == "physical-component"
    assert adr.title == "User Service API Component"
    assert len(adr.implements_system) == 1
    assert adr.implements_system[0] == "ADR-PS-0001"
    assert len(adr.implements_logical) == 1
    assert adr.implements_logical[0] == "ADR-L-0001"
    assert len(adr.component_specifications) == 1


def test_parse_adr_auto_detect_physical_component():
    """Test auto-detection of Physical-Component ADR type."""
    parser = ADRParser()
    fixture_path = Path(__file__).parent / "fixtures" / "valid" / "physical-component-minimal.yaml"
    
    adr = parser.parse_adr(fixture_path)
    
    assert isinstance(adr, PhysicalComponentADR)
    assert adr.id == "ADR-PC-0001"


def test_validate_physical_component_adr():
    """Test validation of Physical-Component ADR."""
    parser = ADRParser()
    validator = ADRValidator(parser=parser)
    fixture_path = Path(__file__).parent / "fixtures" / "valid" / "physical-component-minimal.yaml"
    
    result = validator.validate_file(fixture_path)
    
    assert result.valid
    assert len(result.errors) == 0


def test_physical_component_requires_system_reference():
    """Test that Physical-Component ADR must reference system ADR."""
    from adr_kit.models import PhysicalComponentADR, ADRType, Status
    from datetime import date
    
    with pytest.raises(Exception):  # Pydantic validation error
        PhysicalComponentADR(
            schema_version="1.0",
            adr_type=ADRType.PHYSICAL_COMPONENT,
            id="ADR-PC-0001",
            title="Test Component",
            status=Status.PROPOSED,
            created_date=date.today(),
            authors=["test"],
            domains=["test"],
            implements_system=[],  # Empty - should fail
            implements_logical=["ADR-L-0001"],
            context="Test context",
            technology_stack=[],
            component_specifications=[],
        )


def test_physical_component_requires_component_specs():
    """Test that Physical-Component ADR must have component specifications."""
    from adr_kit.models import PhysicalComponentADR, ADRType, Status, TechnologyChoice
    from datetime import date
    
    with pytest.raises(Exception):  # Pydantic validation error
        PhysicalComponentADR(
            schema_version="1.0",
            adr_type=ADRType.PHYSICAL_COMPONENT,
            id="ADR-PC-0001",
            title="Test Component",
            status=Status.PROPOSED,
            created_date=date.today(),
            authors=["test"],
            domains=["test"],
            implements_system=["ADR-PS-0001"],
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
            component_specifications=[],  # Empty - should fail
        )


def test_physical_component_id_format():
    """Test that Physical-Component ADR ID must match ADR-PC-XXXX format."""
    from adr_kit.models import (
        PhysicalComponentADR, ADRType, Status, TechnologyChoice,
        ComponentSpecification, GenerationContext, Interface,
        ImplementationIdentifiers, ImplementationRequirements,
        ErrorHandling, Observability, LoggingConfig, Metric,
        TestingRequirements
    )
    from datetime import date
    
    with pytest.raises(Exception):  # Pydantic validation error
        PhysicalComponentADR(
            schema_version="1.0",
            adr_type=ADRType.PHYSICAL_COMPONENT,
            id="ADR-P-0001",  # Wrong prefix - should be ADR-PC-
            title="Test Component",
            status=Status.PROPOSED,
            created_date=date.today(),
            authors=["test"],
            domains=["test"],
            implements_system=["ADR-PS-0001"],
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
            component_specifications=[
                ComponentSpecification(
                    id="COMP-0001",
                    name="Test Component",
                    type="service",
                    responsibilities="Test",
                    generation_context=GenerationContext(
                        purpose="Test",
                        key_responsibilities=["Test"]
                    ),
                    interfaces=[
                        Interface(
                            id="IFACE-0001",
                            type="REST",
                            specification="Test"
                        )
                    ],
                    implementation_identifiers=ImplementationIdentifiers(
                        module_path="src/test"
                    ),
                    implementation_requirements=ImplementationRequirements(
                        error_handling=ErrorHandling(strategy="Test"),
                        observability=Observability(
                            logging=LoggingConfig(level="info", structured=True),
                            metrics=[Metric(name="test", type="counter")]
                        ),
                        testing_requirements=TestingRequirements(
                            unit_test_coverage=">= 80%"
                        )
                    )
                )
            ],
        )


def test_physical_component_generation_context():
    """Test that component specifications have generation context."""
    parser = ADRParser()
    fixture_path = Path(__file__).parent / "fixtures" / "valid" / "physical-component-minimal.yaml"
    
    adr = parser.parse_physical_component_adr(fixture_path)
    comp = adr.component_specifications[0]
    
    assert comp.generation_context is not None
    assert comp.generation_context.purpose
    assert len(comp.generation_context.key_responsibilities) > 0


def test_physical_component_implementation_requirements():
    """Test that component specifications have implementation requirements."""
    parser = ADRParser()
    fixture_path = Path(__file__).parent / "fixtures" / "valid" / "physical-component-minimal.yaml"
    
    adr = parser.parse_physical_component_adr(fixture_path)
    comp = adr.component_specifications[0]
    
    assert comp.implementation_requirements is not None
    assert comp.implementation_requirements.error_handling is not None
    assert comp.implementation_requirements.observability is not None
    assert comp.implementation_requirements.testing_requirements is not None
