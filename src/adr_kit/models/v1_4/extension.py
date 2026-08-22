"""Strict v1.4 extension and promoted built-in entity contracts."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictFloat, StrictInt, StrictStr, model_validator

from ...semantic_extensions import (
    validate_extension_type,
    validate_property_map,
    validate_rationale,
)
from ..v1_3.identity import UUIDV7_RE, ALIAS_NAME_RE

ExtensionScalar = StrictStr | StrictInt | StrictFloat | StrictBool
ExtensionPropertyValue = ExtensionScalar | list[ExtensionScalar]


class _StrictExtensionModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ExtensionEntityV14(_StrictExtensionModel):
    id: str = Field(..., pattern=UUIDV7_RE.pattern)
    alias_id: str = Field(..., pattern=r"^[A-Z][A-Z0-9]{0,15}-\d{4}$")
    alias_name: str = Field(..., min_length=3, max_length=96, pattern=ALIAS_NAME_RE.pattern)
    entity_type: str
    properties: dict[str, ExtensionPropertyValue] = Field(default_factory=dict)
    rationale: str

    @model_validator(mode="after")
    def validate_extension(self) -> "ExtensionEntityV14":
        validate_extension_type(self.entity_type, kind="entity")
        validate_property_map(self.properties)
        validate_rationale(self.rationale)
        return self


class ExtensionRelationshipV14(_StrictExtensionModel):
    id: str = Field(..., pattern=UUIDV7_RE.pattern)
    alias_id: str = Field(..., pattern=r"^[A-Z][A-Z0-9]{0,15}-\d{4}$")
    alias_name: str = Field(..., min_length=3, max_length=96, pattern=ALIAS_NAME_RE.pattern)
    relationship_type: str
    from_entity_id: str = Field(..., pattern=UUIDV7_RE.pattern)
    to_entity_id: str = Field(..., pattern=UUIDV7_RE.pattern)
    properties: dict[str, ExtensionPropertyValue] = Field(default_factory=dict)
    rationale: str

    @model_validator(mode="after")
    def validate_extension(self) -> "ExtensionRelationshipV14":
        validate_extension_type(self.relationship_type, kind="relationship")
        validate_property_map(self.properties)
        validate_rationale(self.rationale)
        return self


class ConstraintV14(_StrictExtensionModel):
    id: str = Field(..., pattern=UUIDV7_RE.pattern)
    alias_id: str = Field(..., pattern=r"^CONST-\d{4}$")
    alias_name: str = Field(..., min_length=3, max_length=96, pattern=ALIAS_NAME_RE.pattern)
    type: Literal["technical", "business", "regulatory", "performance", "security"]
    description: str
    rationale: str


class NonFunctionalRequirementV14(_StrictExtensionModel):
    id: str = Field(..., pattern=UUIDV7_RE.pattern)
    alias_id: str = Field(..., pattern=r"^NFR-\d{4}$")
    alias_name: str = Field(..., min_length=3, max_length=96, pattern=ALIAS_NAME_RE.pattern)
    category: Literal[
        "performance",
        "security",
        "scalability",
        "reliability",
        "maintainability",
        "usability",
    ]
    requirement: str
    acceptance_criteria: str


class GapV14(_StrictExtensionModel):
    id: str = Field(..., pattern=UUIDV7_RE.pattern)
    alias_id: str = Field(..., pattern=r"^GAP-\d{4}$")
    alias_name: str = Field(..., min_length=3, max_length=96, pattern=ALIAS_NAME_RE.pattern)
    question: str
    context: str | None = None
    impact: Literal["high", "medium", "low"]
    blocking: bool
    affects: list[str] = Field(default_factory=list)
    options: list[dict[str, object]] = Field(default_factory=list)
    decision_required_from: str | None = None
