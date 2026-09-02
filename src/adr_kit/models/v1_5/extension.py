"""Authoring v1.5 extension relationship validation at the model boundary."""

from __future__ import annotations

from pydantic import model_validator

from ...decorators import implements_adr
from ...semantic_extensions import (
    validate_extension_type,
    validate_property_map,
    validate_rationale,
)
from ..v1_4.extension import ExtensionRelationshipV14


@implements_adr("ADR-L-0023", "ADR-L-0025")
class ExtensionRelationshipV15(ExtensionRelationshipV14):
    """Same persisted shape as v1.4 with v1.5 reserved-core collision rules."""

    @model_validator(mode="after")
    def validate_extension(self) -> "ExtensionRelationshipV15":
        validate_extension_type(
            self.relationship_type,
            kind="relationship",
            authoring_version="1.5",
        )
        validate_property_map(self.properties)
        validate_rationale(self.rationale)
        return self
