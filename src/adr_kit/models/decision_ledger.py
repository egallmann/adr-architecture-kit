"""Pydantic models for Decision Ledger (v1.1)."""

from datetime import date
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class LedgerDecision(BaseModel):
    """Ledger-local decision (pre-ADR design question)."""
    ledger_decision_id: str = Field(..., pattern=r"^LDEC-\d{4}$", description="Ledger-local decision identifier")
    question: str = Field(..., description="What decision must be made?")
    alternatives: List[str] = Field(..., description="Alternatives to consider")
    related_snapshot_items: Optional[List[str]] = Field(
        default_factory=list,
        description="Related snapshot requirement items (RQCAP, RQCONST, RQINV, RQNFR)"
    )
    resolved_by_decisions: Optional[List[str]] = Field(
        default_factory=list,
        description="ADR decisions (DEC-XXXX) that resolved this ledger decision"
    )


class LedgerConstraints(BaseModel):
    """Constraints that bound the design space."""
    snapshot_items: Optional[List[str]] = Field(
        default_factory=list,
        description="Snapshot requirement items that constrain design (RQINV, RQNFR, RQCONST)"
    )


class DecisionLedger(BaseModel):
    """Bounds design space and constrains ADR creation."""
    schema_version: Literal["1.1"] = "1.1"
    type: Literal["decision_ledger"] = "decision_ledger"
    ledger_id: str = Field(..., pattern=r"^LEDGER-\d{4}$")
    version: str = Field(default="1.0", pattern=r"^\d+\.\d+$")
    created_date: date
    source_requirements_snapshot: str = Field(..., pattern=r"^REQ-\d{4}$", description="Immutable reference to requirements snapshot")
    target_logical_adr: str = Field(..., pattern=r"^ADR-L-\d{4}$")
    required_decisions: List[LedgerDecision] = Field(default_factory=list)
    constraints: Optional[LedgerConstraints] = None
