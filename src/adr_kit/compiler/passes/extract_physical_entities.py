"""Physical entity extraction pass helper."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ...models import (
    NormalizedEntity,
    PhysicalADR,
    PhysicalComponentADR,
    PhysicalSystemADR,
    lifecycle_stage_from_adr_status,
)
from ..frontend.adr_access import (
    field_get,
    field_list,
    is_physical_component_adr,
    is_physical_system_adr,
    topology_components,
)
from .extract_logical_entities import ExtractedEntity


@dataclass
class PhysicalExtractionResult:
    """Physical extraction output."""

    entities: list[ExtractedEntity] = field(default_factory=list)
    system_ids: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ExtractPhysicalEntitiesPass:
    """Pass-shaped helper for physical ADR extraction."""

    name = "extract_physical_entities"
    required = True
    depends_on: tuple[str, ...] = ()
    halts_on_error = True

    def run(
        self,
        physical_adrs: list[tuple[PhysicalADR | PhysicalSystemADR | PhysicalComponentADR, Path]],
        *,
        source_path,
        canonical,
        provenance,
        summary,
        complete,
        system_entity_id,
    ) -> PhysicalExtractionResult:
        return extract_physical_entities(
            physical_adrs,
            source_path=source_path,
            canonical=canonical,
            provenance=provenance,
            summary=summary,
            complete=complete,
            system_entity_id=system_entity_id,
        )


def _with_aliases(metadata: dict[str, Any], obj: Any) -> dict[str, Any]:
    alias_id = field_get(obj, "alias_id")
    alias_name = field_get(obj, "alias_name")
    if isinstance(alias_id, str) and alias_id:
        metadata["alias_id"] = alias_id
    if isinstance(alias_name, str) and alias_name:
        metadata["alias_name"] = alias_name
    return metadata


def extract_physical_entities(
    physical_adrs: list[tuple[PhysicalADR | PhysicalSystemADR | PhysicalComponentADR, Path]],
    *,
    source_path,
    canonical,
    provenance,
    summary,
    complete,
    system_entity_id,
) -> PhysicalExtractionResult:
    """Extract projectable physical entities."""

    result = PhysicalExtractionResult()

    for adr, path in physical_adrs:
        artifact = source_path(path)
        governance = getattr(adr, "governance", None)
        status = getattr(adr, "status", None)
        status_value = (
            status.value
            if status is not None and hasattr(status, "value")
            else str(status)
        )
        adr_lifecycle = lifecycle_stage_from_adr_status(status_value)
        source_type = (
            "physical_component_adr"
            if is_physical_component_adr(adr)
            else "physical_system_adr"
            if is_physical_system_adr(adr)
            else "physical_adr"
        )
        context = getattr(adr, "context", "") or ""
        impl_auth = (
            getattr(governance, "implementation_authority", None) if governance else None
        )
        adr_metadata = _with_aliases(
            {
                "status": status_value,
                "domains": list(getattr(adr, "domains", []) or []),
                "tags": list(getattr(adr, "tags", []) or []),
                "implementation_authority": (
                    getattr(impl_auth, "value", None) if impl_auth is not None else None
                ),
                "related_reviews": list(getattr(governance, "related_reviews", []) or []) if governance else [],
                "related_overrides": list(getattr(governance, "related_overrides", []) or []) if governance else [],
            },
            adr,
        )
        result.entities.append(
            ExtractedEntity(
                entity=NormalizedEntity(
                    id=adr.id,
                    entity_type="adr",
                    name=adr.title,
                    summary=summary(context),
                    lifecycle_stage=adr_lifecycle,
                    canonical_source=canonical(source_type, adr.id, artifact),
                    metadata=adr_metadata,
                    completeness=complete(),
                    provenance=provenance(source_type, adr.id, "extract_adr", "explicit"),
                ),
                allow_reference_merge=True,
            )
        )

        if is_physical_system_adr(adr):
            authored_system = getattr(adr, "system", None)
            if authored_system is not None:
                system_id = field_get(authored_system, "id")
                if not isinstance(system_id, str) or not system_id:
                    raise ValueError(f"Physical-system ADR {adr.id} is missing authored system.id")
                system_name = field_get(authored_system, "name") or adr.title
                system_metadata = _with_aliases(
                    {
                        "adr_id": adr.id,
                        "adr_alias_id": getattr(adr, "alias_id", adr.id),
                        "implements_logical": list(adr.implements_logical),
                        "technologies": list(getattr(adr, "technologies", []) or []),
                    },
                    authored_system,
                )
            else:
                system_id = system_entity_id(adr.id)
                system_name = adr.title
                system_metadata = {
                    "adr_id": adr.id,
                    "adr_alias_id": getattr(adr, "alias_id", adr.id),
                    "implements_logical": list(adr.implements_logical),
                    "technologies": list(getattr(adr, "technologies", []) or []),
                }
            result.system_ids[adr.id] = system_id
            result.entities.append(
                ExtractedEntity(
                    entity=NormalizedEntity(
                        id=system_id,
                        entity_type="system",
                        name=system_name,
                        summary=summary(context),
                        lifecycle_stage=adr_lifecycle,
                        canonical_source=canonical("physical_system_adr", adr.id, artifact),
                        metadata=system_metadata,
                        completeness=complete(),
                        provenance=provenance("physical_system_adr", adr.id, "extract_system", "explicit"),
                    )
                )
            )
            for topology_component in topology_components(adr):
                component_id = field_get(topology_component, "id")
                if component_id is None:
                    continue
                source_ref = f"{adr.id}#{component_id}"
                result.entities.append(
                    ExtractedEntity(
                        entity=NormalizedEntity(
                            id=component_id,
                            entity_type="component",
                            name=field_get(topology_component, "name") or component_id,
                            summary=summary(field_get(topology_component, "purpose") or ""),
                            lifecycle_stage=adr_lifecycle,
                            canonical_source=canonical(
                                "physical_system_adr", source_ref, artifact
                            ),
                            metadata=_with_aliases(
                                {
                                    "adr_id": adr.id,
                                    "adr_alias_id": getattr(adr, "alias_id", adr.id),
                                    "topology_type": field_get(topology_component, "type"),
                                    "implements_adr": field_get(
                                        topology_component, "implements_adr"
                                    ),
                                },
                                topology_component,
                            ),
                            completeness=complete(),
                            provenance=provenance(
                                "physical_system_adr",
                                source_ref,
                                "extract_topology_component",
                                "explicit",
                            ),
                        )
                    )
                )

        if is_physical_component_adr(adr):
            for component in field_list(adr, "component_specifications"):
                component_id = field_get(component, "component_id") or field_get(component, "id")
                impl_ids = field_get(component, "implementation_identifiers") or {}
                result.entities.append(
                    ExtractedEntity(
                        entity=NormalizedEntity(
                            id=component_id,
                            entity_type="component",
                            name=field_get(component, "name") or component_id,
                            summary=summary(field_get(component, "responsibilities") or ""),
                            lifecycle_stage=adr_lifecycle,
                            canonical_source=canonical("physical_component_adr", f"{adr.id}#{component_id}", artifact),
                            metadata=_with_aliases(
                                {
                                    "adr_id": adr.id,
                                    "adr_alias_id": getattr(adr, "alias_id", adr.id),
                                    "legacy_component_id": field_get(component, "id"),
                                    "technologies": list(getattr(adr, "technologies", []) or []),
                                    "module_path": field_get(impl_ids, "module_path"),
                                    "implements_capabilities": field_list(
                                        component, "implements_capabilities"
                                    ),
                                    "implements_system": list(
                                        getattr(adr, "implements_system", []) or []
                                    ),
                                },
                                component,
                            ),
                            completeness=complete(),
                            provenance=provenance("physical_component_adr", f"{adr.id}#{component_id}", "extract_component", "explicit"),
                        )
                    )
                )
                for interface in field_list(component, "interfaces"):
                    interface_id = field_get(interface, "id")
                    source_ref = f"{adr.id}#{interface_id}"
                    result.entities.append(
                        ExtractedEntity(
                            entity=NormalizedEntity(
                                id=interface_id,
                                entity_type="interface",
                                name=interface_id,
                                summary=summary(field_get(interface, "specification") or ""),
                                lifecycle_stage=adr_lifecycle,
                                canonical_source=canonical(
                                    "physical_component_adr", source_ref, artifact
                                ),
                                metadata=_with_aliases(
                                    {
                                        "adr_id": adr.id,
                                        "adr_alias_id": getattr(adr, "alias_id", adr.id),
                                        "component_id": component_id,
                                        "interface_type": field_get(interface, "type"),
                                        "contract_reference": field_get(
                                            interface, "contract_reference"
                                        ),
                                        "contract_tests": field_get(interface, "contract_tests"),
                                    },
                                    interface,
                                ),
                                completeness=complete(),
                                provenance=provenance(
                                    "physical_component_adr",
                                    source_ref,
                                    "extract_interface",
                                    "explicit",
                                ),
                            )
                        )
                    )

            for decision in field_list(adr, "implementation_decisions"):
                decision_id = field_get(decision, "id")
                source_ref = f"{adr.id}#{decision_id}"
                result.entities.append(
                    ExtractedEntity(
                        entity=NormalizedEntity(
                            id=decision_id,
                            entity_type="implementation_decision",
                            name=field_get(decision, "summary") or decision_id,
                            summary=summary(field_get(decision, "rationale") or ""),
                            lifecycle_stage=adr_lifecycle,
                            canonical_source=canonical(
                                "physical_component_adr", source_ref, artifact
                            ),
                            metadata=_with_aliases(
                                {
                                    "adr_id": adr.id,
                                    "adr_alias_id": getattr(adr, "alias_id", adr.id),
                                    "implements_invariants": field_list(
                                        decision, "implements_invariants"
                                    ),
                                },
                                decision,
                            ),
                            completeness=complete(),
                            provenance=provenance(
                                "physical_component_adr",
                                source_ref,
                                "extract_implementation_decision",
                                "explicit",
                            ),
                        )
                    )
                )

    return result
