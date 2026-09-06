"""Relationship derivation pass helper."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from pydantic import BaseModel, Field

from ...identity import derive_assertion_id
from ...models import (
    LogicalADR,
    NormalizedEntity,
    PhysicalADR,
    PhysicalComponentADR,
    PhysicalSystemADR,
    StandaloneInvariant,
)
from ...models.common import EntityReference, ExternalReference
from ..frontend.adr_access import (
    field_get,
    field_list,
    is_physical_component_adr,
    is_physical_system_adr,
    topology_components,
    topology_edge_fields,
    topology_relationships,
)


@dataclass(frozen=True)
class DerivedGapSignal:
    """Structured unresolved precursor emitted during relationship derivation."""

    gap_id: str
    gap_type: str
    source_entity_id: str
    severity: str
    source_ref: str
    evidence: list[str]
    related_entity_id: str | None = None
    expected_relationship: str | None = None


class DerivedRelationship(BaseModel):
    """Version-neutral derivation candidate. Not a public normalized contract."""

    relationship_id: str
    assertion_id: str = ""
    relationship_type: str
    from_entity_id: str
    to_entity_id: str
    provenance_classification: str = "explicit"
    evidence: list[str] = Field(default_factory=list)
    canonical_source_ref: str
    source_pointer: str | None = None
    confidence: float = 1.0
    metadata: dict = Field(default_factory=dict)

    def model_post_init(self, __context: object) -> None:
        if not self.assertion_id:
            self.assertion_id = derive_assertion_id(
                self.relationship_type,
                self.from_entity_id,
                self.to_entity_id,
                self.canonical_source_ref,
                self.source_pointer,
            )


@dataclass
class RelationshipDerivationResult:
    """Derived relationships plus unresolved precursor signals."""

    relationships: list[DerivedRelationship] = field(default_factory=list)
    generator_gaps: list[DerivedGapSignal] = field(default_factory=list)


@dataclass(frozen=True)
class DeriveRelationshipsPass:
    """Pass-shaped helper for relationship derivation."""

    name = "derive_relationships"
    required = True
    depends_on: tuple[str, ...] = ()
    halts_on_error = True

    def run(
        self,
        *,
        entities: dict[str, NormalizedEntity],
        logical_adrs: list[tuple[LogicalADR, Path]],
        standalone_invariants: list[tuple[StandaloneInvariant, Path]],
        physical_adrs: list[tuple[PhysicalADR | PhysicalSystemADR | PhysicalComponentADR, Path]],
        system_ids: dict[str, str],
        relationship_id,
    ) -> RelationshipDerivationResult:
        return derive_relationships(
            entities=entities,
            logical_adrs=logical_adrs,
            standalone_invariants=standalone_invariants,
            physical_adrs=physical_adrs,
            system_ids=system_ids,
            relationship_id=relationship_id,
        )


def derive_relationships(
    *,
    entities: dict[str, NormalizedEntity],
    logical_adrs: list[tuple[LogicalADR, Path]],
    standalone_invariants: list[tuple[StandaloneInvariant, Path]],
    physical_adrs: list[tuple[PhysicalADR | PhysicalSystemADR | PhysicalComponentADR, Path]],
    system_ids: dict[str, str],
    relationship_id,
) -> RelationshipDerivationResult:
    """Derive relationships and unresolved precursor signals using current generator rules."""

    relationships: dict[str, DerivedRelationship] = {}
    result = RelationshipDerivationResult()

    def add_relationship(
        relationship_type: str,
        from_id: str,
        to_id: str,
        source_ref: str,
        evidence: list[str],
        *,
        classification: str = "explicit",
        confidence: float = 1.0,
        metadata: dict | None = None,
        source_pointer: str | None = None,
        allow_nonlocal_target: bool = False,
    ) -> None:
        if from_id not in entities:
            return
        if to_id not in entities and not allow_nonlocal_target:
            return
        rel_id = relationship_id(relationship_type, from_id, to_id)
        if rel_id in relationships:
            return
        relationships[rel_id] = DerivedRelationship(
            relationship_id=rel_id,
            relationship_type=relationship_type,
            from_entity_id=from_id,
            to_entity_id=to_id,
            provenance_classification=classification,
            evidence=sorted(set(evidence)),
            canonical_source_ref=source_ref,
            source_pointer=source_pointer,
            confidence=confidence,
            metadata=metadata or {},
        )

    def normalized_binding_reference(
        reference: EntityReference, *, owner: str, pointer: str
    ) -> str | dict[str, str]:
        if isinstance(reference, str):
            if reference not in entities:
                raise ValueError(
                    f"Unresolved local binding reference {reference!r} at " f"{owner}#{pointer}"
                )
            return reference
        if not isinstance(reference, ExternalReference):
            raise TypeError(f"Unsupported binding reference at {owner}#{pointer}")
        payload = reference.model_dump(mode="json")
        payload["qualified_id"] = reference.qualified_id
        return payload

    def add_gap(
        gap_id: str,
        gap_type: str,
        source_entity_id: str,
        severity: str,
        source_ref: str,
        evidence: list[str],
        *,
        related_entity_id: str | None = None,
        expected_relationship: str | None = None,
    ) -> None:
        result.generator_gaps.append(
            DerivedGapSignal(
                gap_id=gap_id,
                gap_type=gap_type,
                source_entity_id=source_entity_id,
                severity=severity,
                source_ref=source_ref,
                evidence=evidence,
                related_entity_id=related_entity_id,
                expected_relationship=expected_relationship,
            )
        )

    for entity in list(entities.values()):
        if entity.entity_type != "adr":
            adr_id = entity.canonical_source.source_ref.split("#")[0]
            if adr_id in entities:
                add_relationship(
                    "declared_in",
                    entity.id,
                    adr_id,
                    entity.canonical_source.source_ref,
                    [entity.canonical_source.source_ref],
                )

    for adr, _ in logical_adrs:
        for related in adr.related_adrs:
            if related in entities:
                add_relationship("references", adr.id, related, adr.id, [adr.id])
        for target in field_list(adr, "supersedes"):
            if target in entities:
                add_relationship("supersedes", adr.id, target, adr.id, [adr.id])
                add_relationship(
                    "superseded_by",
                    target,
                    adr.id,
                    adr.id,
                    [adr.id],
                    classification="derived",
                )
        superseded_by = field_get(adr, "superseded_by")
        if isinstance(superseded_by, str) and superseded_by in entities:
            add_relationship("superseded_by", adr.id, superseded_by, adr.id, [adr.id])
            add_relationship(
                "supersedes",
                superseded_by,
                adr.id,
                adr.id,
                [adr.id],
                classification="derived",
            )
        elif superseded_by:
            for target in field_list(adr, "superseded_by"):
                if target in entities:
                    add_relationship("superseded_by", adr.id, target, adr.id, [adr.id])
                    add_relationship(
                        "supersedes",
                        target,
                        adr.id,
                        adr.id,
                        [adr.id],
                        classification="derived",
                    )
        for capability in adr.capabilities:
            for component_id in capability.implemented_by_components:
                if component_id in entities:
                    add_relationship(
                        "implemented_by",
                        capability.id,
                        component_id,
                        f"{adr.id}#{capability.id}",
                        [adr.id],
                    )
                else:
                    add_gap(
                        f"GAP-IMPL-{capability.id}-{component_id}",
                        "capability_without_implementing_component",
                        capability.id,
                        "important",
                        f"{adr.id}#{capability.id}",
                        [adr.id, component_id],
                        related_entity_id=component_id,
                        expected_relationship="implemented_by",
                    )
        for contract in adr.interaction_contracts:
            for party in contract.parties:
                if party in entities:
                    add_relationship(
                        "related_to",
                        contract.id,
                        party,
                        f"{adr.id}#{contract.id}",
                        [adr.id],
                    )
        for decision in adr.decisions:
            for invariant_id in sorted(
                set(decision.related_invariants + decision.enforces_invariants)
            ):
                if invariant_id in entities:
                    add_relationship(
                        "enforces", decision.id, invariant_id, f"{adr.id}#{decision.id}", [adr.id]
                    )
                else:
                    add_gap(
                        f"GAP-INV-{decision.id}-{invariant_id}",
                        "unresolved_reference",
                        decision.id,
                        "important",
                        f"{adr.id}#{decision.id}",
                        [adr.id, invariant_id],
                        related_entity_id=invariant_id,
                        expected_relationship="enforces",
                    )
            for capability_id in decision.enables_capabilities:
                if capability_id in entities:
                    add_relationship(
                        "enables", decision.id, capability_id, f"{adr.id}#{decision.id}", [adr.id]
                    )
                    add_relationship(
                        "enabled_by",
                        capability_id,
                        decision.id,
                        f"{adr.id}#{decision.id}",
                        [adr.id],
                        classification="derived",
                    )
                else:
                    add_gap(
                        f"GAP-CAP-{decision.id}-{capability_id}",
                        "unresolved_reference",
                        decision.id,
                        "important",
                        f"{adr.id}#{decision.id}",
                        [adr.id, capability_id],
                        related_entity_id=capability_id,
                        expected_relationship="enables",
                    )
            for component_id in decision.governs_components:
                if component_id in entities:
                    add_relationship(
                        "governs", decision.id, component_id, f"{adr.id}#{decision.id}", [adr.id]
                    )
            for target in decision.supersedes:
                if target in entities:
                    add_relationship(
                        "supersedes", decision.id, target, f"{adr.id}#{decision.id}", [adr.id]
                    )
                    add_relationship(
                        "superseded_by",
                        target,
                        decision.id,
                        f"{adr.id}#{decision.id}",
                        [adr.id],
                        classification="derived",
                    )
            for target in decision.refines:
                if target in entities:
                    add_relationship(
                        "refines", decision.id, target, f"{adr.id}#{decision.id}", [adr.id]
                    )
        for invariant in adr.invariants:
            for target in getattr(invariant, "supersedes", []) or []:
                if target in entities:
                    add_relationship(
                        "supersedes", invariant.id, target, f"{adr.id}#{invariant.id}", [adr.id]
                    )
                    add_relationship(
                        "superseded_by",
                        target,
                        invariant.id,
                        f"{adr.id}#{invariant.id}",
                        [adr.id],
                        classification="derived",
                    )

        for index, substrate_binding in enumerate(adr.substrate_bindings):
            pointer = f"/substrate_bindings/{index}"
            normalized_binding_reference(
                substrate_binding.selected_by,
                owner=adr.id,
                pointer=f"{pointer}/selected_by",
            )
            external_reference = {
                "namespace": substrate_binding.external_namespace,
                "id": substrate_binding.artifact_id,
                "kind": substrate_binding.kind,
                "fingerprint": substrate_binding.fingerprint,
                "qualified_id": (
                    f"{substrate_binding.external_namespace}:"
                    f"{substrate_binding.artifact_id}"
                ),
            }
            add_relationship(
                "binds_substrate",
                adr.id,
                external_reference["qualified_id"],
                adr.id,
                [adr.id],
                source_pointer=pointer,
                allow_nonlocal_target=True,
                metadata={
                    "target_scope": "external",
                    "external_reference": external_reference,
                    "version": substrate_binding.version,
                    "source_pack": substrate_binding.source_pack,
                    "role": substrate_binding.role,
                    "selected_by": substrate_binding.selected_by,
                    "local_config_ref": substrate_binding.local_config_ref,
                    "supersedes": [
                        normalized_binding_reference(
                            item,
                            owner=adr.id,
                            pointer=f"{pointer}/supersedes/{item_index}",
                        )
                        for item_index, item in enumerate(substrate_binding.supersedes)
                    ],
                },
            )

        for index, rule_binding in enumerate(adr.rule_bindings):
            pointer = f"/rule_bindings/{index}"
            affected_entities = [
                normalized_binding_reference(
                    item,
                    owner=adr.id,
                    pointer=f"{pointer}/affected_entities/{item_index}",
                )
                for item_index, item in enumerate(rule_binding.affected_entities)
            ]
            qualified_id = f"{rule_binding.namespace}:{rule_binding.rule_id}"
            add_relationship(
                "binds_rule",
                adr.id,
                qualified_id,
                adr.id,
                [adr.id],
                source_pointer=pointer,
                allow_nonlocal_target=True,
                metadata={
                    "target_scope": "external",
                    "external_reference": {
                        "namespace": rule_binding.namespace,
                        "id": rule_binding.rule_id,
                        "kind": "rule",
                        "fingerprint": rule_binding.fingerprint,
                        "qualified_id": qualified_id,
                    },
                    "version": rule_binding.version,
                    "disposition": rule_binding.disposition,
                    "rationale": rule_binding.rationale,
                    "exception_ref": rule_binding.exception_ref,
                    "owner": rule_binding.owner,
                    "affected_entities": affected_entities,
                    "expected_evidence_ref": rule_binding.expected_evidence_ref,
                },
            )

        for index, expectation in enumerate(adr.evidence_expectations):
            pointer = f"/evidence_expectations/{index}"
            related_entities = [
                normalized_binding_reference(
                    item,
                    owner=adr.id,
                    pointer=f"{pointer}/related_entities/{item_index}",
                )
                for item_index, item in enumerate(expectation.related_entities)
            ]
            add_relationship(
                "expects_evidence",
                adr.id,
                expectation.expectation_id,
                adr.id,
                [adr.id],
                source_pointer=pointer,
                allow_nonlocal_target=True,
                metadata={
                    "target_scope": "expectation",
                    "kind": expectation.kind,
                    "description": expectation.description,
                    "related_entities": related_entities,
                    "observed_evidence": False,
                },
            )

    for physical_adr, _ in physical_adrs:
        for logical_id in field_list(physical_adr, "implements_logical"):
            if logical_id in entities:
                add_relationship(
                    "implements_logical",
                    physical_adr.id,
                    logical_id,
                    physical_adr.id,
                    [physical_adr.id],
                )
        for target in field_list(physical_adr, "supersedes"):
            if target in entities:
                add_relationship("supersedes", physical_adr.id, target, physical_adr.id, [physical_adr.id])
                add_relationship(
                    "superseded_by",
                    target,
                    physical_adr.id,
                    physical_adr.id,
                    [physical_adr.id],
                    classification="derived",
                )
        superseded_by = field_get(physical_adr, "superseded_by")
        if isinstance(superseded_by, str) and superseded_by in entities:
            add_relationship(
                "superseded_by", physical_adr.id, superseded_by, physical_adr.id, [physical_adr.id]
            )
            add_relationship(
                "supersedes",
                superseded_by,
                physical_adr.id,
                physical_adr.id,
                [physical_adr.id],
                classification="derived",
            )
        if is_physical_component_adr(physical_adr):
            for component in field_list(physical_adr, "component_specifications"):
                component_id = field_get(component, "component_id") or field_get(component, "id")
                for interface in field_list(component, "interfaces"):
                    interface_id = field_get(interface, "id")
                    add_relationship(
                        "provides_interface",
                        component_id,
                        interface_id,
                        f"{physical_adr.id}#{interface_id}",
                        [physical_adr.id],
                    )
                for capability_id in field_list(component, "implements_capabilities"):
                    if capability_id in entities:
                        add_relationship(
                            "implemented_by",
                            capability_id,
                            component_id,
                            f"{physical_adr.id}#{component_id}",
                            [physical_adr.id],
                        )
                    else:
                        add_gap(
                            f"GAP-MISSING-CAP-{component_id}-{capability_id}",
                            "unresolved_reference",
                            component_id,
                            "important",
                            f"{physical_adr.id}#{component_id}",
                            [physical_adr.id, capability_id],
                            related_entity_id=capability_id,
                            expected_relationship="implemented_by",
                        )
                for system_id in field_list(physical_adr, "implements_system"):
                    resolved_system_id = system_ids.get(system_id)
                    if resolved_system_id is None and isinstance(system_id, str):
                        # Legacy ADR-PS-* refs derive SYS-*; UUID refs must hit system_ids.
                        if system_id.startswith("ADR-PS-"):
                            resolved_system_id = f"SYS-{system_id.replace('ADR-PS-', '')}"
                        else:
                            resolved_system_id = system_id
                    if resolved_system_id in entities:
                        add_relationship(
                            "embodied_in",
                            component_id,
                            resolved_system_id,
                            f"{physical_adr.id}#{component_id}",
                            [physical_adr.id],
                        )
                    else:
                        add_gap(
                            f"GAP-MISSING-SYS-{component_id}-{system_id}",
                            "component_without_system",
                            component_id,
                            "important",
                            f"{physical_adr.id}#{component_id}",
                            [physical_adr.id, system_id],
                            related_entity_id=system_id,
                            expected_relationship="embodied_in",
                        )
                for dep in field_list(component, "dependencies"):
                    if dep in entities:
                        add_relationship(
                            "related_to",
                            component_id,
                            dep,
                            f"{physical_adr.id}#{component_id}",
                            [physical_adr.id],
                            classification="derived",
                            confidence=0.8,
                        )
            for implementation_decision in field_list(physical_adr, "implementation_decisions"):
                decision_id = field_get(implementation_decision, "id")
                for invariant_id in field_list(implementation_decision, "implements_invariants"):
                    if invariant_id in entities:
                        add_relationship(
                            "enforces",
                            decision_id,
                            invariant_id,
                            f"{physical_adr.id}#{decision_id}",
                            [physical_adr.id],
                        )
        if is_physical_system_adr(physical_adr):
            system_id = system_ids[physical_adr.id]
            handle_to_comp: dict[str, str] = {}
            for index, topology_component in enumerate(topology_components(physical_adr)):
                topology_id = field_get(topology_component, "id")
                component_ref = field_get(topology_component, "component_ref")
                if topology_id and isinstance(component_ref, str) and component_ref:
                    handle_to_comp[topology_id] = component_ref
                    add_relationship(
                        "composed_of",
                        system_id,
                        component_ref,
                        f"{physical_adr.id}#{topology_id}",
                        [physical_adr.id],
                        source_pointer=f"/component_topology/components/{index}",
                    )
                elif topology_id is not None:
                    add_relationship(
                        "composed_of",
                        system_id,
                        topology_id,
                        f"{physical_adr.id}#{topology_id}",
                        [physical_adr.id],
                    )
            for index, topology_rel in enumerate(topology_relationships(physical_adr)):
                from_handle, to_handle, verb, protocol, description = topology_edge_fields(
                    topology_rel
                )
                if not from_handle or not to_handle or not verb:
                    continue
                from_comp = handle_to_comp.get(from_handle)
                to_comp = handle_to_comp.get(to_handle)
                if not from_comp or not to_comp:
                    continue
                metadata: dict = {}
                if protocol:
                    metadata["protocol"] = protocol
                if description:
                    metadata["description"] = description
                add_relationship(
                    str(verb),
                    from_comp,
                    to_comp,
                    f"{physical_adr.id}#{from_handle}->{to_handle}",
                    [physical_adr.id],
                    source_pointer=f"/component_topology/relationships/{index}",
                    metadata=metadata or None,
                )
            for component_adr in field_list(physical_adr, "references_components"):
                if component_adr in entities:
                    add_relationship(
                        "related_to",
                        physical_adr.id,
                        component_adr,
                        physical_adr.id,
                        [physical_adr.id],
                        classification="derived",
                        confidence=0.8,
                    )

    result.relationships = sorted(relationships.values(), key=lambda item: item.relationship_id)
    result.generator_gaps.sort(key=lambda item: item.gap_id)
    return result
