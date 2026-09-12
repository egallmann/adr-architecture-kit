"""ADR-scoped NormativeProposition authoring contract v1.6."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ..v1_3.identity import UUIDV7_RE

NormativeForceV16 = Literal["MUST", "MUST NOT", "SHOULD", "SHOULD NOT", "MAY"]


class NormativePropositionV16(BaseModel):
    """A declared proposition whose authority remains with its containing ADR."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., pattern=UUIDV7_RE.pattern)
    alias_id: str = Field(..., pattern=r"^NP-[0-9]{4}$")
    alias_name: str = Field(..., pattern=r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
    statement: str = Field(..., min_length=1)
    normative_force: NormativeForceV16
    scope: str = Field(..., min_length=1)
    rationale: str | None = None
