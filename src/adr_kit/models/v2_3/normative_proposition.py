"""Lifecycle-free normalized NormativeProposition envelope for model v2.3."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from ..architecture_discovery import (
    CanonicalSource,
    Completeness,
    DiscoveryProvenance,
    EntityRelationshipSummary,
    SourceRef,
)
from ..v1_3.identity import UUIDV7_RE
from ..v1_6.normative_proposition import NormativeForceV16


class DeclaringADRQualificationV23(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider: str = Field(..., min_length=1)
    id: str = Field(..., pattern=UUIDV7_RE.pattern)
    alias_id: str = Field(..., pattern=r"^ADR-(L|PS|PC)-[0-9]{4}$")
    alias_name: str = Field(..., pattern=r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")


class SourceArtifactQualificationV23(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_type: str = Field(..., min_length=1)
    source_ref: str = Field(..., min_length=1)
    artifact_path: str = Field(..., min_length=1)
    content_digest: str = Field(..., pattern=r"^sha256:[0-9a-f]{64}$")


class SourceContractQualificationV23(BaseModel):
    model_config = ConfigDict(extra="forbid")
    family: str = Field(..., pattern=r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
    version: str = Field(..., min_length=1)
    fingerprint: str = Field(..., pattern=r"^sha256:[0-9a-f]{64}$")


class NormativePropositionEntityV23(BaseModel):
    """Normalized NP data; declaring ADR lifecycle is intentionally not copied."""

    model_config = ConfigDict(extra="forbid")
    id: str = Field(..., pattern=UUIDV7_RE.pattern)
    alias_id: str = Field(..., pattern=r"^NP-[0-9]{4}$")
    alias_name: str = Field(
        ..., min_length=3, max_length=96, pattern=r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$"
    )
    alias_ref: str
    entity_type: str = Field("normative_proposition", pattern=r"^normative_proposition$")
    name: str
    summary: str
    uri: str
    created_at: str
    entity_fingerprint: str = Field(..., pattern=r"^sha256:[0-9a-f]{64}$")
    statement: str = Field(..., min_length=1)
    normative_force: NormativeForceV16
    scope: str = Field(..., min_length=1)
    rationale: str | None = None
    declaring_adr: DeclaringADRQualificationV23
    source_artifact: SourceArtifactQualificationV23
    source_contract: SourceContractQualificationV23
    canonical_source: CanonicalSource
    source_refs: list[SourceRef] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)
    relationships: EntityRelationshipSummary = Field(default_factory=EntityRelationshipSummary)
    completeness: Completeness
    provenance: DiscoveryProvenance
