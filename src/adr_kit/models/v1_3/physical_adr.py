"""Flexible Pydantic models for schema v1.3 physical ADR lines."""

from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from ..common import ADRType, Status
from .identity import UUIDV7_RE, ALIAS_NAME_RE


class PhysicalADRv13(BaseModel):
    """Schema v1.3 legacy physical ADR with UUID identity (extra fields allowed)."""

    schema_version: str = Field("1.3", pattern=r"^1\.3$")
    adr_type: ADRType = Field(ADRType.PHYSICAL, frozen=True)
    id: str = Field(..., pattern=UUIDV7_RE.pattern)
    alias_id: str = Field(..., pattern=r"^ADR-P-\d{4}$")
    alias_name: str = Field(..., min_length=3, max_length=96, pattern=ALIAS_NAME_RE.pattern)
    title: str = Field(..., min_length=5, max_length=200)
    status: Status
    created_date: str
    authors: List[str] = Field(..., min_length=1)
    related_adrs: List[str] = Field(default_factory=list)
    supersedes: List[str] = Field(default_factory=list)
    superseded_by: Optional[str] = None
    component_specifications: List[dict[str, Any]] = Field(default_factory=list)
    implementation_decisions: List[dict[str, Any]] = Field(default_factory=list)

    model_config = ConfigDict(extra="allow")


class PhysicalComponentADRv13(BaseModel):
    """Schema v1.3 physical-component ADR with UUID identity."""

    schema_version: str = Field("1.3", pattern=r"^1\.3$")
    adr_type: ADRType = Field(ADRType.PHYSICAL_COMPONENT, frozen=True)
    id: str = Field(..., pattern=UUIDV7_RE.pattern)
    alias_id: str = Field(..., pattern=r"^ADR-PC-\d{4}$")
    alias_name: str = Field(..., min_length=3, max_length=96, pattern=ALIAS_NAME_RE.pattern)
    title: str = Field(..., min_length=5, max_length=200)
    status: Status
    created_date: str
    authors: List[str] = Field(..., min_length=1)
    related_adrs: List[str] = Field(default_factory=list)
    supersedes: List[str] = Field(default_factory=list)
    superseded_by: Optional[str] = None
    component_specifications: List[dict[str, Any]] = Field(default_factory=list)
    implementation_decisions: List[dict[str, Any]] = Field(default_factory=list)

    model_config = ConfigDict(extra="allow")
