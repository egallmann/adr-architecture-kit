"""Pydantic models for remediation ledger governance artifacts."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator


RemediationState = Literal["sentinel", "pending_approval", "approved"]


class RemediationLedgerEntry(BaseModel):
    """Track remediation state for a sentinel-capable field."""

    field_ref: str = Field(..., min_length=1, description="Canonical field reference, e.g. entity:CAP-1000.summary")
    state: RemediationState
    authority_ref: Optional[str] = Field(
        default=None,
        description="Canonical authority reference required for approved state",
    )
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    notes: Optional[str] = None

    @model_validator(mode="after")
    def validate_state_requirements(self) -> "RemediationLedgerEntry":
        """Enforce approval metadata for approved entries only."""
        if self.state == "approved":
            missing = [
                field_name
                for field_name in ("authority_ref", "approved_by", "approved_at")
                if getattr(self, field_name) in (None, "")
            ]
            if missing:
                raise ValueError(
                    f"approved remediation entries require: {', '.join(missing)}"
                )
        return self


class RemediationLedger(BaseModel):
    """Governance ledger for monotonic sentinel remediation."""

    schema_version: Literal["0.1"] = "0.1"
    type: Literal["remediation_ledger"] = "remediation_ledger"
    entries: list[RemediationLedgerEntry] = Field(default_factory=list)
