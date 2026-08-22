"""Logical ADR v1.4 model with explicit extension sections."""

from __future__ import annotations

from pydantic import Field

from ..v1_3.logical_adr import LogicalADRv13
from .extension import (
    ConstraintV14,
    ExtensionEntityV14,
    ExtensionRelationshipV14,
    GapV14,
    NonFunctionalRequirementV14,
)


class LogicalADRv14(LogicalADRv13):
    schema_version: str = Field("1.4", pattern=r"^1\.4$")
    constraints: list[ConstraintV14] = Field(default_factory=list)
    non_functional_requirements: list[NonFunctionalRequirementV14] = Field(default_factory=list)
    gaps: list[GapV14] = Field(default_factory=list)
    extension_entities: list[ExtensionEntityV14] = Field(default_factory=list)
    extension_relationships: list[ExtensionRelationshipV14] = Field(default_factory=list)
