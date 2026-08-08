"""Physical entity extraction pass helper."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ...models import (
    NormalizedEntity,
    PhysicalADR,
    PhysicalComponentADR,
    PhysicalSystemADR,
    lifecycle_stage_from_adr_status,
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
        governance = adr.governance
        adr_lifecycle = lifecycle_stage_from_adr_status(adr.status.value)
        source_type = (
            "physical_component_adr"
            if isinstance(adr, PhysicalComponentADR)
            else "physical_system_adr"
            if isinstance(adr, PhysicalSystemADR)
            else "physical_adr"
        )
        result.entities.append(
            ExtractedEntity(
                entity=NormalizedEntity(
                    id=adr.id,
                    entity_type="adr",
                    name=adr.title,
                    summary=summary(adr.context),
                    lifecycle_stage=adr_lifecycle,
                    canonical_source=canonical(source_type, adr.id, artifact),
                    metadata={
                        "status": adr.status.value,
                        "domains": list(adr.domains),
                        "tags": list(adr.tags),
                        "implementation_authority": governance.implementation_authority.value if governance and governance.implementation_authority else None,
                        "related_reviews": list(governance.related_reviews) if governance else [],
                        "related_overrides": list(governance.related_overrides) if governance else [],
                    },
                    completeness=complete(),
                    provenance=provenance(source_type, adr.id, "extract_adr", "explicit"),
                ),
                allow_reference_merge=True,
            )
        )

        if isinstance(adr, PhysicalSystemADR):
            system_id = system_entity_id(adr.id)
            result.system_ids[adr.id] = system_id
            result.entities.append(
                ExtractedEntity(
                    entity=NormalizedEntity(
                        id=system_id,
                        entity_type="system",
                        name=adr.title,
                        summary=summary(adr.context),
                        lifecycle_stage=adr_lifecycle,
                        canonical_source=canonical("physical_system_adr", adr.id, artifact),
                        metadata={
                            "adr_id": adr.id,
                            "implements_logical": list(adr.implements_logical),
                            "technologies": list(adr.technologies),
                        },
                        completeness=complete(),
                        provenance=provenance("physical_system_adr", adr.id, "extract_system", "explicit"),
                    )
                )
            )
            for topology_component in (
                adr.component_topology.components if adr.component_topology else []
            ):
                if topology_component.id is None:
                    continue
                source_ref = f"{adr.id}#{topology_component.id}"
                result.entities.append(
                    ExtractedEntity(
                        entity=NormalizedEntity(
                            id=topology_component.id,
                            entity_type="component",
                            name=topology_component.name,
                            summary=summary(topology_component.purpose),
                            lifecycle_stage=adr_lifecycle,
                            canonical_source=canonical(
                                "physical_system_adr", source_ref, artifact
                            ),
                            metadata={
                                "adr_id": adr.id,
                                "topology_type": topology_component.type,
                                "implements_adr": topology_component.implements_adr,
                            },
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

        if isinstance(adr, PhysicalComponentADR):
            for component in adr.component_specifications:
                component_id = component.component_id or component.id
                result.entities.append(
                    ExtractedEntity(
                        entity=NormalizedEntity(
                            id=component_id,
                            entity_type="component",
                            name=component.name,
                            summary=summary(component.responsibilities),
                            lifecycle_stage=adr_lifecycle,
                            canonical_source=canonical("physical_component_adr", f"{adr.id}#{component_id}", artifact),
                            metadata={
                                "adr_id": adr.id,
                                "legacy_component_id": component.id,
                                "technologies": list(adr.technologies),
                                "module_path": component.implementation_identifiers.module_path,
                                "implements_capabilities": list(component.implements_capabilities),
                                "implements_system": list(adr.implements_system),
                            },
                            completeness=complete(),
                            provenance=provenance("physical_component_adr", f"{adr.id}#{component_id}", "extract_component", "explicit"),
                        )
                    )
                )
                for interface in component.interfaces:
                    source_ref = f"{adr.id}#{interface.id}"
                    result.entities.append(
                        ExtractedEntity(
                            entity=NormalizedEntity(
                                id=interface.id,
                                entity_type="interface",
                                name=interface.id,
                                summary=summary(interface.specification),
                                lifecycle_stage=adr_lifecycle,
                                canonical_source=canonical(
                                    "physical_component_adr", source_ref, artifact
                                ),
                                metadata={
                                    "adr_id": adr.id,
                                    "component_id": component_id,
                                    "interface_type": interface.type,
                                    "contract_reference": interface.contract_reference,
                                    "contract_tests": interface.contract_tests,
                                },
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

            for decision in adr.implementation_decisions:
                source_ref = f"{adr.id}#{decision.id}"
                result.entities.append(
                    ExtractedEntity(
                        entity=NormalizedEntity(
                            id=decision.id,
                            entity_type="implementation_decision",
                            name=decision.summary,
                            summary=summary(decision.rationale),
                            lifecycle_stage=adr_lifecycle,
                            canonical_source=canonical(
                                "physical_component_adr", source_ref, artifact
                            ),
                            metadata={
                                "adr_id": adr.id,
                                "implements_invariants": list(
                                    decision.implements_invariants
                                ),
                            },
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
