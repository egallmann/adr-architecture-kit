"""Physical-Component ADR YAML generator."""

from ..models import PhysicalComponentADR
from .source_adr_generator import SourceADRGenerator


class PhysicalComponentADRGenerator(SourceADRGenerator[PhysicalComponentADR]):
    """Generate YAML source files for Physical-Component ADRs."""

    model_class = PhysicalComponentADR
    schema_name = "physical_component"
