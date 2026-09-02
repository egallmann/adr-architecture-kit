"""Post-derivation IR semantic validation for model 2.2 topology."""

from __future__ import annotations

from typing import Any

from ...decorators import implements_adr
from ..frontend.adr_access import (
    field_get,
    field_list,
    is_physical_component_adr,
    is_physical_system_adr,
    topology_components,
)
from ..ir.rel_graph import IRRelationship
from .topology_resolution import TOPOLOGY_VERBS


class TopologySemanticError(ValueError):
    """Raised when derived IR topology violates DEC-0174/0175."""


def _entity_type(entities: Any, entity_id: str) -> str | None:
    entity = entities.get(entity_id)
    if entity is None:
        return None
    return getattr(entity, "entity_type", None)


@implements_adr("ADR-L-0025")
def validate_ir_topology_semantics(
    *,
    entities: Any,
    relationships: list[IRRelationship],
    physical_adrs: list[tuple[Any, Any]],
) -> None:
    """Level A IR semantic checks. Never coerce through RelationshipRecord."""

    for entity in entities.values():
        entity_id = getattr(entity, "id", "")
        if isinstance(entity_id, str) and entity_id.startswith("TOPO-"):
            raise TopologySemanticError(
                f"TOPO handle {entity_id} was admitted as a normalized entity identity"
            )

    composed: dict[str, set[str]] = {}
    for relationship in relationships:
        from_id = relationship.from_entity_id
        to_id = relationship.to_entity_id
        if from_id.startswith("TOPO-") or to_id.startswith("TOPO-"):
            raise TopologySemanticError(
                f"Relationship {relationship.relationship_type} uses TOPO identity "
                f"{from_id} -> {to_id}"
            )
        from_type = _entity_type(entities, from_id)
        to_type = _entity_type(entities, to_id)
        if from_type is None or (to_type is None and relationship.metadata.get("target_scope") not in {"external", "expectation"}):
            raise TopologySemanticError(
                f"Relationship {relationship.relationship_type} endpoint does not exist: "
                f"{from_id} -> {to_id}"
            )
        if relationship.relationship_type == "composed_of":
            if from_type != "system" or to_type != "component":
                raise TopologySemanticError(
                    f"composed_of requires SYS -> COMP, found {from_type} -> {to_type} "
                    f"({from_id} -> {to_id})"
                )
            composed.setdefault(from_id, set()).add(to_id)
        if relationship.relationship_type in TOPOLOGY_VERBS:
            if from_type != "component" or to_type != "component":
                raise TopologySemanticError(
                    f"{relationship.relationship_type} requires COMP -> COMP, found "
                    f"{from_type} -> {to_type} ({from_id} -> {to_id})"
                )
            if relationship.provenance_classification != "explicit":
                raise TopologySemanticError(
                    f"Topology verb {relationship.relationship_type} must be explicit provenance"
                )
        if relationship.relationship_type == "consumes_interface":
            raise TopologySemanticError(
                "consumes_interface must not be inferred; no authored extraction path exists "
                "in v1.5 topology"
            )

    # DEC-0174: PS membership vs PC implements_system — do not pick a side.
    system_id_by_adr: dict[str, str] = {}
    members_by_system: dict[str, set[str]] = {}
    for adr, _path in physical_adrs:
        if not is_physical_system_adr(adr):
            continue
        authored = getattr(adr, "system", None)
        system_id = field_get(authored, "id") if authored is not None else None
        if not isinstance(system_id, str):
            continue
        system_id_by_adr[str(adr.id)] = system_id
        members = {
            ref
            for component in topology_components(adr)
            if isinstance((ref := field_get(component, "component_ref")), str) and ref
        }
        members_by_system[system_id] = members

    def _resolve_system_ref(reference: str) -> str:
        return system_id_by_adr.get(reference, reference)

    pc_systems: dict[str, set[str]] = {}
    for adr, _path in physical_adrs:
        if not is_physical_component_adr(adr):
            continue
        systems = {
            _resolve_system_ref(item)
            for item in field_list(adr, "implements_system")
            if isinstance(item, str)
        }
        for component in field_list(adr, "component_specifications"):
            component_id = field_get(component, "component_id") or field_get(component, "id")
            if isinstance(component_id, str):
                pc_systems[component_id] = systems

    for system_id, members in members_by_system.items():
        for component_id in members:
            claimed = pc_systems.get(component_id, set())
            if claimed and system_id not in claimed:
                raise TopologySemanticError(
                    f"PS membership vs PC implements_system contradiction: COMP {component_id} "
                    f"is composed_of SYS {system_id} but the PC does not list that system"
                )
            if not claimed:
                raise TopologySemanticError(
                    f"PS membership vs PC implements_system contradiction: COMP {component_id} "
                    f"is composed_of SYS {system_id} but no PC implements_system claim exists"
                )
