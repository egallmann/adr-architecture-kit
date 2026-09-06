"""Logical ADR v1.5 model with version-aware extension relationships."""

from __future__ import annotations

from pydantic import Field

from ...decorators import implements_adr
from ..v1_4.extension import ExtensionEntityV14
from ..v1_4.logical_adr import LogicalADRv14
from .extension import ExtensionRelationshipV15


@implements_adr("ADR-L-0001", "ADR-L-0025")
class LogicalADRv15(LogicalADRv14):
    schema_version: str = Field("1.5", pattern=r"^1\.5$")
    # v1.5 JSON Schema leaves these as untyped arrays; do not inherit v1.4
    # ConstraintV14/GapV14 envelopes (that would silently tighten the contract).
    constraints: list[dict[str, object]] = Field(default_factory=list)
    non_functional_requirements: list[dict[str, object]] = Field(default_factory=list)
    gaps: list[dict[str, object]] = Field(default_factory=list)
    extension_entities: list[ExtensionEntityV14] = Field(default_factory=list)
    extension_relationships: list[ExtensionRelationshipV15] = Field(default_factory=list)
