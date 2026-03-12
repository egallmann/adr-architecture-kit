"""Pydantic models for standalone invariants."""

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from .common import EnforcementLevel


class InvariantException(BaseModel):
    """Granted exception to an invariant."""
    id: str = Field(..., pattern=r"^EXC-\d{4}$")
    granted_to: str = Field(..., description="Service or component granted exception")
    rationale: str
    expires: date
    approved_by: Optional[str] = None


class StandaloneInvariant(BaseModel):
    """Standalone invariant definition (can also be embedded in ADRs)."""
    
    schema_version: str = Field("1.0", pattern=r"^1\.0$")
    type: str = Field("invariant", pattern=r"^invariant$")
    id: str = Field(..., pattern=r"^INV-\d{4}$")
    
    statement: str = Field(..., min_length=10, description="What must always be true")
    scope: str = Field(..., description="global, domain name, or component name")
    enforcement_level: EnforcementLevel
    enforcement_mechanism: str = Field(..., pattern=r"^(design|runtime|test|policy|manual)$")
    verification_method: str = Field(..., pattern=r"^(automated|manual|audit)$")
    rationale: str
    
    defined_in: Optional[str] = Field(None, pattern=r"^ADR-(L|P|PS|PC|D)-\d{4}$")
    enforced_by: List[str] = Field(default_factory=list)
    related_constraints: List[str] = Field(default_factory=list)
    
    policy_reference: Optional[str] = Field(None, description="Organizational policy reference")
    compliance_frameworks: List[str] = Field(default_factory=list)
    exceptions: List[InvariantException] = Field(default_factory=list)
    
    validation_query: Optional[str] = Field(None, description="Query to validate compliance")
    validation_frequency: Optional[str] = Field(None, pattern=r"^(on_change|daily|weekly|monthly)$")
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{
                "schema_version": "1.0",
                "type": "invariant",
                "id": "INV-0001",
                "statement": "All ADRs must validate against schema before commit",
                "scope": "global",
                "enforcement_level": "must",
                "enforcement_mechanism": "policy",
                "verification_method": "automated",
                "rationale": "Schema validation ensures structural integrity and STE compliance",
                "defined_in": "ADR-L-0001",
                "enforced_by": ["ADR-P-0002"],
                "policy_reference": "ORG-POL-001"
            }]
        }
    )
