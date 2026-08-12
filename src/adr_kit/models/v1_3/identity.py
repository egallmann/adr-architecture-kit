"""Shared v1.3 identity-envelope base types."""

from __future__ import annotations

import re
from pydantic import BaseModel, Field

UUIDV7_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
ALIAS_NAME_RE = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")


class IdentityEnvelope(BaseModel):
    """Minimal identity fields required on every v1.3 admitted record."""

    id: str = Field(..., pattern=UUIDV7_RE.pattern)
    alias_id: str = Field(...)
    alias_name: str = Field(..., min_length=3, max_length=96, pattern=ALIAS_NAME_RE.pattern)
