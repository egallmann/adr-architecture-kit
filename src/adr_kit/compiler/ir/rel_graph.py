"""Relationship graph IR types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


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
    "supersedes",
    "superseded_by",
    "refines",
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

    def __post_init__(self) -> None:
        if not self.relationship_id:
            self.relationship_id = f"{self.relationship_type}:{self.from_entity_id}:{self.to_entity_id}"
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
