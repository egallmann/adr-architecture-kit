"""Entity graph IR types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ...models.architecture_discovery import (
    CanonicalSource,
    Completeness,
    DiscoveryProvenance,
    SourceRef,
    TOPOLOGY_RELATIONSHIP_TYPES,
)

IR_ENTITY_TYPES = (
    "adr",
    "system",
    "component",
    "decision",
    "capability",
    "invariant",
    "boundary",
    "contract",
    "constraint",
    "nfr",
    "gap",
    "interface",
    "integration",
    "implementation_decision",
)

ENTITY_RELATIONSHIP_TYPES = (
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
    *TOPOLOGY_RELATIONSHIP_TYPES,
    "binds_substrate",
    "binds_rule",
    "expects_evidence",
)


@dataclass
class IREntity:
    """IR entity representation used by compiler passes."""

    id: str
    entity_type: str
    name: str
    summary: str
    canonical_source: CanonicalSource
    source_refs: list[SourceRef] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    extension: dict[str, Any] | None = None
    completeness: Completeness = field(
        default_factory=lambda: Completeness(status="complete", missing_fields=[])
    )
    provenance: DiscoveryProvenance = field(
        default_factory=lambda: DiscoveryProvenance(
            source_type="ir",
            source_ref="ir",
            extraction_phase="projection",
            classification="derived",
            generator="adr-compiler",
        )
    )


@dataclass
class EntityGraph:
    """Deterministic IR entity store."""

    _entities: dict[str, IREntity] = field(default_factory=dict)

    def add(self, entity: IREntity) -> None:
        if entity.id in self._entities:
            raise ValueError(f"Duplicate IR entity ID: {entity.id}")
        self._entities[entity.id] = entity

    def get(self, entity_id: str) -> IREntity | None:
        return self._entities.get(entity_id)

    def values(self) -> list[IREntity]:
        return [self._entities[key] for key in sorted(self._entities)]

    def by_type(self, entity_type: str) -> list[IREntity]:
        return [entity for entity in self.values() if entity.entity_type == entity_type]
