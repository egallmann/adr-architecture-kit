"""Normalized entity with UUID canonical identity for model 2.0."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, cast

from pydantic import BaseModel, Field

from ..architecture_discovery import (
    CanonicalSource,
    Completeness,
    DiscoveryProvenance,
    EntityRelationshipSummary,
    SourceRef,
)
from ...decorators import implements_adr
from ...identity import (
    derive_alias_ref,
    derive_entity_uri,
    entity_fingerprint as compute_entity_fingerprint,
    uuidv7_created_at,
    validate_uuidv7,
)

NormalizedEntityTypeV2 = Literal[
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


@implements_adr("ADR-L-0019", "ADR-L-0013")
class NormalizedEntityV2(BaseModel):
    """Normalized entity with UUIDv7 canonical identity (model 2.0)."""

    id: str = Field(
        ...,
        pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    )
    alias_id: str
    alias_name: str = Field(..., min_length=3, max_length=96)
    alias_ref: str
    entity_type: NormalizedEntityTypeV2
    name: str
    summary: str
    uri: str = Field(..., pattern=r"^adr://[a-z0-9._-]+/entities/[0-9a-f-]{36}$")
    created_at: str
    entity_fingerprint: str = Field(..., pattern=r"^sha256:[0-9a-f]{64}$")
    lifecycle_stage: Literal["proposed", "active", "deprecated", "superseded"] = "active"
    canonical_source: CanonicalSource
    source_refs: List[SourceRef] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    relationships: EntityRelationshipSummary = Field(default_factory=EntityRelationshipSummary)
    completeness: Completeness
    provenance: DiscoveryProvenance

    @classmethod
    def from_identity_fields(
        cls,
        *,
        uuid: str,
        alias_id: str,
        alias_name: str,
        entity_type: str,
        name: str,
        summary: str,
        architecture_namespace: str,
        lifecycle_stage: str = "active",
        canonical_source: CanonicalSource,
        source_refs: list[SourceRef] | None = None,
        metadata: dict[str, Any] | None = None,
        relationships: EntityRelationshipSummary | None = None,
        completeness: Completeness | None = None,
        provenance: DiscoveryProvenance | None = None,
        fingerprint_record: dict[str, Any] | None = None,
    ) -> NormalizedEntityV2:
        """Construct from authored identity, deriving alias_ref/uri/created_at/fingerprint."""
        validate_uuidv7(uuid)
        ref = derive_alias_ref(alias_id, alias_name)
        uri = derive_entity_uri(architecture_namespace, uuid)
        created = uuidv7_created_at(uuid)
        fp_input = fingerprint_record or {
            "id": uuid,
            "alias_id": alias_id,
            "alias_name": alias_name,
            "entity_type": entity_type,
            "name": name,
        }
        fp = compute_entity_fingerprint(fp_input)
        return cls(
            id=uuid,
            alias_id=alias_id,
            alias_name=alias_name,
            alias_ref=ref,
            entity_type=cast(NormalizedEntityTypeV2, entity_type),
            name=name,
            summary=summary,
            uri=uri,
            created_at=created,
            entity_fingerprint=fp,
            lifecycle_stage=cast(
                Literal["proposed", "active", "deprecated", "superseded"],
                lifecycle_stage,
            ),
            canonical_source=canonical_source,
            source_refs=source_refs or [],
            metadata=metadata or {},
            relationships=relationships or EntityRelationshipSummary(),
            completeness=completeness or Completeness(status="complete", missing_fields=[]),
            provenance=provenance
            or DiscoveryProvenance(
                source_type="compiler",
                source_ref="v2.0",
                extraction_phase="projection",
                classification="derived",
                generator="adr-compiler",
            ),
        )
