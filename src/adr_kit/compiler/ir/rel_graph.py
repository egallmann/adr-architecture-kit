"""Relationship graph IR types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ...identity import derive_assertion_id

RELATIONSHIP_TYPES = (
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
    "composed_of",
    "binds_substrate",
    "binds_rule",
    "expects_evidence",
)


@dataclass
class IRRelationship:
    """IR relationship representation."""

    relationship_type: str
    from_entity_id: str
    to_entity_id: str
    canonical_source_ref: str
    provenance_classification: str = "explicit"
    evidence: list[str] = field(default_factory=list)
    confidence: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)
    relationship_id: str = ""
    assertion_id: str = ""
    source_pointer: str | None = None
    source_owner_id: str | None = None
    id: str = ""
    alias_id: str = ""
    alias_name: str = ""
    extension: dict[str, Any] | None = None
    record_kind: str = "compatibility"

    def __post_init__(self) -> None:
        if self.id:
            self.record_kind = "canonical"
        if not self.relationship_id:
            self.relationship_id = (
                f"{self.relationship_type}:{self.from_entity_id}:{self.to_entity_id}"
            )
        if not self.assertion_id:
            self.assertion_id = derive_assertion_id(
                self.relationship_type,
                self.from_entity_id,
                self.to_entity_id,
                self.canonical_source_ref,
                self.source_pointer,
            )
        self.evidence = sorted(set(self.evidence))


@dataclass
class RelGraph:
    """Deterministic IR relationship store."""

    _relationships: dict[str, IRRelationship] = field(default_factory=dict)

    def add(self, relationship: IRRelationship) -> None:
        if relationship.relationship_id in self._relationships:
            return
        self._relationships[relationship.relationship_id] = relationship

    def values(self) -> list[IRRelationship]:
        return [self._relationships[key] for key in sorted(self._relationships)]

    def outgoing(self, entity_id: str) -> list[IRRelationship]:
        return [
            relationship
            for relationship in self.values()
            if relationship.from_entity_id == entity_id
        ]
