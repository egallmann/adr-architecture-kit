"""Pydantic models for Requirements Snapshot (v1.1)."""

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field


class RequiredCapability(BaseModel):
    """Snapshot-local capability requirement."""
    req_item_id: str = Field(..., pattern=r"^RQCAP-\d{4}$", description="Snapshot-local capability identifier")
    name: str
    description: str


class RequiredConstraint(BaseModel):
    """Snapshot-local constraint requirement."""
    req_item_id: str = Field(..., pattern=r"^RQCONST-\d{4}$", description="Snapshot-local constraint identifier")
    statement: str


class RequiredInvariant(BaseModel):
    """Snapshot-local invariant requirement."""
    req_item_id: str = Field(..., pattern=r"^RQINV-\d{4}$", description="Snapshot-local invariant identifier")
    statement: str


class RequiredNFR(BaseModel):
    """Snapshot-local NFR requirement."""
    req_item_id: str = Field(..., pattern=r"^RQNFR-\d{4}$", description="Snapshot-local NFR identifier")
    statement: str
    acceptance_criteria: str


class TechnologySignals(BaseModel):
    """Technology stack signals for rule activation."""
    language: Optional[str] = None
    infrastructure: Optional[str] = None
    architecture_pattern: Optional[str] = None


class RequirementsSnapshot(BaseModel):
    """Captures requirements interrogation state at a point in time."""
    schema_version: str = Field(default="1.1", const=True)
    type: str = Field(default="requirements_snapshot", const=True)
    snapshot_id: str = Field(..., pattern=r"^REQ-\d{4}$")
    created_date: date
    required_capabilities: Optional[List[RequiredCapability]] = Field(default_factory=list)
    required_constraints: Optional[List[RequiredConstraint]] = Field(default_factory=list)
    required_invariants: Optional[List[RequiredInvariant]] = Field(default_factory=list)
    required_nfrs: Optional[List[RequiredNFR]] = Field(default_factory=list)
    domains: Optional[List[str]] = Field(default_factory=list, description="Business/technical domains in scope")
    technology_signals: Optional[TechnologySignals] = None
    feeds_logical_adr: Optional[str] = Field(None, pattern=r"^ADR-L-\d{4}$", description="Logical ADR this snapshot feeds")
