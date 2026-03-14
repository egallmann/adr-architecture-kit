"""Unresolved item IR types."""

from __future__ import annotations

from dataclasses import dataclass, field

from ...models.architecture_discovery import DiscoveryProvenance


@dataclass
class IRUnresolved:
    """IR unresolved record."""

    id: str
    gap_class: str
    gap_type: str
    source_entity_id: str
    severity: str
    provenance: DiscoveryProvenance
    evidence: list[str] = field(default_factory=list)
    related_entity_id: str | None = None
    expected_relationship: str | None = None
    suggested_resolution: str | None = None


@dataclass
class UnresolvedList:
    """Deterministic unresolved record store."""

    _items: dict[str, IRUnresolved] = field(default_factory=dict)

    def add(self, item: IRUnresolved) -> None:
        if item.id in self._items:
            raise ValueError(f"Duplicate unresolved ID: {item.id}")
        self._items[item.id] = item

    def values(self) -> list[IRUnresolved]:
        return [self._items[key] for key in sorted(self._items)]
