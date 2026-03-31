"""Pydantic models for implementation attribution evidence."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


ImplementationEntityType = Literal[
    "function",
    "class",
    "module",
    "service",
    "workflow",
    "infrastructure_template",
    "configuration_file",
    "schema_definition",
    "pipeline",
    "script",
    "data_model",
]


class ImplementationAttributionProvenance(BaseModel):
    """Extraction provenance for an implementation attribution claim."""

    source_file: str
    extractor: str
    commit: str | None = None


class ImplementationAttributionRecord(BaseModel):
    """A single implementation-to-ADR attribution claim."""

    implementation_entity_id: str
    implementation_entity_type: ImplementationEntityType
    attributed_adrs: list[str] = Field(default_factory=list)
    enforced_invariants: list[str] = Field(default_factory=list)
    provenance: ImplementationAttributionProvenance
    metadata: dict[str, Any] = Field(default_factory=dict)


class ImplementationAttributionEvidence(BaseModel):
    """Collection of extracted implementation attribution claims."""

    schema_version: str = "1.0"
    type: Literal["implementation_attribution_evidence"] = "implementation_attribution_evidence"
    records: list[ImplementationAttributionRecord] = Field(default_factory=list)
