"""Pydantic models for Logical ADRs."""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .common import (
    ADRFrontmatter,
    ADRType,
    Alternative,
    Consequences,
    EnforcementLevel,
    Gap,
)


class Capability(BaseModel):
    """System capability defined by logical ADR."""
    id: str = Field(..., pattern=r"^CAP-\d{4}$")
    name: str
    description: str
    implemented_by_components: List[str] = Field(default_factory=list)
    enabled_by_decisions: List[str] = Field(default_factory=list)


class ArchitecturalBoundary(BaseModel):
    """Architectural boundary or separation of concerns."""
    id: str = Field(..., pattern=r"^BOUND-\d{4}$")
    name: str
    description: str
    rationale: str


class InteractionContract(BaseModel):
    """Contract between components."""
    id: str = Field(..., pattern=r"^CONTRACT-\d{4}$")
    parties: List[str] = Field(..., min_length=2)
    protocol: str
    guarantees: str


class Constraint(BaseModel):
    """Constraint that shapes the architecture."""
    id: str = Field(..., pattern=r"^CONST-\d{4}$")
    type: str = Field(..., pattern=r"^(technical|business|regulatory|performance|security)$")
    description: str
    rationale: str


class Invariant(BaseModel):
    """Invariant that must hold (embedded in ADR)."""
    id: str = Field(..., pattern=r"^INV-\d{4}$")
    statement: str = Field(..., description="What must always be true")
    scope: str = Field(..., description="global, domain name, or component name")
    enforcement_level: EnforcementLevel
    enforcement_mechanism: str = Field(..., pattern=r"^(design|runtime|test|policy|manual)$")
    verification_method: str = Field(..., pattern=r"^(automated|manual|audit)$")
    rationale: str
    declaration_mode: Optional[str] = Field(None, pattern=r"^(canonical|local|reference)$")
    upheld_by_decisions: List[str] = Field(default_factory=list)
    
    policy_reference: Optional[str] = None
    compliance_frameworks: List[str] = Field(default_factory=list)
    exceptions: List[str] = Field(default_factory=list)


class NonFunctionalRequirement(BaseModel):
    """Non-functional requirement."""
    id: str = Field(..., pattern=r"^NFR-\d{4}$")
    category: str = Field(..., pattern=r"^(performance|security|scalability|reliability|maintainability|usability)$")
    requirement: str
    acceptance_criteria: str


class Decision(BaseModel):
    """Architectural decision (logical level)."""
    id: str = Field(..., pattern=r"^DEC-\d{4}$")
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


class LogicalADR(ADRFrontmatter):
    """Logical ADR - conceptual design without implementation details."""
    
    adr_type: ADRType = Field(ADRType.LOGICAL, frozen=True)
    id: str = Field(..., pattern=r"^ADR-(L|V)-\d{4}$")
    vision_category: bool = False
    promotable_to_logical: Optional[bool] = None
    
    context: str = Field(..., description="Problem space, business drivers, constraints")
    
    capabilities: List[Capability] = Field(default_factory=list)
    architectural_boundaries: List[ArchitecturalBoundary] = Field(default_factory=list)
    interaction_contracts: List[InteractionContract] = Field(default_factory=list)
    constraints: List[Constraint] = Field(default_factory=list)
    invariants: List[Invariant] = Field(default_factory=list)
    non_functional_requirements: List[NonFunctionalRequirement] = Field(default_factory=list)
    decisions: List[Decision] = Field(default_factory=list)
    gaps: List[Gap] = Field(default_factory=list)
    
    model_config = ConfigDict(
        extra="allow",
        json_schema_extra={
            "examples": [{
                "schema_version": "1.0",
                "adr_type": "logical",
                "id": "ADR-L-0001",
                "title": "Two-Layer Architecture Model",
                "status": "accepted",
                "created_date": "2026-03-07",
                "authors": ["erik.gallmann"],
                "domains": ["architecture", "governance"],
                "context": "Need to separate conceptual design from implementation...",
                "decisions": [{
                    "id": "DEC-0001",
                    "summary": "Separate logical and physical ADRs",
                    "rationale": "Enables architectural thinking without implementation bias"
                }]
            }]
        }
    )

    @model_validator(mode="after")
    def validate_logical_variant(self) -> "LogicalADR":
        """Enforce strict ADR-L rules while allowing lightweight ADR-V structure."""
        if self.id.startswith("ADR-L-") and not self.decisions:
            raise ValueError("ADR-L logical ADRs must define at least one decision")
        if self.id.startswith("ADR-V-") and not self.vision_category:
            raise ValueError("ADR-V logical ADRs must set vision_category: true")
        return self
