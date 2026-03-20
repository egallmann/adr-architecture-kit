"""Pydantic models for canonical steelman review artifacts."""

from datetime import date
from enum import Enum
from typing import List

from pydantic import BaseModel, Field


class ReviewDisposition(str, Enum):
    """Allowed steelman objection dispositions."""

    CLOSED = "closed"
    DEFERRED_WITH_AUTHORITY = "deferred_with_authority"
    BLOCKING = "blocking"


class SteelmanObjection(BaseModel):
    """Structured objection captured during steelman review."""

    statement: str = Field(..., min_length=5)
    why_it_matters: str = Field(..., min_length=5)
    gap_type: str = Field(..., min_length=3)
    evidence_needed: str = Field(..., min_length=5)
    downstream_failure_if_unanswered: str = Field(..., min_length=5)
    disposition: ReviewDisposition


class SteelmanReview(BaseModel):
    """Canonical steelman review artifact."""

    schema_version: str = Field("1.1", pattern=r"^1\.1$")
    type: str = Field("steelman_review", pattern=r"^steelman_review$")
    id: str = Field(..., pattern=r"^REVIEW-\d{4}$")
    target_adr: str = Field(..., pattern=r"^ADR-(L|V|P|PS|PC|D)-\d{4}$")
    review_kind: str = Field("steelman", pattern=r"^steelman$")
    review_date: date
    reviewed_by: str = Field(..., min_length=1)
    overall_recommendation: str = Field(..., min_length=3)
    objections: List[SteelmanObjection] = Field(default_factory=list, min_length=1)
