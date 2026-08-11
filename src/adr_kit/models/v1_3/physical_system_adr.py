"""Pydantic model for schema v1.3 Physical-System ADRs."""

from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from ..common import (
    ADRType,
    Governance,
    Ownership,
    Status,
    SubstrateBinding,
    RuleBinding,
    EvidenceExpectation,
)
from ..physical_system_adr import TechnologyChoice
from .identity import UUIDV7_RE, ALIAS_NAME_RE


class AuthoredSystem(BaseModel):
    """Authored system identity object required in v1.3 physical-system ADRs."""

    id: str = Field(..., pattern=UUIDV7_RE.pattern)
    alias_id: str = Field(..., pattern=r"^SYS-\d{4}$")
    alias_name: str = Field(..., min_length=3, max_length=96, pattern=ALIAS_NAME_RE.pattern)
    name: Optional[str] = None


class PhysicalSystemADRv13(BaseModel):
    """Schema v1.3 Physical-System ADR with canonical UUID identity."""

    schema_version: str = Field("1.3", pattern=r"^1\.3$")
    adr_type: ADRType = Field(ADRType.PHYSICAL_SYSTEM, frozen=True)
    id: str = Field(..., pattern=UUIDV7_RE.pattern)
    alias_id: str = Field(..., pattern=r"^ADR-PS-\d{4}$")
    alias_name: str = Field(..., min_length=3, max_length=96, pattern=ALIAS_NAME_RE.pattern)
    title: str = Field(..., min_length=5, max_length=200)
    status: Status
    created_date: str
    modified_date: Optional[str] = None
    authors: List[str] = Field(..., min_length=1)

    domains: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    related_adrs: List[str] = Field(default_factory=list)
    supersedes: List[str] = Field(default_factory=list)
    superseded_by: Optional[str] = None
    ownership: Optional[Ownership] = None
    governance: Optional[Governance] = None
    projection_signals: List[str] = Field(default_factory=list)
    ai_projectable: Optional[dict[str, object]] = None
    introduces_entities: List[str] = Field(default_factory=list)
    modifies_entities: List[str] = Field(default_factory=list)
    realizes_entities: List[str] = Field(default_factory=list)
    substrate_bindings: List[SubstrateBinding] = Field(default_factory=list)
    rule_bindings: List[RuleBinding] = Field(default_factory=list)
    evidence_expectations: List[EvidenceExpectation] = Field(default_factory=list)

    implements_logical: List[str] = Field(..., min_length=1)
    technologies: List[str] = Field(default_factory=list)
    context: str
    technology_stack: List[TechnologyChoice] = Field(..., min_length=1)

    system: AuthoredSystem

    system_boundaries: List[Any] = Field(default_factory=list)
    component_topology: Optional[dict[str, Any]] = None
    integration_patterns: List[Any] = Field(default_factory=list)
    data_flows: List[Any] = Field(default_factory=list)
    references_components: List[str] = Field(default_factory=list)
    deployment_model: Optional[Any] = None
    scalability_strategy: Optional[Any] = None
    failure_modes: List[Any] = Field(default_factory=list)
    operational_requirements: Optional[Any] = None
    conversation_metadata: Optional[Any] = None
    gaps: List[Any] = Field(default_factory=list)

    model_config = ConfigDict(extra="allow")
