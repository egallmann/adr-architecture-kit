"""Compiler identity helpers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, order=True)
class QualifiedEntityId:
    """Qualified identifier for a compiler entity."""

    scope: str
    entity_id: str

    def __str__(self) -> str:
        return f"{self.scope}::{self.entity_id}"
