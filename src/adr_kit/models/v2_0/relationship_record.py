"""Relationship record with UUID endpoints and source-owner for model 2.0."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, cast

from pydantic import BaseModel, Field

from ...decorators import implements_adr
from ...identity import (
    derive_assertion_id_v13,
    derive_relationship_id_v13,
    validate_uuidv7,
)


RelationshipTypeV2 = Literal[
    "declared_in",
    "references",
    "related_to",
    "enforces",
    "enabled_by",
    "enables",
    "governs",
    "implemented_by",
    "embodied_in",
    "implements_logical",
    "supersedes",
    "superseded_by",
    "refines",
    "provides_interface",
    "consumes_interface",
    "composed_of",
    "depends_on",
    "calls",
    "publishes_to",
    "subscribes_to",
    "reads_from",
    "writes_to",
    "binds_substrate",
    "binds_rule",
    "expects_evidence",
]


@implements_adr("ADR-L-0019", "ADR-L-0018")
class RelationshipRecordV2(BaseModel):
    """Relationship with UUID endpoints and explicit source owner (model 2.0)."""

    relationship_id: str
    assertion_id: str = Field(..., pattern=r"^asrt-[0-9a-f]{64}$")
    relationship_type: RelationshipTypeV2
    from_entity_id: str = Field(
        ...,
        pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    )
    to_entity_id: str = Field(
        ...,
        pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    )
    source_owner_id: str = Field(
        ...,
        pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    )
    source_pointer: Optional[str] = None
    provenance_classification: Literal["explicit", "derived", "heuristic"]
    evidence: List[str] = Field(default_factory=list)
    canonical_source_ref: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_uuids(
        cls,
        *,
        relationship_type: str,
        source_uuid: str,
        target_uuid: str,
        source_owner_uuid: str,
        source_pointer: str | None = None,
        provenance_classification: str = "explicit",
        evidence: list[str] | None = None,
        canonical_source_ref: str,
        confidence: float = 1.0,
        metadata: dict[str, Any] | None = None,
    ) -> RelationshipRecordV2:
        """Construct from UUID endpoints, deriving relationship_id and assertion_id."""
        validate_uuidv7(source_uuid)
        validate_uuidv7(target_uuid)
        validate_uuidv7(source_owner_uuid)
        rel_id = derive_relationship_id_v13(relationship_type, source_uuid, target_uuid)
        asrt_id = derive_assertion_id_v13(
            relationship_type,
            source_uuid,
            target_uuid,
            source_owner_uuid,
            source_pointer,
        )
        return cls(
            relationship_id=rel_id,
            assertion_id=asrt_id,
            relationship_type=cast(RelationshipTypeV2, relationship_type),
            from_entity_id=source_uuid,
            to_entity_id=target_uuid,
            source_owner_id=source_owner_uuid,
            source_pointer=source_pointer,
            provenance_classification=cast(
                Literal["explicit", "derived", "heuristic"],
                provenance_classification,
            ),
            evidence=evidence or [],
            canonical_source_ref=canonical_source_ref,
            confidence=confidence,
            metadata=metadata or {},
        )
