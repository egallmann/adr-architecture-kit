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

AttributionConfidenceLevel = Literal["declared", "inferred", "heuristic"]

AttributionSourceLanguage = Literal["python", "typescript", "cloudformation", "csharp", "unknown"]


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
    confidence: AttributionConfidenceLevel = "declared"
    attributed_capabilities: list[str] = Field(default_factory=list)
    attribution_source_language: AttributionSourceLanguage | None = None


class ImplementationAttributionEvidence(BaseModel):
    """Collection of extracted implementation attribution claims."""

    schema_version: Literal["1.0", "1.2"] = "1.2"
    type: Literal["implementation_attribution_evidence"] = "implementation_attribution_evidence"
    records: list[ImplementationAttributionRecord] = Field(default_factory=list)
