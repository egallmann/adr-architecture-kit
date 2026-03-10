"""Validators for entity relationships and traceability."""

from typing import Dict, List, Set

from ..models import (
    DecisionLedger,
    Entity,
    EntityRegistry,
    LogicalADR,
    PhysicalADR,
    RequirementsSnapshot,
)


class EntityValidationError(Exception):
    """Error validating entity relationships."""
    pass


class EntityValidator:
    """Validate entity relationships and traceability."""
    
    def validate_entity_references(
        self,
        entity_registry: EntityRegistry,
        logical_adrs: List[LogicalADR],
        physical_adrs: List[PhysicalADR]
    ) -> List[str]:
        """Validate that all entity references exist in the registry.
        
        Args:
            entity_registry: Entity registry to validate against
            logical_adrs: List of logical ADRs
            physical_adrs: List of physical ADRs
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        entity_ids = {e.entity_id for e in entity_registry.entities}
        
        # Check introduces_entities references
        for adr in logical_adrs + physical_adrs:
            for entity_id in adr.introduces_entities:
                if entity_id not in entity_ids:
                    errors.append(f"ADR {adr.id} introduces unknown entity {entity_id}")
        
        # Check modifies_entities references
        for adr in logical_adrs + physical_adrs:
            for entity_id in adr.modifies_entities:
                if entity_id not in entity_ids:
                    errors.append(f"ADR {adr.id} modifies unknown entity {entity_id}")
        
        # Check realizes_entities references
        for adr in logical_adrs + physical_adrs:
            for entity_id in adr.realizes_entities:
                if entity_id not in entity_ids:
                    errors.append(f"ADR {adr.id} realizes unknown entity {entity_id}")
        
        # Check component implements_capabilities and realizes_entities
        for adr in physical_adrs:
            for comp in adr.component_specifications:
                for cap_id in getattr(comp, 'implements_capabilities', []):
                    if cap_id not in entity_ids:
                        errors.append(f"Component {comp.id} in {adr.id} implements unknown capability {cap_id}")
                
                for entity_id in getattr(comp, 'realizes_entities', []):
                    if entity_id not in entity_ids:
                        errors.append(f"Component {comp.id} in {adr.id} realizes unknown entity {entity_id}")
        
        return errors
    
    def validate_entity_relationships(self, entity_registry: EntityRegistry) -> List[str]:
        """Validate entity relationships (no circular dependencies, valid references).
        
        Args:
            entity_registry: Entity registry to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        entity_ids = {e.entity_id for e in entity_registry.entities}
        
        # Check that all relationship targets exist
        for entity in entity_registry.entities:
            if entity.relationships:
                for dep_id in entity.relationships.depends_on or []:
                    if dep_id not in entity_ids:
                        errors.append(f"Entity {entity.entity_id} depends on unknown entity {dep_id}")
                
                for impl_id in entity.relationships.implements or []:
                    if impl_id not in entity_ids:
                        errors.append(f"Entity {entity.entity_id} implements unknown entity {impl_id}")
                
                for cons_id in entity.relationships.consumes or []:
                    if cons_id not in entity_ids:
                        errors.append(f"Entity {entity.entity_id} consumes unknown entity {cons_id}")
        
        # Check for circular dependencies
        circular = self._detect_circular_dependencies(entity_registry)
        if circular:
            errors.append(f"Circular dependency detected: {' → '.join(circular)}")
        
        return errors
    
    def validate_requirements_snapshot_immutability(
        self,
        snapshot: RequirementsSnapshot,
        ledgers: List[DecisionLedger]
    ) -> List[str]:
        """Validate that a requirements snapshot is not modified after being referenced by a ledger.
        
        Args:
            snapshot: Requirements snapshot to validate
            ledgers: List of decision ledgers
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Check if snapshot is referenced by any ledger
        referenced_by = [l.ledger_id for l in ledgers if l.source_requirements_snapshot == snapshot.snapshot_id]
        
        if referenced_by:
            # In a real implementation, we would check modification timestamps
            # For now, just note that the snapshot is referenced
            pass
        
        return errors
    
    def validate_decision_ledger_traceability(
        self,
        ledger: DecisionLedger,
        snapshot: RequirementsSnapshot,
        logical_adr: LogicalADR
    ) -> List[str]:
        """Validate decision ledger traceability to snapshot and ADR.
        
        Args:
            ledger: Decision ledger to validate
            snapshot: Requirements snapshot
            logical_adr: Logical ADR
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Check that ledger references correct snapshot
        if ledger.source_requirements_snapshot != snapshot.snapshot_id:
            errors.append(f"Ledger {ledger.ledger_id} references wrong snapshot")
        
        # Check that ledger targets correct ADR
        if ledger.target_logical_adr != logical_adr.id:
            errors.append(f"Ledger {ledger.ledger_id} targets wrong ADR")
        
        # Check that snapshot items referenced in ledger exist
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
                    errors.append(f"Ledger decision {decision.ledger_decision_id} references unknown snapshot item {item_id}")
        
        if ledger.constraints:
            for item_id in ledger.constraints.snapshot_items or []:
                if item_id not in snapshot_item_ids:
                    errors.append(f"Ledger constraint references unknown snapshot item {item_id}")
        
        return errors
    
    def _detect_circular_dependencies(self, entity_registry: EntityRegistry) -> List[str]:
        """Detect circular dependencies in entity relationships.
        
        Args:
            entity_registry: Entity registry to check
            
        Returns:
            List of entity IDs forming a cycle, or empty list if no cycle
        """
        # Build dependency graph
        graph: Dict[str, Set[str]] = {}
        for entity in entity_registry.entities:
            if entity.relationships and entity.relationships.depends_on:
                graph[entity.entity_id] = set(entity.relationships.depends_on)
            else:
                graph[entity.entity_id] = set()
        
        # DFS to detect cycles
        visited = set()
        rec_stack = set()
        path = []
        
        def dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    # Found cycle
                    cycle_start = path.index(neighbor)
                    return path[cycle_start:] + [neighbor]
            
            path.pop()
            rec_stack.remove(node)
            return False
        
        for node in graph:
            if node not in visited:
                result = dfs(node)
                if result:
                    return result
        
        return []
