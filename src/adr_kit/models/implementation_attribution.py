"""Pydantic models for implementation attribution evidence."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from adr_kit.identity import UUIDV7_PATTERN


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

SemanticAttributionRelationship = Literal["implements", "enforces", "embodies"]

ResolvedTargetEntityType = Literal[
    "adr",
    "system",
    "component",
    "decision",
    "capability",
    "invariant",
    "boundary",
    "contract",
    "interface",
    "implementation_decision",
]


class ImplementationAttributionProvenance(BaseModel):
    """Extraction provenance for an implementation attribution claim."""

    source_file: str
    extractor: str
    commit: str | None = None


class ImplementationAttributionRecord(BaseModel):
    """A single implementation-to-ADR attribution claim (schema 1.0/1.2)."""

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
    """Collection of extracted implementation attribution claims (schema 1.0/1.2)."""

    schema_version: Literal["1.0", "1.2"] = "1.2"
    type: Literal["implementation_attribution_evidence"] = "implementation_attribution_evidence"
    records: list[ImplementationAttributionRecord] = Field(default_factory=list)


class SemanticAttributionClaim(BaseModel):
    """A UUID-canonical semantic attribution claim (schema 1.5)."""

    relationship: SemanticAttributionRelationship
    target_entity_id: str
    confidence: AttributionConfidenceLevel
    asserted_target_entity_type: ResolvedTargetEntityType | None = None

    @field_validator("target_entity_id")
    @classmethod
    def _require_uuidv7(cls, value: str) -> str:
        if not isinstance(value, str) or not UUIDV7_PATTERN.match(value):
            raise ValueError(f"Not a valid lowercase UUIDv7: {value!r}")
        return value


class ImplementationAttributionRecordV15(BaseModel):
    """A single implementation surface with v1.5 semantic claims."""

    implementation_entity_id: str
    implementation_entity_type: ImplementationEntityType
    provenance: ImplementationAttributionProvenance
    claims: list[SemanticAttributionClaim] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    attribution_source_language: AttributionSourceLanguage | None = None


class ImplementationAttributionEvidenceV15(BaseModel):
    """Collection of UUID-canonical implementation attribution claims."""

    schema_version: Literal["1.5"] = "1.5"
    type: Literal["implementation_attribution_evidence"] = "implementation_attribution_evidence"
    records: list[ImplementationAttributionRecordV15] = Field(default_factory=list)


AttributionEvidenceDocument = ImplementationAttributionEvidence | ImplementationAttributionEvidenceV15
