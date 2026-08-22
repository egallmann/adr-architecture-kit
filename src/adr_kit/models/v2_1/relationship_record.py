"""Canonical and compatibility relationship records for model v2.1."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ...semantic_extensions import validate_extension_type
from .normalized_entity import ExtensionPayloadV21

UUIDV7_FIELD = r"^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"


class CanonicalRelationshipV21(BaseModel):
    """An authored/effective relationship with persisted identity."""

    model_config = ConfigDict(extra="forbid")
    record_kind: Literal["canonical"] = "canonical"
    id: str = Field(..., pattern=UUIDV7_FIELD)
    alias_id: str = Field(..., pattern=r"^[A-Z][A-Z0-9]{0,15}-\d{4}$")
    alias_name: str = Field(..., min_length=3, max_length=96)
    relationship_type: str
    from_entity_id: str = Field(..., pattern=UUIDV7_FIELD)
    to_entity_id: str = Field(..., pattern=UUIDV7_FIELD)
    source_owner_id: str | None = Field(None, pattern=UUIDV7_FIELD)
    source_pointer: str | None = None
    provenance_classification: Literal["explicit", "derived", "heuristic"] = "explicit"
    evidence: list[str] = Field(default_factory=list)
    canonical_source_ref: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    extension: ExtensionPayloadV21 | None = None

    @model_validator(mode="after")
    def validate_canonical_boundary(self) -> "CanonicalRelationshipV21":
        if ":" in self.relationship_type:
            validate_extension_type(self.relationship_type, kind="relationship")
            if self.extension is None:
                raise ValueError("Extension canonical relationships require an extension payload")
        elif self.extension is not None:
            raise ValueError("Core canonical relationships cannot carry an extension payload")
        return self


class CompatibilityRelationshipV21(BaseModel):
    """Hash-identified legacy projection, never canonical graph identity."""

    model_config = ConfigDict(extra="forbid")
    record_kind: Literal["compatibility"] = "compatibility"
    relationship_id: str
    assertion_id: str = Field(..., pattern=r"^asrt-[0-9a-f]{64}$")
    relationship_type: str
    from_entity_id: str = Field(..., pattern=UUIDV7_FIELD)
    to_entity_id: str = Field(..., pattern=UUIDV7_FIELD)
    source_owner_id: str | None = Field(None, pattern=UUIDV7_FIELD)
    source_pointer: str | None = None
    provenance_classification: Literal["explicit", "derived", "heuristic"]
    evidence: list[str] = Field(default_factory=list)
    canonical_source_ref: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    metadata: dict[str, object] = Field(default_factory=dict)

    @model_validator(mode="after")
    def reject_extension_compatibility(self) -> "CompatibilityRelationshipV21":
        if ":" in self.relationship_type:
            raise ValueError("Qualified extension relationships require canonical identity")
        return self
