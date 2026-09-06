"""Canonical and compatibility relationship records for model v2.2."""

from __future__ import annotations

from pydantic import model_validator

from ...decorators import implements_adr
from ...semantic_extensions import validate_extension_type
from ..v2_1.relationship_record import CanonicalRelationshipV21, CompatibilityRelationshipV21


@implements_adr("ADR-L-0023", "ADR-L-0025")
class CanonicalRelationshipV22(CanonicalRelationshipV21):
    """Authored/effective relationship with v2.2 reserved-core collision rules."""

    @model_validator(mode="after")
    def validate_canonical_boundary(self) -> "CanonicalRelationshipV22":
        if ":" in self.relationship_type:
            validate_extension_type(
                self.relationship_type,
                kind="relationship",
                model_version="2.2",
            )
            if self.extension is None:
                raise ValueError("Extension canonical relationships require an extension payload")
        elif self.extension is not None:
            raise ValueError("Core canonical relationships cannot carry an extension payload")
        return self


class CompatibilityRelationshipV22(CompatibilityRelationshipV21):
    """Hash-identified compatibility projection for model 2.2."""
