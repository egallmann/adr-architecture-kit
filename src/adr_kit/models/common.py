"""Common Pydantic models and types for ADR artifacts."""

from datetime import date, datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class ADRType(str, Enum):
    """ADR type enumeration."""
    LOGICAL = "logical"
    PHYSICAL = "physical"
    DECISION = "decision"


class Status(str, Enum):
    """ADR lifecycle status."""
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    DEPRECATED = "deprecated"
    SUPERSEDED = "superseded"


class EnforcementLevel(str, Enum):
    """RFC 2119 enforcement levels for invariants."""
    MUST = "must"
    SHOULD = "should"
    MAY = "may"


class ImpactLevel(str, Enum):
    """Impact assessment levels."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Alternative(BaseModel):
    """Alternative approach that was considered and rejected."""
    name: str
    rejected_because: str = Field(..., description="Why this alternative was not chosen")


class Consequences(BaseModel):
    """Positive and negative consequences of a decision."""
    positive: List[str] = Field(default_factory=list)
    negative: List[str] = Field(default_factory=list)


class Gap(BaseModel):
    """Explicit gap or unresolved question."""
    id: str = Field(..., pattern=r"^GAP-\d{4}$")
    question: str = Field(..., description="Unresolved design question")
    context: Optional[str] = None
    impact: ImpactLevel
    blocking: bool = Field(..., description="Does this gap block implementation?")
    affects: List[str] = Field(default_factory=list)
    options: List[dict] = Field(default_factory=list)
    decision_required_from: Optional[str] = None


class Ownership(BaseModel):
    """Ownership metadata for governance."""
    architecture_authority: Optional[str] = Field(None, description="Team responsible for architectural decisions")
    implementation_owners: List[str] = Field(default_factory=list, description="Teams implementing this ADR")


class ADRFrontmatter(BaseModel):
    """Common frontmatter for all ADR types (STE-compliant, PRIME-1, PRIME-2)."""
    
    schema_version: str = Field("1.0", pattern=r"^1\.0$")
    adr_type: ADRType
    id: str = Field(..., pattern=r"^ADR-(L|P|D)-\d{4}$")
    title: str = Field(..., min_length=5, max_length=200)
    status: Status
    created_date: date
    modified_date: Optional[date] = None
    authors: List[str] = Field(..., min_items=1)
    
    domains: List[str] = Field(default_factory=list, min_items=1)
    tags: List[str] = Field(default_factory=list)
    
    related_adrs: List[str] = Field(default_factory=list)
    supersedes: List[str] = Field(default_factory=list)
    superseded_by: Optional[str] = None

    projection_signals: List[str] = Field(
        default_factory=list,
        description="Context signals for rule projection (ste-rules-library)"
    )
    ai_projectable: Optional[dict] = Field(
        None,
        description="AI-first projection hints (minimal_sections, primary_domains)"
    )
    
    ownership: Optional[Ownership] = None
    
    @field_validator('id')
    @classmethod
    def validate_id_matches_type(cls, v: str, info) -> str:
        """Validate that ID prefix matches adr_type."""
        adr_type = info.data.get('adr_type')
        if adr_type == ADRType.LOGICAL and not v.startswith('ADR-L-'):
            raise ValueError(f"Logical ADR must have ID starting with ADR-L-, got {v}")
        elif adr_type == ADRType.PHYSICAL and not v.startswith('ADR-P-'):
            raise ValueError(f"Physical ADR must have ID starting with ADR-P-, got {v}")
        elif adr_type == ADRType.DECISION and not v.startswith('ADR-D-'):
            raise ValueError(f"Decision ADR must have ID starting with ADR-D-, got {v}")
        return v
