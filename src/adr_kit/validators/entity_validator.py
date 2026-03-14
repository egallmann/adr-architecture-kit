"""Validators for entity relationships and traceability."""

from __future__ import annotations

from typing import Dict, List, Set

from ..models import (
    CanonicalSource,
    Completeness,
    DecisionLedger,
    DiscoveryProvenance,
    Entity,
    EntityRegistry,
    LogicalADR,
    NormalizedArchitectureModel,
    NormalizedEntity,
    PhysicalADR,
    RelationshipRecord,
    RequirementsSnapshot,
)


class EntityValidationError(Exception):
    """Error validating entity relationships."""


class EntityValidator:
    """Validate entity relationships and traceability."""

    def validate_entity_references(
        self,
        entity_registry: EntityRegistry | NormalizedArchitectureModel,
        logical_adrs: List[LogicalADR],
        physical_adrs: List[PhysicalADR],
    ) -> List[str]:
        """Validate that all entity references exist in semantic architecture state."""

        model = self._coerce_model(entity_registry)
        errors = []
        entity_ids = {entity.id for entity in model.entities}

        for adr in logical_adrs + physical_adrs:
            for entity_id in adr.introduces_entities:
                if entity_id not in entity_ids:
                    errors.append(f"ADR {adr.id} introduces unknown entity {entity_id}")

        for adr in logical_adrs + physical_adrs:
            for entity_id in adr.modifies_entities:
                if entity_id not in entity_ids:
                    errors.append(f"ADR {adr.id} modifies unknown entity {entity_id}")

        for adr in logical_adrs + physical_adrs:
            for entity_id in adr.realizes_entities:
                if entity_id not in entity_ids:
                    errors.append(f"ADR {adr.id} realizes unknown entity {entity_id}")

        for adr in physical_adrs:
            for comp in adr.component_specifications:
                for cap_id in getattr(comp, "implements_capabilities", []):
                    if cap_id not in entity_ids:
                        errors.append(f"Component {comp.id} in {adr.id} implements unknown capability {cap_id}")

                for entity_id in getattr(comp, "realizes_entities", []):
                    if entity_id not in entity_ids:
                        errors.append(f"Component {comp.id} in {adr.id} realizes unknown entity {entity_id}")

        return errors

    def validate_entity_relationships(
        self,
        entity_registry: EntityRegistry | NormalizedArchitectureModel,
    ) -> List[str]:
        """Validate semantic relationships and unresolved references."""

        model = self._coerce_model(entity_registry)
        errors = []
        entity_ids = {entity.id for entity in model.entities}

        for relationship in model.relationships:
            if relationship.from_entity_id not in entity_ids:
                errors.append(
                    f"Relationship {relationship.relationship_id} references unknown source entity "
                    f"{relationship.from_entity_id}"
                )
            if relationship.to_entity_id not in entity_ids and not relationship.to_entity_id.startswith("ADR-"):
                errors.append(
                    f"Relationship {relationship.relationship_id} references unknown target entity "
                    f"{relationship.to_entity_id}"
                )

        for unresolved in model.unresolved:
            if unresolved.source_entity_id not in entity_ids:
                errors.append(
                    f"Unresolved record {unresolved.id} references unknown source entity "
                    f"{unresolved.source_entity_id}"
                )
            if unresolved.related_entity_id and unresolved.related_entity_id not in entity_ids:
                errors.append(
                    f"Unresolved record {unresolved.id} references unknown related entity "
                    f"{unresolved.related_entity_id}"
                )

        circular = self._detect_circular_dependencies(model)
        if circular:
            errors.append(f"Circular dependency detected: {' -> '.join(circular)}")

        return errors

    def validate_requirements_snapshot_immutability(
        self,
        snapshot: RequirementsSnapshot,
        ledgers: List[DecisionLedger],
    ) -> List[str]:
        """Validate that a requirements snapshot is not modified after being referenced by a ledger."""

        errors = []
        referenced_by = [l.ledger_id for l in ledgers if l.source_requirements_snapshot == snapshot.snapshot_id]

        if referenced_by:
            pass

        return errors

    def validate_decision_ledger_traceability(
        self,
        ledger: DecisionLedger,
        snapshot: RequirementsSnapshot,
        logical_adr: LogicalADR,
    ) -> List[str]:
        """Validate decision ledger traceability to snapshot and ADR."""

        errors = []

        if ledger.source_requirements_snapshot != snapshot.snapshot_id:
            errors.append(f"Ledger {ledger.ledger_id} references wrong snapshot")

        if ledger.target_logical_adr != logical_adr.id:
            errors.append(f"Ledger {ledger.ledger_id} targets wrong ADR")

        snapshot_item_ids = set()
        for cap in snapshot.required_capabilities or []:
            snapshot_item_ids.add(cap.req_item_id)
        for const in snapshot.required_constraints or []:
            snapshot_item_ids.add(const.req_item_id)
        for inv in snapshot.required_invariants or []:
            snapshot_item_ids.add(inv.req_item_id)
        for nfr in snapshot.required_nfrs or []:
            snapshot_item_ids.add(nfr.req_item_id)

        for decision in ledger.required_decisions:
            for item_id in decision.related_snapshot_items or []:
                if item_id not in snapshot_item_ids:
                    errors.append(
                        f"Ledger decision {decision.ledger_decision_id} references unknown snapshot item {item_id}"
                    )

        if ledger.constraints:
            for item_id in ledger.constraints.snapshot_items or []:
                if item_id not in snapshot_item_ids:
                    errors.append(f"Ledger constraint references unknown snapshot item {item_id}")

        return errors

    def _detect_circular_dependencies(self, model: NormalizedArchitectureModel) -> List[str]:
        """Detect circular semantic dependency relationships."""

        graph: Dict[str, Set[str]] = {
            entity.id: set(model.related_entity_ids(entity.id, relationship_type="related_to", direction="outgoing"))
            for entity in model.entities
        }

        visited = set()
        rec_stack = set()
        path: list[str] = []

        def dfs(node: str) -> List[str] | bool:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in sorted(graph.get(node, [])):
                if neighbor not in visited:
                    result = dfs(neighbor)
                    if result:
                        return result
                elif neighbor in rec_stack:
                    cycle_start = path.index(neighbor)
                    return path[cycle_start:] + [neighbor]

            path.pop()
            rec_stack.remove(node)
            return False

        for node in sorted(graph):
            if node not in visited:
                result = dfs(node)
                if result:
                    return result

        return []

    def _coerce_model(
        self,
        entity_registry: EntityRegistry | NormalizedArchitectureModel,
    ) -> NormalizedArchitectureModel:
        if getattr(entity_registry, "type", None) == "normalized_architecture_model":
            return NormalizedArchitectureModel.model_validate(
                entity_registry.model_dump(mode="json", exclude_none=True)
            )
        return self._legacy_registry_to_model(entity_registry)

    def _legacy_registry_to_model(self, entity_registry: EntityRegistry) -> NormalizedArchitectureModel:
        entities = [self._legacy_entity_to_normalized(entity) for entity in entity_registry.entities]
        relationships = self._legacy_relationships(entities)
        return NormalizedArchitectureModel(
            mode="legacy",
            scope_root=".",
            architecture_namespace=None,
            fingerprint="legacy-entity-validator",
            entities=entities,
            relationships=relationships,
            unresolved=[],
            validation_summary=None,
            source_coverage=None,
        )

    def _legacy_entity_to_normalized(self, entity: Entity) -> NormalizedEntity:
        entity_type = entity.entity_type.value
        if entity_type == "implementation_decision":
            entity_type = "decision"
        return NormalizedEntity(
            id=entity.entity_id,
            entity_type=entity_type,
            name=entity.name,
            summary=entity.name,
            canonical_source=CanonicalSource(
                source_type=entity.source_artifact_type.value,
                source_ref=f"{entity.introduced_by}#{entity.entity_id}",
                artifact_path=entity.source_path,
            ),
            metadata={
                "status": entity.lifecycle_stage.value,
                "domains": list(entity.domains or []),
                "introduced_by": entity.introduced_by,
            },
            relationships={
                "declared_in": [entity.introduced_by],
                "related_to": list(getattr(entity.relationships, "depends_on", []) or []),
                "enables": list(getattr(entity.relationships, "implements", []) or []),
                "enforces": list(getattr(entity.relationships, "realizes", []) or []),
            },
            completeness=Completeness(status="partial", missing_fields=["legacy_normalized_semantics"]),
            provenance=DiscoveryProvenance(
                source_type="legacy_entity_registry",
                source_ref=f"adrs/entities/registry.yaml#{entity.entity_id}",
                extraction_phase="entity_validator._legacy_registry_to_model",
                classification="derived",
                generator="entity-validator",
            ),
        )

    def _legacy_relationships(self, entities: list[NormalizedEntity]) -> list[RelationshipRecord]:
        known_ids = {entity.id for entity in entities}
        relationships: list[RelationshipRecord] = []
        for entity in entities:
            relationships.extend(
                self._relationship_records_for_targets(
                    entity=entity,
                    relationship_type="declared_in",
                    targets=list(entity.relationships.declared_in),
                    known_ids=known_ids,
                )
            )
            relationships.extend(
                self._relationship_records_for_targets(
                    entity=entity,
                    relationship_type="related_to",
                    targets=list(entity.relationships.related_to),
                    known_ids=known_ids,
                )
            )
            relationships.extend(
                self._relationship_records_for_targets(
                    entity=entity,
                    relationship_type="enables",
                    targets=list(entity.relationships.enables),
                    known_ids=known_ids,
                )
            )
            relationships.extend(
                self._relationship_records_for_targets(
                    entity=entity,
                    relationship_type="enforces",
                    targets=list(entity.relationships.enforces),
                    known_ids=known_ids,
                )
            )
        return sorted(relationships, key=lambda item: item.relationship_id)

    def _relationship_records_for_targets(
        self,
        *,
        entity: NormalizedEntity,
        relationship_type: str,
        targets: list[str],
        known_ids: set[str],
    ) -> list[RelationshipRecord]:
        records: list[RelationshipRecord] = []
        for target in sorted(set(targets)):
            if target not in known_ids and not target.startswith("ADR-"):
                continue
            records.append(
                RelationshipRecord(
                    relationship_id=f"{relationship_type}:{entity.id}:{target}",
                    relationship_type=relationship_type,
                    from_entity_id=entity.id,
                    to_entity_id=target,
                    provenance_classification="derived",
                    evidence=[f"Adapted from legacy entity registry for {entity.id}"],
                    canonical_source_ref=entity.canonical_source.source_ref,
                    confidence=1.0,
                )
            )
        return records
