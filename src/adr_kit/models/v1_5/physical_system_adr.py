"""Physical-system ADR v1.5 with typed slim topology."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ...decorators import implements_adr
from ..v1_3.identity import UUIDV7_RE
from ..v1_4.extension import ExtensionEntityV14
from ..v1_4.physical_system_adr import PhysicalSystemADRv14
from .extension import ExtensionRelationshipV15

TOPO_HANDLE_RE = r"^TOPO-[A-Z0-9][A-Z0-9-]*$"
TopologyVerb = Literal[
    "calls",
    "publishes_to",
    "subscribes_to",
    "reads_from",
    "writes_to",
    "depends_on",
]


class TopologyComponentV15(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(..., pattern=TOPO_HANDLE_RE)
    component_ref: str = Field(..., pattern=UUIDV7_RE.pattern)
    purpose: str


class TopologyRelationshipV15(BaseModel):
    model_config = ConfigDict(extra="forbid")
    from_: str = Field(..., alias="from", pattern=TOPO_HANDLE_RE)
    to: str = Field(..., pattern=TOPO_HANDLE_RE)
    type: TopologyVerb
    protocol: str | None = None
    description: str | None = None


class ComponentTopologyV15(BaseModel):
    model_config = ConfigDict(extra="forbid")
    components: list[TopologyComponentV15] = Field(default_factory=list)
    relationships: list[TopologyRelationshipV15] = Field(default_factory=list)


@implements_adr("ADR-L-0001", "ADR-L-0025")
class PhysicalSystemADRv15(PhysicalSystemADRv14):
    schema_version: str = Field("1.5", pattern=r"^1\.5$")
    component_topology: ComponentTopologyV15 | None = None
    extension_entities: list[ExtensionEntityV14] = Field(default_factory=list)
    extension_relationships: list[ExtensionRelationshipV15] = Field(default_factory=list)

    @model_validator(mode="after")
    def reject_dual_authored_component_refs(self) -> "PhysicalSystemADRv15":
        if self.references_components:
            raise ValueError(
                "references_components must be empty in authoring v1.5; "
                "membership is derived from component_topology.components[].component_ref"
            )
        return self
