"""Pydantic models for objection override governance artifacts."""

from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ImplementationEffect(str, Enum):
    """Allowed implementation effect semantics for an override."""

    EXCEPTION = "exception"
    DEFERRED_COMPLIANCE = "deferred_compliance"
    RISK_ACCEPTED_VARIANCE = "risk_accepted_variance"


class ObjectionOverride(BaseModel):
    """Canonical record of an overridden steelman objection."""

    schema_version: str = Field("1.1", pattern=r"^1\.1$")
    type: str = Field("objection_override", pattern=r"^objection_override$")
    id: str = Field(..., pattern=r"^OVERRIDE-\d{4}$")
    related_adr: str = Field(..., pattern=r"^ADR-(L|V|P|PS|PC|D)-\d{4}$")
    related_review: Optional[str] = Field(None, pattern=r"^REVIEW-\d{4}$")
    related_adr_version: Optional[date] = None
    objection_summary: str = Field(..., min_length=5)
    override_rationale: str = Field(..., min_length=5)
    accepted_risk: str = Field(..., min_length=5)
    approving_authority: str = Field(..., min_length=1)
    approved_date: datetime
    implementation_effect: ImplementationEffect
