"""Normalized entity v2.1 with a typed extension payload."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ...semantic_extensions import (
    validate_extension_type,
    validate_property_map,
    validate_rationale,
)
from ..v2_0.normalized_entity import NormalizedEntityV2
from ..v1_4.extension import ExtensionPropertyValue


class ExtensionPayloadV21(BaseModel):
    """Opaque, schema-bounded consumer payload."""

    model_config = ConfigDict(extra="forbid")
    properties: dict[str, ExtensionPropertyValue] = Field(default_factory=dict)
    rationale: str

    @model_validator(mode="after")
    def validate_payload(self) -> "ExtensionPayloadV21":
        validate_property_map(self.properties)
        validate_rationale(self.rationale)
        return self


class NormalizedEntityV21(NormalizedEntityV2):
    """UUID normalized entity with qualified extension semantics."""

    schema_version: str = "2.1"
    entity_type: str
    extension: ExtensionPayloadV21 | None = None

    @model_validator(mode="after")
    def validate_extension_boundary(self) -> "NormalizedEntityV21":
        qualified = ":" in self.entity_type
        if qualified:
            validate_extension_type(self.entity_type, kind="entity")
            if self.extension is None:
                raise ValueError("Extension normalized entities require an extension payload")
        elif self.extension is not None:
            raise ValueError("Core normalized entities cannot carry an extension payload")
        return self
