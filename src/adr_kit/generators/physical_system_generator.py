"""Physical-System ADR YAML generator."""

from ..models import PhysicalSystemADR
from .source_adr_generator import SourceADRGenerator


class PhysicalSystemADRGenerator(SourceADRGenerator[PhysicalSystemADR]):
    """Generate YAML source files for Physical-System ADRs."""

    model_class = PhysicalSystemADR
    schema_name = "physical_system"
