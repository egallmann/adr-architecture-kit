"""Physical-system ADR v1.4 model with explicit extension sections."""

from __future__ import annotations

from pydantic import Field

from ..v1_3.physical_system_adr import PhysicalSystemADRv13
from .extension import ExtensionEntityV14, ExtensionRelationshipV14


class PhysicalSystemADRv14(PhysicalSystemADRv13):
    schema_version: str = Field("1.4", pattern=r"^1\.4$")
    extension_entities: list[ExtensionEntityV14] = Field(default_factory=list)
    extension_relationships: list[ExtensionRelationshipV14] = Field(default_factory=list)

