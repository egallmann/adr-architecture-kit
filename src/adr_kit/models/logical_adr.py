"""Pydantic models for Logical ADRs."""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

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


class LogicalADR(ADRFrontmatter):
    """Logical ADR - conceptual design without implementation details."""
    
    adr_type: ADRType = Field(ADRType.LOGICAL, frozen=True)
    id: str = Field(..., pattern=r"^ADR-L-\d{4}$")
    
    context: str = Field(..., description="Problem space, business drivers, constraints")
    
    capabilities: List[Capability] = Field(default_factory=list)
    architectural_boundaries: List[ArchitecturalBoundary] = Field(default_factory=list)
    interaction_contracts: List[InteractionContract] = Field(default_factory=list)
    constraints: List[Constraint] = Field(default_factory=list)
    invariants: List[Invariant] = Field(default_factory=list)
    non_functional_requirements: List[NonFunctionalRequirement] = Field(default_factory=list)
    decisions: List[Decision] = Field(..., min_length=1)
    gaps: List[Gap] = Field(default_factory=list)
    
    model_config = ConfigDict(
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
