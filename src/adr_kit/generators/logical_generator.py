"""Logical and vision ADR YAML generator."""

from ..models import LogicalADR
from .source_adr_generator import SourceADRGenerator


class LogicalADRGenerator(SourceADRGenerator[LogicalADR]):
    """Generate YAML source files for Logical and Vision ADRs."""

    model_class = LogicalADR
    schema_name = "logical"
