"""Physical-component ADR v1.5 — topology is not authored on ADR-PC."""

from __future__ import annotations

from typing import Any

from pydantic import Field, model_validator

from ...decorators import implements_adr
from ..v1_4.extension import ExtensionEntityV14
from ..v1_4.physical_adr import PhysicalComponentADRv14
from .extension import ExtensionRelationshipV15


@implements_adr("ADR-L-0001", "ADR-L-0025")
class PhysicalComponentADRv15(PhysicalComponentADRv14):
    schema_version: str = Field("1.5", pattern=r"^1\.5$")
    extension_entities: list[ExtensionEntityV14] = Field(default_factory=list)
    extension_relationships: list[ExtensionRelationshipV15] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def reject_component_topology(cls, data: Any) -> Any:
        if isinstance(data, dict) and "component_topology" in data:
            raise ValueError(
                "component_topology is not permitted on ADR-PC authoring v1.5; "
                "topology is authored by ADR-PS"
            )
        return data
