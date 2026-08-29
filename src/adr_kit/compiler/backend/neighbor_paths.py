"""NeighborPath grammar for Projection v3."""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any, Iterable

from ...decorators import implements_adr
from ..ir.rel_graph import IRRelationship

STRUCTURAL_BRIDGES = frozenset({"declared_in", "embodied_in", "composed_of"})
SEMANTIC_ARCHITECTURE = frozenset(
    {
        "depends_on",
        "calls",
        "publishes_to",
        "subscribes_to",
        "reads_from",
        "writes_to",
        "implements_logical",
        "implemented_by",
        "governs",
        "provides_interface",
        "consumes_interface",
        "enforces",
        "enables",
        "enabled_by",
        "refines",
    }
)
LIFECYCLE_ASSOCIATION = frozenset({"supersedes", "superseded_by", "references", "related_to"})
GOVERNANCE = frozenset({"binds_substrate", "binds_rule", "expects_evidence"})


@dataclass(frozen=True)
class NeighborPath:
    peer_adr_id: str
    semantic_verb: str
    from_id: str
    to_id: str
    source_pointer: str | None
    hop_count: int
    bridge_count: int
    relationship: IRRelationship


def _structural_distance(
    relationships: Iterable[IRRelationship], origins: set[str]
) -> dict[str, int]:
    """Expand subject/far side without reverse composed_of hops across systems.

    ``declared_in`` is an undirected local bridge. ``composed_of`` is directed
    SYS → COMP. ``embodied_in`` remains a structural-bridge class but is not a
    BFS hop: shared-system embodiment would otherwise union unrelated topologies.
    """
    composed: dict[str, set[str]] = defaultdict(set)
    local: dict[str, set[str]] = defaultdict(set)
    for rel in relationships:
        if rel.relationship_type == "composed_of":
            composed[rel.from_entity_id].add(rel.to_entity_id)
        elif rel.relationship_type == "declared_in":
            local[rel.from_entity_id].add(rel.to_entity_id)
            local[rel.to_entity_id].add(rel.from_entity_id)
    dist = {node: 0 for node in origins}
    queue = deque(origins)
    while queue:
        node = queue.popleft()
        neighbors = local.get(node, set()) | composed.get(node, set())
        for nxt in neighbors:
            if nxt in dist:
                continue
            dist[nxt] = dist[node] + 1
            queue.append(nxt)
    return dist


def _owning_adr(entity_id: str, declared_in: dict[str, str], entity_types: dict[str, str]) -> str | None:
    if entity_types.get(entity_id) == "adr":
        return entity_id
    return declared_in.get(entity_id)


@implements_adr("ADR-L-0007", "ADR-L-0025")
def select_neighbor_paths(
    *,
    subject_id: str,
    relationships: list[IRRelationship],
    entity_types: dict[str, str],
) -> list[NeighborPath]:
    """Enumerate grammatical NeighborPaths and keep one path per peer."""

    declared_in: dict[str, str] = {}
    for rel in relationships:
        if rel.relationship_type == "declared_in" and entity_types.get(rel.to_entity_id) == "adr":
            declared_in[rel.from_entity_id] = rel.to_entity_id

    owned = {subject_id}
    for entity_id, adr_id in declared_in.items():
        if adr_id == subject_id:
            owned.add(entity_id)

    subject_side = _structural_distance(relationships, owned)

    candidates: list[NeighborPath] = []
    for rel in relationships:
        if rel.relationship_type not in SEMANTIC_ARCHITECTURE:
            continue
        endpoints = (rel.from_entity_id, rel.to_entity_id)
        for start, far in (endpoints, (endpoints[1], endpoints[0])):
            if start not in subject_side:
                continue
            # ADR-to-ADR semantic edges already name the peer. Expanding
            # composed_of from that ADR would union every topology member
            # as a false peer and collapse the neighborhood to one edge.
            if entity_types.get(far) == "adr":
                if far == subject_id:
                    continue
                far_side = {far: 0}
                peers = {far}
            else:
                far_side = _structural_distance(relationships, {far})
                peers = set()
                for node in far_side:
                    owner = _owning_adr(node, declared_in, entity_types)
                    if owner and owner != subject_id:
                        peers.add(owner)
            for peer in peers:
                prefix = subject_side[start]
                suffix = min(
                    (
                        far_side[node]
                        for node in far_side
                        if _owning_adr(node, declared_in, entity_types) == peer
                    ),
                    default=0,
                )
                hop_count = prefix + 1 + suffix
                candidates.append(
                    NeighborPath(
                        peer_adr_id=peer,
                        semantic_verb=rel.relationship_type,
                        from_id=rel.from_entity_id,
                        to_id=rel.to_entity_id,
                        source_pointer=rel.source_pointer,
                        hop_count=hop_count,
                        bridge_count=prefix + suffix,
                        relationship=rel,
                    )
                )

    selected: dict[str, NeighborPath] = {}
    for path in sorted(
        candidates,
        key=lambda item: (
            item.bridge_count,
            item.hop_count,
            item.semantic_verb,
            item.from_id,
            item.to_id,
            item.source_pointer or "",
            item.peer_adr_id,
        ),
    ):
        current = selected.get(path.peer_adr_id)
        if current is None:
            selected[path.peer_adr_id] = path
    return [selected[key] for key in sorted(selected)]
