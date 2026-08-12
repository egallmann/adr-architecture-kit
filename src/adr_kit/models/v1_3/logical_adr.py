"""Pydantic model for schema v1.3 Logical ADRs."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..common import (
    ADRType,
    Alternative,
    Consequences,
    EnforcementLevel,
    Gap,
    Governance,
    Ownership,
    Status,
    SubstrateBinding,
    RuleBinding,
    EvidenceExpectation,
)
from .identity import IdentityEnvelope, UUIDV7_RE, ALIAS_NAME_RE


class CapabilityV13(IdentityEnvelope):
    """Capability with v1.3 identity envelope."""

    alias_id: str = Field(..., pattern=r"^CAP-\d{4}$")
    name: str
    description: str
    implemented_by_components: List[str] = Field(default_factory=list)
    enabled_by_decisions: List[str] = Field(default_factory=list)


class ArchitecturalBoundaryV13(IdentityEnvelope):
    """Boundary with v1.3 identity envelope."""

    alias_id: str = Field(..., pattern=r"^BOUND-\d{4}$")
    name: str
    description: str
    rationale: str


class InteractionContractV13(IdentityEnvelope):
    """Contract with v1.3 identity envelope."""

    alias_id: str = Field(..., pattern=r"^CONTRACT-\d{4}$")
    parties: List[str] = Field(..., min_length=2)
    protocol: str
    guarantees: str


class InvariantV13(IdentityEnvelope):
    """Invariant with v1.3 identity envelope."""

    alias_id: str = Field(..., pattern=r"^INV-\d{4}$")
    statement: str
    scope: str
    enforcement_level: EnforcementLevel
    enforcement_mechanism: str = Field(..., pattern=r"^(design|runtime|test|policy|manual)$")
    verification_method: str = Field(..., pattern=r"^(automated|manual|audit)$")
    rationale: str
    declaration_mode: Optional[str] = Field(None, pattern=r"^(canonical|local|reference)$")
    upheld_by_decisions: List[str] = Field(default_factory=list)
    policy_reference: Optional[str] = None
    compliance_frameworks: List[str] = Field(default_factory=list)
    exceptions: List[str] = Field(default_factory=list)
    supersedes: List[str] = Field(default_factory=list)


class DecisionV13(IdentityEnvelope):
    """Decision with v1.3 identity envelope."""

    alias_id: str = Field(..., pattern=r"^DEC-\d{4}$")
    summary: str
    rationale: str
    alternatives_considered: List[Alternative] = Field(default_factory=list)
    consequences: Optional[Consequences] = None
    related_invariants: List[str] = Field(default_factory=list)
    enforces_invariants: List[str] = Field(default_factory=list)
    enables_capabilities: List[str] = Field(default_factory=list)
    governs_components: List[str] = Field(default_factory=list)
    supersedes: List[str] = Field(default_factory=list)
    refines: List[str] = Field(default_factory=list)


class LogicalADRv13(BaseModel):
    """Schema v1.3 Logical ADR with canonical UUID identity."""

    schema_version: str = Field("1.3", pattern=r"^1\.3$")
    adr_type: ADRType = Field(ADRType.LOGICAL, frozen=True)
    id: str = Field(..., pattern=UUIDV7_RE.pattern)
    alias_id: str = Field(..., pattern=r"^ADR-(L|V)-\d{4}$")
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

    vision_category: bool = False
    promotable_to_logical: Optional[bool] = None
    context: str = Field(..., description="Problem space and business drivers")

    capabilities: List[CapabilityV13] = Field(default_factory=list)
    architectural_boundaries: List[ArchitecturalBoundaryV13] = Field(default_factory=list)
    interaction_contracts: List[InteractionContractV13] = Field(default_factory=list)
    constraints: List[dict[str, object]] = Field(default_factory=list)
    invariants: List[InvariantV13] = Field(default_factory=list)
    non_functional_requirements: List[dict[str, object]] = Field(default_factory=list)
    decisions: List[DecisionV13] = Field(default_factory=list)
    gaps: List[Gap] = Field(default_factory=list)

    model_config = ConfigDict(extra="allow")

    @model_validator(mode="after")
    def validate_logical_variant(self) -> "LogicalADRv13":
        if self.alias_id.startswith("ADR-L-") and not self.decisions:
            raise ValueError("ADR-L logical ADRs must define at least one decision")
        if self.alias_id.startswith("ADR-V-") and not self.vision_category:
            raise ValueError("ADR-V logical ADRs must set vision_category: true")
        return self
