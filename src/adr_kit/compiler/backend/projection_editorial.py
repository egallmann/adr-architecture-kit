"""Shared editorial helpers for Projection v3 human rendering."""

from __future__ import annotations

from typing import Any, Iterable

from ..ir.rel_graph import IRRelationship
from .neighbor_paths import SEMANTIC_ARCHITECTURE, STRUCTURAL_BRIDGES

TOPOLOGY_EDGE_VERBS = frozenset(
    {
        "depends_on",
        "calls",
        "publishes_to",
        "subscribes_to",
        "reads_from",
        "writes_to",
    }
)
_PC_INTERNAL_STRUCTURE_VERBS = frozenset({"declared_in", "provides_interface"})
_PC_PRIMARY_ARCH_VERBS = frozenset(
    {
        "depends_on",
        "calls",
        "reads_from",
        "writes_to",
        "publishes_to",
        "subscribes_to",
        "provides_interface",
        "consumes_interface",
    }
)
_LOGICAL_SPOKE_VERBS = frozenset({"implements_logical", "implemented_by"})


def is_trivial_ps_topology(component_count: int, relationship_count: int) -> bool:
    """Omit one-node topology diagrams when the system has no internal edges."""
    return component_count == 1 and relationship_count == 0


def should_render_pc_internal_graph(
    *,
    owned_component_count: int,
    structure_edges: Iterable[IRRelationship],
) -> bool:
    """Use a compact entity table instead of a star ownership diagram when trivial."""
    if owned_component_count != 1:
        return True
    edges = list(structure_edges)
    if not edges:
        return False
    return any(rel.relationship_type not in _PC_INTERNAL_STRUCTURE_VERBS for rel in edges)


def is_logical_spoke_only_edges(
    edges: Iterable[IRRelationship],
    *,
    subject_id: str,
    ego_ids: set[str],
) -> bool:
    """True when every edge is a direct logical spoke from the subject ADR."""
    edge_list = list(edges)
    if not edge_list:
        return False
    for rel in edge_list:
        if rel.relationship_type not in _LOGICAL_SPOKE_VERBS:
            return False
        if rel.from_entity_id not in ego_ids and rel.to_entity_id not in ego_ids:
            return False
        if rel.from_entity_id != subject_id and rel.to_entity_id != subject_id:
            if rel.from_entity_id not in ego_ids or rel.to_entity_id not in ego_ids:
                return False
    return True


def is_declared_in_dominated_graph(edges: Iterable[IRRelationship]) -> bool:
    """True when declared_in is the only non-trivial edge type present."""
    edge_list = [rel for rel in edges if rel.relationship_type not in STRUCTURAL_BRIDGES]
    if not edge_list:
        return True
    semantic = [rel for rel in edge_list if rel.relationship_type in SEMANTIC_ARCHITECTURE]
    if not semantic:
        return True
    return all(rel.relationship_type == "declared_in" for rel in edge_list)


def filter_neighborhood_graph_edges(
    edges: Iterable[IRRelationship],
    *,
    subject_id: str,
    ego_ids: set[str],
    has_human_relationship_inventory: bool,
) -> list[IRRelationship]:
    """Drop low-value neighborhood edges before diagram rendering."""
    filtered: list[IRRelationship] = []
    for rel in edges:
        if rel.relationship_type in STRUCTURAL_BRIDGES:
            continue
        if has_human_relationship_inventory and rel.relationship_type in TOPOLOGY_EDGE_VERBS:
            if rel.from_entity_id in ego_ids or rel.to_entity_id in ego_ids:
                continue
        filtered.append(rel)
    if is_logical_spoke_only_edges(filtered, subject_id=subject_id, ego_ids=ego_ids):
        return []
    if has_human_relationship_inventory and is_declared_in_dominated_graph(filtered):
        return []
    return filtered


def ps_member_component_refs(adr: Any) -> set[str]:
    from ..frontend.adr_access import field_get, topology_components

    refs: set[str] = set()
    for component in topology_components(adr):
        ref = field_get(component, "component_ref")
        if isinstance(ref, str) and ref:
            refs.add(ref)
    return refs


def ps_member_owner_ids(
    member_refs: set[str],
    relationships: Iterable[IRRelationship],
) -> set[str]:
    owners: set[str] = set()
    for rel in relationships:
        if rel.relationship_type != "declared_in":
            continue
        if rel.from_entity_id in member_refs:
            owners.add(rel.to_entity_id)
    return owners


def is_internal_ps_member_peer(
    *,
    peer_id: str,
    member_refs: set[str],
    member_owners: set[str],
    paths_for_peer: Iterable[Any],
) -> bool:
    """Filter owning ADR-PC peers reached only through in-system topology."""
    if peer_id not in member_owners:
        return False
    for path in paths_for_peer:
        rel = path.relationship
        if rel.relationship_type not in TOPOLOGY_EDGE_VERBS:
            return False
        if rel.from_entity_id not in member_refs or rel.to_entity_id not in member_refs:
            return False
    return True


def select_pc_primary_architecture_edges(
    *,
    ego: set[str],
    relationships: Iterable[IRRelationship],
) -> list[IRRelationship]:
    """Subject-centered component architecture edges without structural bridges."""
    selected: list[IRRelationship] = []
    seen: set[tuple[str, str, str]] = set()
    for rel in relationships:
        if rel.relationship_type not in _PC_PRIMARY_ARCH_VERBS:
            continue
        if rel.from_entity_id not in ego and rel.to_entity_id not in ego:
            continue
        key = (rel.relationship_type, rel.from_entity_id, rel.to_entity_id)
        if key in seen:
            continue
        seen.add(key)
        selected.append(rel)
    return selected
