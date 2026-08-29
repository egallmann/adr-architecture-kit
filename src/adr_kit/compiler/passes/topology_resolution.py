"""Pre-derivation topology handle resolution for authoring v1.5 / model 2.2."""

from __future__ import annotations

from typing import Any

from ...decorators import implements_adr
from ...identity import UUIDV7_PATTERN
from ..frontend.adr_access import (
    field_get,
    is_physical_system_adr,
    topology_components,
    topology_edge_fields,
    topology_relationships,
)

TOPOLOGY_VERBS = frozenset(
    {"calls", "publishes_to", "subscribes_to", "reads_from", "writes_to", "depends_on"}
)


class TopologyResolutionError(ValueError):
    """Raised when authored topology cannot be resolved before derivation."""


@implements_adr("ADR-L-0025")
def resolve_topology_handles(
    *,
    physical_adrs: list[tuple[Any, Any]],
    entities: dict[str, Any],
    model_version: str,
) -> dict[str, dict[str, str]]:
    """Return per-PS maps of TOPO handle -> COMP UUID.

    Legacy fat topology (no ``component_ref``) is skipped. v1.5 slim topology
    fails closed on duplicate handles, missing refs, unresolved COMPs, or
    non-local from/to handles. Name fallback is not permitted.
    """

    if model_version != "2.2":
        return {}

    resolved: dict[str, dict[str, str]] = {}
    for adr, _path in physical_adrs:
        if not is_physical_system_adr(adr):
            continue
        components = topology_components(adr)
        if not components:
            continue
        handles: dict[str, str] = {}
        seen: list[str] = []
        for component in components:
            handle = field_get(component, "id")
            component_ref = field_get(component, "component_ref")
            if not isinstance(handle, str) or not handle:
                raise TopologyResolutionError(
                    f"{getattr(adr, 'alias_id', adr.id)} topology component is missing id"
                )
            if handle in seen:
                raise TopologyResolutionError(
                    f"{getattr(adr, 'alias_id', adr.id)} duplicate TOPO handle {handle}"
                )
            seen.append(handle)
            if not isinstance(component_ref, str) or not component_ref:
                raise TopologyResolutionError(
                    f"{getattr(adr, 'alias_id', adr.id)} topology {handle} is missing "
                    "component_ref; name fallback is not permitted under authoring v1.5"
                )
            if not UUIDV7_PATTERN.match(component_ref):
                raise TopologyResolutionError(
                    f"{getattr(adr, 'alias_id', adr.id)} topology {handle} component_ref "
                    f"{component_ref!r} is not a UUIDv7"
                )
            entity = entities.get(component_ref)
            if entity is None or getattr(entity, "entity_type", None) != "component":
                raise TopologyResolutionError(
                    f"{getattr(adr, 'alias_id', adr.id)} topology {handle} component_ref "
                    f"{component_ref} does not resolve to exactly one admitted COMP"
                )
            handles[handle] = component_ref
        for rel in topology_relationships(adr):
            from_handle, to_handle, verb, _protocol, _description = topology_edge_fields(rel)
            if verb not in TOPOLOGY_VERBS:
                raise TopologyResolutionError(
                    f"{getattr(adr, 'alias_id', adr.id)} topology edge type {verb!r} "
                    "is not a governed topology verb"
                )
            if from_handle not in handles or to_handle not in handles:
                raise TopologyResolutionError(
                    f"{getattr(adr, 'alias_id', adr.id)} topology edge "
                    f"{from_handle} -> {to_handle} does not resolve locally within the owning PS"
                )
        resolved[str(getattr(adr, "id"))] = handles
    return resolved
