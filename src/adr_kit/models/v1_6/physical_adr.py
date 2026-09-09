"""Physical-component ADR authoring v1.6."""

from __future__ import annotations

from pydantic import Field, model_validator

from ...decorators import implements_adr
from ..v1_5.physical_adr import PhysicalComponentADRv15
from .normative_proposition import NormativePropositionV16


@implements_adr("ADR-L-0001", "ADR-L-0028")
class PhysicalComponentADRv16(PhysicalComponentADRv15):
    schema_version: str = Field("1.6", pattern=r"^1\.6$")
    normative_propositions: list[NormativePropositionV16] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_unique_normative_proposition_identity(self) -> "PhysicalComponentADRv16":
        ids = [item.id for item in self.normative_propositions]
        aliases = [item.alias_id for item in self.normative_propositions]
        if len(ids) != len(set(ids)) or len(aliases) != len(set(aliases)):
            raise ValueError("normative_propositions must have unique id and alias_id values")
        return self
